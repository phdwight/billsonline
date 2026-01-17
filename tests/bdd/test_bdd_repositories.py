"""Step definitions for repositories.feature."""
import pytest
from pytest_bdd import scenarios, given, when, then, parsers

from app import create_app
from app.extensions import db
from app.models import Participant, MonthlyBill, MeterReading, BillComponent, ComponentAdjustment
from app.repositories import (
    ParticipantRepository, MonthlyBillRepository, MeterReadingRepository,
    BillComponentRepository, ComponentAdjustmentRepository,
    MonthParticipantRepository
)

scenarios('../features/repositories.feature')


def _datatable_to_dicts(datatable):
    """Convert pytest-bdd datatable (list of lists) to list of dicts."""
    headers = datatable[0]
    return [dict(zip(headers, row)) for row in datatable[1:]]


# ============ Fixtures ============
@pytest.fixture
def repo_app():
    """Create application with test config."""
    app = create_app()
    app.config.update({
        "TESTING": True,
        "SQLALCHEMY_DATABASE_URI": "sqlite:///:memory:",
        "WTF_CSRF_ENABLED": False,
    })
    with app.app_context():
        db.create_all()
        yield app
        db.session.remove()
        db.drop_all()


@pytest.fixture
def repo_context(repo_app):
    """Context for repository tests - store IDs not objects."""
    return {
        'app': repo_app,
        'p_repo': ParticipantRepository(),
        'b_repo': MonthlyBillRepository(),
        'r_repo': MeterReadingRepository(),
        'mp_repo': MonthParticipantRepository(),
        'c_repo': BillComponentRepository(),
        'ca_repo': ComponentAdjustmentRepository(),
        # Store IDs instead of objects
        'participant_id': None,
        'participant_ids': [],
        'bill_id': None,
        'bill_ids': [],
        'reading_id': None,
        'component_id': None,
        'component_ids': [],
        'adjustment_id': None,
        # For assertions that need actual values
        'result': None,
        'count': None,
        'names': [],
        'prev_bill_data': None,  # Dict with year, month
        'page_data': None,  # Dict with items count, total
    }


# ============ Helper Functions ============
def _get_participant(ctx):
    """Get participant by stored ID."""
    return db.session.get(Participant, ctx['participant_id'])


def _get_bill(ctx):
    """Get bill by stored ID."""
    return db.session.get(MonthlyBill, ctx['bill_id'])


def _get_component(ctx):
    """Get component by stored ID."""
    return db.session.get(BillComponent, ctx['component_id'])


def _get_reading(ctx):
    """Get reading by stored ID."""
    return db.session.get(MeterReading, ctx['reading_id'])


def _get_adjustment(ctx):
    """Get adjustment by stored ID."""
    return db.session.get(ComponentAdjustment, ctx['adjustment_id'])


# ============ Given Steps ============
@given('the database is initialized')
def db_initialized(repo_context):
    pass


@given(parsers.parse('I add participants "{names}" via repository'))
def add_participants(repo_context, names):
    with repo_context['app'].app_context():
        for name in (n.strip() for n in names.split(',')):
            p = repo_context['p_repo'].add(name)
            repo_context['participant_ids'].append(p.id)


@given(parsers.parse('I add a participant "{name}" via repository'))
def add_participant(repo_context, name):
    with repo_context['app'].app_context():
        p = repo_context['p_repo'].add(name)
        repo_context['participant_id'] = p.id


@given(parsers.parse('a participant "{name}" exists'))
def participant_exists(repo_context, name):
    with repo_context['app'].app_context():
        p = repo_context['p_repo'].add(name)
        repo_context['participant_id'] = p.id


@given(parsers.parse('participants "{names}" exist'))
def participants_exist(repo_context, names):
    with repo_context['app'].app_context():
        for name in (n.strip() for n in names.split(',')):
            p = repo_context['p_repo'].add(name)
            repo_context['participant_ids'].append(p.id)


