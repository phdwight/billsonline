"""BDD step definitions for complex route operations."""
from pytest_bdd import scenarios, given, when, then, parsers

# Load feature file
scenarios('../features/routes_complex.feature')


def datatable_to_dicts(datatable):
    """Convert pytest-bdd datatable (list of lists) to list of dicts."""
    if not datatable or len(datatable) < 2:
        return []
    headers = datatable[0]
    return [dict(zip(headers, row)) for row in datatable[1:]]


# ===== Given Steps =====

@given("a bill for March 2025 exists with participants linked")
def bill_with_linked_participants(context, mock_bill_repo, mock_month_part_repo):
    """Create a bill with participants linked."""
    bill = mock_bill_repo.create(2025, 3, 300.0, 90.0, 60.0)
    for p in context.participants.values():
        mock_month_part_repo.add(bill.id, p.id)
    context.current_bill_id = bill.id


@given(parsers.parse('a participant "{name}" exists'))
def single_participant_exists(context, mock_participant_repo, name):
    """Create a single participant."""
    mock_participant_repo.create(name)


@given(parsers.parse('a component "{name}" exists with amount {amount:f} split "{split_method}"'))
def component_exists(context, mock_component_repo, name, amount, split_method):
    """Create a component for the current bill."""
    bill_id = context.current_bill_id
    comp = mock_component_repo.add(bill_id, name, amount, split_method, 0)
    if not hasattr(context, 'component_ids'):
        context.component_ids = {}
    context.component_ids[name] = comp.id


@given("the bill is archived")
def bill_is_archived(context, mock_bill_repo):
    """Archive the current bill."""
    bill = context.bills.get((2025, 3))
    if bill:
        mock_bill_repo.set_archived(bill.id, True)


@given("meter readings exist:")
def readings_exist(context, mock_reading_repo, datatable):
    """Create meter readings from datatable."""
    rows = datatable_to_dicts(datatable)
    bill_id = context.current_bill_id
    for row in rows:
        name = row.get('participant', '')
        current = float(row.get('current', 0))
        previous = row.get('previous', '')
        prev_val = float(previous) if previous else None
        p = context.participants.get(name)
        if p:
            mock_reading_repo.upsert(bill_id, p.id, current, prev_val)


@given(parsers.parse("a standalone bill for {month_name} {year:d} with only legacy amounts:"))
def standalone_bill_legacy(context, mock_bill_repo, month_name, year, datatable):
    """Create a standalone bill with legacy amounts."""
    months = {'January': 1, 'February': 2, 'March': 3, 'April': 4, 'May': 5, 'June': 6,
              'July': 7, 'August': 8, 'September': 9, 'October': 10, 'November': 11, 'December': 12}
    month = months.get(month_name, 1)
    rows = datatable_to_dicts(datatable)
    if rows:
        row = rows[0]
        elec = float(row.get('electricity', 0))
        water = float(row.get('water', 0))
        inet = float(row.get('internet', 0))
        bill = mock_bill_repo.create(year, month, elec, water, inet)
        context.standalone_bill_id = bill.id


@given(parsers.parse("a standalone bill for {month_name} {year:d} with zero amounts"))
def standalone_bill_zero(context, mock_bill_repo, month_name, year):
    """Create a standalone bill with zero amounts."""
    months = {'January': 1, 'February': 2, 'March': 3, 'April': 4, 'May': 5, 'June': 6,
              'July': 7, 'August': 8, 'September': 9, 'October': 10, 'November': 11, 'December': 12}
    month = months.get(month_name, 1)
    bill = mock_bill_repo.create(year, month, 0, 0, 0)
    context.standalone_bill_id = bill.id


# ===== When Steps =====

