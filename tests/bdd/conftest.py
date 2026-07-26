"""Shared pytest-bdd fixtures and common step definitions."""
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import pytest
from unittest.mock import Mock
from pytest_bdd import given, parsers
from dataclasses import dataclass, field
from typing import Dict, Any, Optional, List


# Simple data classes to avoid SQLAlchemy model issues
@dataclass
class MockParticipant:
    """Mock participant without SQLAlchemy dependencies."""
    id: int
    name: str


@dataclass
class MockBill:
    """Mock monthly bill without SQLAlchemy dependencies."""
    id: int
    year: int
    month: int
    electricity_amount: float
    water_amount: float
    internet_amount: float
    archived: bool = False


@dataclass
class MockComponent:
    """Mock bill component without SQLAlchemy dependencies."""
    id: int
    month_id: int
    name: str
    amount: float
    split_method: str
    position: int
    distribution: Optional[Dict[str, float]] = None


@dataclass
class MockReading:
    """Mock meter reading without SQLAlchemy dependencies."""
    month_id: int
    participant_id: int
    reading: int
    prev_reading: int

    def usage(self) -> int:
        if self.prev_reading is None:
            return 0
        return max(0, self.reading - self.prev_reading)


@dataclass
class MockAdjustment:
    """Mock component adjustment without SQLAlchemy dependencies."""
    id: int
    month_id: int
    component_id: int  # Keep for compatibility with calculator
    component_name: str
    from_participant_id: int
    to_participant_id: Optional[int]
    mode: str
    value: float
    participant_id: int = 0  # alias for from_participant_id for calculator compatibility
    zero: bool = False
    redis_rule: Optional[Dict[str, Any]] = None


@dataclass
class MockContribution:
    """Mock contribution result."""
    participant: MockParticipant
    components: Dict[str, float] = field(default_factory=dict)

    @property
    def total(self) -> float:
        return round(sum(self.components.values()), 2)


