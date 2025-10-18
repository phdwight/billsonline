from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, List

from .models import MonthlyBill, MeterReading, Participant


@dataclass(frozen=True)
class Contribution:
    participant: Participant
    electricity: float
    water: float
    internet: float

    @property
    def total(self) -> float:
        return self.electricity + self.water + self.internet


class BillCalculator:
    def compute_contributions(self, bill: MonthlyBill, readings: List[MeterReading], participants: List[Participant]) -> List[Contribution]:
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

        # Internet divided evenly among included only
        internet_participants = [p for p in participants if p.include_in_internet]
        internet_share = (bill.internet_amount / len(internet_participants)) if internet_participants else 0.0

        contributions: List[Contribution] = []
        for p in participants:
            contributions.append(
                Contribution(
                    participant=p,
                    electricity=round(electricity_shares.get(p.id, 0.0), 2),
                    water=round(water_share, 2),
                    internet=round(internet_share if p.include_in_internet else 0.0, 2),
                )
            )

        return contributions