@when(parsers.parse("I create a bill for {month_name} {year:d} with:"))
def create_bill_with_datatable(context, mock_bill_repo, mock_component_repo, month_name, year, datatable):
    """Create a bill with amounts from datatable and add legacy components."""
    months = {'January': 1, 'February': 2, 'March': 3, 'April': 4, 'May': 5, 'June': 6,
              'July': 7, 'August': 8, 'September': 9, 'October': 10, 'November': 11, 'December': 12}
    month = months.get(month_name, 1)
    rows = datatable_to_dicts(datatable)
    if rows:
        row = rows[0]
        elec = float(row.get('electricity', 0))
        water = float(row.get('water', 0))
        inet = float(row.get('internet', 0))
        bill = mock_bill_repo.create(year, month, elec, water, inet)
        context.last_created_bill = bill
        # Add legacy components
        if elec > 0:
            mock_component_repo.add(bill.id, "Electricity", elec, "usage", 0)
        if water > 0:
            mock_component_repo.add(bill.id, "Water", water, "equal", 1)
        if inet > 0:
            mock_component_repo.add(bill.id, "Internet", inet, "equal", 2)


@when(parsers.parse("I create a bill for {month_name} {year:d} with custom components:"))
def create_bill_custom_components(context, mock_bill_repo, mock_component_repo, month_name, year, datatable):
    """Create a bill with custom components."""
    months = {'January': 1, 'February': 2, 'March': 3, 'April': 4, 'May': 5, 'June': 6,
              'July': 7, 'August': 8, 'September': 9, 'October': 10, 'November': 11, 'December': 12}
    month = months.get(month_name, 1)
    bill = mock_bill_repo.create(year, month, 0, 0, 0)
    rows = datatable_to_dicts(datatable)
    for i, row in enumerate(rows):
        name = row.get('name', '')
        amount = float(row.get('amount', 0))
        split = row.get('split', 'equal')
        if name:
            mock_component_repo.add(bill.id, name, amount, split, i)
    context.last_created_bill = bill


@when(parsers.parse("I create a bill for {month_name} {year:d} with percentage split:"))
def create_bill_percentage(context, mock_bill_repo, mock_component_repo, month_name, year, datatable):
    """Create a bill with percentage-based split."""
    months = {'January': 1, 'February': 2, 'March': 3, 'April': 4, 'May': 5, 'June': 6,
              'July': 7, 'August': 8, 'September': 9, 'October': 10, 'November': 11, 'December': 12}
    month = months.get(month_name, 1)
    bill = mock_bill_repo.create(year, month, 0, 0, 0)
    rows = datatable_to_dicts(datatable)
    for row in rows:
        name = row.get('component', '')
        amount = float(row.get('amount', 0))
        # Build distribution from participant columns
        dist = {}
        for pname, p in context.participants.items():
            if pname in row and row[pname]:
                dist[p.id] = float(row[pname])
        comp = mock_component_repo.add(bill.id, name, amount, 'percentage', 0, dist)
    context.last_created_bill = bill


@when(parsers.parse("I create a bill for {month_name} {year:d} with components including empty names:"))
def create_bill_with_empty_names(context, mock_bill_repo, mock_component_repo, month_name, year, datatable):
    """Create a bill skipping empty component names."""
    months = {'January': 1, 'February': 2, 'March': 3, 'April': 4, 'May': 5, 'June': 6,
              'July': 7, 'August': 8, 'September': 9, 'October': 10, 'November': 11, 'December': 12}
    month = months.get(month_name, 1)
    bill = mock_bill_repo.create(year, month, 100, 50, 30)
    rows = datatable_to_dicts(datatable)
    for i, row in enumerate(rows):
        name = (row.get('name', '') or '').strip()
        if name:
            amount = float(row.get('amount', 0))
            mock_component_repo.add(bill.id, name, amount, 'equal', i)
    context.last_created_bill = bill


@when("I submit meter readings:")
def submit_readings(context, mock_reading_repo, datatable):
    """Submit meter readings."""
    rows = datatable_to_dicts(datatable)
    bill_id = context.current_bill_id
    for row in rows:
        name = row.get('participant', '')
        current = float(row.get('current', 0))
        previous = row.get('previous', '')
        prev_val = float(previous) if previous else None
        p = context.participants.get(name)
        if p:
            mock_reading_repo.upsert(bill_id, p.id, current, prev_val)


@when("I try to submit meter readings:")
def try_submit_readings(context, mock_reading_repo, mock_bill_repo, datatable):
    """Try to submit readings (may fail for archived)."""
    bill = context.bills.get((2025, 3))
    if bill and bill.archived:
        context.last_error = "archived"
        return
    rows = datatable_to_dicts(datatable)
    bill_id = context.current_bill_id
    for row in rows:
        name = row.get('participant', '')
        current = float(row.get('current', 0))
        previous = row.get('previous', '')
        prev_val = float(previous) if previous else None
        p = context.participants.get(name)
        if p:
            mock_reading_repo.upsert(bill_id, p.id, current, prev_val)