@given('I create bills:')
def create_bills_table(repo_context, datatable):
    rows = _datatable_to_dicts(datatable)
    with repo_context['app'].app_context():
        for row in rows:
            year = int(row['year'])
            month = int(row['month'])
            archived = row.get('archived', 'false').lower() == 'true'
            bill = repo_context['b_repo'].create(year, month, 100.0, 50.0, 30.0)
            if archived:
                repo_context['b_repo'].set_archived(bill.id, True)
            repo_context['bill_ids'].append(bill.id)


@given(parsers.parse('I create bills for months {start:d} through {end:d} of {year:d}'))
def create_bills_range(repo_context, start, end, year):
    with repo_context['app'].app_context():
        for m in range(start, end + 1):
            bill = repo_context['b_repo'].create(year, m, 100.0, 50.0, 30.0)
            repo_context['bill_ids'].append(bill.id)


@given(parsers.parse('I create a bill for year {year:d} month {month:d} via repository'))
def create_bill_repo(repo_context, year, month):
    with repo_context['app'].app_context():
        bill = repo_context['b_repo'].create(year, month, 100.0, 50.0, 30.0)
        repo_context['bill_id'] = bill.id


@given(parsers.parse('I create a bill for year {year:d} month {month:d} with amounts {elec:f}, {water:f}, {inet:f} via repository'))
def create_bill_amounts_repo(repo_context, year, month, elec, water, inet):
    with repo_context['app'].app_context():
        bill = repo_context['b_repo'].create(year, month, elec, water, inet)
        repo_context['bill_id'] = bill.id


@given(parsers.parse('a bill for year {year:d} month {month:d} exists'))
def bill_exists(repo_context, year, month):
    with repo_context['app'].app_context():
        bill = repo_context['b_repo'].create(year, month, 100.0, 50.0, 30.0)
        repo_context['bill_id'] = bill.id


@given(parsers.parse('a reading exists with current {current:f} and previous {previous:f}'))
def reading_exists(repo_context, current, previous):
    with repo_context['app'].app_context():
        reading = repo_context['r_repo'].upsert(
            repo_context['bill_id'],
            repo_context['participant_id'],
            current, previous
        )
        repo_context['reading_id'] = reading.id


@given('readings exist for both participants')
def readings_for_both(repo_context):
    with repo_context['app'].app_context():
        for pid in repo_context['participant_ids']:
            repo_context['r_repo'].upsert(
                repo_context['bill_id'],
                pid,
                100.0, 50.0
            )


@given('the participant is linked to the month')
def participant_linked(repo_context):
    with repo_context['app'].app_context():
        repo_context['mp_repo'].add(
            repo_context['bill_id'],
            repo_context['participant_id']
        )


@given('components exist:')
def components_exist(repo_context, datatable):
    rows = _datatable_to_dicts(datatable)
    with repo_context['app'].app_context():
        for row in rows:
            comp = repo_context['c_repo'].add(
                repo_context['bill_id'],
                row['name'],
                float(row['amount']),
                position=int(row['position'])
            )
            repo_context['component_ids'].append(comp.id)


@given(parsers.parse('a component "{name}" exists with amount {amount:f}'))
def component_exists(repo_context, name, amount):
    with repo_context['app'].app_context():
        comp = repo_context['c_repo'].add(
            repo_context['bill_id'],
            name,
            amount,
            split_method='equal'
        )
        repo_context['component_id'] = comp.id


@given(parsers.parse('a component "{name}" exists'))
def component_exists_name(repo_context, name):
    with repo_context['app'].app_context():
        comp = repo_context['c_repo'].add(
            repo_context['bill_id'],
            name,
            100.0
        )
        repo_context['component_id'] = comp.id


@given('a participant exists')
def a_participant_exists(repo_context):
    with repo_context['app'].app_context():
        p = repo_context['p_repo'].add("TestParticipant")
        repo_context['participant_id'] = p.id


