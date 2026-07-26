"""Meter Readings must show each participant's raw usage cost before adjustments."""
import pytest

from app import create_app
from app.extensions import db
from app.models import BillComponent, MeterReading, MonthParticipant, MonthlyBill, Participant


@pytest.fixture
def cost_app():
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
def cost_client(cost_app):
    return cost_app.test_client()


@pytest.fixture
def usage_month(cost_app):
    alice = Participant(name="Alice")
    bob = Participant(name="Bob")
    db.session.add_all([alice, bob])
    db.session.flush()
    bill = MonthlyBill(year=2026, month=6, electricity_amount=0, water_amount=0, internet_amount=0)
    db.session.add(bill)
    db.session.flush()
    db.session.add_all([
        MonthParticipant(month_id=bill.id, participant_id=alice.id),
        MonthParticipant(month_id=bill.id, participant_id=bob.id),
        MeterReading(month_id=bill.id, participant_id=alice.id,
                     reading_previous=100, reading_current=150),   # 5 kWh (delta / 10)
        MeterReading(month_id=bill.id, participant_id=bob.id,
                     reading_previous=200, reading_current=350),   # 15 kWh (delta / 10)
        BillComponent(month_id=bill.id, name="Electricity", amount=2000.0,
                      split_method="usage", position=0),
    ])
    db.session.commit()
    return bill


def test_month_page_shows_base_cost_and_rate(cost_client, usage_month):
    html = cost_client.get(f"/months/{usage_month.id}").data.decode()
    assert "Base cost (₱)" in html
    assert "₱100.00/kWh" in html         # 2000 / 20 kWh
    assert "1,500.00" in html            # Bob: 15/20 × 2000, before adjustments
    assert 'data-usage-amount="2000' in html


def test_archived_month_page_shows_base_cost(cost_client, usage_month):
    usage_month.archived = True
    db.session.commit()
    html = cost_client.get(f"/months/{usage_month.id}").data.decode()
    assert "Base cost (₱)" in html
    assert "1,500.00" in html


def test_no_base_cost_column_without_usage_components(cost_client, usage_month):
    BillComponent.query.update({"split_method": "equal"})
    db.session.commit()
    html = cost_client.get(f"/months/{usage_month.id}").data.decode()
    assert "Base cost (₱)" not in html
    assert "kWh · usage split" in html
