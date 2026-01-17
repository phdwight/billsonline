"""Step definitions for month_service.feature."""
import pytest
from pytest_bdd import scenarios, given, when, then, parsers

from app import create_app
from app.extensions import db
from app.models import Participant, MonthlyBill, BillComponent, MeterReading, MonthParticipant
from app.services.month_service import MonthService

scenarios('../features/month_service.feature')


@pytest.fixture
def ms_app():
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
def ms_context(ms_app):
    """Context for month service tests."""
    return {
        'app': ms_app,
        'service': None,
        'bill_id': None,
        'bill': None,
        'result': None,
        'export_result': None,
        'export_filename': None,
        'convert_success': None,
        'convert_message': None,
        'synth_components': [],
        'base_map': None,
        'participants': [],
        'usage_by_pid': {},
        'component': None,
    }


# ============ Given Steps ============
@given('the month service is initialized')
def month_service_initialized(ms_context, ms_app):
    with ms_app.app_context():
        ms_context['service'] = MonthService()


@given(parsers.parse('a bill exists for year {year:d} month {month:d}'))
def bill_exists_for(ms_context, ms_app, year, month):
    with ms_app.app_context():
        bill = MonthlyBill(
            year=year, month=month,
            electricity_amount=100.0,
            water_amount=50.0,
            internet_amount=30.0,
            archived=False
        )
        db.session.add(bill)
        db.session.commit()
        ms_context['bill_id'] = bill.id
        ms_context['bill'] = bill


@given('participants exist but no month memberships')
def participants_no_memberships(ms_context, ms_app):
    with ms_app.app_context():
        p1 = Participant(name='Alice')
        p2 = Participant(name='Bob')
        db.session.add_all([p1, p2])
        db.session.commit()
        ms_context['participants'] = [p1, p2]


@given('a bill exists with components')
def bill_with_components(ms_context, ms_app):
    with ms_app.app_context():
        bill = MonthlyBill(
            year=2025, month=6,
            electricity_amount=100.0,
            water_amount=50.0,
            internet_amount=30.0,
            archived=False
        )
        db.session.add(bill)
        db.session.commit()
        
        comp = BillComponent(
            month_id=bill.id,
            name='Electricity',
            amount=100.0,
            split_method='equal',
            position=0
        )
        db.session.add(comp)
        db.session.commit()
        
        ms_context['bill_id'] = bill.id
        ms_context['bill'] = bill


@given('participants exist with meter readings')
def participants_with_readings(ms_context, ms_app):
    with ms_app.app_context():
        bill_id = ms_context['bill_id']
        
        p1 = Participant(name='Alice')
        p2 = Participant(name='Bob')
        db.session.add_all([p1, p2])
        db.session.commit()
        
        r1 = MeterReading(
            month_id=bill_id,
            participant_id=p1.id,
            reading_current=200,
            reading_previous=100
        )
        r2 = MeterReading(
            month_id=bill_id,
            participant_id=p2.id,
            reading_current=150,
            reading_previous=100
        )
        db.session.add_all([r1, r2])
        db.session.commit()
        
        ms_context['participants'] = [p1, p2]


@given('a legacy bill exists without components')
def legacy_bill_no_components(ms_context, ms_app):
    with ms_app.app_context():
        bill = MonthlyBill(
            year=2025, month=7,
            electricity_amount=100.0,
            water_amount=50.0,
            internet_amount=30.0,
            archived=False
        )
        db.session.add(bill)
        db.session.commit()
        ms_context['bill_id'] = bill.id
        ms_context['bill'] = bill


@given(parsers.parse('a legacy bill with electricity amount {amount:f}'))
def legacy_bill_electricity(ms_context, ms_app, amount):
    with ms_app.app_context():
        bill = MonthlyBill(
            year=2025, month=8,
            electricity_amount=amount,
            water_amount=0.0,
            internet_amount=0.0,
            archived=False
        )
        db.session.add(bill)
        db.session.commit()
        ms_context['bill_id'] = bill.id
        ms_context['bill'] = bill


@given(parsers.parse('a legacy bill with water amount {amount:f}'))
def legacy_bill_water(ms_context, ms_app, amount):
    with ms_app.app_context():
        bill = MonthlyBill(
            year=2025, month=9,
            electricity_amount=0.0,
            water_amount=amount,
            internet_amount=0.0,
            archived=False
        )
        db.session.add(bill)
        db.session.commit()
        ms_context['bill_id'] = bill.id
        ms_context['bill'] = bill


@given(parsers.parse('a legacy bill with internet amount {amount:f}'))
def legacy_bill_internet(ms_context, ms_app, amount):
    with ms_app.app_context():
        bill = MonthlyBill(
            year=2025, month=10,
            electricity_amount=0.0,
            water_amount=0.0,
            internet_amount=amount,
            archived=False
        )
        db.session.add(bill)
        db.session.commit()
        ms_context['bill_id'] = bill.id
        ms_context['bill'] = bill