@given(parsers.parse('an adjustment exists with zero flag {flag}'))
def adjustment_exists_flag(repo_context, flag):
    with repo_context['app'].app_context():
        zero = flag.lower() == 'true'
        adj = repo_context['ca_repo'].upsert(
            repo_context['bill_id'],
            repo_context['component_id'],
            repo_context['participant_id'],
            zero
        )
        repo_context['adjustment_id'] = adj.id


@given('an adjustment exists')
def adjustment_exists(repo_context):
    with repo_context['app'].app_context():
        adj = repo_context['ca_repo'].upsert(
            repo_context['bill_id'],
            repo_context['component_id'],
            repo_context['participant_id'],
            True
        )
        repo_context['adjustment_id'] = adj.id


@given('adjustments exist for both participants')
def adjustments_for_both(repo_context):
    with repo_context['app'].app_context():
        for i, pid in enumerate(repo_context['participant_ids']):
            repo_context['ca_repo'].upsert(
                repo_context['bill_id'],
                repo_context['component_id'],
                pid,
                i == 0
            )


# ============ When Steps ============
@when(parsers.parse('I add a participant "{name}" via repository'))
def when_add_participant(repo_context, name):
    with repo_context['app'].app_context():
        p = repo_context['p_repo'].add(name)
        repo_context['participant_id'] = p.id


@when('I list all participants')
def list_participants(repo_context):
    with repo_context['app'].app_context():
        participants = repo_context['p_repo'].list_all()
        repo_context['names'] = [p.name for p in participants]
        repo_context['count'] = len(participants)


@when('I get the participant by ID')
def get_participant_by_id(repo_context):
    with repo_context['app'].app_context():
        p = repo_context['p_repo'].get(repo_context['participant_id'])
        repo_context['result'] = p.name if p else None


@when(parsers.parse('I get participant with ID {pid:d}'))
def get_participant_specific_id(repo_context, pid):
    with repo_context['app'].app_context():
        p = repo_context['p_repo'].get(pid)
        repo_context['result'] = p.name if p else None


@when(parsers.parse('I update the participant name to "{name}"'))
def update_participant_name(repo_context, name):
    with repo_context['app'].app_context():
        p = repo_context['p_repo'].update(repo_context['participant_id'], name)
        repo_context['result'] = p.name if p else None


@when('I delete the participant')
def delete_participant(repo_context):
    with repo_context['app'].app_context():
        repo_context['p_repo'].delete(repo_context['participant_id'])
        p = repo_context['p_repo'].get(repo_context['participant_id'])
        repo_context['result'] = p.name if p else None


@when(parsers.parse('I create a bill for year {year:d} month {month:d} with amounts {elec:f}, {water:f}, {inet:f} via repository'))
def when_create_bill(repo_context, year, month, elec, water, inet):
    with repo_context['app'].app_context():
        bill = repo_context['b_repo'].create(year, month, elec, water, inet)
        repo_context['bill_id'] = bill.id


@when('I list all bills')
def list_bills(repo_context):
    with repo_context['app'].app_context():
        bills = repo_context['b_repo'].list_all()
        repo_context['count'] = len(bills)
        # Store first bill's month for single-bill assertions
        if len(bills) == 1:
            repo_context['result'] = bills[0].month


@when(parsers.parse('I list bills page {page:d} with {per_page:d} per page'))
def list_bills_paginated(repo_context, page, per_page):
    with repo_context['app'].app_context():
        page_result = repo_context['b_repo'].list_paginated(page, per_page)
        repo_context['page_data'] = {
            'items_count': len(page_result.items),
            'total': page_result.total
        }


@when('I get the bill by ID')
def get_bill_by_id(repo_context):
    with repo_context['app'].app_context():
        b = repo_context['b_repo'].get_by_id(repo_context['bill_id'])
        repo_context['result'] = b.month if b else None


@when(parsers.parse('I get the previous bill for {year:d} month {month:d}'))
def get_previous_bill(repo_context, year, month):
    with repo_context['app'].app_context():
        prev = repo_context['b_repo'].get_previous(year, month)
        repo_context['prev_bill_data'] = {'year': prev.year, 'month': prev.month} if prev else None


