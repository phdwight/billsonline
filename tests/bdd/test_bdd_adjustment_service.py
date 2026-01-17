"""Step definitions for adjustment_service.feature."""
import pytest
from pytest_bdd import scenarios, given, when, then, parsers

from app import create_app
from app.extensions import db
from app.models import Participant, MonthlyBill, BillComponent, MeterReading, MonthParticipant
from app.services.adjustment_service import AdjustmentService
from app.repositories import (
    MonthlyBillRepository,
    ParticipantRepository,
    MeterReadingRepository,
    BillComponentRepository,
    ComponentAdjustmentRepository,
    MonthParticipantRepository,
)

scenarios('../features/adjustment_service.feature')


@pytest.fixture
def adj_app():
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
def adj_context(adj_app):
    """Context for adjustment tests."""
    return {
        'app': adj_app,
        'service': None,
        'component': None,
        'base_amount': None,
        'participant_ids': [],
        'participants': [],
        'usage_by_pid': {},
        'total_usage': 0,
        'validation_result': None,
        'validation_error': None,
        'process_result': None,
        'process_message': None,
        'process_saved': 0,
        'bill_id': None,
        'form_data': {},
    }


# ============ Given Steps ============
@given('the adjustment service is initialized')
def adjustment_service_initialized(adj_context, adj_app):
    with adj_app.app_context():
        adj_context['service'] = AdjustmentService()


@given(parsers.parse('a component "{name}" with amount {amount:f}'))
def component_with_amount(adj_context, adj_app, name, amount):
    with adj_app.app_context():
        comp = BillComponent(
            month_id=1,  # Dummy ID
            name=name,
            amount=amount,
            split_method='equal',
            position=0
        )
        # Don't add to DB - just use for validation
        adj_context['component'] = comp


@given(parsers.parse('the base amount for participant is {amount:f}'))
def set_base_amount(adj_context, amount):
    adj_context['base_amount'] = amount


@given(parsers.parse('a component with amount {amount:f} and split method "{method}"'))
def component_with_split(adj_context, adj_app, amount, method):
    with adj_app.app_context():
        comp = BillComponent(
            month_id=1,
            name='TestComponent',
            amount=amount,
            split_method=method,
            position=0
        )
        adj_context['component'] = comp


@given(parsers.parse('there are {count:d} participants'))
def set_participant_count(adj_context, count):
    adj_context['participant_ids'] = list(range(1, count + 1))


@given(parsers.parse('participant {pid:d} has usage {usage:d} out of total {total:d}'))
def set_participant_usage(adj_context, pid, usage, total):
    adj_context['usage_by_pid'][pid] = float(usage)
    adj_context['total_usage'] = float(total)


@given(parsers.parse('total usage is {total:d}'))
def set_total_usage(adj_context, total):
    adj_context['total_usage'] = float(total)


@given('an archived month exists')
def archived_month_exists(adj_context, adj_app):
    with adj_app.app_context():
        bill = MonthlyBill(
            year=2025, month=1,
            electricity_amount=100.0,
            water_amount=50.0,
            internet_amount=30.0,
            archived=True
        )
        db.session.add(bill)
        db.session.commit()
        adj_context['bill_id'] = bill.id


@given('an active month with components and participants')
def active_month_with_data(adj_context, adj_app):
    with adj_app.app_context():
        # Create participants
        p1 = Participant(name='Alice')
        p2 = Participant(name='Bob')
        p3 = Participant(name='Charlie')
        db.session.add_all([p1, p2, p3])
        db.session.commit()
        
        # Create bill
        bill = MonthlyBill(
            year=2025, month=1,
            electricity_amount=300.0,
            water_amount=150.0,
            internet_amount=100.0,
            archived=False
        )
        db.session.add(bill)
        db.session.commit()
        
        # Create component
        comp = BillComponent(
            month_id=bill.id,
            name='Electricity',
            amount=300.0,
            split_method='equal',
            position=0
        )
        db.session.add(comp)
        db.session.commit()
        
        # Link participants to month
        for p in [p1, p2, p3]:
            mp = MonthParticipant(month_id=bill.id, participant_id=p.id)
            db.session.add(mp)
        db.session.commit()
        
        # Store context
        adj_context['bill_id'] = bill.id
        adj_context['participant_ids'] = [p1.id, p2.id, p3.id]
        adj_context['participants'] = [p1, p2, p3]
        adj_context['component_id'] = comp.id
        adj_context['form_data'] = {}


