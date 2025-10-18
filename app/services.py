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
    def compute_contributions(self, bill: MonthlyBill, readings: List[MeterReading], participants: List[Participant], adjustments: Dict[int, Dict[str, object]] | None = None) -> List[Contribution]:
        """Compute contributions and apply adjustments.
        adjustments: mapping participant_id -> {
          '<comp>': True/False (zero flag), and optionally
          'redis_<comp>': { 'mode': 'percent'|'amount', 'targets': { pid: value, ... } }
        }
        """
        # 1) Compute base shares per component
        electricity_shares, water_share, internet_share = self._compute_base_shares(bill, readings, participants)

        # 2) Initialize contributions from base shares
        contributions: List[Contribution] = [
            Contribution(
                participant=p,
                electricity=round(electricity_shares.get(p.id, 0.0), 2),
                water=round(water_share, 2),
                internet=round(internet_share, 2),
            )
            for p in participants
        ]

        # 3) Apply zero-out and custom redistribution per component
        adjustments = adjustments or {}
        # Build base maps for components
        water_map = {p.id: water_share for p in participants}
        internet_map = {p.id: internet_share for p in participants}
        self._redistribute_component('electricity', contributions, electricity_shares, adjustments)
        self._redistribute_component('water', contributions, water_map, adjustments)
        self._redistribute_component('internet', contributions, internet_map, adjustments)

        return contributions

    def _compute_base_shares(self, bill: MonthlyBill, readings: List[MeterReading], participants: List[Participant]):
        """Return (electricity_shares map, water_share value, internet_share value)."""
        usage_by_pid: Dict[int, float] = {r.participant_id: r.usage() for r in readings}
        total_usage = sum(usage_by_pid.values())
        electricity_shares: Dict[int, float] = {}
        for p in participants:
            u = usage_by_pid.get(p.id, 0.0)
            share = (bill.electricity_amount * (u / total_usage)) if total_usage > 0 else 0.0
            electricity_shares[p.id] = share
        water_share = (bill.water_amount / len(participants)) if participants else 0.0
        internet_share = (bill.internet_amount / len(participants)) if participants else 0.0
        return electricity_shares, water_share, internet_share

    def _redistribute_component(self, component: str, contributions: List[Contribution], base_map: Dict[int, float], adjustments: Dict[int, Dict[str, object]]):
        """Apply zero-out flags and custom redistribution rules for a single component."""
        amounts, zeros, zeroed_total, remaining_ids = self._prepare_amounts(component, contributions, base_map, adjustments)
        if zeroed_total > 0 and remaining_ids:
            allocated = 0.0
            for zpid in zeros:
                allocated += self._apply_rule_for_zeroed(component, zpid, base_map, adjustments, remaining_ids, amounts)
            # Any leftover distributes equally among remaining
            self._distribute_leftover(zeroed_total, allocated, remaining_ids, amounts)
            # Correct rounding drift to preserve total after rounding
            rounded = {pid: round(val, 2) for pid, val in amounts.items()}
            target_total = round(sum(base_map.values()), 2)
            current_total = round(sum(rounded.values()), 2)
            delta = round(target_total - current_total, 2)
            if abs(delta) >= 0.01:
                # adjust the participant with the largest current share among remaining_ids
                candidates = [pid for pid in remaining_ids if rounded.get(pid, 0.0) > 0]
                if candidates:
                    adjust_pid = max(candidates, key=lambda pid: rounded.get(pid, 0.0))
                    rounded[adjust_pid] = max(0.0, round(rounded[adjust_pid] + delta, 2))
                # write back rounded values
                for pid, val in rounded.items():
                    amounts[pid] = val
        # Write back rounded values
        for c in contributions:
            setattr(c, component, round(amounts.get(c.participant.id, 0.0), 2))

    def _prepare_amounts(self, component: str, contributions: List[Contribution], base_map: Dict[int, float], adjustments: Dict[int, Dict[str, object]]):
        amounts = {c.participant.id: getattr(c, component) for c in contributions}
        zeros = {pid for pid, flags in adjustments.items() if isinstance(flags, dict) and flags.get(component, False)}
        zeroed_total = sum(base_map.get(pid, 0.0) for pid in zeros)
        for pid in zeros:
            amounts[pid] = 0.0
        remaining_ids = [pid for pid, amt in amounts.items() if amt > 0]
        return amounts, zeros, zeroed_total, remaining_ids

    def _apply_rule_for_zeroed(self, component: str, zpid: int, base_map: Dict[int, float], adjustments: Dict[int, Dict[str, object]], remaining_ids: List[int], amounts: Dict[int, float]) -> float:
        flags = adjustments.get(zpid, {})
        rule = None
        if isinstance(flags, dict):
            rule = flags.get(f"redis_{component}")
        allocated = 0.0
        if rule and isinstance(rule, dict) and 'mode' in rule and 'targets' in rule:
            mode = rule.get('mode')
            targets = rule.get('targets') or {}
            base_amount = base_map.get(zpid, 0.0)
            to_distribute = base_amount
            if mode == 'percent':
                allocated += self._allocate_percent(to_distribute, targets, remaining_ids, amounts)
            elif mode == 'amount':
                allocated += self._allocate_amount(to_distribute, targets, remaining_ids, amounts)
        return allocated

    def _allocate_percent(self, to_distribute: float, targets: Dict, remaining_ids: List[int], amounts: Dict[int, float]) -> float:
        allocated = 0.0
        try:
            total_pct = sum(float(v) for v in targets.values())
        except (TypeError, ValueError):
            total_pct = 0.0
        if total_pct > 0:
            for tpid, pct in targets.items():
                try:
                    tpid_i = int(tpid)
                    pct_f = float(pct)
                except (TypeError, ValueError):
                    continue
                if tpid_i in remaining_ids:
                    inc = to_distribute * (pct_f / total_pct)
                    amounts[tpid_i] += inc
                    allocated += inc
        return allocated

    def _allocate_amount(self, to_distribute: float, targets: Dict, remaining_ids: List[int], amounts: Dict[int, float]) -> float:
        allocated = 0.0
        try:
            sum_vals = sum(float(v) for v in targets.values())
        except (TypeError, ValueError):
            sum_vals = 0.0
        if sum_vals > 0:
            norm = min(1.0, to_distribute / sum_vals)
            for tpid, val in targets.items():
                try:
                    tpid_i = int(tpid)
                    inc_val = float(val)
                except (TypeError, ValueError):
                    continue
                if tpid_i in remaining_ids:
                    inc = inc_val * norm
                    amounts[tpid_i] += inc
                    allocated += inc
        return allocated

    def _distribute_leftover(self, zeroed_total: float, allocated: float, remaining_ids: List[int], amounts: Dict[int, float]) -> None:
        leftover = max(0.0, zeroed_total - allocated)
        if leftover > 0 and remaining_ids:
            equal_increment = leftover / len(remaining_ids)
            for pid in remaining_ids:
                amounts[pid] += equal_increment
