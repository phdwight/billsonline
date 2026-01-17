"""Step definitions for reports.feature."""
import pytest
from pytest_bdd import scenarios, given, when, then, parsers

from app import create_app
from app.extensions import db
from app.models import Participant, MonthlyBill, BillComponent, MonthParticipant, MeterReading

scenarios('../features/reports.feature')


@pytest.fixture
def reports_app():
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
def reports_client(reports_app):
    return reports_app.test_client()


@pytest.fixture
def reports_context(reports_app, reports_client):
    """Context for reports tests."""
    return {
        'app': reports_app,
        'client': reports_client,
        'response': None,
        'json_data': None,
    }


# ============ Given Steps ============
@given('the reports app is running')
def reports_app_running(reports_context):
    pass


@given('no bills exist')
def no_bills_exist(reports_context):
    with reports_context['app'].app_context():
        MonthlyBill.query.delete()
        db.session.commit()


@given(parsers.parse('bills exist for months {start:d} through {end:d} of {year:d}'))
def bills_exist_range(reports_context, start, end, year):
    with reports_context['app'].app_context():
        for m in range(start, end + 1):
            bill = MonthlyBill(
                year=year, month=m,
                electricity_amount=100.0 * m,
                water_amount=50.0,
                internet_amount=30.0,
                archived=False
            )
            db.session.add(bill)
        db.session.commit()


@given(parsers.parse('bills exist for months {start:d} through {end:d} of {year:d} with participants and components'))
def bills_with_data(reports_context, start, end, year):
    with reports_context['app'].app_context():
        # Create participants
        p1 = Participant(name='Alice')
        p2 = Participant(name='Bob')
        db.session.add_all([p1, p2])
        db.session.commit()
        
        for m in range(start, end + 1):
            bill = MonthlyBill(
                year=year, month=m,
                electricity_amount=100.0 * m,
                water_amount=50.0,
                internet_amount=30.0,
                archived=False
            )
            db.session.add(bill)
            db.session.commit()
            
            # Add component
            comp = BillComponent(
                month_id=bill.id,
                name='Electricity',
                amount=100.0 * m,
                split_method='equal',
                position=0
            )
            db.session.add(comp)
            
            # Add month participants
            mp1 = MonthParticipant(month_id=bill.id, participant_id=p1.id)
            mp2 = MonthParticipant(month_id=bill.id, participant_id=p2.id)
            db.session.add_all([mp1, mp2])
            db.session.commit()


@given(parsers.parse('bills exist for months {start:d} through {end:d} of {year:d} with participants and meter readings'))
def bills_with_meter_readings(reports_context, start, end, year):
    with reports_context['app'].app_context():
        # Create participants
        p1 = Participant(name='Alice')
        p2 = Participant(name='Bob')
        db.session.add_all([p1, p2])
        db.session.commit()
        
        for m in range(start, end + 1):
            bill = MonthlyBill(
                year=year, month=m,
                electricity_amount=100.0 * m,
                water_amount=50.0,
                internet_amount=30.0,
                archived=False
            )
            db.session.add(bill)
            db.session.commit()
            
            # Add component
            comp = BillComponent(
                month_id=bill.id,
                name='Electricity',
                amount=100.0 * m,
                split_method='by_usage',
                position=0
            )
            db.session.add(comp)
            
            # Add meter readings for each participant
            reading1 = MeterReading(
                month_id=bill.id,
                participant_id=p1.id,
                reading_previous=100 + (m - 1) * 50,
                reading_current=100 + m * 50
            )
            reading2 = MeterReading(
                month_id=bill.id,
                participant_id=p2.id,
                reading_previous=200 + (m - 1) * 30,
                reading_current=200 + m * 30
            )
            db.session.add_all([reading1, reading2])
            
            # Add month participants
            mp1 = MonthParticipant(month_id=bill.id, participant_id=p1.id)
            mp2 = MonthParticipant(month_id=bill.id, participant_id=p2.id)
            db.session.add_all([mp1, mp2])
            db.session.commit()


# ============ When Steps ============
@when('I visit the reports page')
def visit_reports_page(reports_context):
    reports_context['response'] = reports_context['client'].get('/reports/')


@when('I visit the home page')
def visit_home_page(reports_context):
    reports_context['response'] = reports_context['client'].get('/', follow_redirects=True)


@when(parsers.parse('I request report data from {from_month} {from_year:d} to {to_month} {to_year:d}'))
def request_report_data(reports_context, from_month, from_year, to_month, to_year):
    month_map = {
        'January': 1, 'February': 2, 'March': 3, 'April': 4,
        'May': 5, 'June': 6, 'July': 7, 'August': 8,
        'September': 9, 'October': 10, 'November': 11, 'December': 12
    }
    from_m = month_map.get(from_month, 1)
    to_m = month_map.get(to_month, 1)
    
    response = reports_context['client'].get(
        f'/reports/data?from_year={from_year}&from_month={from_m}&to_year={to_year}&to_month={to_m}'
    )
    reports_context['response'] = response
    reports_context['json_data'] = response.get_json()


@when('I request report data with invalid parameters')
def request_invalid_params(reports_context):
    response = reports_context['client'].get(
        '/reports/data?from_year=abc&from_month=xyz&to_year=123&to_month=456'
    )
    reports_context['response'] = response
    reports_context['json_data'] = response.get_json()


@when('I request report data with missing parameters')
def request_missing_params(reports_context):
    response = reports_context['client'].get('/reports/data')
    reports_context['response'] = response
    reports_context['json_data'] = response.get_json()


# ============ Then Steps ============
@then(parsers.parse('the response status should be {status:d}'))
def response_status(reports_context, status):
    assert reports_context['response'].status_code == status


@then(parsers.parse('the page should contain "{text}"'))
def page_contains(reports_context, text):
    assert text in reports_context['response'].data.decode()


@then(parsers.parse('the response should contain labels for {count:d} months'))
def response_contains_labels(reports_context, count):
    data = reports_context['json_data']
    assert 'labels' in data
    assert len(data['labels']) == count


@then('the response should contain participant datasets')
def response_contains_datasets(reports_context):
    data = reports_context['json_data']
    assert 'datasets' in data
    assert len(data['datasets']) > 0


@then('the response should have error status')
def response_error_status(reports_context):
    # Invalid params should return 400 or have error in JSON
    data = reports_context['json_data']
    assert 'error' in data or reports_context['response'].status_code == 400


@then(parsers.parse('the response should have error "{message}"'))
def response_error_message(reports_context, message):
    data = reports_context['json_data']
    assert 'error' in data
    assert message in data['error']


@then('the response should contain empty labels')
def response_empty_labels(reports_context):
    data = reports_context['json_data']
    assert 'labels' in data
    assert len(data['labels']) == 0


@then('the page should contain link to reports')
def page_contains_reports_link(reports_context):
    html = reports_context['response'].data.decode()
    assert '/reports' in html.lower() or 'reports' in html.lower()


@then('the response should contain usage datasets')
def response_contains_usage_datasets(reports_context):
    data = reports_context['json_data']
    assert 'usage_datasets' in data
    assert len(data['usage_datasets']) > 0


@then('each usage dataset should have data for each month')
def usage_datasets_have_data(reports_context):
    data = reports_context['json_data']
    num_labels = len(data['labels'])
    for ds in data['usage_datasets']:
        assert 'data' in ds
        assert len(ds['data']) == num_labels
        # Verify there's actual usage data (not all zeros)
        assert any(v > 0 for v in ds['data'])