class MockCalculator:
    """Simple mock calculator for testing."""

    def compute_contributions_dynamic(
        self,
        bill,
        components: List,
        readings: List,
        participants: List,
        component_adjustments: List = None,
    ) -> List[MockContribution]:
        """Compute contributions using simple logic."""
        if not participants or not components:
            return [MockContribution(participant=p, components={}) for p in participants]

        # Build usage map
        usage_by_pid = {r.participant_id: r.usage() for r in readings}
        total_usage = sum(usage_by_pid.values())

        # Build adjustments map by component - store list of adjustments per component
        adjs_by_comp: Dict[int, List[MockAdjustment]] = {}
        if component_adjustments:
            for adj in component_adjustments:
                adjs_by_comp.setdefault(adj.component_id, []).append(adj)

        # Calculate per-participant, per-component amounts
        per_comp_amounts: Dict[int, Dict[str, float]] = {p.id: {} for p in participants}

        for comp in sorted(components, key=lambda c: (c.position or 0, c.id)):
            base_map: Dict[int, float] = {}

            if comp.split_method == 'usage':
                for p in participants:
                    u = usage_by_pid.get(p.id, 0.0)
                    share = (comp.amount * (u / total_usage)) if total_usage > 0 else 0.0
                    base_map[p.id] = share
            elif comp.split_method == 'equal':
                equal_share = comp.amount / len(participants) if participants else 0.0
                for p in participants:
                    base_map[p.id] = equal_share
            elif comp.split_method == 'percentage':
                dist = comp.distribution or {}
                total_pct = sum(float(dist.get(str(p.id), 0)) for p in participants)
                for p in participants:
                    pct = float(dist.get(str(p.id), 0))
                    share = comp.amount * (pct / (total_pct if total_pct > 0 else 100.0))
                    base_map[p.id] = share
            elif comp.split_method == 'amount':
                dist = comp.distribution or {}
                for p in participants:
                    base_map[p.id] = float(dist.get(str(p.id), 0))
            else:
                equal_share = comp.amount / len(participants) if participants else 0.0
                for p in participants:
                    base_map[p.id] = equal_share

            # Apply adjustments if any
            comp_adjs = adjs_by_comp.get(comp.id, [])
            final_map = self._apply_adjustments(base_map, comp_adjs, participants)

            for p in participants:
                per_comp_amounts[p.id][comp.name] = round(final_map.get(p.id, 0.0), 2)

        return [
            MockContribution(participant=p, components=per_comp_amounts.get(p.id, {}))
            for p in participants
        ]

    def _apply_adjustments(
        self,
        base_map: Dict[int, float],
        adjustments: List[MockAdjustment],
        participants: List
    ) -> Dict[int, float]:
        """Apply redistribution adjustments."""
        if not adjustments:
            return base_map

        final_map = dict(base_map)

        # Group adjustments by from_participant_id
        by_from: Dict[int, List[MockAdjustment]] = {}
        for adj in adjustments:
            by_from.setdefault(adj.from_participant_id, []).append(adj)

        # Identify all zeroed participants (those with untargeted 100% zero)
        zeroed_pids = set()
        for from_pid, adj_list in by_from.items():
            for adj in adj_list:
                if adj.mode == 'percent' and adj.value == 100.0 and adj.to_participant_id is None:
                    zeroed_pids.add(from_pid)

        # Track amounts to redistribute
        to_redistribute = 0.0

        for from_pid, adj_list in by_from.items():
            zeroed_amount = final_map.get(from_pid, 0)

            # Check if this is a targeted redistribution
            targeted_adjs = [a for a in adj_list if a.to_participant_id is not None]

            if targeted_adjs:
                # Calculate total percentage/value being redistributed
                total_pct = sum(a.value for a in targeted_adjs if a.mode == 'percent')

                # Zero out the from participant
                final_map[from_pid] = 0

                # Distribute according to targets
                for adj in targeted_adjs:
                    if adj.mode == 'percent':
                        transfer_amount = zeroed_amount * (adj.value / total_pct) if total_pct > 0 else 0
                    else:  # fixed amount
                        transfer_amount = adj.value

                    final_map[adj.to_participant_id] = final_map.get(adj.to_participant_id, 0) + transfer_amount
            else:
                # Equal redistribution to non-zeroed others
                for adj in adj_list:
                    if adj.mode == 'percent' and adj.value == 100.0:
                        final_map[from_pid] = 0
                        to_redistribute += zeroed_amount

        # Redistribute pooled amounts to non-zeroed participants
        if to_redistribute > 0:
            others = [p for p in participants if p.id not in zeroed_pids]
            if others:
                per_other = to_redistribute / len(others)
                for p in others:
                    final_map[p.id] = final_map.get(p.id, 0) + per_other

        return final_map


class MockContext:
    """Shared context for BDD scenarios."""

    def __init__(self):
        self.participants: Dict[str, MockParticipant] = {}
        self.bills: Dict[tuple, MockBill] = {}
        self.components: Dict[str, MockComponent] = {}
        self.readings: Dict[int, MockReading] = {}
        self.adjustments: Dict[tuple, MockAdjustment] = {}
        self.last_result = None
        self.last_error = None
        self.calculator = MockCalculator()
        self.contributions: List[MockContribution] = None
        self.extra: Dict[str, Any] = {}
        self._next_id = 1

    def get_next_id(self):
        id_val = self._next_id
        self._next_id += 1
        return id_val


@pytest.fixture
def context():
    """Provide a fresh context for each scenario."""
    return MockContext()


