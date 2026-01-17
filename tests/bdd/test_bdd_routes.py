"""Step definitions for routes.feature."""
import pytest
from pytest_bdd import scenarios, given, when, then, parsers
from io import BytesIO

from app import create_app
from app.extensions import db
from app.models import Participant, MonthlyBill, BillComponent, MonthParticipant

scenarios('../features/routes.feature')


# ============ Fixtures ============
@pytest.fixture
def route_app():
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
def route_client(route_app):
    return route_app.test_client()


@pytest.fixture
def route_context(route_app, route_client):
    """Context for route tests."""
    return {
        'app': route_app,
        'client': route_client,
        'response': None,
        'participant_id': None,
        'participant_ids': [],
        'bill_id': None,
        'component_id': None,
    }


# ============ Given Steps ============
@given('the application is running')
def app_running(route_context):
    pass


@given('no bills exist')
def no_bills(route_context):
    with route_context['app'].app_context():
        MonthlyBill.query.delete()
        db.session.commit()


@given(parsers.parse('a bill exists for year {year:d} month {month:d}'))
def bill_exists(route_context, year, month):
    with route_context['app'].app_context():
        bill = MonthlyBill(
            year=year, month=month,
            electricity_amount=100.0,
            water_amount=50.0,
            internet_amount=30.0
        )
        db.session.add(bill)
        db.session.commit()
        route_context['bill_id'] = bill.id


@given(parsers.parse('bills exist for months {start:d} through {end:d} of {year:d}'))
def bills_exist_range(route_context, start, end, year):
    with route_context['app'].app_context():
        for m in range(start, end + 1):
            bill = MonthlyBill(
                year=year, month=m,
                electricity_amount=100.0,
                water_amount=50.0,
                internet_amount=30.0
            )
            db.session.add(bill)
        db.session.commit()


@given(parsers.parse('participant "{name}" exists'))
def participant_exists(route_context, name):
    with route_context['app'].app_context():
        p = Participant(name=name)
        db.session.add(p)
        db.session.commit()
        route_context['participant_id'] = p.id


@given(parsers.parse('participants "{names}" exist'))
def participants_exist(route_context, names):
    with route_context['app'].app_context():
        for name in (n.strip() for n in names.split(',')):
            p = Participant(name=name)
            db.session.add(p)
            db.session.commit()
            route_context['participant_ids'].append(p.id)


@given(parsers.parse('an archived bill exists for year {year:d} month {month:d}'))
def archived_bill_exists(route_context, year, month):
    with route_context['app'].app_context():
        bill = MonthlyBill(
            year=year, month=month,
            electricity_amount=100.0,
            water_amount=50.0,
            internet_amount=30.0,
            archived=True
        )
        db.session.add(bill)
        db.session.commit()
        route_context['bill_id'] = bill.id


@given(parsers.parse('component "{name}" exists with amount {amount:f}'))
def component_exists(route_context, name, amount):
    with route_context['app'].app_context():
        comp = BillComponent(
            month_id=route_context['bill_id'],
            name=name,
            amount=amount,
            split_method='equal'
        )
        db.session.add(comp)
        db.session.commit()
        route_context['component_id'] = comp.id


@given(parsers.parse('component "{name}" exists'))
def component_exists_name(route_context, name):
    with route_context['app'].app_context():
        comp = BillComponent(
            month_id=route_context['bill_id'],
            name=name,
            amount=100.0,
            split_method='equal'
        )
        db.session.add(comp)
        db.session.commit()
        route_context['component_id'] = comp.id


@given(parsers.parse('participant "{name}" is linked to the month'))
def participant_linked(route_context, name):
    with route_context['app'].app_context():
        # Create participant if it doesn't exist
        p = Participant.query.filter_by(name=name).first()
        if not p:
            p = Participant(name=name)
            db.session.add(p)
            db.session.flush()
        route_context['participant_id'] = p.id
        mp = MonthParticipant(month_id=route_context['bill_id'], participant_id=p.id)
        db.session.add(mp)
        db.session.commit()


