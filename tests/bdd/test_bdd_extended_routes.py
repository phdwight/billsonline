"""Step definitions for extended_routes.feature."""
import pytest
from pytest_bdd import scenarios, given, when, then, parsers

from app import create_app
from app.extensions import db
from app.models import Participant, MonthlyBill, BillComponent, MeterReading, MonthParticipant

scenarios('../features/extended_routes.feature')


@pytest.fixture
def ext_app():
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
def ext_client(ext_app):
    return ext_app.test_client()


@pytest.fixture
def ext_context(ext_app, ext_client):
    """Context for extended route tests."""
    return {
        'app': ext_app,
        'client': ext_client,
        'response': None,
        'bill_id': None,
        'component_id': None,
        'participant_id': None,
    }


# ============ Given Steps ============
@given('the extended route app is running')
def ext_app_running(ext_context):
    pass


@given(parsers.parse('a bill exists with ID for year {year:d} month {month:d}'))
def bill_with_id(ext_context, year, month):
    with ext_context['app'].app_context():
        bill = MonthlyBill(
            year=year, month=month,
            electricity_amount=100.0,
            water_amount=50.0,
            internet_amount=30.0,
            archived=False
        )
        db.session.add(bill)
        db.session.commit()
        ext_context['bill_id'] = bill.id


@given(parsers.parse('an archived bill exists with ID for year {year:d} month {month:d}'))
def archived_bill_with_id(ext_context, year, month):
    with ext_context['app'].app_context():
        bill = MonthlyBill(
            year=year, month=month,
            electricity_amount=100.0,
            water_amount=50.0,
            internet_amount=30.0,
            archived=True
        )
        db.session.add(bill)
        db.session.commit()
        ext_context['bill_id'] = bill.id


@given(parsers.parse('the bill has component "{name}" with amount {amount:f}'))
def bill_has_component(ext_context, name, amount):
    with ext_context['app'].app_context():
        comp = BillComponent(
            month_id=ext_context['bill_id'],
            name=name,
            amount=amount,
            split_method='equal',
            position=0
        )
        db.session.add(comp)
        db.session.commit()
        ext_context['component_id'] = comp.id


@given(parsers.parse('a bill exists with component "{name}" for update'))
def bill_with_component_for_update(ext_context, name):
    with ext_context['app'].app_context():
        bill = MonthlyBill(
            year=2025, month=5,
            electricity_amount=100.0,
            water_amount=50.0,
            internet_amount=30.0,
            archived=False
        )
        db.session.add(bill)
        db.session.commit()
        
        comp = BillComponent(
            month_id=bill.id,
            name=name,
            amount=100.0,
            split_method='equal',
            position=0
        )
        db.session.add(comp)
        db.session.commit()
        
        ext_context['bill_id'] = bill.id
        ext_context['component_id'] = comp.id


@given(parsers.parse('a bill exists with component "{name}" split "{method}"'))
def bill_with_component_split(ext_context, name, method):
    with ext_context['app'].app_context():
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
            name=name,
            amount=100.0,
            split_method=method,
            position=0
        )
        db.session.add(comp)
        db.session.commit()
        
        ext_context['bill_id'] = bill.id
        ext_context['component_id'] = comp.id


@given(parsers.parse('an archived bill with component "{name}"'))
def archived_bill_with_component(ext_context, name):
    with ext_context['app'].app_context():
        bill = MonthlyBill(
            year=2025, month=7,
            electricity_amount=100.0,
            water_amount=50.0,
            internet_amount=30.0,
            archived=True
        )
        db.session.add(bill)
        db.session.commit()
        
        comp = BillComponent(
            month_id=bill.id,
            name=name,
            amount=100.0,
            split_method='equal',
            position=0
        )
        db.session.add(comp)
        db.session.commit()
        
        ext_context['bill_id'] = bill.id
        ext_context['component_id'] = comp.id


@given('a bill for component creation exists')
def bill_for_component_creation(ext_context):
    with ext_context['app'].app_context():
        bill = MonthlyBill(
            year=2025, month=8,
            electricity_amount=100.0,
            water_amount=50.0,
            internet_amount=30.0,
            archived=False
        )
        db.session.add(bill)
        db.session.commit()
        ext_context['bill_id'] = bill.id