@pytest.fixture
def mock_participant_repo(context):
    """Mock ParticipantRepository."""
    repo = Mock()

    def add(name):
        if any(p.name.lower() == name.lower() for p in context.participants.values()):
            context.last_error = "A participant with that name already exists"
            return None
        p = MockParticipant(id=context.get_next_id(), name=name)
        context.participants[name] = p
        return p

    def list_all():
        return sorted(context.participants.values(), key=lambda p: p.name)

    def get(pid):
        return next((p for p in context.participants.values() if p.id == pid), None)

    def update(pid, name):
        for old_name, p in list(context.participants.items()):
            if p.id == pid:
                del context.participants[old_name]
                new_p = MockParticipant(id=pid, name=name)
                context.participants[name] = new_p
                return new_p
        return None

    repo.add = Mock(side_effect=add)
    repo.list_all = Mock(side_effect=list_all)
    repo.get = Mock(side_effect=get)
    repo.update = Mock(side_effect=update)

    return repo


@pytest.fixture
def mock_bill_repo(context):
    """Mock MonthlyBillRepository."""
    repo = Mock()

    def create(year, month, electricity, water, internet):
        key = (year, month)
        if key in context.bills:
            context.last_error = "A month for that period already exists"
            return None
        bill = MockBill(
            id=context.get_next_id(),
            year=year,
            month=month,
            electricity_amount=electricity,
            water_amount=water,
            internet_amount=internet,
            archived=False
        )
        context.bills[key] = bill
        return bill

    def get_by_id(bill_id):
        return next((b for b in context.bills.values() if b.id == bill_id), None)

    def find_by_year_month(year, month):
        return context.bills.get((year, month))

    def list_all():
        return [b for b in context.bills.values() if not b.archived]

    def delete(bill_id):
        for key, bill in list(context.bills.items()):
            if bill.id == bill_id:
                del context.bills[key]
                return

    def set_archived(bill_id, archived):
        for key, bill in context.bills.items():
            if bill.id == bill_id:
                # Create updated bill
                new_bill = MockBill(
                    id=bill.id,
                    year=bill.year,
                    month=bill.month,
                    electricity_amount=bill.electricity_amount,
                    water_amount=bill.water_amount,
                    internet_amount=bill.internet_amount,
                    archived=archived
                )
                context.bills[key] = new_bill
                return new_bill
        return None

    def update_amounts(bill_id, electricity, water, internet):
        for key, bill in context.bills.items():
            if bill.id == bill_id:
                new_bill = MockBill(
                    id=bill.id,
                    year=bill.year,
                    month=bill.month,
                    electricity_amount=electricity,
                    water_amount=water,
                    internet_amount=internet,
                    archived=bill.archived
                )
                context.bills[key] = new_bill
                return new_bill
        return None

    repo.create = Mock(side_effect=create)
    repo.get_by_id = Mock(side_effect=get_by_id)
    repo.find_by_year_month = Mock(side_effect=find_by_year_month)
    repo.list_all = Mock(side_effect=list_all)
    repo.delete = Mock(side_effect=delete)
    repo.set_archived = Mock(side_effect=set_archived)
    repo.update_amounts = Mock(side_effect=update_amounts)

    return repo


@pytest.fixture
def mock_component_repo(context):
    """Mock BillComponentRepository."""
    repo = Mock()

    def add(month_id, name, amount, split_method='equal', position=0, distribution=None):
        comp = MockComponent(
            id=context.get_next_id(),
            month_id=month_id,
            name=name,
            amount=amount,
            split_method=split_method,
            position=position,
            distribution=distribution or {}
        )
        context.components[name] = comp
        return comp

    def list_for_month(month_id):
        return sorted(
            [c for c in context.components.values() if c.month_id == month_id],
            key=lambda c: (c.position, c.id)
        )

    def update(component_id, name=None, amount=None, split_method=None, position=None, distribution=None):
        for comp_name, comp in list(context.components.items()):
            if comp.id == component_id:
                new_comp = MockComponent(
                    id=comp.id,
                    month_id=comp.month_id,
                    name=name if name is not None else comp.name,
                    amount=amount if amount is not None else comp.amount,
                    split_method=split_method if split_method is not None else comp.split_method,
                    position=position if position is not None else comp.position,
                    distribution=distribution if distribution is not None else comp.distribution
                )
                del context.components[comp_name]
                context.components[new_comp.name] = new_comp
                return new_comp
        return None

    def delete(component_id):
        for name, comp in list(context.components.items()):
            if comp.id == component_id:
                del context.components[name]
                return

    repo.add = Mock(side_effect=add)
    repo.list_for_month = Mock(side_effect=list_for_month)
    repo.update = Mock(side_effect=update)
    repo.delete = Mock(side_effect=delete)

    return repo