@given(parsers.parse('participants "{names}" are linked to the month'))
def participants_linked_many(route_context, names):
    with route_context['app'].app_context():
        for name in (n.strip() for n in names.split(',')):
            # Create participant if it doesn't exist
            p = Participant.query.filter_by(name=name).first()
            if not p:
                p = Participant(name=name)
                db.session.add(p)
                db.session.flush()
            mp = MonthParticipant(month_id=route_context['bill_id'], participant_id=p.id)
            db.session.add(mp)
        db.session.commit()


@given(parsers.parse('participant "{name}" exists but is not linked'))
def participant_not_linked(route_context, name):
    with route_context['app'].app_context():
        p = Participant.query.filter_by(name=name).first()
        if not p:
            p = Participant(name=name)
            db.session.add(p)
            db.session.commit()


@given(parsers.parse('a bill without components exists for year {year:d} month {month:d} with amounts {elec:d}, {water:d}, {inet:d}'))
def bill_without_components(route_context, year, month, elec, water, inet):
    with route_context['app'].app_context():
        bill = MonthlyBill(
            year=year, month=month,
            electricity_amount=elec,
            water_amount=water,
            internet_amount=inet
        )
        db.session.add(bill)
        db.session.commit()
        route_context['bill_id'] = bill.id


# ============ When Steps ============
@when('I visit the home page')
def visit_home(route_context):
    route_context['response'] = route_context['client'].get('/')


@when(parsers.parse('I visit "{path}"'))
def visit_path(route_context, path):
    route_context['response'] = route_context['client'].get(path, follow_redirects=True)


@when('I visit the month detail page')
def visit_month_detail(route_context):
    route_context['response'] = route_context['client'].get(
        f"/months/{route_context['bill_id']}"
    )


@when('I visit the month edit page')
def visit_month_edit(route_context):
    route_context['response'] = route_context['client'].get(
        f"/months/{route_context['bill_id']}/edit",
        follow_redirects=True
    )


@when('I POST to add participant with empty name')
def post_add_participant_empty(route_context):
    route_context['response'] = route_context['client'].post(
        '/participants/', data={'name': ''}, follow_redirects=True
    )


@when('I POST to update participant with empty name')
def post_update_participant_empty(route_context):
    route_context['response'] = route_context['client'].post(
        f"/participants/{route_context['participant_id']}",
        data={'name': ''},
        follow_redirects=True
    )


@when('I POST to add component with empty name')
def post_add_component_empty(route_context):
    route_context['response'] = route_context['client'].post(
        f"/months/{route_context['bill_id']}/components",
        data={
            'component_name': '',
            'component_amount': 75.0,
            'component_split_method': 'equal',
            'component_position': 0,
        },
        follow_redirects=True
    )


@when(parsers.parse('I POST to "{path}" with name "{name}"'))
def post_with_name(route_context, path, name):
    route_context['response'] = route_context['client'].post(
        path, data={'name': name}, follow_redirects=True
    )


@when(parsers.parse('I POST to update participant with name "{name}"'))
def post_update_participant(route_context, name):
    route_context['response'] = route_context['client'].post(
        f"/participants/{route_context['participant_id']}",
        data={'name': name},
        follow_redirects=True
    )


@when('I POST to delete the participant')
def post_delete_participant(route_context):
    route_context['response'] = route_context['client'].post(
        f"/participants/{route_context['participant_id']}/delete",
        follow_redirects=True
    )


@when(parsers.parse('I POST to "/months" with year {year:d}, month {month:d}, amounts {elec:f}, {water:f}, {inet:f}'))
def post_create_month(route_context, year, month, elec, water, inet):
    route_context['response'] = route_context['client'].post('/months', data={
        'year': year,
        'month': month,
        'electricity_amount': elec,
        'water_amount': water,
        'internet_amount': inet,
    }, follow_redirects=True)