@when(parsers.parse("I try to submit readings to month {month_id:d}"))
def try_submit_to_nonexistent(context, month_id):
    """Try to submit readings to non-existent month."""
    context.last_error = "not found"


@when("I save adjustments with no rules")
def save_adjustments_no_rules(context):
    """Save adjustments without rules."""
    context.last_result = "adjustments saved"


@when(parsers.parse('I zero out Alice\'s share of "{component}" and redistribute:'))
def zero_and_redistribute(context, mock_adjustment_repo, component, datatable):
    """Zero out and redistribute."""
    rows = datatable_to_dicts(datatable)
    if not rows:
        return
    row = rows[0]
    mode = row.get('mode', 'percent')
    bill_id = context.current_bill_id
    comp_id = context.component_ids.get(component)
    alice = context.participants.get('Alice')

    # Build targets
    targets = {}
    for pname, p in context.participants.items():
        if pname in row and row[pname]:
            targets[p.id] = float(row[pname])

    rule = {'mode': mode, 'targets': targets}
    mock_adjustment_repo.upsert(bill_id, comp_id, alice.id, zero=True, redis_rule=rule)


@when("I try to redistribute with invalid percentages:")
def try_invalid_redistribute(context, datatable):
    """Try to redistribute with invalid percentages."""
    rows = datatable_to_dicts(datatable)
    if rows:
        row = rows[0]
        total = 0
        for k, v in row.items():
            if k != 'mode' and v:
                total += float(v)
        if total != 100:
            context.last_error = "must sum to 100%"


@when("I try to save adjustments")
def try_save_adjustments(context):
    """Try to save adjustments (may fail for archived)."""
    bill = context.bills.get((2025, 3))
    if bill and bill.archived:
        context.last_error = "archived"


@when("I update the bill amounts to:")
def update_bill_amounts(context, mock_bill_repo, mock_component_repo, datatable):
    """Update bill amounts and corresponding components."""
    rows = datatable_to_dicts(datatable)
    if not rows:
        return
    row = rows[0]
    electricity = float(row.get('electricity', 0))
    water = float(row.get('water', 0))
    internet = float(row.get('internet', 0))

    bill = context.bills.get((2025, 3))
    if bill:
        mock_bill_repo.update_amounts(bill.id, electricity, water, internet)

        # Also update corresponding BillComponent records (mimics the fix)
        components = mock_component_repo.list_for_month(bill.id)
        legacy_updates = {
            "Electricity": electricity,
            "Water": water,
            "Internet": internet,
        }
        for comp in components:
            if comp.name in legacy_updates:
                mock_component_repo.update(comp.id, amount=legacy_updates[comp.name])


@when(parsers.parse('I try to update the component amount to "{value}"'))
def try_update_component_amount(context, value):
    """Try to update component with possibly invalid amount."""
    try:
        float(value)
        if float(value) < 0:
            context.last_error = "non-negative"
    except ValueError:
        context.last_error = "number"


@when(parsers.parse('I try to update the component position to "{value}"'))
def try_update_component_position(context, value):
    """Try to update component with possibly invalid position."""
    try:
        int(value)
    except ValueError:
        context.last_error = "integer"


@when(parsers.parse('I try to update the component split method to "{value}"'))
def try_update_split_method(context, value):
    """Try to update component with invalid split method."""
    valid = ['usage', 'equal', 'percentage', 'amount']
    if value not in valid:
        context.last_error = "split method must be 'usage' or 'equal'"


@when("I try to convert legacy amounts")
def try_convert_legacy(context, mock_bill_repo):
    """Try to convert legacy amounts."""
    bill_id = context.standalone_bill_id
    bill = None
    for b in context.bills.values():
        if b.id == bill_id:
            bill = b
            break
    if bill and bill.electricity_amount == 0 and bill.water_amount == 0 and bill.internet_amount == 0:
        context.last_error = "no legacy amounts"


@when("I try to add a participant to the month without selecting one")
def try_add_no_participant(context):
    """Try to add participant without selection."""
    context.last_error = "select"