@pytest.fixture
def mock_month_part_repo(context):
    """Mock MonthParticipantRepository."""
    repo = Mock()

    def add(month_id, participant_id):
        key = (month_id, participant_id)
        if not hasattr(context, 'month_participants'):
            context.month_participants = {}
        context.month_participants[key] = {'month_id': month_id, 'participant_id': participant_id}
        return context.month_participants[key]

    def list_for_month(month_id):
        if not hasattr(context, 'month_participants'):
            return []
        return [v for k, v in context.month_participants.items() if k[0] == month_id]

    def remove(month_id, participant_id):
        if hasattr(context, 'month_participants'):
            key = (month_id, participant_id)
            if key in context.month_participants:
                del context.month_participants[key]

    repo.add = Mock(side_effect=add)
    repo.list_for_month = Mock(side_effect=list_for_month)
    repo.remove = Mock(side_effect=remove)

    return repo


@pytest.fixture
def mock_reading_repo(context):
    """Mock MeterReadingRepository."""
    repo = Mock()

    def upsert(month_id, participant_id, reading, prev_reading):
        reading_obj = MockReading(
            month_id=month_id,
            participant_id=participant_id,
            reading=reading,
            prev_reading=prev_reading
        )
        context.readings[(month_id, participant_id)] = reading_obj
        return reading_obj

    def list_for_month(month_id):
        return [r for r in context.readings.values() if r.month_id == month_id]

    def get(month_id, participant_id):
        return context.readings.get((month_id, participant_id))

    repo.upsert = Mock(side_effect=upsert)
    repo.list_for_month = Mock(side_effect=list_for_month)
    repo.get = Mock(side_effect=get)

    return repo


@pytest.fixture
def mock_adjustment_repo(context):
    """Mock ComponentAdjustmentRepository."""
    repo = Mock()

    def upsert(month_id, component_id, participant_id, zero=False, redis_rule=None, notes=None):
        """Upsert an adjustment for a component/participant."""
        # Find component name from id
        comp_name = None
        for name, comp in context.components.items():
            if comp.id == component_id:
                comp_name = name
                break

        adj = MockAdjustment(
            id=context.get_next_id(),
            month_id=month_id,
            component_id=component_id,
            component_name=comp_name or "",
            from_participant_id=participant_id,
            to_participant_id=None,
            mode=redis_rule.get('mode') if redis_rule else None,
            value=0,
            participant_id=participant_id,
            zero=zero,
            redis_rule=redis_rule
        )
        key = (month_id, component_id, participant_id)
        context.adjustments[key] = adj
        return adj

    def add(month_id, component_name, from_participant_id, to_participant_id, mode, value):
        # Find component id from name
        comp = context.components.get(component_name)
        component_id = comp.id if comp else 0

        adj = MockAdjustment(
            id=context.get_next_id(),
            month_id=month_id,
            component_id=component_id,
            component_name=component_name,
            from_participant_id=from_participant_id,
            to_participant_id=to_participant_id,
            mode=mode,
            value=value,
            participant_id=from_participant_id,
            zero=(mode == 'percent' and value == 100.0)
        )
        # Use unique key including to_participant_id to avoid overwrites
        key = (component_name, from_participant_id, to_participant_id)
        context.adjustments[key] = adj
        return adj

    def list_for_month(month_id):
        return list(context.adjustments.values())

    def get(month_id, component_id, participant_id):
        """Get adjustment by month/component/participant."""
        key = (month_id, component_id, participant_id)
        return context.adjustments.get(key)

    def delete(adj_id):
        for key, adj in list(context.adjustments.items()):
            if adj.id == adj_id:
                del context.adjustments[key]
                return

    repo.upsert = Mock(side_effect=upsert)
    repo.add = Mock(side_effect=add)
    repo.list_for_month = Mock(side_effect=list_for_month)
    repo.get = Mock(side_effect=get)
    repo.delete = Mock(side_effect=delete)

    return repo


