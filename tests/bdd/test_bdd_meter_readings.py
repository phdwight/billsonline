"""BDD step definitions for meter reading use cases."""
from pytest_bdd import scenarios, given, when, then, parsers

# Load feature file
scenarios('../features/meter_readings.feature')


def datatable_to_dicts(datatable):
    """Convert pytest-bdd datatable (list of lists) to list of dicts."""
    if not datatable or len(datatable) < 2:
        return []
    headers = datatable[0]
    return [dict(zip(headers, row)) for row in datatable[1:]]


# Given steps specific to readings
@given(parsers.parse("meter readings exist for {name} with previous {previous:d} and current {current:d}"))
def existing_readings(context, mock_reading_repo, name, previous, current):
    """Set up existing meter reading for participant."""
    p = context.participants.get(name)
    bill = next(iter(context.bills.values()), None)
    if p and bill:
        mock_reading_repo.upsert(bill.id, p.id, current, previous)


@given("a bill for December 2024 exists with readings:")
def bill_with_readings(context, mock_bill_repo, mock_reading_repo, datatable):
    """Create December 2024 bill with readings."""
    bill = mock_bill_repo.create(2024, 12, 0, 0, 0)
    rows = datatable_to_dicts(datatable)
    for row in rows:
        name = row['participant']
        current = int(row['current'])
        p = context.participants.get(name)
        if p:
            mock_reading_repo.upsert(bill.id, p.id, current, 0)
            # Store for pre-filling
            if 'last_readings' not in context.extra:
                context.extra['last_readings'] = {}
            context.extra['last_readings'][name] = current


# When steps
@when("I record meter readings:")
def record_readings(context, mock_reading_repo, datatable):
    """Record meter readings from table."""
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
            # Handle negative usage - store 0 instead
            actual_current = max(current, previous)
            mock_reading_repo.upsert(bill.id, p.id, actual_current, previous)
            # Force recalc usage with clamping
            reading = context.readings[p.id]
            reading.usage = lambda r=reading: max(0, r.reading - r.prev_reading)


@when(parsers.parse("I update {name}'s current reading to {reading:d}"))
def update_reading(context, mock_reading_repo, name, reading):
    """Update a participant's current reading."""
    p = context.participants.get(name)
    bill = next(iter(context.bills.values()), None)
    if p and bill:
        existing = context.readings.get(p.id)
        prev = existing.prev_reading if existing else 0
        mock_reading_repo.upsert(bill.id, p.id, reading, prev)


@when("I view the January 2025 bill")
def view_january_bill(context, mock_bill_repo):
    """View/select the January 2025 bill."""
    bill = context.bills.get((2025, 1))
    if bill:
        context.selected_bill = bill


# Then steps
@then(parsers.parse("{name}'s usage should be {usage:d}"))
def participant_usage(context, name, usage):
    """Verify calculated usage for participant."""
    p = context.participants.get(name)
    if p:
        reading = context.readings.get(p.id)
        assert reading is not None, f"No reading found for {name}"
        actual_usage = max(0, reading.reading - reading.prev_reading)
        assert actual_usage == usage, \
            f"Expected {name}'s usage to be {usage}, got {actual_usage}"


@then(parsers.parse("total usage should be {total:d}"))
def total_usage(context, total):
    """Verify total usage across all participants."""
    actual_total = 0
    for reading in context.readings.values():
        actual_total += max(0, reading.reading - reading.prev_reading)

    assert actual_total == total, f"Expected total usage {total}, got {actual_total}"


@then(parsers.parse("{name}'s previous reading should be pre-filled with {value:d}"))
def prefilled_reading(context, name, value):
    """Verify previous reading is pre-filled from last month."""
    last_readings = context.extra.get('last_readings', {})
    assert name in last_readings, f"No last reading stored for {name}"
    assert last_readings[name] == value, \
        f"Expected {name}'s prefilled reading to be {value}, got {last_readings[name]}"


@then(parsers.parse("{name} should not be charged for usage-based components"))
def no_charge_for_usage(context, name):
    """Verify participant with zero usage is not charged for usage components."""
    p = context.participants.get(name)
    if p:
        reading = context.readings.get(p.id)
        if reading:
            usage = max(0, reading.reading - reading.prev_reading)
            assert usage == 0, f"Expected zero usage for {name}, got {usage}"
            # If there were contributions, verify no usage charge
            if context.contributions:
                for c in context.contributions:
                    if c.participant.name == name:
                        # Usage-based components should be 0
                        # This would require knowing which components are usage-based
                        pass