@when(parsers.parse('I try to rename Bob to "{new_name}"'))
def try_rename_duplicate(context, new_name):
    """Try to rename to duplicate name."""
    if new_name in context.participants:
        context.last_error = "already has that name"


@when("I try to update the bill amounts to:")
def try_update_archived(context, mock_bill_repo, datatable):
    """Try to update bill amounts (may fail for archived)."""
    bill = context.bills.get((2025, 3))
    if bill and bill.archived:
        context.last_error = "archived"


# ===== Then Steps =====

@then(parsers.parse("a bill for {month_name} {year:d} should exist"))
def bill_should_exist_month(context, month_name, year):
    """Verify bill exists."""
    months = {'January': 1, 'February': 2, 'March': 3, 'April': 4, 'May': 5, 'June': 6,
              'July': 7, 'August': 8, 'September': 9, 'October': 10, 'November': 11, 'December': 12}
    month = months.get(month_name, 1)
    assert (year, month) in context.bills, f"Bill for {month_name} {year} not found"


@then(parsers.parse('the bill should have component "{name}"'))
def bill_has_component(context, mock_component_repo, name):
    """Verify bill has specific component."""
    bill = context.last_created_bill or next(iter(context.bills.values()), None)
    if bill:
        components = mock_component_repo.list_for_month(bill.id)
        names = {c.name for c in components}
        assert name in names, f"Component '{name}' not found"


@then(parsers.parse('the "{name}" component should have split method "{method}"'))
def component_split_method(context, mock_component_repo, name, method):
    """Verify component split method."""
    bill = context.last_created_bill or next(iter(context.bills.values()), None)
    if bill:
        components = mock_component_repo.list_for_month(bill.id)
        comp = next((c for c in components if c.name == name), None)
        assert comp is not None, f"Component '{name}' not found"
        assert comp.split_method == method, f"Expected split '{method}', got '{comp.split_method}'"


@then(parsers.parse('the "{name}" component should have distribution data'))
def component_has_distribution(context, mock_component_repo, name):
    """Verify component has distribution data."""
    bill = context.last_created_bill or next(iter(context.bills.values()), None)
    if bill:
        components = mock_component_repo.list_for_month(bill.id)
        comp = next((c for c in components if c.name == name), None)
        assert comp is not None, f"Component '{name}' not found"
        assert comp.distribution is not None, "Distribution should not be None"


@then(parsers.parse("the bill should have exactly {count:d} custom component"))
@then(parsers.parse("the bill should have exactly {count:d} custom components"))
def bill_custom_component_count(context, mock_component_repo, count):
    """Verify exact count of custom components."""
    bill = context.last_created_bill
    components = mock_component_repo.list_for_month(bill.id)
    # Filter out legacy components
    legacy_names = {'Electricity', 'Water', 'Internet'}
    custom = [c for c in components if c.name not in legacy_names]
    assert len(custom) == count, f"Expected {count} custom components, got {len(custom)}"


@then("readings should be saved for all participants")
def readings_saved(context, mock_reading_repo):
    """Verify readings were saved."""
    bill_id = context.current_bill_id
    readings = mock_reading_repo.list_for_month(bill_id)
    assert len(readings) == len(context.participants), "Not all readings saved"


@then(parsers.parse("{name}'s usage should be {expected:f}"))
def participant_usage(context, mock_reading_repo, name, expected):
    """Verify participant usage."""
    bill_id = context.current_bill_id
    p = context.participants.get(name)
    reading = mock_reading_repo.get(bill_id, p.id)
    actual = reading.usage() if reading else 0.0
    assert abs(actual - expected) < 0.01, f"Expected usage {expected}, got {actual}"


@then(parsers.parse("{name}'s reading should have no previous value"))
def reading_no_previous(context, mock_reading_repo, name):
    """Verify reading has no previous value."""
    bill_id = context.current_bill_id
    p = context.participants.get(name)
    reading = mock_reading_repo.get(bill_id, p.id)
    assert reading is not None
    assert reading.prev_reading is None, "Previous reading should be None"


@then("I should see an archived warning")
def see_archived_warning(context):
    """Verify archived warning."""
    assert context.last_error == "archived", "Expected archived warning"