@when(parsers.parse('I find the bill by year {year:d} and month {month:d}'))
def find_bill(repo_context, year, month):
    with repo_context['app'].app_context():
        b = repo_context['b_repo'].find_by_year_month(year, month)
        repo_context['result'] = b.month if b else None


@when(parsers.parse('I update the bill amounts to {elec:f}, {water:f}, {inet:f}'))
def update_bill_amounts(repo_context, elec, water, inet):
    with repo_context['app'].app_context():
        repo_context['b_repo'].update_amounts(repo_context['bill_id'], elec, water, inet)


@when('I delete the bill')
def delete_bill(repo_context):
    with repo_context['app'].app_context():
        repo_context['b_repo'].delete(repo_context['bill_id'])
        b = repo_context['b_repo'].get_by_id(repo_context['bill_id'])
        repo_context['result'] = b is not None


@when('I set the bill as archived')
def set_archived(repo_context):
    with repo_context['app'].app_context():
        repo_context['b_repo'].set_archived(repo_context['bill_id'], True)


@when(parsers.parse('I upsert a reading with current {current:f} and previous {previous:f}'))
def upsert_reading(repo_context, current, previous):
    with repo_context['app'].app_context():
        reading = repo_context['r_repo'].upsert(
            repo_context['bill_id'],
            repo_context['participant_id'],
            current, previous
        )
        repo_context['reading_id'] = reading.id


@when('I list readings for the month')
def list_readings(repo_context):
    with repo_context['app'].app_context():
        readings = repo_context['r_repo'].list_for_month(repo_context['bill_id'])
        repo_context['count'] = len(readings)


@when('I add the participant to the month')
def add_to_month(repo_context):
    with repo_context['app'].app_context():
        repo_context['mp_repo'].add(repo_context['bill_id'], repo_context['participant_id'])


@when('I add the participant to the month twice')
def add_to_month_twice(repo_context):
    with repo_context['app'].app_context():
        repo_context['mp_repo'].add(repo_context['bill_id'], repo_context['participant_id'])
        repo_context['mp_repo'].add(repo_context['bill_id'], repo_context['participant_id'])


@when('I list participants for the month')
def list_month_participants(repo_context):
    with repo_context['app'].app_context():
        members = repo_context['mp_repo'].list_for_month(repo_context['bill_id'])
        repo_context['count'] = len(members)


@when('I remove the participant from the month')
def remove_from_month(repo_context):
    with repo_context['app'].app_context():
        repo_context['mp_repo'].remove(repo_context['bill_id'], repo_context['participant_id'])


@when(parsers.parse('I add a component "{name}" with amount {amount:f} and split method "{method}"'))
def add_component(repo_context, name, amount, method):
    with repo_context['app'].app_context():
        comp = repo_context['c_repo'].add(
            repo_context['bill_id'], name, amount, method, position=0
        )
        repo_context['component_id'] = comp.id


@when(parsers.parse('I add a component "{name}" with amount {amount:f} and distribution:'))
def add_component_dist(repo_context, name, amount, datatable):
    rows = _datatable_to_dicts(datatable)
    with repo_context['app'].app_context():
        dist = {}
        for row in rows:
            dist[int(row['participant_id'])] = int(row['percent'])
        comp = repo_context['c_repo'].add(
            repo_context['bill_id'], name, amount, 'percentage', distribution=dist
        )
        repo_context['component_id'] = comp.id


@when('I list components for the month')
def list_components(repo_context):
    with repo_context['app'].app_context():
        components = repo_context['c_repo'].list_for_month(repo_context['bill_id'])
        repo_context['names'] = [c.name for c in components]
        repo_context['count'] = len(components)


@when(parsers.parse('I update the component to name "{name}" with amount {amount:f} and split method "{method}"'))
def update_component(repo_context, name, amount, method):
    with repo_context['app'].app_context():
        repo_context['c_repo'].update(
            repo_context['component_id'], name=name, amount=amount, split_method=method
        )


@when('I delete the component')
def delete_component(repo_context):
    with repo_context['app'].app_context():
        repo_context['c_repo'].delete(repo_context['component_id'])