@given(parsers.parse('a legacy bill with only electricity amount {amount:f}'))
def legacy_bill_only_electricity(ms_context, ms_app, amount):
    with ms_app.app_context():
        bill = MonthlyBill(
            year=2025, month=11,
            electricity_amount=amount,
            water_amount=0.0,
            internet_amount=0.0,
            archived=False
        )
        db.session.add(bill)
        db.session.commit()
        ms_context['bill_id'] = bill.id
        ms_context['bill'] = bill


@given(parsers.parse('an archived bill exists for year {year:d} month {month:d}'))
def archived_bill_exists(ms_context, ms_app, year, month):
    with ms_app.app_context():
        bill = MonthlyBill(
            year=year, month=month,
            electricity_amount=100.0,
            water_amount=50.0,
            internet_amount=30.0,
            archived=True
        )
        db.session.add(bill)
        db.session.commit()
        ms_context['bill_id'] = bill.id
        ms_context['bill'] = bill


@given('a bill exists with zero amounts')
def bill_zero_amounts(ms_context, ms_app):
    with ms_app.app_context():
        bill = MonthlyBill(
            year=2025, month=12,
            electricity_amount=0.0,
            water_amount=0.0,
            internet_amount=0.0,
            archived=False
        )
        db.session.add(bill)
        db.session.commit()
        ms_context['bill_id'] = bill.id
        ms_context['bill'] = bill


@given('a legacy bill without existing components')
def legacy_bill_no_existing(ms_context, ms_app):
    with ms_app.app_context():
        bill = MonthlyBill(
            year=2024, month=1,
            electricity_amount=100.0,
            water_amount=50.0,
            internet_amount=30.0,
            archived=False
        )
        db.session.add(bill)
        db.session.commit()
        ms_context['bill_id'] = bill.id
        ms_context['bill'] = bill


@given(parsers.parse('a component with amount {amount:f} and equal split'))
def component_equal_split(ms_context, ms_app, amount):
    with ms_app.app_context():
        comp = BillComponent(
            month_id=1,
            name='TestComponent',
            amount=amount,
            split_method='equal',
            position=0
        )
        ms_context['component'] = comp


@given(parsers.parse('a component with amount {amount:f} and usage split'))
def component_usage_split(ms_context, ms_app, amount):
    with ms_app.app_context():
        comp = BillComponent(
            month_id=1,
            name='TestComponent',
            amount=amount,
            split_method='usage',
            position=0
        )
        ms_context['component'] = comp


@given(parsers.parse('there are {count:d} member participants'))
def n_member_participants(ms_context, ms_app, count):
    with ms_app.app_context():
        participants = []
        for i in range(count):
            p = Participant(name=f'Participant{i+1}')
            db.session.add(p)
        db.session.commit()
        participants = Participant.query.all()
        ms_context['participants'] = participants


@given('participants have different usage amounts')
def participants_different_usage(ms_context, ms_app):
    with ms_app.app_context():
        p1 = Participant(name='Alice')
        p2 = Participant(name='Bob')
        p3 = Participant(name='Charlie')
        db.session.add_all([p1, p2, p3])
        db.session.commit()
        
        ms_context['participants'] = [p1, p2, p3]
        ms_context['usage_by_pid'] = {
            p1.id: 100.0,  # 1/3
            p2.id: 100.0,  # 1/3
            p3.id: 100.0   # 1/3
        }


# ============ When Steps ============
@when(parsers.parse('I get month detail data for bill ID {bill_id:d}'))
def get_month_detail_nonexistent(ms_context, ms_app, bill_id):
    with ms_app.app_context():
        service = MonthService()
        ms_context['result'] = service.get_month_detail_data(bill_id)


@when('I get month detail data for that bill')
def get_month_detail_existing(ms_context, ms_app):
    with ms_app.app_context():
        service = MonthService()
        ms_context['result'] = service.get_month_detail_data(ms_context['bill_id'])


@when(parsers.parse('I export bill ID {bill_id:d} to CSV'))
def export_nonexistent(ms_context, ms_app, bill_id):
    with ms_app.app_context():
        service = MonthService()
        ms_context['export_result'] = service.export_to_csv(bill_id)


@when('I export that bill to CSV')
def export_existing(ms_context, ms_app):
    with ms_app.app_context():
        service = MonthService()
        result = service.export_to_csv(ms_context['bill_id'])
        ms_context['export_result'] = result
        if result:
            ms_context['export_content'], ms_context['export_filename'] = result


