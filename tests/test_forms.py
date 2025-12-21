"""Tests for Flask-WTF forms validation."""
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import pytest
from app import create_app
from app.extensions import db
from app.models import MonthlyBill
from app.forms import MonthForm


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


class TestMonthForm:
    def test_valid_form_data(self, app):
        with app.app_context():
            with app.test_request_context(method='POST', data={
                "year": "2025",
                "month": "6",
                "electricity_amount": "100.0",
                "water_amount": "50.0",
                "internet_amount": "30.0",
            }):
                form = MonthForm()
                # Validate individual field data types
                assert form.year.data == 2025
                assert form.month.data == 6

    def test_invalid_year_too_low(self, app):
        with app.app_context():
            with app.test_request_context():
                form = MonthForm(data={
                    "year": 1999,  # Below min
                    "month": 6,
                    "electricity_amount": 100.0,
                    "water_amount": 50.0,
                    "internet_amount": 30.0,
                })
                assert form.validate() is False
                assert "year" in form.errors

    def test_invalid_year_too_high(self, app):
        with app.app_context():
            with app.test_request_context():
                form = MonthForm(data={
                    "year": 3001,  # Above max
                    "month": 6,
                    "electricity_amount": 100.0,
                    "water_amount": 50.0,
                    "internet_amount": 30.0,
                })
                assert form.validate() is False
                assert "year" in form.errors

    def test_negative_amount(self, app):
        with app.app_context():
            with app.test_request_context():
                form = MonthForm(data={
                    "year": 2025,
                    "month": 6,
                    "electricity_amount": -100.0,  # Negative
                    "water_amount": 50.0,
                    "internet_amount": 30.0,
                })
                assert form.validate() is False
                assert "electricity_amount" in form.errors

    def test_missing_required_field(self, app):
        with app.app_context():
            with app.test_request_context():
                form = MonthForm(data={
                    "year": 2025,
                    "month": 6,
                    # Missing electricity_amount
                    "water_amount": 50.0,
                    "internet_amount": 30.0,
                })
                assert form.validate() is False
                assert "electricity_amount" in form.errors

    def test_duplicate_check_disabled_by_default(self, app):
        with app.app_context():
            # Create existing bill
            bill = MonthlyBill(year=2025, month=6, electricity_amount=100, water_amount=50, internet_amount=30)
            db.session.add(bill)
            db.session.commit()
            with app.test_request_context(method='POST', data={
                "year": "2025",
                "month": "6",
                "electricity_amount": "100.0",
                "water_amount": "50.0",
                "internet_amount": "30.0",
            }):
                form = MonthForm()
                # Without check_duplicates flag, duplicate check is skipped
                # The attribute doesn't exist by default - it's set dynamically in routes
                assert not getattr(form, 'check_duplicates', False)

    def test_duplicate_check_enabled(self, app):
        with app.app_context():
            # Create existing bill
            bill = MonthlyBill(year=2025, month=6, electricity_amount=100, water_amount=50, internet_amount=30)
            db.session.add(bill)
            db.session.commit()
            with app.test_request_context():
                form = MonthForm(data={
                    "year": 2025,
                    "month": 6,
                    "electricity_amount": 100.0,
                    "water_amount": 50.0,
                    "internet_amount": 30.0,
                })
                form.check_duplicates = True
                assert form.validate() is False
                assert "month" in form.errors