@given(parsers.parse('participant {pid:d} redistributes {percent:d}% of component {cid:d} to participant {tpid:d}'))
def set_percent_redistribution(adj_context, adj_app, pid, percent, cid, tpid):
    with adj_app.app_context():
        # Find actual participant IDs from the stored list
        actual_pid = adj_context['participant_ids'][pid - 1]
        actual_tpid = adj_context['participant_ids'][tpid - 1]
        actual_cid = adj_context['component_id']
        
        # Set form data
        adj_context['form_data'][f"mode_comp_{actual_cid}_{actual_pid}"] = "percent"
        adj_context['form_data'][f"redis_comp_{actual_cid}_{actual_pid}_{actual_tpid}"] = str(float(percent))


@given(parsers.parse('participant {pid:d} has adjustment notes "{notes}"'))
def set_adjustment_notes(adj_context, adj_app, pid, notes):
    with adj_app.app_context():
        actual_pid = adj_context['participant_ids'][pid - 1]
        actual_cid = adj_context['component_id']
        adj_context['form_data'][f"notes_comp_{actual_cid}_{actual_pid}"] = notes


@given(parsers.parse('participant {pid:d} redistributes their base amount equally to others using amount mode'))
def set_amount_redistribution_equal(adj_context, adj_app, pid):
    with adj_app.app_context():
        actual_pid = adj_context['participant_ids'][pid - 1]
        actual_cid = adj_context['component_id']
        
        # Base amount = 300 / 3 = 100
        # Redistribute 50 to each of the other 2 participants
        other_pids = [p for p in adj_context['participant_ids'] if p != actual_pid]
        
        adj_context['form_data'][f"mode_comp_{actual_cid}_{actual_pid}"] = "amount"
        for i, tpid in enumerate(other_pids):
            # 50 each to make 100 total
            adj_context['form_data'][f"redis_comp_{actual_cid}_{actual_pid}_{tpid}"] = "50.0"


@given(parsers.parse('participant {pid:d} redistributes wrong amount to participant {tpid:d} using amount mode'))
def set_wrong_amount_redistribution(adj_context, adj_app, pid, tpid):
    with adj_app.app_context():
        actual_pid = adj_context['participant_ids'][pid - 1]
        actual_tpid = adj_context['participant_ids'][tpid - 1]
        actual_cid = adj_context['component_id']
        
        # Base amount = 300 / 3 = 100, but we set 50 (wrong)
        adj_context['form_data'][f"mode_comp_{actual_cid}_{actual_pid}"] = "amount"
        adj_context['form_data'][f"redis_comp_{actual_cid}_{actual_pid}_{actual_tpid}"] = "50.0"


# ============ When Steps ============
@when(parsers.parse('I validate a percent rule with targets summing to {total:f}'))
def validate_percent_rule(adj_context, adj_app, total):
    with adj_app.app_context():
        service = AdjustmentService()
        comp = adj_context['component']
        rule = {
            'mode': 'percent',
            'targets': {1: total / 2, 2: total / 2}  # Split evenly for test
        }
        ok, err = service.validate_redistribution_rule(
            comp=comp,
            pid=1,
            rule=rule,
            participant_name='TestParticipant',
            base_amount=adj_context.get('base_amount', comp.amount / 3)
        )
        adj_context['validation_result'] = ok
        adj_context['validation_error'] = err


@when(parsers.parse('I validate an amount rule with targets summing to {total:f}'))
def validate_amount_rule(adj_context, adj_app, total):
    with adj_app.app_context():
        service = AdjustmentService()
        comp = adj_context['component']
        base = adj_context.get('base_amount', comp.amount / 3)
        rule = {
            'mode': 'amount',
            'targets': {1: total / 2, 2: total / 2}  # Split evenly for test
        }
        ok, err = service.validate_redistribution_rule(
            comp=comp,
            pid=1,
            rule=rule,
            participant_name='TestParticipant',
            base_amount=base
        )
        adj_context['validation_result'] = ok
        adj_context['validation_error'] = err


@when('I validate an empty rule')
def validate_empty_rule(adj_context, adj_app):
    with adj_app.app_context():
        service = AdjustmentService()
        comp = adj_context['component']
        ok, err = service.validate_redistribution_rule(
            comp=comp,
            pid=1,
            rule={},
            participant_name='TestParticipant',
            base_amount=100.0
        )
        adj_context['validation_result'] = ok
        adj_context['validation_error'] = err


@when('I validate a None rule')
def validate_none_rule(adj_context, adj_app):
    with adj_app.app_context():
        service = AdjustmentService()
        comp = adj_context['component']
        ok, err = service.validate_redistribution_rule(
            comp=comp,
            pid=1,
            rule=None,
            participant_name='TestParticipant',
            base_amount=100.0
        )
        adj_context['validation_result'] = ok
        adj_context['validation_error'] = err