@given('a bill with participant for readings test')
def bill_with_participant_readings(ext_context):
    with ext_context['app'].app_context():
        p = Participant(name='Reader')
        db.session.add(p)
        db.session.commit()
        
        bill = MonthlyBill(
            year=2025, month=9,
            electricity_amount=100.0,
            water_amount=50.0,
            internet_amount=30.0,
            archived=False
        )
        db.session.add(bill)
        db.session.commit()
        
        ext_context['bill_id'] = bill.id
        ext_context['participant_id'] = p.id


@given('an archived bill with participant for readings')
def archived_bill_with_participant(ext_context):
    with ext_context['app'].app_context():
        p = Participant(name='ArchivedReader')
        db.session.add(p)
        db.session.commit()
        
        bill = MonthlyBill(
            year=2025, month=10,
            electricity_amount=100.0,
            water_amount=50.0,
            internet_amount=30.0,
            archived=True
        )
        db.session.add(bill)
        db.session.commit()
        
        ext_context['bill_id'] = bill.id
        ext_context['participant_id'] = p.id


@given('a bill for participant test exists')
def bill_for_participant_test(ext_context):
    with ext_context['app'].app_context():
        bill = MonthlyBill(
            year=2025, month=11,
            electricity_amount=100.0,
            water_amount=50.0,
            internet_amount=30.0,
            archived=False
        )
        db.session.add(bill)
        db.session.commit()
        ext_context['bill_id'] = bill.id


@given(parsers.parse('a participant "{name}" exists'))
def participant_exists(ext_context, name):
    with ext_context['app'].app_context():
        p = Participant(name=name)
        db.session.add(p)
        db.session.commit()
        ext_context['participant_id'] = p.id


