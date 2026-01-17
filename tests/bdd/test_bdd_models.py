"""Step definitions for models.feature."""
import pytest
from pytest_bdd import scenarios, given, when, then, parsers

from app import create_app
from app.extensions import db
from app.models import (
    Participant, MonthlyBill, MeterReading, MonthParticipant,
    BillComponent, ComponentAdjustment
)

scenarios('../features/models.feature')


def _datatable_to_dicts(datatable):
    """Convert pytest-bdd datatable (list of lists) to list of dicts."""
    headers = datatable[0]
    return [dict(zip(headers, row)) for row in datatable[1:]]


# ============ Fixtures ============
@pytest.fixture
def model_app():
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
def model_context(model_app):
    """Context for model tests."""
    return {
        'app': model_app,
        'participant': None,
        'bill': None,
        'reading': None,
        'link': None,
        'component': None,
        'adjustment': None,
        'error': None,
    }


# ============ Given Steps ============
@given('the database is initialized')
def db_initialized(model_context):
    pass  # Already done via fixture


@given(parsers.parse('a participant named "{name}" exists'))
def participant_exists(model_context, name):
    with model_context['app'].app_context():
        p = Participant(name=name)
        db.session.add(p)
        db.session.commit()
        model_context['participant'] = p.id


@given(parsers.parse('a bill exists for year {year:d} month {month:d}'))
def bill_exists_model(model_context, year, month):
    with model_context['app'].app_context():
        bill = MonthlyBill(
            year=year, month=month,
            electricity_amount=100.0,
            water_amount=50.0,
            internet_amount=30.0
        )
        db.session.add(bill)
        db.session.commit()
        model_context['bill'] = bill.id


@given(parsers.parse('a participant "{name}" exists'))
def named_participant_exists(model_context, name):
    with model_context['app'].app_context():
        p = Participant(name=name)
        db.session.add(p)
        db.session.commit()
        model_context['participant'] = p.id


@given(parsers.parse('a bill for year {year:d} month {month:d} exists'))
def bill_for_year_month_exists(model_context, year, month):
    with model_context['app'].app_context():
        bill = MonthlyBill(
            year=year, month=month,
            electricity_amount=100.0,
            water_amount=50.0,
            internet_amount=30.0
        )
        db.session.add(bill)
        db.session.commit()
        model_context['bill'] = bill.id


@given('the participant is linked to the month')
def participant_linked(model_context):
    with model_context['app'].app_context():
        mp = MonthParticipant(
            month_id=model_context['bill'],
            participant_id=model_context['participant']
        )
        db.session.add(mp)
        db.session.commit()
        model_context['link'] = mp.id


@given(parsers.parse('a component "{name}" exists for the bill'))
def component_exists(model_context, name):
    with model_context['app'].app_context():
        comp = BillComponent(
            month_id=model_context['bill'],
            name=name,
            amount=100.0,
            split_method="usage"
        )
        db.session.add(comp)
        db.session.commit()
        model_context['component'] = comp.id


# ============ When Steps ============
@when(parsers.parse('I create a participant named "{name}"'))
def create_participant(model_context, name):
    with model_context['app'].app_context():
        p = Participant(name=name)
        db.session.add(p)
        db.session.commit()
        model_context['participant'] = db.session.get(Participant, p.id)


@when(parsers.parse('I try to create a participant named "{name}"'))
def try_create_participant(model_context, name):
    with model_context['app'].app_context():
        p = Participant(name=name)
        db.session.add(p)
        try:
            db.session.commit()
        except Exception as e:
            db.session.rollback()
            model_context['error'] = e


@when(parsers.parse('I create a bill for year {year:d} month {month:d} with amounts {elec:f}, {water:f}, {inet:f}'))
def create_bill(model_context, year, month, elec, water, inet):
    with model_context['app'].app_context():
        bill = MonthlyBill(
            year=year, month=month,
            electricity_amount=elec,
            water_amount=water,
            internet_amount=inet
        )
        db.session.add(bill)
        db.session.commit()
        model_context['bill'] = db.session.get(MonthlyBill, bill.id)


@when(parsers.parse('I try to create another bill for year {year:d} month {month:d}'))
def try_create_duplicate_bill(model_context, year, month):
    with model_context['app'].app_context():
        bill = MonthlyBill(
            year=year, month=month,
            electricity_amount=200.0,
            water_amount=100.0,
            internet_amount=60.0
        )
        db.session.add(bill)
        try:
            db.session.commit()
        except Exception as e:
            db.session.rollback()
            model_context['error'] = e