@when(parsers.parse('I compute the base amount for participant {pid:d}'))
def compute_base_amount(adj_context, adj_app, pid):
    with adj_app.app_context():
        service = AdjustmentService()
        comp = adj_context['component']
        result = service.compute_base_amount(
            comp=comp,
            pid=pid,
            pids=adj_context['participant_ids'],
            usage_by_pid=adj_context.get('usage_by_pid', {}),
            total_usage=adj_context.get('total_usage', 0)
        )
        adj_context['base_amount'] = result


@when(parsers.parse('I process adjustments for bill ID {bill_id:d}'))
def process_adjustments_for_bill(adj_context, adj_app, bill_id):
    with adj_app.app_context():
        service = AdjustmentService()
        success, message, saved = service.process_adjustments(bill_id, {})
        adj_context['process_result'] = success
        adj_context['process_message'] = message
        adj_context['process_saved'] = saved


@when('I process adjustments for that month')
def process_adjustments_for_context_month(adj_context, adj_app):
    with adj_app.app_context():
        service = AdjustmentService()
        success, message, saved = service.process_adjustments(
            adj_context['bill_id'],
            adj_context['form_data']
        )
        adj_context['process_result'] = success
        adj_context['process_message'] = message
        adj_context['process_saved'] = saved


@when('I process the adjustments')
def process_the_adjustments(adj_context, adj_app):
    with adj_app.app_context():
        service = AdjustmentService()
        success, message, saved = service.process_adjustments(
            adj_context['bill_id'],
            adj_context['form_data']
        )
        adj_context['process_result'] = success
        adj_context['process_message'] = message
        adj_context['process_saved'] = saved


@when('I process empty adjustments')
def process_empty_adjustments(adj_context, adj_app):
    with adj_app.app_context():
        service = AdjustmentService()
        success, message, saved = service.process_adjustments(
            adj_context['bill_id'],
            {}  # Empty form data
        )
        adj_context['process_result'] = success
        adj_context['process_message'] = message
        adj_context['process_saved'] = saved


# ============ Then Steps ============
@then('the validation should pass')
def validation_should_pass(adj_context):
    assert adj_context['validation_result'] is True
    assert adj_context['validation_error'] is None


@then('the validation should fail with error containing "must sum to 100%"')
def validation_should_fail_percent(adj_context):
    assert adj_context['validation_result'] is False
    assert adj_context['validation_error'] is not None
    assert 'must sum to 100%' in adj_context['validation_error']


@then('the validation should fail with error containing "must sum to"')
def validation_should_fail_amount(adj_context):
    assert adj_context['validation_result'] is False
    assert adj_context['validation_error'] is not None
    assert 'must sum to' in adj_context['validation_error']


@then(parsers.parse('the base amount should be {expected:f}'))
def base_amount_should_be(adj_context, expected):
    assert abs(adj_context['base_amount'] - expected) < 0.01


@then(parsers.parse('the result should be failure with message "{message}"'))
def result_should_fail_with_message(adj_context, message):
    assert adj_context['process_result'] is False
    assert adj_context['process_message'] == message


@then('the result should be failure with message containing "archived"')
def result_should_fail_archived(adj_context):
    assert adj_context['process_result'] is False
    assert 'archived' in adj_context['process_message'].lower()


@then('the result should be success')
def result_should_be_success(adj_context):
    assert adj_context['process_result'] is True


@then('the result should be failure')
def result_should_be_failure(adj_context):
    assert adj_context['process_result'] is False


@then('the error should contain "must sum to 100%"')
def error_should_contain_percent(adj_context):
    assert 'must sum to 100%' in adj_context['process_message']


@then('the error should contain "must sum to"')
def error_should_contain_sum(adj_context):
    assert 'must sum to' in adj_context['process_message']


@then(parsers.parse('{count:d} redistribution rule should be saved'))
def n_rules_saved(adj_context, count):
    assert adj_context['process_saved'] == count


@then(parsers.parse('{count:d} redistribution rules should be saved'))
def n_rules_saved_plural(adj_context, count):
    assert adj_context['process_saved'] == count


@then('the notes should be saved')
def notes_should_be_saved(adj_context, adj_app):
    with adj_app.app_context():
        repo = ComponentAdjustmentRepository()
        adjs = repo.list_for_month(adj_context['bill_id'])
        notes_found = any(a.notes for a in adjs)
        assert notes_found


@then(parsers.parse('the result should be success with message "{message}"'))
def result_success_with_message(adj_context, message):
    assert adj_context['process_result'] is True
    assert adj_context['process_message'] == message