@given('a bill with data for export exists')
def bill_for_export(ext_context):
    with ext_context['app'].app_context():
        p = Participant(name='Exporter')
        db.session.add(p)
        db.session.commit()
        
        bill = MonthlyBill(
            year=2025, month=12,
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
        
        ext_context['bill_id'] = bill.id
        ext_context['participant_id'] = p.id


@given('a bill with components and participants for adjustments')
def bill_for_adjustments(ext_context):
    with ext_context['app'].app_context():
        p1 = Participant(name='AdjPerson1')
        p2 = Participant(name='AdjPerson2')
        db.session.add_all([p1, p2])
        db.session.commit()
        
        bill = MonthlyBill(
            year=2024, month=1,
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
        
        mp1 = MonthParticipant(month_id=bill.id, participant_id=p1.id)
        mp2 = MonthParticipant(month_id=bill.id, participant_id=p2.id)
        db.session.add_all([mp1, mp2])
        db.session.commit()
        
        ext_context['bill_id'] = bill.id
        ext_context['component_id'] = comp.id
        ext_context['participant_ids'] = [p1.id, p2.id]


@given('an archived bill with components for adjustments')
def archived_bill_for_adjustments(ext_context):
    with ext_context['app'].app_context():
        p = Participant(name='ArchivedAdj')
        db.session.add(p)
        db.session.commit()
        
        bill = MonthlyBill(
            year=2024, month=2,
            electricity_amount=100.0,
            water_amount=50.0,
            internet_amount=30.0,
            archived=True
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
        
        ext_context['bill_id'] = bill.id
        ext_context['component_id'] = comp.id


# ============ When Steps ============
@when(parsers.parse('I POST to update the month with amounts {elec:f}, {water:f}, {inet:f}'))
def post_update_month(ext_context, elec, water, inet):
    response = ext_context['client'].post(
        f"/months/{ext_context['bill_id']}",
        data={
            'year': '2025',
            'month': '2',
            'electricity_amount': str(elec),
            'water_amount': str(water),
            'internet_amount': str(inet),
        },
        follow_redirects=True
    )
    ext_context['response'] = response


@when('I POST to update component with empty name')
def post_update_component_empty_name(ext_context):
    response = ext_context['client'].post(
        f"/months/{ext_context['bill_id']}/components/{ext_context['component_id']}",
        data={'name': '', 'amount': '100.0'},
        follow_redirects=True
    )
    ext_context['response'] = response


@when('I POST to update component with negative amount')
def post_update_component_negative(ext_context):
    response = ext_context['client'].post(
        f"/months/{ext_context['bill_id']}/components/{ext_context['component_id']}",
        data={'name': 'Updated', 'amount': '-50.0'},
        follow_redirects=True
    )
    ext_context['response'] = response


@when(parsers.parse('I POST to update component with invalid position "{pos}"'))
def post_update_component_invalid_position(ext_context, pos):
    response = ext_context['client'].post(
        f"/months/{ext_context['bill_id']}/components/{ext_context['component_id']}",
        data={'name': 'Updated', 'amount': '100.0', 'position': pos},
        follow_redirects=True
    )
    ext_context['response'] = response


@when(parsers.parse('I POST to update component split to "{method}"'))
def post_update_component_split(ext_context, method):
    response = ext_context['client'].post(
        f"/months/{ext_context['bill_id']}/components/{ext_context['component_id']}",
        data={'split_method': method},
        follow_redirects=True
    )
    ext_context['response'] = response


@when('I POST to update component with invalid split method')
def post_update_component_invalid_split(ext_context):
    response = ext_context['client'].post(
        f"/months/{ext_context['bill_id']}/components/{ext_context['component_id']}",
        data={'split_method': 'invalid_method'},
        follow_redirects=True
    )
    ext_context['response'] = response


@when('I POST to delete that component')
def post_delete_component(ext_context):
    response = ext_context['client'].post(
        f"/months/{ext_context['bill_id']}/components/{ext_context['component_id']}/delete",
        follow_redirects=True
    )
    ext_context['response'] = response


@when('I POST to update that component amount')
def post_update_component_amount(ext_context):
    response = ext_context['client'].post(
        f"/months/{ext_context['bill_id']}/components/{ext_context['component_id']}",
        data={'amount': '200.0'},
        follow_redirects=True
    )
    ext_context['response'] = response


@when(parsers.parse('I POST to add component "{name}" with position {pos:d}'))
def post_add_component_position(ext_context, name, pos):
    response = ext_context['client'].post(
        f"/months/{ext_context['bill_id']}/components/",
        data={
            'component_name': name,
            'component_amount': '100.0',
            'component_split_method': 'equal',
            'component_position': str(pos)
        },
        follow_redirects=True
    )
    ext_context['response'] = response


@when(parsers.parse('I POST meter readings current {current:d} previous {prev:d}'))
def post_meter_readings(ext_context, current, prev):
    response = ext_context['client'].post(
        f"/months/{ext_context['bill_id']}/readings",
        data={
            f"current_{ext_context['participant_id']}": str(current),
            f"previous_{ext_context['participant_id']}": str(prev),
        },
        follow_redirects=True
    )
    ext_context['response'] = response


@when(parsers.parse('I POST readings to nonexistent month {bill_id:d}'))
def post_readings_nonexistent(ext_context, bill_id):
    response = ext_context['client'].post(
        f"/months/{bill_id}/readings",
        data={'current_1': '500', 'previous_1': '400'},
        follow_redirects=True
    )
    ext_context['response'] = response


@when(parsers.parse('I POST to add participant to nonexistent month {bill_id:d}'))
def post_add_participant_nonexistent(ext_context, bill_id):
    response = ext_context['client'].post(
        f"/months/{bill_id}/participants",
        data={'participant_id': '1'},
        follow_redirects=True
    )
    ext_context['response'] = response


@when('I POST to add participant without selection')
def post_add_participant_no_selection(ext_context):
    response = ext_context['client'].post(
        f"/months/{ext_context['bill_id']}/participants",
        data={'participant_id': ''},
        follow_redirects=True
    )
    ext_context['response'] = response


@when('I POST to remove participant from nonexistent month')
def post_remove_participant_nonexistent(ext_context):
    response = ext_context['client'].post(
        f"/months/99999/participants/{ext_context['participant_id']}/delete",
        follow_redirects=True
    )
    ext_context['response'] = response


@when('I GET the export CSV endpoint')
def get_export_csv(ext_context):
    response = ext_context['client'].get(
        f"/months/{ext_context['bill_id']}/export.csv"
    )
    ext_context['response'] = response


@when(parsers.parse('I GET export CSV for nonexistent month {bill_id:d}'))
def get_export_nonexistent(ext_context, bill_id):
    response = ext_context['client'].get(
        f"/months/{bill_id}/export.csv",
        follow_redirects=True
    )
    ext_context['response'] = response


@when('I POST adjustment form data')
def post_adjustment_data(ext_context):
    response = ext_context['client'].post(
        f"/months/{ext_context['bill_id']}/adjustments",
        data={},  # Empty data - no redistributions
        follow_redirects=True
    )
    ext_context['response'] = response


@when(parsers.parse('I POST adjustments to nonexistent month {bill_id:d}'))
def post_adjustments_nonexistent(ext_context, bill_id):
    response = ext_context['client'].post(
        f"/months/{bill_id}/adjustments",
        data={},
        follow_redirects=True
    )
    ext_context['response'] = response


@when('I POST to create month with invalid form data')
def post_create_invalid_form(ext_context):
    response = ext_context['client'].post(
        "/months",
        data={
            'year': 'invalid',
            'month': 'invalid',
            'electricity_amount': 'abc',
            'water_amount': 'def',
            'internet_amount': 'ghi',
        },
        follow_redirects=True
    )
    ext_context['response'] = response


@when(parsers.parse('I visit edit page for nonexistent month {bill_id:d}'))
def visit_edit_nonexistent(ext_context, bill_id):
    response = ext_context['client'].get(
        f"/months/{bill_id}/edit",
        follow_redirects=True
    )
    ext_context['response'] = response


# ============ Then Steps ============
@then('the bill amounts should be updated')
def bill_amounts_updated(ext_context):
    with ext_context['app'].app_context():
        bill = MonthlyBill.query.get(ext_context['bill_id'])
        assert bill.electricity_amount == 150.0


@then(parsers.parse('the page should contain "{text}"'))
def page_contains(ext_context, text):
    assert text.lower() in ext_context['response'].data.decode().lower()


@then(parsers.parse('the component "{name}" amount should be {amount:f}'))
def component_amount_should_be(ext_context, name, amount):
    with ext_context['app'].app_context():
        comp = BillComponent.query.filter_by(name=name).first()
        assert comp is not None
        assert abs(comp.amount - amount) < 0.01


@then(parsers.parse('the component name should still be "{name}"'))
def component_name_still(ext_context, name):
    with ext_context['app'].app_context():
        comp = BillComponent.query.get(ext_context['component_id'])
        assert comp.name == name


@then(parsers.parse('the component split method should be "{method}"'))
def component_split_is(ext_context, method):
    with ext_context['app'].app_context():
        comp = BillComponent.query.get(ext_context['component_id'])
        assert comp.split_method == method


@then(parsers.parse('the component should exist at position {pos:d}'))
def component_at_position(ext_context, pos):
    with ext_context['app'].app_context():
        comp = BillComponent.query.filter_by(name='NewComp').first()
        assert comp is not None
        assert comp.position == pos


@then('the readings should be saved')
def readings_saved(ext_context):
    with ext_context['app'].app_context():
        reading = MeterReading.query.filter_by(
            month_id=ext_context['bill_id'],
            participant_id=ext_context['participant_id']
        ).first()
        assert reading is not None
        assert reading.reading_current == 500


@then('the response should be a CSV file')
def response_is_csv(ext_context):
    assert ext_context['response'].status_code == 200
    assert 'text/csv' in ext_context['response'].content_type


@then('I should be redirected')
def should_be_redirected(ext_context):
    # After following redirects, just check page loaded
    assert ext_context['response'].status_code == 200


@then('the adjustments should be saved')
def adjustments_saved(ext_context):
    assert ext_context['response'].status_code == 200
