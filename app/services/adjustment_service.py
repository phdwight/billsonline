"""Adjustment service - business logic for component adjustments.

Follows Single Responsibility Principle: handles adjustment validation
and processing separate from routes and data access.
"""
from __future__ import annotations

from typing import Dict, List, Any, Optional, Tuple

from ..models import BillComponent
from ..repositories import (
    MonthlyBillRepository,
    ParticipantRepository,
    MeterReadingRepository,
    BillComponentRepository,
    ComponentAdjustmentRepository,
    MonthParticipantRepository,
)


class AdjustmentService:
    """Service class for component adjustment business logic."""

    # pylint: disable=too-many-arguments
    def __init__(
        self,
        bill_repo: MonthlyBillRepository | None = None,
        participants_repo: ParticipantRepository | None = None,
        reading_repo: MeterReadingRepository | None = None,
        component_repo: BillComponentRepository | None = None,
        comp_adjust_repo: ComponentAdjustmentRepository | None = None,
        month_part_repo: MonthParticipantRepository | None = None,
    ):
        """Initialize with injected dependencies (or defaults)."""
        self.bill_repo = bill_repo or MonthlyBillRepository()
        self.participants_repo = participants_repo or ParticipantRepository()
        self.reading_repo = reading_repo or MeterReadingRepository()
        self.component_repo = component_repo or BillComponentRepository()
        self.comp_adjust_repo = comp_adjust_repo or ComponentAdjustmentRepository()
        self.month_part_repo = month_part_repo or MonthParticipantRepository()

    def validate_redistribution_rule(
        self,
        comp: BillComponent,
        pid: int,
        rule: Dict[str, Any],
        participant_name: str,
        base_amount: float,
    ) -> Tuple[bool, Optional[str]]:
        """Validate a redistribution rule.

        Args:
            comp: The component being adjusted
            pid: The participant ID whose share is being redistributed
            rule: The redistribution rule dict with 'mode' and 'targets'
            participant_name: Name for error messages
            base_amount: The base contribution amount for this participant

        Returns:
            Tuple of (is_valid, error_message)
        """
        if not rule or not isinstance(rule, dict):
            return True, None

        mode = rule.get('mode')
        targets = rule.get('targets') or {}

        try:
            vals = [float(v) for v in targets.values()]
        except (TypeError, ValueError):
            vals = []

        if mode == 'percent':
            tot = sum(vals)
            if abs(tot - 100.0) > 0.01:
                msg = f"{comp.name}: {participant_name}'s redistribution must sum to 100%"
                return False, f"{msg} (currently {tot:.2f}%)"
        elif mode == 'amount':
            tot = sum(vals)
            if abs(tot - float(base_amount)) > 0.01:
                msg = f"{comp.name}: {participant_name}'s redistribution must sum to"
                return False, f"{msg} ₱{base_amount:.2f} (currently ₱{tot:.2f})"

        return True, None

    def compute_base_amount(
        self,
        comp: BillComponent,
        pid: int,
        pids: List[int],
        usage_by_pid: Dict[int, float],
        total_usage: float,
    ) -> float:
        """Compute the base contribution amount for a participant on a component.

        Args:
            comp: The bill component
            pid: The participant ID
            pids: List of all member participant IDs
            usage_by_pid: Dict mapping participant ID to usage
            total_usage: Total usage across all participants

        Returns:
            The base contribution amount
        """
        if comp.split_method == 'equal':
            return (comp.amount / len(pids)) if pids else 0.0

        u = usage_by_pid.get(pid, 0.0)
        return (comp.amount * (u / total_usage)) if total_usage > 0 else 0.0

    def process_adjustments(
        self,
        bill_id: int,
        form_data: Dict[str, Any],
    ) -> Tuple[bool, str, int]:
        """Process and save component adjustments from form data.

        Args:
            bill_id: The bill/month ID
            form_data: Dict-like form data

        Returns:
            Tuple of (success, message, saved_rules_count)
        """
        bill = self.bill_repo.get_by_id(bill_id)
        if not bill:
            return False, "Month not found", 0

        if bill.archived:
            return False, "This month is archived. Unarchive to make changes.", 0

        participants = self.participants_repo.list_all()
        member_ids = {m.participant_id for m in self.month_part_repo.list_for_month(bill.id)}
        if not member_ids:
            member_ids = {p.id for p in participants}

        pids = [p.id for p in participants if p.id in member_ids]
        components = self.component_repo.list_for_month(bill.id)
        readings = self.reading_repo.list_for_month(bill.id)
        usage_by_pid = {r.participant_id: r.usage() for r in readings}
        total_usage = sum(usage_by_pid.values())

        saved_rules = 0
        errors = []

        for comp in components:
            for pid in pids:
                zero = False
                rule = None

                # Parse mode and targets from form
                mode = form_data.get(f"mode_comp_{comp.id}_{pid}")
                targets = {}

                for tpid in pids:
                    raw = form_data.get(f"redis_comp_{comp.id}_{pid}_{tpid}")
                    if raw is None or raw == "":
                        continue
                    try:
                        val = float(raw)
                    except ValueError:
                        continue
                    if val > 0:
                        targets[tpid] = val

                if targets and mode in ("percent", "amount"):
                    rule = {"mode": mode, "targets": targets}

                # Get notes from form
                notes = form_data.get(f"notes_comp_{comp.id}_{pid}", "").strip() or None

                # Validate rule
                if rule:
                    name = next((p.name for p in participants if p.id == pid), str(pid))
                    base_amount = self.compute_base_amount(comp, pid, pids, usage_by_pid, total_usage)
                    ok, err = self.validate_redistribution_rule(comp, pid, rule, name, base_amount)
                    if not ok:
                        errors.append(err)
                        rule = None

                if rule:
                    zero = True

                self.comp_adjust_repo.upsert(bill.id, comp.id, pid, zero=zero, redis_rule=rule, notes=notes)
                if rule:
                    saved_rules += 1

        if errors:
            return False, errors[0], saved_rules

        if saved_rules:
            return True, f"Component adjustments saved ({saved_rules} redistribution rule(s) updated)", saved_rules

        return True, "Component adjustments saved", saved_rules