@when(parsers.parse('I upsert an adjustment with zero flag {flag}'))
def upsert_adjustment(repo_context, flag):
    with repo_context['app'].app_context():
        zero = flag.lower() == 'true'
        adj = repo_context['ca_repo'].upsert(
            repo_context['bill_id'],
            repo_context['component_id'],
            repo_context['participant_id'],
            zero
        )
        repo_context['adjustment_id'] = adj.id


@when('I list adjustments for the month')
def list_adjustments(repo_context):
    with repo_context['app'].app_context():
        adjustments = repo_context['ca_repo'].list_for_month(repo_context['bill_id'])
        repo_context['count'] = len(adjustments)


@when('I clear adjustments for the month')
def clear_adjustments(repo_context):
    with repo_context['app'].app_context():
        repo_context['ca_repo'].clear_for_month(repo_context['bill_id'])


# ============ Then Steps ============
@then('the participant should have an ID')
def participant_has_id(repo_context):
    assert repo_context['participant_id'] is not None


@then(parsers.parse('the participant name should be "{name}"'))
def participant_name_is(repo_context, name):
    with repo_context['app'].app_context():
        p = _get_participant(repo_context)
        assert p.name == name


@then(parsers.parse('the participants should be in order "{order}"'))
def participants_in_order(repo_context, order):
    expected = [n.strip() for n in order.split(',')]
    assert repo_context['names'] == expected


@then('the participant should be found')
def participant_found(repo_context):
    assert repo_context['result'] is not None


@then('the result should be none')
def result_is_none(repo_context):
    assert repo_context['result'] is None


@then('the participant should no longer exist')
def participant_deleted(repo_context):
    assert repo_context['result'] is None


@then('the bill should have an ID')
def bill_has_id(repo_context):
    assert repo_context['bill_id'] is not None


@then(parsers.parse('the bill year should be {year:d}'))
def bill_year_is(repo_context, year):
    with repo_context['app'].app_context():
        b = _get_bill(repo_context)
        assert b.year == year


@then(parsers.parse('the bill month should be {month:d}'))
def bill_month_is(repo_context, month):
    if repo_context['result'] is not None:
        assert repo_context['result'] == month
    else:
        with repo_context['app'].app_context():
            b = _get_bill(repo_context)
            assert b.month == month


@then(parsers.parse('only {count:d} bill should be returned'))
def bills_count(repo_context, count):
    assert repo_context['count'] == count


@then(parsers.parse('{count:d} bills should be returned'))
def n_bills_returned(repo_context, count):
    assert repo_context['page_data']['items_count'] == count


@then(parsers.parse('the total count should be {count:d}'))
def total_count(repo_context, count):
    assert repo_context['page_data']['total'] == count


@then(parsers.parse('the previous bill month should be {month:d}'))
def prev_bill_month(repo_context, month):
    assert repo_context['prev_bill_data']['month'] == month


@then(parsers.parse('the previous bill year should be {year:d}'))
def prev_bill_year(repo_context, year):
    assert repo_context['prev_bill_data']['year'] == year


@then('the bill should be found')
def bill_found(repo_context):
    assert repo_context['result'] is not None


@then('the bill should not be found')
def bill_not_found(repo_context):
    assert repo_context['result'] is None


@then(parsers.parse('the electricity amount should be {amount:f}'))
def elec_amount_is(repo_context, amount):
    with repo_context['app'].app_context():
        b = _get_bill(repo_context)
        assert b.electricity_amount == amount


@then(parsers.parse('the water amount should be {amount:f}'))
def water_amount_is(repo_context, amount):
    with repo_context['app'].app_context():
        b = _get_bill(repo_context)
        assert b.water_amount == amount


@then(parsers.parse('the internet amount should be {amount:f}'))
def inet_amount_is(repo_context, amount):
    with repo_context['app'].app_context():
        b = _get_bill(repo_context)
        assert b.internet_amount == amount


@then('the bill should no longer exist')
def bill_deleted(repo_context):
    assert repo_context['result'] is False