@when(parsers.parse('I POST to add component "{name}" with amount {amount:f} and split method "{method}"'))
def post_add_component(route_context, name, amount, method):
    route_context['response'] = route_context['client'].post(
        f"/months/{route_context['bill_id']}/components",
        data={
            'component_name': name,
            'component_amount': amount,
            'component_split_method': method,
            'component_position': 0,
        },
        follow_redirects=True
    )


@when(parsers.parse('I POST to update component to name "{name}" with amount {amount:f} and split method "{method}"'))
def post_update_component(route_context, name, amount, method):
    route_context['response'] = route_context['client'].post(
        f"/months/{route_context['bill_id']}/components/{route_context['component_id']}",
        data={
            'name': name,
            'amount': amount,
            'split_method': method,
        },
        follow_redirects=True
    )


@when('I POST to delete the component')
def post_delete_component(route_context):
    route_context['response'] = route_context['client'].post(
        f"/months/{route_context['bill_id']}/components/{route_context['component_id']}/delete",
        follow_redirects=True
    )


@when('I POST to add the participant to the month')
def post_add_participant_to_month(route_context):
    route_context['response'] = route_context['client'].post(
        f"/months/{route_context['bill_id']}/participants",
        data={'participant_id': route_context['participant_id']},
        follow_redirects=True
    )


@when('I POST to remove the participant from the month')
def post_remove_participant(route_context):
    route_context['response'] = route_context['client'].post(
        f"/months/{route_context['bill_id']}/participants/{route_context['participant_id']}/delete",
        follow_redirects=True
    )


@when('I POST to convert the bill to dynamic components')
def post_convert_legacy(route_context):
    route_context['response'] = route_context['client'].post(
        f"/months/{route_context['bill_id']}/components/convert-legacy",
        follow_redirects=True
    )


@when('I POST to archive the month')
def post_archive(route_context):
    route_context['response'] = route_context['client'].post(
        f"/months/{route_context['bill_id']}/archive",
        follow_redirects=True
    )


@when('I POST to delete the month')
def post_delete_month(route_context):
    route_context['response'] = route_context['client'].post(
        f"/months/{route_context['bill_id']}/delete",
        follow_redirects=True
    )


@when(parsers.parse('I POST to "/settings/database" with {condition}'))
def post_database_upload(route_context, condition):
    if condition == 'no file':
        route_context['response'] = route_context['client'].post(
            '/settings/database', follow_redirects=True
        )
    elif condition == 'empty filename':
        data = {"database": (BytesIO(b""), "")}
        route_context['response'] = route_context['client'].post(
            '/settings/database',
            data=data,
            content_type="multipart/form-data",
            follow_redirects=True
        )
    elif condition == 'invalid type':
        data = {"database": (BytesIO(b"test"), "test.txt")}
        route_context['response'] = route_context['client'].post(
            '/settings/database',
            data=data,
            content_type="multipart/form-data",
            follow_redirects=True
        )


@when('I create a month with all participants selected')
def create_month_all_participants(route_context):
    route_context['response'] = route_context['client'].post('/months', data={
        'year': 2025,
        'month': 1,
        'electricity_amount': 100.0,
        'water_amount': 50.0,
        'internet_amount': 30.0,
        'selected_participants': route_context['participant_ids'],
    }, follow_redirects=True)
    with route_context['app'].app_context():
        bill = MonthlyBill.query.filter_by(year=2025, month=1).first()
        route_context['bill_id'] = bill.id


@when(parsers.parse('I create a month with only "{names}" selected'))
def create_month_subset(route_context, names):
    with route_context['app'].app_context():
        selected = []
        for name in (n.strip() for n in names.split(',')):
            p = Participant.query.filter_by(name=name).first()
            selected.append(p.id)
    
    route_context['response'] = route_context['client'].post('/months', data={
        'year': 2025,
        'month': 2,
        'electricity_amount': 100.0,
        'water_amount': 50.0,
        'internet_amount': 30.0,
        'selected_participants': selected,
    }, follow_redirects=True)
    with route_context['app'].app_context():
        bill = MonthlyBill.query.filter_by(year=2025, month=2).first()
        route_context['bill_id'] = bill.id


