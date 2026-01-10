"""BDD step definitions for monthly bill management use cases."""
from pytest_bdd import scenarios, given, when, then, parsers

# Load feature file
scenarios('../features/monthly_bills.feature')


def datatable_to_dicts(datatable):
    """Convert pytest-bdd datatable (list of lists) to list of dicts."""
    if not datatable or len(datatable) < 2:
        return []
    headers = datatable[0]
    return [dict(zip(headers, row)) for row in datatable[1:]]


# Given steps specific to bills
@given("a bill for January 2025 exists with components")
def bill_with_components(context, mock_bill_repo, mock_component_repo):
    """Create a bill with default components."""
    bill = mock_bill_repo.create(2025, 1, 1000.0, 500.0, 300.0)
    mock_component_repo.add(bill.id, "Electricity", 1000.0, "usage", 0)
    mock_component_repo.add(bill.id, "Water", 500.0, "equal", 1)
    mock_component_repo.add(bill.id, "Internet", 300.0, "equal", 2)


@given("meter readings are recorded for all participants")
def readings_for_all(context, mock_reading_repo):
    """Record meter readings for all participants."""
    bill = next(iter(context.bills.values()), None)
    if bill:
        for i, p in enumerate(context.participants.values()):
            mock_reading_repo.upsert(bill.id, p.id, 100 + (i + 1) * 50, 100)


# When steps
@when("I create a bill for January 2025 with:")
def create_bill_with_table(context, mock_bill_repo, datatable):
    """Create a bill from datatable."""
    rows = datatable_to_dicts(datatable)
    if not rows:
        return
    row = rows[0]
    electricity = float(row.get('electricity', 0))
    water = float(row.get('water', 0))
    internet = float(row.get('internet', 0))
    result = mock_bill_repo.create(2025, 1, electricity, water, internet)
    context.last_result = result


@when("I try to create another bill for January 2025")
def try_create_duplicate_bill(context, mock_bill_repo):
    """Try to create a duplicate bill."""
    result = mock_bill_repo.create(2025, 1, 0, 0, 0)
    context.last_result = result


@when(parsers.parse("I update the bill electricity amount to {amount:f}"))
def update_bill_electricity(context, mock_bill_repo, amount):
    """Update bill electricity amount."""
    bill = next(iter(context.bills.values()), None)
    if bill:
        mock_bill_repo.update_amounts(bill.id, amount, bill.water_amount, bill.internet_amount)


@when("I archive the bill for January 2025")
def archive_bill(context, mock_bill_repo):
    """Archive a bill."""
    bill = context.bills.get((2025, 1))
    if bill:
        mock_bill_repo.set_archived(bill.id, True)


@when("I delete the bill for January 2025")
def delete_bill(context, mock_bill_repo):
    """Delete a bill."""
    bill = context.bills.get((2025, 1))
    if bill:
        mock_bill_repo.delete(bill.id)


@when("I export the bill to CSV")
def export_to_csv(context, mock_component_repo, mock_reading_repo):
    """Export bill to CSV format."""
    from io import StringIO
    import csv

    bill = next(iter(context.bills.values()), None)
    if not bill:
        return

    components = mock_component_repo.list_for_month(bill.id)
    readings = mock_reading_repo.list_for_month(bill.id)
    participants = list(context.participants.values())

    # Compute contributions
    contributions = context.calculator.compute_contributions_dynamic(
        bill=bill,
        components=components,
        readings=readings,
        participants=participants,
        component_adjustments=[],
    )

    # Generate CSV
    si = StringIO()
    writer = csv.writer(si)

    comp_names = [c.name for c in components]
    writer.writerow(["Participant", *comp_names, "Total"])

    for c in contributions:
        row = [c.participant.name]
        total = 0.0
        for name in comp_names:
            val = round(float(c.components.get(name, 0.0)), 2)
            row.append(f"{val:.2f}")
            total += val
        row.append(f"{total:.2f}")
        writer.writerow(row)

    # Totals row
    comp_totals = [float(c.amount) for c in components]
    grand_total = sum(comp_totals)
    writer.writerow(["Totals", *[f"{amt:.2f}" for amt in comp_totals], f"{grand_total:.2f}"])

    context.csv_output = si.getvalue()


# Then steps
@then("a bill for January 2025 should exist")
def bill_should_exist(context):
    """Verify bill exists."""
    assert (2025, 1) in context.bills, "Bill for January 2025 not found"


@then("the bill for January 2025 should not exist")
def bill_should_not_exist(context):
    """Verify bill does not exist."""
    assert (2025, 1) not in context.bills, "Bill for January 2025 should not exist"


@then(parsers.parse("the bill total should be {total:f}"))
def bill_total(context, total):
    """Verify bill total."""
    bill = context.last_result
    actual_total = bill.electricity_amount + bill.water_amount + bill.internet_amount
    assert abs(actual_total - total) < 0.01, f"Expected total {total}, got {actual_total}"


@then(parsers.parse("the bill electricity amount should be {amount:f}"))
def bill_electricity_amount(context, amount):
    """Verify bill electricity amount."""
    bill = next(iter(context.bills.values()), None)
    assert bill is not None
    assert abs(bill.electricity_amount - amount) < 0.01, \
        f"Expected electricity {amount}, got {bill.electricity_amount}"


@then("the bill should be marked as archived")
def bill_archived(context):
    """Verify bill is archived."""
    bill = next(iter(context.bills.values()), None)
    assert bill is not None
    assert bill.archived is True, "Bill should be archived"


@then("the bill should not appear in active bills list")
def bill_not_in_active(context, mock_bill_repo):
    """Verify bill is not in active list."""
    active_bills = mock_bill_repo.list_all()
    assert len(active_bills) == 0, "Archived bill should not appear in active list"


@then("I should receive a CSV file")
def received_csv(context):
    """Verify CSV was generated."""
    assert context.csv_output is not None
    assert len(context.csv_output) > 0


@then("the CSV should contain all participant names")
def csv_has_participants(context):
    """Verify CSV contains all participants."""
    for name in context.participants.keys():
        assert name in context.csv_output, f"Participant '{name}' not found in CSV"


@then("the CSV should have a totals row")
def csv_has_totals(context):
    """Verify CSV has totals row."""
    assert "Totals" in context.csv_output, "CSV should have a Totals row"


@then(parsers.parse('the operation should fail with "{error_message}"'))
def operation_should_fail(context, error_message):
    """Verify operation failed with expected error."""
    assert context.last_error is not None, "Expected an error but none occurred"
    assert error_message.lower() in context.last_error.lower(), \
        f"Expected error containing '{error_message}', got '{context.last_error}'"
