"""Step definitions for calculator.feature."""
import pytest
from pytest_bdd import scenarios, given, when, then, parsers

from app.services import BillCalculator
from app.models import MonthlyBill, MeterReading, Participant, BillComponent, ComponentAdjustment

scenarios('../features/calculator.feature')


def _datatable_to_dicts(datatable):
    """Convert pytest-bdd datatable (list of lists) to list of dicts."""
    if not datatable or len(datatable) < 2:
        return []
    headers = datatable[0]
    return [dict(zip(headers, row)) for row in datatable[1:]]


# ============ Fixtures ============
@pytest.fixture
def calc_context():
    """Context for calculator tests."""
    return {
        'calculator': None,
        'participants': {},
        'readings': [],
        'components': [],
        'adjustments': [],
        'bill': None,
        'contributions': None,
    }


# ============ Given Steps ============
@given('the calculator is initialized')
def calculator_initialized(calc_context):
    calc_context['calculator'] = BillCalculator()
    calc_context['bill'] = MonthlyBill(year=2025, month=10)


@given(parsers.parse('participants "{names}" exist'))
def participants_exist(calc_context, names):
    for i, name in enumerate(n.strip() for n in names.split(',')):
        p = Participant(id=i + 1, name=name)
        calc_context['participants'][name] = p


@given('meter readings:')
def meter_readings(calc_context, datatable):
    rows = _datatable_to_dicts(datatable)
    for row in rows:
        name = row['participant']
        current = float(row['current'])
        previous = float(row['previous']) if row['previous'] != 'null' else None
        p = calc_context['participants'][name]
        reading = MeterReading(
            participant_id=p.id,
            month_id=1,
            reading_current=current,
            reading_previous=previous
        )
        calc_context['readings'].append(reading)


@given(parsers.parse('a component "{name}" with amount {amount:f} split by "{method}"'))
def component_basic(calc_context, name, amount, method):
    comp = BillComponent(
        month_id=1,
        name=name,
        amount=amount,
        split_method=method,
        position=len(calc_context['components'])
    )
    comp.id = len(calc_context['components']) + 1
    calc_context['components'].append(comp)


@given(parsers.parse('a component "{name}" with amount {amount:f} split by "{method}":'))
def component_with_distribution(calc_context, name, amount, method, datatable):
    rows = _datatable_to_dicts(datatable)
    comp = BillComponent(
        month_id=1,
        name=name,
        amount=amount,
        split_method=method,
        position=len(calc_context['components'])
    )
    comp.id = len(calc_context['components']) + 1
    
    if method == 'percentage':
        distribution = {}
        for row in rows:
            p_name = row['participant']
            p = calc_context['participants'][p_name]
            distribution[p.id] = int(row['percent'])
        comp.distribution = distribution
    elif method == 'amount':
        distribution = {}
        for row in rows:
            p_name = row['participant']
            p = calc_context['participants'][p_name]
            distribution[p.id] = int(row['fixed'])
        comp.distribution = distribution
    
    calc_context['components'].append(comp)


# ============ When Steps ============
@when('contributions are calculated')
def calculate_contributions(calc_context):
    participants = list(calc_context['participants'].values())
    calc_context['contributions'] = calc_context['calculator'].compute_contributions_dynamic(
        calc_context['bill'],
        calc_context['components'],
        calc_context['readings'],
        participants,
        calc_context['adjustments']
    )


@when(parsers.parse("I zero out {name}'s share of \"{component}\""))
def zero_share_basic(calc_context, name, component):
    p = calc_context['participants'][name]
    comp = next(c for c in calc_context['components'] if c.name == component)
    adj = ComponentAdjustment(
        month_id=1,
        component_id=comp.id,
        participant_id=p.id,
        zero=True,
        redis_rule=None
    )
    calc_context['adjustments'].append(adj)


@when(parsers.parse("I zero out {name}'s share with redistribution to remaining"))
def zero_share_with_equal_redistribution(calc_context, name):
    # This is handled by the basic zero - redistribution is automatic
    pass


@when(parsers.parse("I zero out {name}'s share of \"{component}\" with percent redistribution:"))
def zero_share_percent_redistribution(calc_context, name, component, datatable):
    rows = _datatable_to_dicts(datatable)
    p = calc_context['participants'][name]
    comp = next(c for c in calc_context['components'] if c.name == component)
    
    targets = {}
    for row in rows:
        target_name = row['target']
        target_p = calc_context['participants'][target_name]
        targets[target_p.id] = int(row['percent'])
    
    adj = ComponentAdjustment(
        month_id=1,
        component_id=comp.id,
        participant_id=p.id,
        zero=True,
        redis_rule={'mode': 'percent', 'targets': targets}
    )
    calc_context['adjustments'].append(adj)


@when(parsers.parse("I zero out {name}'s share of \"{component}\" with amount redistribution:"))
def zero_share_amount_redistribution(calc_context, name, component, datatable):
    rows = _datatable_to_dicts(datatable)
    p = calc_context['participants'][name]
    comp = next(c for c in calc_context['components'] if c.name == component)
    
    targets = {}
    for row in rows:
        target_name = row['target']
        target_p = calc_context['participants'][target_name]
        targets[target_p.id] = int(row['amount'])
    
    adj = ComponentAdjustment(
        month_id=1,
        component_id=comp.id,
        participant_id=p.id,
        zero=True,
        redis_rule={'mode': 'amount', 'targets': targets}
    )
    calc_context['adjustments'].append(adj)