@when('I create a month without participant selection')
def create_month_no_selection(route_context):
    route_context['response'] = route_context['client'].post('/months', data={
        'year': 2025,
        'month': 4,
        'electricity_amount': 100.0,
        'water_amount': 50.0,
        'internet_amount': 30.0,
    }, follow_redirects=True)
    with route_context['app'].app_context():
        bill = MonthlyBill.query.filter_by(year=2025, month=4).first()
        route_context['bill_id'] = bill.id


@when(parsers.parse('I add "{name}" to the month'))
def add_participant_to_month(route_context, name):
    with route_context['app'].app_context():
        p = Participant.query.filter_by(name=name).first()
        route_context['response'] = route_context['client'].post(
            f"/months/{route_context['bill_id']}/participants",
            data={'participant_id': p.id},
            follow_redirects=True
        )


@when(parsers.parse('I remove "{name}" from the month'))
def remove_participant_from_month(route_context, name):
    with route_context['app'].app_context():
        p = Participant.query.filter_by(name=name).first()
        route_context['response'] = route_context['client'].post(
            f"/months/{route_context['bill_id']}/participants/{p.id}/delete",
            follow_redirects=True
        )


# ============ Then Steps ============
@then(parsers.parse('I should be redirected to "{path}"'))
def redirected_to(route_context, path):
    assert route_context['response'].status_code == 302
    assert path in route_context['response'].location


@then('I should be redirected to the month detail page')
def redirected_to_month(route_context):
    assert route_context['response'].status_code == 302
    assert f"/months/{route_context['bill_id']}" in route_context['response'].location


@then('I should be redirected to settings')
def redirected_to_settings(route_context):
    assert route_context['response'].status_code == 200 or '/settings' in route_context['response'].request.path


@then(parsers.parse('the response status should be {status:d}'))
def response_status(route_context, status):
    assert route_context['response'].status_code == status


@then(parsers.parse('the page should contain "{text}"'))
def page_contains(route_context, text):
    assert text.encode() in route_context['response'].data or text in route_context['response'].data.decode()


@then(parsers.parse('the page should contain \'{text}\''))
def page_contains_single_quote(route_context, text):
    assert text.encode() in route_context['response'].data


@then(parsers.parse('the page should contain "{text1}" or "{text2}"'))
def page_contains_or(route_context, text1, text2):
    data = route_context['response'].data.decode().lower()
    assert text1.lower() in data or text2.lower() in data


@then(parsers.parse('participant "{name}" should exist'))
def participant_exists_check(route_context, name):
    with route_context['app'].app_context():
        p = Participant.query.filter_by(name=name).first()
        assert p is not None


@then('the participant should not exist')
def participant_not_exist(route_context):
    with route_context['app'].app_context():
        p = db.session.get(Participant, route_context['participant_id'])
        assert p is None


@then(parsers.parse('only {count:d} participant named "{name}" should exist'))
def count_participants_named(route_context, count, name):
    with route_context['app'].app_context():
        c = Participant.query.filter_by(name=name).count()
        assert c == count


@then(parsers.parse('the participant name should be "{name}"'))
def participant_name_is(route_context, name):
    with route_context['app'].app_context():
        p = db.session.get(Participant, route_context['participant_id'])
        assert p.name == name


@then(parsers.parse('a bill for year {year:d} month {month:d} should exist'))
def bill_should_exist(route_context, year, month):
    with route_context['app'].app_context():
        bill = MonthlyBill.query.filter_by(year=year, month=month).first()
        assert bill is not None
        route_context['bill_id'] = bill.id


@then(parsers.parse('the electricity amount should be {amount:f}'))
def elec_amount_is(route_context, amount):
    with route_context['app'].app_context():
        bill = db.session.get(MonthlyBill, route_context['bill_id'])
        assert bill.electricity_amount == amount


