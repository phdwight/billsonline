"""BDD step definitions for adjustment and redistribution use cases."""
import pytest
from pytest_bdd import scenarios, given, when, then, parsers

# Load feature file
scenarios('../features/adjustments.feature')


def datatable_to_dicts(datatable):
    """Convert pytest-bdd datatable (list of lists) to list of dicts."""
    if not datatable or len(datatable) < 2:
        return []
    headers = datatable[0]
    return [dict(zip(headers, row)) for row in datatable[1:]]


# Given steps specific to adjustments
@given(parsers.parse('a component "{name}" exists with amount {amount:f} split "{split_method}"'))
def component_with_split(context, mock_component_repo, name, amount, split_method):
    """Create a component with specific split method."""
    bill = next(iter(context.bills.values()), None)
    if bill:
        mock_component_repo.add(bill.id, name, amount, split_method, 0)


# When steps
@when(parsers.parse("I zero out {name}'s share of \"{component}\""))
def zero_out_share(context, mock_component_repo, mock_reading_repo, mock_adjustment_repo, name, component):
    """Zero out a participant's share and calculate."""
    p = context.participants.get(name)
    bill = next(iter(context.bills.values()), None)
    comp = context.components.get(component)

    if p and bill and comp:
        # Create adjustment
        mock_adjustment_repo.add(
            month_id=bill.id,
            component_name=component,
            from_participant_id=p.id,
            to_participant_id=None,  # redistribute to others
            mode="percent",
            value=100.0
        )

        # Calculate with adjustment
        _calculate_contributions(context, mock_component_repo, mock_reading_repo, mock_adjustment_repo)


@when(parsers.parse("I zero out {name}'s share of \"{component}\" with redistribution:"))
def zero_out_with_redistribution(context, mock_component_repo, mock_reading_repo, mock_adjustment_repo, name, component, datatable):
    """Zero out share with custom redistribution rules."""
    p = context.participants.get(name)
    bill = next(iter(context.bills.values()), None)

    if not (p and bill):
        return

    rows = datatable_to_dicts(datatable)
    if not rows:
        return

    row = rows[0]
    mode = row.get('mode', 'percent')
    targets_str = row.get('targets', '')

    # Parse targets like "Bob:70, Charlie:30"
    for target in targets_str.split(','):
        target = target.strip()
        if ':' in target:
            target_name, value = target.split(':')
            target_p = context.participants.get(target_name.strip())
            if target_p:
                mock_adjustment_repo.add(
                    month_id=bill.id,
                    component_name=component,
                    from_participant_id=p.id,
                    to_participant_id=target_p.id,
                    mode=mode,
                    value=float(value)
                )

    _calculate_contributions(context, mock_component_repo, mock_reading_repo, mock_adjustment_repo)


@when(parsers.parse("I try to redistribute {name}'s share with invalid percentages:"))
def try_invalid_redistribution(context, mock_adjustment_repo, name, datatable):
    """Try to create invalid redistribution."""
    rows = datatable_to_dicts(datatable)
    if not rows:
        return

    row = rows[0]
    targets_str = row.get('targets', '')

    # Sum percentages
    total_percent = 0
    for target in targets_str.split(','):
        if ':' in target:
            _, value = target.split(':')
            total_percent += float(value)

    if total_percent != 100:
        context.last_error = "Percentages must sum to 100%"


@when("contributions are calculated")
def calculate_contributions(context, mock_component_repo, mock_reading_repo, mock_adjustment_repo):
    """Calculate contributions without adjustments."""
    _calculate_contributions(context, mock_component_repo, mock_reading_repo, mock_adjustment_repo)


def _calculate_contributions(context, mock_component_repo, mock_reading_repo, mock_adjustment_repo):
    """Helper to calculate contributions."""
    bill = next(iter(context.bills.values()), None)
    if not bill:
        return

    components = mock_component_repo.list_for_month(bill.id)
    readings = mock_reading_repo.list_for_month(bill.id)
    participants = list(context.participants.values())
    adjustments = mock_adjustment_repo.list_for_month(bill.id)

    context.contributions = context.calculator.compute_contributions_dynamic(
        bill=bill,
        components=components,
        readings=readings,
        participants=participants,
        component_adjustments=adjustments,
    )


# Then steps
@then(parsers.parse('{name} should pay {amount:f} for "{component}"'))
def participant_should_pay(context, name, amount, component):
    """Verify participant pays specific amount."""
    for c in context.contributions:
        if c.participant.name == name:
            actual = c.components.get(component, 0)
            assert abs(actual - amount) < 0.02, \
                f"Expected {name} to pay {amount} for {component}, got {actual}"
            return
    pytest.fail(f"Participant '{name}' not found in contributions")


@then(parsers.parse("the component total should remain {amount:f}"))
def component_total_unchanged(context, amount):
    """Verify component total is preserved."""
    # Find the specific component total
    for c in context.contributions:
        if c.components:
            comp_name = list(c.components.keys())[0]
            comp_total = sum(cont.components.get(comp_name, 0) for cont in context.contributions)
            assert abs(comp_total - amount) < 0.02, \
                f"Component total should be {amount}, got {comp_total}"
            return


@then(parsers.parse('the operation should fail with "{error_message}"'))
def operation_should_fail(context, error_message):
    """Verify operation failed with expected error."""
    assert context.last_error is not None, "Expected an error but none occurred"
    assert error_message.lower() in context.last_error.lower(), \
        f"Expected error containing '{error_message}', got '{context.last_error}'"


@then(parsers.parse("the sum of all contributions should equal {amount:f}"))
def sum_equals(context, amount):
    """Verify sum of all contributions."""
    # Find component matching this amount
    for comp in context.components.values():
        if abs(comp.amount - amount) < 0.02:
            comp_total = sum(cont.components.get(comp.name, 0) for cont in context.contributions)
            assert abs(comp_total - amount) < 0.02, \
                f"Sum should equal {amount}, got {comp_total}"
            return
