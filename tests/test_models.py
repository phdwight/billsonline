"""Tests for SQLAlchemy models."""
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import pytest
from app import create_app
from app.extensions import db
from app.models import (
    Participant, MonthlyBill, MeterReading, MonthParticipant,
    MonthlyAdjustment, BillComponent, ComponentAdjustment
)


@pytest.fixture
def app():
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


class TestParticipantModel:
    def test_create_participant(self, app):
        with app.app_context():
            p = Participant(name="TestUser")
            db.session.add(p)
            db.session.commit()
            assert p.id is not None
            assert p.name == "TestUser"

    def test_participant_unique_name(self, app):
        with app.app_context():
            p1 = Participant(name="Unique")
            db.session.add(p1)
            db.session.commit()
            p2 = Participant(name="Unique")
            db.session.add(p2)
            with pytest.raises(Exception):
                db.session.commit()


class TestMonthlyBillModel:
    def test_create_bill(self, app):
        with app.app_context():
            bill = MonthlyBill(year=2025, month=1, electricity_amount=100.0, water_amount=50.0, internet_amount=30.0)
            db.session.add(bill)
            db.session.commit()
            assert bill.id is not None
            assert bill.archived is False

    def test_unique_year_month(self, app):
        with app.app_context():
            b1 = MonthlyBill(year=2025, month=1, electricity_amount=100.0, water_amount=50.0, internet_amount=30.0)
            db.session.add(b1)
            db.session.commit()
            b2 = MonthlyBill(year=2025, month=1, electricity_amount=200.0, water_amount=100.0, internet_amount=60.0)
            db.session.add(b2)
            with pytest.raises(Exception):
                db.session.commit()


class TestMeterReadingModel:
    def test_usage_calculation(self, app):
        with app.app_context():
            p = Participant(name="Reader")
            bill = MonthlyBill(year=2025, month=1, electricity_amount=100.0, water_amount=50.0, internet_amount=30.0)
            db.session.add_all([p, bill])
            db.session.commit()
            reading = MeterReading(participant_id=p.id, month_id=bill.id, reading_current=150.0, reading_previous=100.0)
            assert reading.usage() == 50.0

    def test_usage_no_previous(self, app):
        with app.app_context():
            p = Participant(name="Reader")
            bill = MonthlyBill(year=2025, month=1, electricity_amount=100.0, water_amount=50.0, internet_amount=30.0)
            db.session.add_all([p, bill])
            db.session.commit()
            reading = MeterReading(participant_id=p.id, month_id=bill.id, reading_current=150.0, reading_previous=None)
            assert reading.usage() == 0.0

    def test_usage_negative_returns_zero(self, app):
        with app.app_context():
            p = Participant(name="Reader")
            bill = MonthlyBill(year=2025, month=1, electricity_amount=100.0, water_amount=50.0, internet_amount=30.0)
            db.session.add_all([p, bill])
            db.session.commit()
            reading = MeterReading(participant_id=p.id, month_id=bill.id, reading_current=50.0, reading_previous=100.0)
            assert reading.usage() == 0.0


class TestMonthParticipantModel:
    def test_create_link(self, app):
        with app.app_context():
            p = Participant(name="Member")
            bill = MonthlyBill(year=2025, month=1, electricity_amount=100.0, water_amount=50.0, internet_amount=30.0)
            db.session.add_all([p, bill])
            db.session.commit()
            mp = MonthParticipant(month_id=bill.id, participant_id=p.id)
            db.session.add(mp)
            db.session.commit()
            assert mp.id is not None

    def test_unique_constraint(self, app):
        with app.app_context():
            p = Participant(name="Member")
            bill = MonthlyBill(year=2025, month=1, electricity_amount=100.0, water_amount=50.0, internet_amount=30.0)
            db.session.add_all([p, bill])
            db.session.commit()
            mp1 = MonthParticipant(month_id=bill.id, participant_id=p.id)
            db.session.add(mp1)
            db.session.commit()
            mp2 = MonthParticipant(month_id=bill.id, participant_id=p.id)
            db.session.add(mp2)
            with pytest.raises(Exception):
                db.session.commit()


class TestMonthlyAdjustmentModel:
    def test_create_adjustment(self, app):
        with app.app_context():
            p = Participant(name="Adjusted")
            bill = MonthlyBill(year=2025, month=1, electricity_amount=100.0, water_amount=50.0, internet_amount=30.0)
            db.session.add_all([p, bill])
            db.session.commit()
            adj = MonthlyAdjustment(
                month_id=bill.id,
                participant_id=p.id,
                zero_electricity=True,
                zero_water=False,
                zero_internet=True
            )
            db.session.add(adj)
            db.session.commit()
            assert adj.id is not None
            assert adj.zero_electricity is True

    def test_adjustment_with_redistribution(self, app):
        with app.app_context():
            p = Participant(name="Adjusted")
            bill = MonthlyBill(year=2025, month=1, electricity_amount=100.0, water_amount=50.0, internet_amount=30.0)
            db.session.add_all([p, bill])
            db.session.commit()
            redis_rule = {"mode": "percent", "targets": {2: 100}}
            adj = MonthlyAdjustment(
                month_id=bill.id,
                participant_id=p.id,
                zero_electricity=True,
                zero_water=False,
                zero_internet=False,
                redis_electricity=redis_rule
            )
            db.session.add(adj)
            db.session.commit()
            # JSON serialization converts int keys to strings
            assert adj.redis_electricity["mode"] == "percent"
            assert "2" in adj.redis_electricity["targets"] or 2 in adj.redis_electricity["targets"]


class TestBillComponentModel:
    def test_create_component(self, app):
        with app.app_context():
            bill = MonthlyBill(year=2025, month=1, electricity_amount=100.0, water_amount=50.0, internet_amount=30.0)
            db.session.add(bill)
            db.session.commit()
            comp = BillComponent(month_id=bill.id, name="Electricity", amount=150.0, split_method="usage", position=0)
            db.session.add(comp)
            db.session.commit()
            assert comp.id is not None
            assert comp.name == "Electricity"

    def test_component_with_distribution(self, app):
        with app.app_context():
            bill = MonthlyBill(year=2025, month=1, electricity_amount=100.0, water_amount=50.0, internet_amount=30.0)
            db.session.add(bill)
            db.session.commit()
            dist = {1: 50, 2: 30, 3: 20}
            comp = BillComponent(
                month_id=bill.id,
                name="Custom",
                amount=100.0,
                split_method="percentage",
                distribution=dist
            )
            db.session.add(comp)
            db.session.commit()
            # JSON serialization converts int keys to strings
            assert comp.distribution is not None
            assert len(comp.distribution) == 3
            # Values should be preserved
            assert sum(comp.distribution.values()) == 100


class TestComponentAdjustmentModel:
    def test_create_component_adjustment(self, app):
        with app.app_context():
            p = Participant(name="Adjusted")
            bill = MonthlyBill(year=2025, month=1, electricity_amount=100.0, water_amount=50.0, internet_amount=30.0)
            db.session.add_all([p, bill])
            db.session.commit()
            comp = BillComponent(month_id=bill.id, name="Electricity", amount=100.0, split_method="usage")
            db.session.add(comp)
            db.session.commit()
            adj = ComponentAdjustment(
                month_id=bill.id,
                component_id=comp.id,
                participant_id=p.id,
                zero=True,
                redis_rule={"mode": "percent", "targets": {2: 100}}
            )
            db.session.add(adj)
            db.session.commit()
            assert adj.id is not None
            assert adj.zero is True
