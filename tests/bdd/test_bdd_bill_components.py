"""BDD step definitions for bill component split method use cases."""
import pytest
from pytest_bdd import scenarios, given, when, then, parsers

# Load feature file
scenarios('../features/bill_components.feature')


def datatable_to_dicts(datatable):
    """Convert pytest-bdd datatable (list of lists) to list of dicts."""
    if not datatable or len(datatable) < 2:
        return []
    headers = datatable[0]
    return [dict(zip(headers, row)) for row in datatable[1:]]


# Given steps specific to components
@given("meter readings are:")
def meter_readings_table(context, mock_reading_repo, datatable):
    """Set up meter readings from a table."""
    bill = next(iter(context.bills.values()), None)
    if not bill:
        return

    rows = datatable_to_dicts(datatable)
    for row in rows:
        name = row['participant']
        previous = int(row['previous'])
        current = int(row['current'])
        p = context.participants.get(name)
        if p:
            mock_reading_repo.upsert(bill.id, p.id, current, previous)


@given(parsers.parse('a component "{name}" exists with amount {amount:f}'))
def component_with_amount(context, mock_component_repo, name, amount):
    """Create a component with default equal split."""
    bill = next(iter(context.bills.values()), None)
    if bill:
        mock_component_repo.add(bill.id, name, amount, "equal", 0)


# When steps
@when(parsers.parse('I add a component "{name}" with amount {amount:f} split "{split_method}"'))
def add_component(context, mock_component_repo, mock_reading_repo, name, amount, split_method):
    """Add a component with specific split method."""
    bill = next(iter(context.bills.values()), None)
    if bill:
        idx = len(mock_component_repo.list_for_month(bill.id))
        comp = mock_component_repo.add(bill.id, name, amount, split_method, idx)
        context.last_result = comp

        # Calculate contributions
        components = mock_component_repo.list_for_month(bill.id)
        readings = mock_reading_repo.list_for_month(bill.id)
        participants = list(context.participants.values())

        context.contributions = context.calculator.compute_contributions_dynamic(
            bill=bill,
            components=components,
            readings=readings,
            participants=participants,
            component_adjustments=[],
        )


@when(parsers.parse('I add a component "{name}" with amount {amount:f} split "{split_method}" with distribution:'))
def add_component_with_distribution(context, mock_component_repo, mock_reading_repo, name, amount, split_method, datatable):
    """Add a component with custom distribution."""
    bill = next(iter(context.bills.values()), None)
    if not bill:
        return

    # Build distribution dict from datatable
    rows = datatable_to_dicts(datatable)
    distribution = {}
    for row in rows:
        p_name = row['participant']
        p = context.participants.get(p_name)
        if p:
            if 'percentage' in row:
                distribution[str(p.id)] = float(row['percentage'])
            elif 'amount' in row:
                distribution[str(p.id)] = float(row['amount'])

    idx = len(mock_component_repo.list_for_month(bill.id))
    comp = mock_component_repo.add(bill.id, name, amount, split_method, idx, distribution)
    context.last_result = comp

    # Calculate contributions
    components = mock_component_repo.list_for_month(bill.id)
    readings = mock_reading_repo.list_for_month(bill.id)
    participants = list(context.participants.values())

    context.contributions = context.calculator.compute_contributions_dynamic(
        bill=bill,
        components=components,
        readings=readings,
        participants=participants,
        component_adjustments=[],
    )


@when(parsers.parse('I update the component "{name}" amount to {amount:f}'))
def update_component_amount(context, mock_component_repo, name, amount):
    """Update a component's amount."""
    comp = context.components.get(name)
    if comp:
        mock_component_repo.update(comp.id, amount=amount)


@when(parsers.parse('I delete the component "{name}"'))
def delete_component(context, mock_component_repo, name):
    """Delete a component."""
    comp = context.components.get(name)
    if comp:
        mock_component_repo.delete(comp.id)


# Then steps
@then(parsers.parse('each participant should pay {amount:f} for "{component}"'))
def each_participant_pays(context, amount, component):
    """Verify all participants pay the same amount."""
    for c in context.contributions:
        actual = c.components.get(component, 0)
        assert abs(actual - amount) < 0.02, \
            f"Expected {c.participant.name} to pay {amount} for {component}, got {actual}"


@then(parsers.parse('{name} should pay {amount:f} for "{component}"'))
def participant_pays_for_component(context, name, amount, component):
    """Verify specific participant's payment for a component."""
    for c in context.contributions:
        if c.participant.name == name:
            actual = c.components.get(component, 0)
            assert abs(actual - amount) < 0.02, \
                f"Expected {name} to pay {amount} for {component}, got {actual}"
            return
    pytest.fail(f"Participant '{name}' not found in contributions")


@then(parsers.parse('the component "{name}" amount should be {amount:f}'))
def component_amount(context, name, amount):
    """Verify component amount."""
    comp = context.components.get(name)
    assert comp is not None, f"Component '{name}' not found"
    assert abs(comp.amount - amount) < 0.02, \
        f"Expected component amount {amount}, got {comp.amount}"


@then(parsers.parse('the component "{name}" should not exist'))
def component_not_exist(context, name):
    """Verify component does not exist."""
    assert name not in context.components, f"Component '{name}' should not exist"
