from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, List

from .models import MonthlyBill, MeterReading, Participant


@dataclass
class Contribution:
    participant: Participant
    electricity: float
    water: float
    internet: float

    @property
    def total(self) -> float:
        return self.electricity + self.water + self.internet


class BillCalculator:
    def compute_contributions(self, bill: MonthlyBill, readings: List[MeterReading], participants: List[Participant], adjustments: Dict[int, Dict[str, bool]] | None = None) -> List[Contribution]:
        """Compute contributions.
        adjustments: mapping participant_id -> { 'electricity': True/False, 'water': True/False, 'internet': True/False } meaning zero this component.
        """
        # Electricity by usage share
        usage_by_pid: Dict[int, float] = {r.participant_id: r.usage() for r in readings}
        total_usage = sum(usage_by_pid.values())
        electricity_shares: Dict[int, float] = {}
        for p in participants:
            u = usage_by_pid.get(p.id, 0.0)
            share = (bill.electricity_amount * (u / total_usage)) if total_usage > 0 else 0.0
            electricity_shares[p.id] = share

        # Water divided evenly among all participants with any presence
        active_participants = [p for p in participants]
        water_share = (bill.water_amount / len(active_participants)) if active_participants else 0.0

        # Internet divided evenly among all participants (exclusions handled via adjustments)
        internet_participants = [p for p in participants]
        internet_share = (bill.internet_amount / len(internet_participants)) if internet_participants else 0.0

        contributions: List[Contribution] = []
        for p in participants:
            contributions.append(
                Contribution(
                    participant=p,
                    electricity=round(electricity_shares.get(p.id, 0.0), 2),
                    water=round(water_share, 2),
                    internet=round(internet_share, 2),
                )
            )

        # Apply zero-out adjustments and redistribute
        adjustments = adjustments or {}

        def redistribute(component: str, total_amount: float):
            # Build current shares vector and zero-out marked participants
            amounts = {c.participant.id: getattr(c, component) for c in contributions}
            zeros = {pid for pid, flags in adjustments.items() if flags.get(component, False)}
            zeroed_total = sum(amounts.get(pid, 0.0) for pid in zeros)
            for pid in zeros:
                amounts[pid] = 0.0
            # Compute remaining eligible participants (those with non-zero base share)
            remaining_ids = [pid for pid, amt in amounts.items() if amt > 0]
            # Redistribute zeroed total equally among remaining eligible participants
            if zeroed_total > 0 and remaining_ids:
                equal_increment = zeroed_total / len(remaining_ids)
                for pid in remaining_ids:
                    amounts[pid] += equal_increment
            # Write back
            for c in contributions:
                setattr(c, component, round(amounts.get(c.participant.id, 0.0), 2))

        redistribute("electricity", bill.electricity_amount)
        redistribute("water", bill.water_amount)
        redistribute("internet", bill.internet_amount)

        return contributions