@then('the bill should not be archived')
def bill_not_archived(repo_context):
    with repo_context['app'].app_context():
        b = _get_bill(repo_context)
        assert b.archived is False


@then('the bill should be archived')
def bill_archived(repo_context):
    with repo_context['app'].app_context():
        b = _get_bill(repo_context)
        assert b.archived is True


@then(parsers.parse('the reading current should be {value:f}'))
def reading_current(repo_context, value):
    with repo_context['app'].app_context():
        r = _get_reading(repo_context)
        assert r.reading_current == value


@then(parsers.parse('the reading previous should be {value:f}'))
def reading_previous(repo_context, value):
    with repo_context['app'].app_context():
        r = _get_reading(repo_context)
        assert r.reading_previous == value


@then(parsers.parse('there should be only {count:d} reading for the month'))
def reading_count(repo_context, count):
    with repo_context['app'].app_context():
        readings = repo_context['r_repo'].list_for_month(repo_context['bill_id'])
        assert len(readings) == count


@then(parsers.parse('{count:d} readings should be returned'))
def n_readings_returned(repo_context, count):
    assert repo_context['count'] == count


@then(parsers.parse('{count:d} participant should be linked'))
def n_participants_linked(repo_context, count):
    assert repo_context['count'] == count


@then(parsers.parse('{count:d} participants should be linked'))
def n_participants_linked_plural(repo_context, count):
    assert repo_context['count'] == count


@then('the component should have an ID')
def component_has_id(repo_context):
    assert repo_context['component_id'] is not None


@then(parsers.parse('the component name should be "{name}"'))
def component_name_is(repo_context, name):
    with repo_context['app'].app_context():
        c = _get_component(repo_context)
        assert c.name == name


@then(parsers.parse('the component amount should be {amount:f}'))
def component_amount_is(repo_context, amount):
    with repo_context['app'].app_context():
        c = _get_component(repo_context)
        assert c.amount == amount


@then(parsers.parse('the component split method should be "{method}"'))
def component_method_is(repo_context, method):
    with repo_context['app'].app_context():
        c = _get_component(repo_context)
        assert c.split_method == method


@then(parsers.parse('the component distribution should have {count:d} entries'))
def distribution_entries(repo_context, count):
    with repo_context['app'].app_context():
        c = _get_component(repo_context)
        assert len(c.distribution) == count


@then(parsers.parse('the distribution sum should be {total:d}'))
def distribution_sum(repo_context, total):
    with repo_context['app'].app_context():
        c = _get_component(repo_context)
        assert sum(c.distribution.values()) == total


@then(parsers.parse('the components should be in order "{order}"'))
def components_in_order(repo_context, order):
    expected = [n.strip() for n in order.split(',')]
    assert repo_context['names'] == expected


@then(parsers.parse('{count:d} components should exist for the month'))
def n_components_for_month(repo_context, count):
    with repo_context['app'].app_context():
        comps = repo_context['c_repo'].list_for_month(repo_context['bill_id'])
        assert len(comps) == count


@then(parsers.parse('the adjustment zero flag should be {flag}'))
def adjustment_flag_is(repo_context, flag):
    with repo_context['app'].app_context():
        adj = _get_adjustment(repo_context)
        expected = flag.lower() == 'true'
        assert adj.zero == expected


@then(parsers.parse('there should be only {count:d} adjustment for the month'))
def one_adjustment(repo_context, count):
    with repo_context['app'].app_context():
        adjs = repo_context['ca_repo'].list_for_month(repo_context['bill_id'])
        assert len(adjs) == count


@then(parsers.parse('{count:d} adjustments should be returned'))
def n_adjustments_returned(repo_context, count):
    assert repo_context['count'] == count


@then(parsers.parse('{count:d} adjustments should exist for the month'))
def n_adjustments_for_month(repo_context, count):
    with repo_context['app'].app_context():
        adjs = repo_context['ca_repo'].list_for_month(repo_context['bill_id'])
        assert len(adjs) == count