@then(parsers.parse('only {count:d} bill for year {year:d} month {month:d} should exist'))
def count_bills(route_context, count, year, month):
    with route_context['app'].app_context():
        c = MonthlyBill.query.filter_by(year=year, month=month).count()
        assert c == count


@then(parsers.parse('component "{name}" should exist with amount {amount:f}'))
def component_should_exist(route_context, name, amount):
    with route_context['app'].app_context():
        comp = BillComponent.query.filter_by(
            month_id=route_context['bill_id'], name=name
        ).first()
        assert comp is not None
        assert comp.amount == amount
        route_context['component_id'] = comp.id


@then(parsers.parse('the component name should be "{name}"'))
def component_name_is(route_context, name):
    with route_context['app'].app_context():
        comp = db.session.get(BillComponent, route_context['component_id'])
        assert comp.name == name


@then(parsers.parse('the component amount should be {amount:f}'))
def component_amount_is(route_context, amount):
    with route_context['app'].app_context():
        comp = db.session.get(BillComponent, route_context['component_id'])
        assert comp.amount == amount


@then('the component should not exist')
def component_not_exist(route_context):
    with route_context['app'].app_context():
        comp = db.session.get(BillComponent, route_context['component_id'])
        assert comp is None


@then('the participant should be linked to the month')
def participant_is_linked(route_context):
    with route_context['app'].app_context():
        mp = MonthParticipant.query.filter_by(
            month_id=route_context['bill_id'],
            participant_id=route_context['participant_id']
        ).first()
        assert mp is not None


@then(parsers.parse('{count:d} components should exist'))
def n_components_exist(route_context, count):
    with route_context['app'].app_context():
        comps = BillComponent.query.filter_by(month_id=route_context['bill_id']).all()
        assert len(comps) == count


@then(parsers.parse('components "{names}" should exist'))
def components_by_name_exist(route_context, names):
    with route_context['app'].app_context():
        expected = set(n.strip() for n in names.split(','))
        actual = set(c.name for c in BillComponent.query.filter_by(month_id=route_context['bill_id']).all())
        assert expected == actual


@then('the bill should be archived')
def bill_is_archived(route_context):
    with route_context['app'].app_context():
        bill = db.session.get(MonthlyBill, route_context['bill_id'])
        assert bill.archived is True


@then('the bill should not exist')
def bill_not_exist(route_context):
    with route_context['app'].app_context():
        bill = db.session.get(MonthlyBill, route_context['bill_id'])
        assert bill is None


@then(parsers.parse('all {count:d} participants should be linked to the month'))
def all_participants_linked(route_context, count):
    with route_context['app'].app_context():
        mps = MonthParticipant.query.filter_by(month_id=route_context['bill_id']).all()
        assert len(mps) == count


@then(parsers.parse('{count:d} participants should be linked to the month'))
def n_participants_linked(route_context, count):
    with route_context['app'].app_context():
        mps = MonthParticipant.query.filter_by(month_id=route_context['bill_id']).all()
        assert len(mps) == count


@then(parsers.parse('{count:d} participant should be linked to the month'))
def one_participant_linked(route_context, count):
    with route_context['app'].app_context():
        mps = MonthParticipant.query.filter_by(month_id=route_context['bill_id']).all()
        assert len(mps) == count


@then(parsers.parse('"{name}" should not be linked to the month'))
def participant_not_linked(route_context, name):
    with route_context['app'].app_context():
        p = Participant.query.filter_by(name=name).first()
        mp = MonthParticipant.query.filter_by(
            month_id=route_context['bill_id'],
            participant_id=p.id
        ).first()
        assert mp is None


@then(parsers.parse('"{name}" should still be linked'))
def participant_still_linked(route_context, name):
    with route_context['app'].app_context():
        p = Participant.query.filter_by(name=name).first()
        mp = MonthParticipant.query.filter_by(
            month_id=route_context['bill_id'],
            participant_id=p.id
        ).first()
        assert mp is not None