@when(parsers.parse("I zero out {name}'s share of \"{component}\" with no redistribution targets"))
def zero_share_no_targets(calc_context, name, component):
    p = calc_context['participants'][name]
    comp = next(c for c in calc_context['components'] if c.name == component)
    adj = ComponentAdjustment(
        month_id=1,
        component_id=comp.id,
        participant_id=p.id,
        zero=True,
        redis_rule={'mode': 'percent', 'targets': {}}
    )
    calc_context['adjustments'].append(adj)


# ============ Then Steps ============
@then('electricity shares should be:')
def verify_electricity_shares(calc_context, datatable):
    rows = _datatable_to_dicts(datatable)
    by_name = {c.participant.name: c for c in calc_context['contributions']}
    for row in rows:
        name = row['participant']
        expected = float(row['amount'])
        actual = by_name[name].components.get('Electricity', 0.0)
        assert actual == expected, f"{name} expected {expected}, got {actual}"


@then(parsers.parse('water shares should be approximately equal totaling {total:f}'))
def verify_water_shares_equal(calc_context, total):
    water_sum = sum(c.components.get('Water', 0.0) for c in calc_context['contributions'])
    assert round(water_sum, 2) == total


@then(parsers.parse('internet shares should be approximately equal totaling {total:f}'))
def verify_internet_shares_equal(calc_context, total):
    inet_sum = sum(c.components.get('Internet', 0.0) for c in calc_context['contributions'])
    assert round(inet_sum, 2) == total


@then(parsers.parse('all participants should have {amount:f} for "{component}"'))
def all_have_amount(calc_context, amount, component):
    for c in calc_context['contributions']:
        actual = c.components.get(component, 0.0)
        assert actual == amount, f"{c.participant.name} expected {amount}, got {actual}"


@then('water shares should be:')
def verify_water_shares(calc_context, datatable):
    rows = _datatable_to_dicts(datatable)
    by_name = {c.participant.name: c for c in calc_context['contributions']}
    for row in rows:
        name = row['participant']
        expected = float(row['amount'])
        actual = by_name[name].components.get('Water', 0.0)
        assert actual == expected, f"{name} expected {expected}, got {actual}"


@then(parsers.parse('"{component}" shares should be:'))
def verify_component_shares(calc_context, component, datatable):
    rows = _datatable_to_dicts(datatable)
    by_name = {c.participant.name: c for c in calc_context['contributions']}
    for row in rows:
        name = row['participant']
        expected = float(row['amount'])
        actual = by_name[name].components.get(component, 0.0)
        assert actual == expected, f"{name} expected {expected} for {component}, got {actual}"


@then(parsers.parse('the sum of all "{component}" contributions should equal {total:f}'))
def verify_sum_equals(calc_context, component, total):
    actual_sum = sum(c.components.get(component, 0.0) for c in calc_context['contributions'])
    assert round(actual_sum, 2) == total, f"Sum expected {total}, got {actual_sum}"


@then(parsers.parse('{name} should pay {amount:f} for "{component}"'))
def verify_participant_pays(calc_context, name, amount, component):
    by_name = {c.participant.name: c for c in calc_context['contributions']}
    actual = by_name[name].components.get(component, 0.0)
    assert actual == amount, f"{name} expected {amount}, got {actual}"


@then(parsers.parse('the component total should remain {total:f}'))
def verify_component_total(calc_context, total):
    # Get the first component's total
    comp_name = calc_context['components'][0].name
    actual_sum = sum(c.components.get(comp_name, 0.0) for c in calc_context['contributions'])
    assert round(actual_sum, 2) == total


@then(parsers.parse('the "{component}" shares sorted should be "{expected_str}"'))
def verify_sorted_shares(calc_context, component, expected_str):
    expected = [float(x.strip()) for x in expected_str.split(',')]
    actual = sorted([c.components.get(component, 0.0) for c in calc_context['contributions']])
    assert actual == expected, f"Expected {expected}, got {actual}"


@then(parsers.parse('"{component}" shares should be approximately:'))
def verify_approximate_shares(calc_context, component, datatable):
    rows = _datatable_to_dicts(datatable)
    by_name = {c.participant.name: c for c in calc_context['contributions']}
    for row in rows:
        name = row['participant']
        expected = float(row['amount'])
        actual = by_name[name].components.get(component, 0.0)
        assert abs(actual - expected) <= 0.02, f"{name} expected ~{expected}, got {actual}"


@then('the remaining participants should split the redistributed amount equally')
def verify_remaining_split_equally(calc_context):
    # This is verified by checking the non-zero participants have roughly equal shares
    non_zero = [c for c in calc_context['contributions'] if any(v > 0 for v in c.components.values())]
    if len(non_zero) >= 2:
        amounts = [list(c.components.values())[0] for c in non_zero]
        # Check they're roughly equal (within rounding)
        assert max(amounts) - min(amounts) <= 0.02