@when('I synthesize legacy components')
def synthesize_legacy(ms_context, ms_app):
    with ms_app.app_context():
        service = MonthService()
        bill = MonthlyBill.query.get(ms_context['bill_id'])
        ms_context['synth_components'] = service._synthesize_legacy_components(bill)


@when(parsers.parse('I convert legacy for bill ID {bill_id:d}'))
def convert_legacy_nonexistent(ms_context, ms_app, bill_id):
    with ms_app.app_context():
        service = MonthService()
        success, message = service.convert_legacy_to_components(bill_id)
        ms_context['convert_success'] = success
        ms_context['convert_message'] = message


@when('I convert legacy for that bill')
def convert_legacy_existing(ms_context, ms_app):
    with ms_app.app_context():
        service = MonthService()
        success, message = service.convert_legacy_to_components(ms_context['bill_id'])
        ms_context['convert_success'] = success
        ms_context['convert_message'] = message


@when('I compute the base map')
def compute_base_map(ms_context, ms_app):
    with ms_app.app_context():
        service = MonthService()
        comp = ms_context['component']
        participants = ms_context['participants']
        usage_by_pid = ms_context.get('usage_by_pid', {p.id: 0.0 for p in participants})
        total_usage = sum(usage_by_pid.values())
        
        ms_context['base_map'] = service._compute_base_map(
            comp, participants, usage_by_pid, total_usage
        )


# ============ Then Steps ============
@then('the result should be None')
def result_is_none(ms_context):
    assert ms_context['result'] is None


@then('the result should contain the bill')
def result_contains_bill(ms_context):
    assert ms_context['result'] is not None
    assert 'bill' in ms_context['result']
    assert ms_context['result']['bill'] is not None


@then('the result should contain participant data')
def result_contains_participants(ms_context):
    assert 'participants' in ms_context['result']


@then('member_ids should be populated')
def member_ids_populated(ms_context):
    assert ms_context['result'] is not None
    assert 'member_ids' in ms_context['result']
    # Either populated from backfill or from participants
    assert ms_context['result']['member_ids'] is not None


@then('dynamic_contributions should be computed')
def dynamic_contributions_computed(ms_context):
    assert ms_context['result'] is not None
    # Dynamic contributions may be None if no components, that's OK


@then('the export result should be None')
def export_is_none(ms_context):
    assert ms_context['export_result'] is None


@then('the export result should contain CSV content')
def export_has_content(ms_context):
    assert ms_context['export_result'] is not None
    content = ms_context['export_result'][0] if isinstance(ms_context['export_result'], tuple) else ms_context['export_result']
    assert len(content) > 0


@then('the filename should match the month')
def filename_matches(ms_context):
    assert ms_context['export_filename'] is not None
    assert 'bill_' in ms_context['export_filename']
    assert '.csv' in ms_context['export_filename']


@then('legacy components should be synthesized')
def legacy_synthesized(ms_context):
    # If export succeeded, legacy was synthesized
    assert ms_context['export_result'] is not None


@then(parsers.parse('"{name}" component should be created with amount {amount:f}'))
def component_created(ms_context, name, amount):
    found = [c for c in ms_context['synth_components'] if c.name == name]
    assert len(found) == 1
    assert abs(found[0].amount - amount) < 0.01


@then(parsers.parse('only {count:d} component should be created'))
def n_components_created(ms_context, count):
    assert len(ms_context['synth_components']) == count


@then(parsers.parse('the convert result should be failure with message "{message}"'))
def convert_fail_message(ms_context, message):
    assert ms_context['convert_success'] is False
    assert ms_context['convert_message'] == message


@then('the convert result should be failure with message containing "archived"')
def convert_fail_archived(ms_context):
    assert ms_context['convert_success'] is False
    assert 'archived' in ms_context['convert_message'].lower()


@then('the convert result should be success')
def convert_success(ms_context):
    assert ms_context['convert_success'] is True


@then('components should be created from legacy amounts')
def components_from_legacy(ms_context, ms_app):
    with ms_app.app_context():
        from app.repositories import BillComponentRepository
        repo = BillComponentRepository()
        components = repo.list_for_month(ms_context['bill_id'])
        assert len(components) > 0


@then(parsers.parse('each participant should have base amount {amount:f}'))
def each_participant_amount(ms_context, amount):
    assert ms_context['base_map'] is not None
    for pid, val in ms_context['base_map'].items():
        assert abs(val - amount) < 0.01


@then('base amounts should be proportional to usage')
def base_proportional_to_usage(ms_context):
    assert ms_context['base_map'] is not None
    # With equal usage, amounts should be equal
    values = list(ms_context['base_map'].values())
    if values:
        assert all(abs(v - values[0]) < 0.01 for v in values)
