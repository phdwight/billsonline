"""Month service - business logic for month/bill operations.

Follows Single Responsibility Principle: handles all month-related business logic
separate from route handling and data access.
"""
from __future__ import annotations

from typing import Dict, List, Any

from ..models import MonthlyBill, BillComponent, Participant
from ..repositories import (
    MonthlyBillRepository,
    ParticipantRepository,
    MeterReadingRepository,
    BillComponentRepository,
    ComponentAdjustmentRepository,
    ComponentImageRepository,
    MonthParticipantRepository,
)
from .bill_calculator import BillCalculator, VALID_SPLIT_METHODS


class MonthService:
    """Service class for month-related business logic."""

    # pylint: disable=too-many-arguments
    def __init__(
        self,
        bill_repo: MonthlyBillRepository | None = None,
        participants_repo: ParticipantRepository | None = None,
        reading_repo: MeterReadingRepository | None = None,
        component_repo: BillComponentRepository | None = None,
        comp_adjust_repo: ComponentAdjustmentRepository | None = None,
        month_part_repo: MonthParticipantRepository | None = None,
        calculator: BillCalculator | None = None,
    ):
        """Initialize with injected dependencies (or defaults)."""
        self.bill_repo = bill_repo or MonthlyBillRepository()
        self.participants_repo = participants_repo or ParticipantRepository()
        self.reading_repo = reading_repo or MeterReadingRepository()
        self.component_repo = component_repo or BillComponentRepository()
        self.comp_adjust_repo = comp_adjust_repo or ComponentAdjustmentRepository()
        self.month_part_repo = month_part_repo or MonthParticipantRepository()
        self.calculator = calculator or BillCalculator()

    def get_month_detail_data(self, bill_id: int) -> Dict[str, Any]:
        """Get all data needed for the month detail view.

        Returns a dictionary with all the data needed to render the month detail template,
        or None if the bill doesn't exist.
        """
        bill = self.bill_repo.get_by_id(bill_id)
        if not bill:
            return None

        participants = self.participants_repo.list_all()
        month_members = self.month_part_repo.list_for_month(bill.id)
        member_ids = {m.participant_id for m in month_members}

        # Backfill default membership for legacy months
        if not member_ids and participants:
            try:
                for p in participants:
                    self.month_part_repo.add(bill.id, p.id)
                member_ids = {p.id for p in participants}
            except Exception:
                member_ids = {p.id for p in participants}

        readings = self.reading_repo.list_for_month(bill.id)
        readings_by_pid = {r.participant_id: r for r in readings}

        # Pre-fill previous readings from previous month
        prev_bill = self.bill_repo.get_previous(bill.year, bill.month)
        prev_readings_map = {}
        if prev_bill:
            prev_readings = self.reading_repo.list_for_month(prev_bill.id)
            prev_readings_map = {r.participant_id: r.reading_current for r in prev_readings}

        # Dynamic components
        components = self.component_repo.list_for_month(bill.id)
        dynamic_contributions = None
        comp_adjustments_map = {}
        dynamic_base_maps = {}

        if components:
            comp_adjs = self.comp_adjust_repo.list_for_month(bill.id)
            for a in comp_adjs:
                comp_adjustments_map.setdefault(a.component_id, {})[a.participant_id] = {
                    'zero': bool(a.zero),
                    'rule': a.redis_rule or None,
                    'notes': a.notes or None,
                }

            usage_by_pid = {r.participant_id: r.usage() for r in readings}
            total_usage = sum(usage_by_pid.values())
            member_participants = [p for p in participants if not member_ids or p.id in member_ids]

            for comp in components:
                base_map = self._compute_base_map(comp, member_participants, usage_by_pid, total_usage)
                dynamic_base_maps[comp.id] = base_map

            dynamic_contributions = self.calculator.compute_contributions_dynamic(
                bill=bill,
                components=components,
                readings=readings,
                participants=member_participants,
                component_adjustments=comp_adjs,
            )

        component_image_ids = ComponentImageRepository().component_ids_with_image(
            [c.id for c in components]
        )

        # Raw usage-based split, before any adjustments/redistribution:
        # each member's share of the usage-split components (typically
        # Electricity), plus the effective rate per kWh.
        member_participants = [p for p in participants if not member_ids or p.id in member_ids]
        usage_by_pid = {r.participant_id: r.usage() for r in readings}
        total_usage = sum(usage_by_pid.get(p.id, 0.0) for p in member_participants)
        usage_split_total = sum(
            float(c.amount or 0) for c in components if c.split_method == 'usage'
        )
        usage_share_base = {
            p.id: (usage_split_total * (usage_by_pid.get(p.id, 0.0) / total_usage))
            if total_usage > 0 else 0.0
            for p in member_participants
        }
        usage_rate = (usage_split_total / total_usage) if total_usage > 0 and usage_split_total > 0 else None

        return {
            'bill': bill,
            'participants': participants,
            'component_image_ids': component_image_ids,
            'member_ids': member_ids,
            'readings': readings,
            'readings_by_pid': readings_by_pid,
            'prev_readings_map': prev_readings_map,
            'contributions': None,
            'components': components,
            'dynamic_contributions': dynamic_contributions,
            'comp_adjustments': comp_adjustments_map,
            'dynamic_base_maps': dynamic_base_maps,
            'usage_share_base': usage_share_base,
            'usage_split_total': usage_split_total,
            'usage_rate': usage_rate,
            'adjustments': {},
            'participant_name_by_id': {p.id: p.name for p in participants},
            'base_electricity_map': {},
            'base_water_share': 0.0,
            'base_internet_share': 0.0,
            'total_bill': 0.0,
        }

    def _compute_base_map(
        self,
        comp: BillComponent,
        participants: List[Participant],
        usage_by_pid: Dict[int, float],
        total_usage: float,
    ) -> Dict[int, float]:
        """Compute base contribution map for a component."""
        base_map = {}
        if comp.split_method == 'usage':
            for p in participants:
                u = usage_by_pid.get(p.id, 0.0)
                base_map[p.id] = (comp.amount * (u / total_usage)) if total_usage > 0 else 0.0
        else:
            share = (comp.amount / len(participants)) if participants else 0.0
            for p in participants:
                base_map[p.id] = share
        return base_map

    # pylint: disable=too-many-arguments
    def create_month_with_components(
        self,
        year: int,
        month: int,
        electricity_amount: float,
        water_amount: float,
        internet_amount: float,
        component_data: List[Dict[str, Any]],
        legacy_splits: Dict[str, str],
        legacy_distributions: Dict[str, Dict[int, float]],
        participants: List[Participant],
    ) -> MonthlyBill:
        """Create a new month with its components.

        Args:
            year: The year
            month: The month (1-12)
            electricity_amount: Legacy electricity amount
            water_amount: Legacy water amount
            internet_amount: Legacy internet amount
            component_data: List of component dictionaries with name, amount, split, position, distribution
            legacy_splits: Dict mapping legacy field to split method
            legacy_distributions: Dict mapping legacy field to distribution
            participants: List of participants to add as members

        Returns:
            The created MonthlyBill
        """
        bill = self.bill_repo.create(year, month, electricity_amount, water_amount, internet_amount)

        # Default membership: include all current participants
        try:
            for p in participants:
                self.month_part_repo.add(bill.id, p.id)
        except Exception:
            pass

        # Create dynamic components
        for comp in component_data:
            name = comp.get('name', '').strip()
            if not name:
                continue
            try:
                self.component_repo.add(
                    bill.id,
                    name=name,
                    amount=comp.get('amount', 0.0),
                    split_method=comp.get('split', 'equal'),
                    position=comp.get('position', 0),
                    distribution=comp.get('distribution'),
                )
            except Exception:
                pass

        # Create default components for legacy fields
        legacy_defs = [
            ("Electricity", electricity_amount, legacy_splits.get('electricity', 'usage'), 0,
             legacy_distributions.get('electricity')),
            ("Water", water_amount, legacy_splits.get('water', 'equal'), 1,
             legacy_distributions.get('water')),
            ("Internet", internet_amount, legacy_splits.get('internet', 'equal'), 2,
             legacy_distributions.get('internet')),
        ]

        for (nm, amt, sp, pos, dist) in legacy_defs:
            if amt and amt > 0:
                try:
                    self.component_repo.add(
                        bill.id,
                        name=nm,
                        amount=amt,
                        split_method=sp if sp in VALID_SPLIT_METHODS else "equal",
                        position=pos,
                        distribution=(dist or None),
                    )
                except Exception:
                    pass

        return bill

    def convert_legacy_to_components(self, bill_id: int) -> tuple[bool, str]:
        """Convert legacy bill amounts to components.

        Returns (success, message) tuple.
        """
        bill = self.bill_repo.get_by_id(bill_id)
        if not bill:
            return False, "Month not found"

        if bill.archived:
            return False, "This month is archived. Unarchive to make changes."

        existing = self.component_repo.list_for_month(bill.id)
        if existing:
            return False, "This month already has components."

        position = 0
        if bill.electricity_amount and bill.electricity_amount > 0:
            self.component_repo.add(bill.id, name="Electricity",
                                    amount=float(bill.electricity_amount),
                                    split_method="usage", position=position)
            position += 1
        if bill.water_amount and bill.water_amount > 0:
            self.component_repo.add(bill.id, name="Water",
                                    amount=float(bill.water_amount),
                                    split_method="equal", position=position)
            position += 1
        if bill.internet_amount and bill.internet_amount > 0:
            self.component_repo.add(bill.id, name="Internet",
                                    amount=float(bill.internet_amount),
                                    split_method="equal", position=position)
            position += 1

        if position == 0:
            return False, "No legacy amounts found to convert."

        return True, "Legacy amounts converted to components."