# Common Given steps
@given("the system is initialized")
def system_initialized(context):
    """Ensure context is fresh."""
    context.last_error = None
    context.last_result = None


@given(parsers.parse('a participant named "{name}" exists'))
def participant_exists(context, mock_participant_repo, name):
    """Create a participant."""
    mock_participant_repo.add(name)


@given(parsers.parse('participants "{names}" exist'))
def participants_exist(context, mock_participant_repo, names):
    """Create multiple participants from comma-separated list."""
    for name in names.split(','):
        mock_participant_repo.add(name.strip())


@given(parsers.parse('a bill for {month_name} {year:d} exists'))
def bill_exists(context, mock_bill_repo, month_name, year):
    """Create a monthly bill."""
    month_map = {
        'January': 1, 'February': 2, 'March': 3, 'April': 4,
        'May': 5, 'June': 6, 'July': 7, 'August': 8,
        'September': 9, 'October': 10, 'November': 11, 'December': 12
    }
    month = month_map.get(month_name, 1)
    mock_bill_repo.create(year, month, 0.0, 0.0, 0.0)


@given(parsers.parse('a bill for {month_name} {year:d} exists with electricity {amount:f}'))
def bill_exists_with_electricity(context, mock_bill_repo, month_name, year, amount):
    """Create a bill with specified electricity amount."""
    month_map = {
        'January': 1, 'February': 2, 'March': 3, 'April': 4,
        'May': 5, 'June': 6, 'July': 7, 'August': 8,
        'September': 9, 'October': 10, 'November': 11, 'December': 12
    }
    month = month_map.get(month_name, 1)
    mock_bill_repo.create(year, month, amount, 0.0, 0.0)


@given(parsers.parse('a component "{name}" exists with amount {amount:f}'))
def component_exists(context, mock_component_repo, name, amount):
    """Create a component with default equal split."""
    # Get the first bill
    bill = next(iter(context.bills.values()), None)
    if bill:
        mock_component_repo.add(bill.id, name, amount, 'equal')


@given(parsers.parse('a component "{name}" exists with amount {amount:f} split "{split_method}"'))
def component_exists_with_split(context, mock_component_repo, name, amount, split_method):
    """Create a component with specified split method."""
    bill = next(iter(context.bills.values()), None)
    if bill:
        comp = mock_component_repo.add(bill.id, name, amount, split_method)
        if not hasattr(context, 'component_ids'):
            context.component_ids = {}
        context.component_ids[name] = comp.id


def _datatable_to_dicts(datatable):
    """Convert pytest-bdd datatable (list of lists) to list of dicts."""
    if not datatable or len(datatable) < 2:
        return []
    headers = datatable[0]
    return [dict(zip(headers, row)) for row in datatable[1:]]


@given("the bill has legacy components:")
def bill_has_legacy_components_conftest(context, mock_component_repo, datatable):
    """Add legacy components to the bill from datatable."""
    rows = _datatable_to_dicts(datatable)
    bill = next(iter(context.bills.values()), None)
    if not bill:
        return
    for i, row in enumerate(rows):
        name = row.get('name', '')
        amount = float(row.get('amount', 0))
        split_method = row.get('split_method', 'equal')
        comp = mock_component_repo.add(bill.id, name, amount, split_method, i)
        if not hasattr(context, 'component_ids'):
            context.component_ids = {}
        context.component_ids[name] = comp.id
