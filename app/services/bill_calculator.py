from __future__ import annotations

from typing import Dict, List, Iterable

from pydantic import BaseModel, ConfigDict, computed_field

from ..models import MonthlyBill, MeterReading, Participant, BillComponent, ComponentAdjustment


class DynamicContribution(BaseModel):
    """Pydantic model for participant contribution data."""
    model_config = ConfigDict(arbitrary_types_allowed=True)

    participant: Participant
    components: Dict[str, float]

    @computed_field
    @property
    def total(self) -> float:
        return round(sum(self.components.values()), 2)


class BillCalculator:
    # ========================= Dynamic components API =========================

    # pylint: disable=too-many-arguments,too-many-branches
    def compute_contributions_dynamic(
        self,
        bill: MonthlyBill,
        components: List[BillComponent],
        readings: List[MeterReading],
        participants: List[Participant],
        component_adjustments: Iterable[ComponentAdjustment] | None = None,
    ) -> List[DynamicContribution]:
        """Compute contributions for arbitrary components.

        components: BillComponent objects with amount and split_method.
        component_adjustments: ComponentAdjustment entries per (component_id, participant_id)
            with zero flag and optional redis_rule.
        Returns list of DynamicContribution preserving per-component columns by name.
        """
        if not participants or not components:
            return [
                DynamicContribution(participant=p, components={})
                for p in participants
            ]

        # Prepare lookups
        usage_by_pid: Dict[int, float] = {r.participant_id: r.usage() for r in readings}
        total_usage = sum(usage_by_pid.values())

        adjs_by_comp: Dict[int, Dict[int, ComponentAdjustment]] = {}
        if component_adjustments:
            for adj in component_adjustments:
                adjs_by_comp.setdefault(adj.component_id, {})[adj.participant_id] = adj

        # Compute per-component amounts per participant
        per_comp_amounts: Dict[int, Dict[str, float]] = {p.id: {} for p in participants}

        for comp in sorted(components, key=lambda c: (c.position or 0, c.id)):
            # Base map for this component
            base_map: Dict[int, float] = {}
            if comp.split_method == 'usage':
                for p in participants:
                    u = usage_by_pid.get(p.id, 0.0)
                    share = (comp.amount * (u / total_usage)) if total_usage > 0 else 0.0
                    base_map[p.id] = share
            elif comp.split_method == 'equal':  # equal
                equal_share = (comp.amount / len(participants)) if participants else 0.0
                for p in participants:
                    base_map[p.id] = equal_share
            elif comp.split_method == 'percentage':
                # distribution: {participant_id: percent}
                dist = getattr(comp, 'distribution', None) or {}
                # Allow sum not exactly 100 by normalizing
                try:
                    total_pct = sum(float(dist.get(str(p.id), dist.get(p.id, 0)) or 0) for p in participants)
                except Exception:
                    total_pct = 0.0
                for p in participants:
                    pct = float(dist.get(str(p.id), dist.get(p.id, 0)) or 0)
                    share = comp.amount * (pct / (total_pct if total_pct > 0 else 100.0))
                    base_map[p.id] = share
            elif comp.split_method == 'amount':
                # distribution: {participant_id: amount}
                dist = getattr(comp, 'distribution', None) or {}
                for p in participants:
                    try:
                        base_map[p.id] = float(dist.get(str(p.id), dist.get(p.id, 0)) or 0)
                    except Exception:
                        base_map[p.id] = 0.0
            else:
                # Unknown method -> treat as equal
                equal_share = (comp.amount / len(participants)) if participants else 0.0
                for p in participants:
                    base_map[p.id] = equal_share

            # Apply zero and redistribution for this component
            final_map = self._apply_component_adjustments_dynamic(
                component=comp,
                base_map=base_map,
                adjustments_for_component=adjs_by_comp.get(comp.id, {}),
            )

            # Round and store by component name
            for p in participants:
                per_comp_amounts[p.id][comp.name] = round(final_map.get(p.id, 0.0), 2)

        # Build DynamicContribution objects
        dyn_contribs: List[DynamicContribution] = []
        for p in participants:
            dyn_contribs.append(
                DynamicContribution(participant=p, components=per_comp_amounts.get(p.id, {}))
            )
        return dyn_contribs

    def _apply_component_adjustments_dynamic(
        self,
        component: BillComponent,
        base_map: Dict[int, float],
        adjustments_for_component: Dict[int, ComponentAdjustment],
    ) -> Dict[int, float]:
        """Return adjusted amounts per participant for one component. Preserves total after rounding.
        adjustments_for_component: map of participant_id -> ComponentAdjustment
        """
        # start with base amounts (unrounded for distribution math)
        amounts = dict(base_map)

        # Collect participants to redistribute (explicit zero or any rule implies zeroing own share)
        zeros = {
            pid
            for pid, adj in adjustments_for_component.items()
            if getattr(adj, 'zero', False) or getattr(adj, 'redis_rule', None)
        }
        zeroed_total = sum(base_map.get(pid, 0.0) for pid in zeros)
        for pid in zeros:
            amounts[pid] = 0.0

        remaining_ids = [pid for pid, amt in amounts.items() if amt > 0]

        allocated = 0.0
        # Apply per-zeroed custom rules
        for zpid in zeros:
            adj = adjustments_for_component.get(zpid)
            rule = getattr(adj, 'redis_rule', None) if adj else None
            if isinstance(rule, dict) and 'mode' in rule and 'targets' in rule:
                mode = rule.get('mode')
                targets = rule.get('targets') or {}
                base_amount = base_map.get(zpid, 0.0)
                to_distribute = base_amount
                if mode == 'percent':
                    allocated += self._allocate_percent(to_distribute, targets, remaining_ids, amounts)
                elif mode == 'amount':
                    allocated += self._allocate_amount(to_distribute, targets, remaining_ids, amounts)

        # Distribute leftover equally
        self._distribute_leftover(zeroed_total, allocated, remaining_ids, amounts)

        # Rounding correction: ensure sum equals component.amount (rounded to cents)
        rounded = {pid: round(val, 2) for pid, val in amounts.items()}
        target_total = round(sum(base_map.values()), 2)
        current_total = round(sum(rounded.values()), 2)
        delta = round(target_total - current_total, 2)
        if abs(delta) >= 0.01:
            candidates = [pid for pid in remaining_ids if rounded.get(pid, 0.0) > 0]
            if candidates:
                adjust_pid = max(candidates, key=lambda pid: rounded.get(pid, 0.0))
                rounded[adjust_pid] = max(0.0, round(rounded[adjust_pid] + delta, 2))

        return rounded

    # Contributions are handled exclusively via dynamic components.

    def _allocate_percent(
        self,
        to_distribute: float,
        targets: Dict,
        remaining_ids: List[int],
        amounts: Dict[int, float]
    ) -> float:
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

    def _allocate_amount(
        self,
        to_distribute: float,
        targets: Dict,
        remaining_ids: List[int],
        amounts: Dict[int, float]
    ) -> float:
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

    def _distribute_leftover(
        self,
        zeroed_total: float,
        allocated: float,
        remaining_ids: List[int],
        amounts: Dict[int, float]
    ) -> None:
        leftover = max(0.0, zeroed_total - allocated)
        if leftover > 0 and remaining_ids:
            equal_increment = leftover / len(remaining_ids)
            for pid in remaining_ids:
                amounts[pid] += equal_increment