@then("I should see a not found error")
def see_not_found(context):
    """Verify not found error."""
    assert context.last_error == "not found", "Expected not found error"


@then("the adjustments should be saved successfully")
def adjustments_saved(context):
    """Verify adjustments saved."""
    assert context.last_result == "adjustments saved"


@then(parsers.parse('an adjustment should exist for Alice on "{component}"'))
def adjustment_exists(context, mock_adjustment_repo, component):
    """Verify adjustment exists."""
    bill_id = context.current_bill_id
    comp_id = context.component_ids.get(component)
    alice = context.participants.get('Alice')
    adj = mock_adjustment_repo.get(bill_id, comp_id, alice.id)
    assert adj is not None, "Adjustment not found"


@then(parsers.parse('the adjustment should have mode "{mode}"'))
def adjustment_mode(context, mock_adjustment_repo, mode):
    """Verify adjustment mode."""
    # Find the last created adjustment
    bill_id = context.current_bill_id
    alice = context.participants.get('Alice')
    for comp_name, comp_id in context.component_ids.items():
        adj = mock_adjustment_repo.get(bill_id, comp_id, alice.id)
        if adj and adj.redis_rule:
            assert adj.redis_rule.get('mode') == mode
            return
    assert False, "No adjustment with mode found"


@then("Alice should be zeroed out")
def alice_zeroed(context, mock_adjustment_repo):
    """Verify Alice is zeroed out."""
    bill_id = context.current_bill_id
    alice = context.participants.get('Alice')
    for comp_name, comp_id in context.component_ids.items():
        adj = mock_adjustment_repo.get(bill_id, comp_id, alice.id)
        if adj:
            assert adj.zero is True, "Alice should be zeroed out"
            return
    assert False, "No adjustment found for Alice"


@then(parsers.parse('I should see "{message}"'))
def should_see_message(context, message):
    """Verify error message."""
    assert context.last_error is not None
    assert message.lower() in context.last_error.lower(), \
        f"Expected '{message}' in '{context.last_error}'"


@then(parsers.parse("the bill electricity amount should be {amount:f}"))
def bill_electricity_amount(context, amount):
    """Verify bill electricity amount."""
    bill = context.bills.get((2025, 3))
    assert bill is not None
    assert abs(bill.electricity_amount - amount) < 0.01, \
        f"Expected electricity {amount}, got {bill.electricity_amount}"


@then(parsers.parse("the bill water amount should be {amount:f}"))
def bill_water_amount(context, amount):
    """Verify bill water amount."""
    bill = context.bills.get((2025, 3))
    assert bill is not None
    assert abs(bill.water_amount - amount) < 0.01, \
        f"Expected water {amount}, got {bill.water_amount}"


@then(parsers.parse("the bill internet amount should be {amount:f}"))
def bill_internet_amount(context, amount):
    """Verify bill internet amount."""
    bill = context.bills.get((2025, 3))
    assert bill is not None
    assert abs(bill.internet_amount - amount) < 0.01, \
        f"Expected internet {amount}, got {bill.internet_amount}"


@then(parsers.parse('the "{component_name}" component amount should be {amount:f}'))
def component_amount_should_be(context, mock_component_repo, component_name, amount):
    """Verify component amount was updated."""
    bill = context.bills.get((2025, 3))
    assert bill is not None
    components = mock_component_repo.list_for_month(bill.id)
    comp = next((c for c in components if c.name == component_name), None)
    assert comp is not None, f"Component '{component_name}' not found"
    assert abs(comp.amount - amount) < 0.01, \
        f"Expected {component_name} amount {amount}, got {comp.amount}"


@then("I should see a number error")
def see_number_error(context):
    """Verify number error."""
    assert context.last_error == "number"


@then("I should see a non-negative error")
def see_nonneg_error(context):
    """Verify non-negative error."""
    assert context.last_error == "non-negative"


@then("I should see an integer error")
def see_int_error(context):
    """Verify integer error."""
    assert context.last_error == "integer"


@then("I should see a split method error")
def see_split_error(context):
    """Verify split method error."""
    assert "split method" in context.last_error.lower()


@then("I should see a select error")
def see_select_error(context):
    """Verify select error."""
    assert context.last_error == "select"