@when(parsers.parse('I create a meter reading with current {current} and previous {previous}'))
def create_reading(model_context, current, previous):
    with model_context['app'].app_context():
        prev_val = None if previous == 'null' else float(previous)
        reading = MeterReading(
            participant_id=model_context['participant'],
            month_id=model_context['bill'],
            reading_current=float(current),
            reading_previous=prev_val
        )
        model_context['reading'] = reading


@when('I link the participant to the month')
def link_participant(model_context):
    with model_context['app'].app_context():
        mp = MonthParticipant(
            month_id=model_context['bill'],
            participant_id=model_context['participant']
        )
        db.session.add(mp)
        db.session.commit()
        model_context['link'] = db.session.get(MonthParticipant, mp.id)


@when('I try to link the same participant to the same month')
def try_duplicate_link(model_context):
    with model_context['app'].app_context():
        mp = MonthParticipant(
            month_id=model_context['bill'],
            participant_id=model_context['participant']
        )
        db.session.add(mp)
        try:
            db.session.commit()
        except Exception as e:
            db.session.rollback()
            model_context['error'] = e


@when(parsers.parse('I create a component "{name}" with amount {amount:f} and split method "{method}"'))
def create_component(model_context, name, amount, method):
    with model_context['app'].app_context():
        comp = BillComponent(
            month_id=model_context['bill'],
            name=name,
            amount=amount,
            split_method=method,
            position=0
        )
        db.session.add(comp)
        db.session.commit()
        model_context['component'] = db.session.get(BillComponent, comp.id)


@when(parsers.parse('I create a component "{name}" with amount {amount:f} and percentage distribution:'))
def create_component_with_dist(model_context, name, amount, datatable):
    rows = _datatable_to_dicts(datatable)
    with model_context['app'].app_context():
        dist = {}
        for row in rows:
            dist[int(row['participant_id'])] = int(row['percent'])
        
        comp = BillComponent(
            month_id=model_context['bill'],
            name=name,
            amount=amount,
            split_method="percentage",
            distribution=dist
        )
        db.session.add(comp)
        db.session.commit()
        model_context['component'] = db.session.get(BillComponent, comp.id)


@when("I create an adjustment to zero the participant's share")
def create_adjustment(model_context):
    with model_context['app'].app_context():
        adj = ComponentAdjustment(
            month_id=model_context['bill'],
            component_id=model_context['component'],
            participant_id=model_context['participant'],
            zero=True,
            redis_rule={"mode": "percent", "targets": {2: 100}}
        )
        db.session.add(adj)
        db.session.commit()
        model_context['adjustment'] = db.session.get(ComponentAdjustment, adj.id)


# ============ Then Steps ============
@then('the participant should have an ID')
def participant_has_id(model_context):
    assert model_context['participant'].id is not None


@then(parsers.parse('the participant name should be "{name}"'))
def participant_name_is(model_context, name):
    if hasattr(model_context['participant'], 'name'):
        assert model_context['participant'].name == name
    else:
        with model_context['app'].app_context():
            p = db.session.get(Participant, model_context['participant'])
            assert p.name == name


@then('a database error should occur')
def database_error_occurred(model_context):
    assert model_context['error'] is not None


@then('the bill should have an ID')
def bill_has_id(model_context):
    assert model_context['bill'].id is not None


@then('the bill should not be archived by default')
def bill_not_archived(model_context):
    assert model_context['bill'].archived is False


@then(parsers.parse('the usage should be {usage:f}'))
def usage_is(model_context, usage):
    assert model_context['reading'].usage() == usage


@then('the link should have an ID')
def link_has_id(model_context):
    assert model_context['link'].id is not None


@then('the component should have an ID')
def component_has_id(model_context):
    assert model_context['component'].id is not None


@then(parsers.parse('the component name should be "{name}"'))
def component_name_is(model_context, name):
    assert model_context['component'].name == name


@then(parsers.parse('the component distribution should have {count:d} entries'))
def distribution_count(model_context, count):
    assert len(model_context['component'].distribution) == count


@then('the distribution values should sum to 100')
def distribution_sum_100(model_context):
    assert sum(model_context['component'].distribution.values()) == 100


@then('the adjustment should have an ID')
def adjustment_has_id(model_context):
    assert model_context['adjustment'].id is not None


@then('the adjustment zero flag should be true')
def adjustment_zero_true(model_context):
    assert model_context['adjustment'].zero is True
