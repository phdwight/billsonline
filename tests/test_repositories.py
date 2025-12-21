"""Tests for repository layer with database operations."""
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import pytest
from app import create_app
from app.extensions import db
from app.models import (
    Participant, MonthlyBill, MeterReading, MonthlyAdjustment,
    BillComponent, ComponentAdjustment, MonthParticipant
)
from app.repositories import (
    ParticipantRepository, MonthlyBillRepository, MeterReadingRepository,
    MonthlyAdjustmentRepository, BillComponentRepository, ComponentAdjustmentRepository,
    MonthParticipantRepository
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


@pytest.fixture
def client(app):
    return app.test_client()


class TestParticipantRepository:
    def test_add_participant(self, app):
        with app.app_context():
            repo = ParticipantRepository()
            p = repo.add("Alice")
            assert p.id is not None
            assert p.name == "Alice"

    def test_list_all_returns_ordered(self, app):
        with app.app_context():
            repo = ParticipantRepository()
            repo.add("Zara")
            repo.add("Alice")
            repo.add("Bob")
            results = repo.list_all()
            names = [p.name for p in results]
            assert names == ["Alice", "Bob", "Zara"]

    def test_get_participant(self, app):
        with app.app_context():
            repo = ParticipantRepository()
            p = repo.add("TestUser")
            fetched = repo.get(p.id)
            assert fetched is not None
            assert fetched.name == "TestUser"

    def test_get_nonexistent_returns_none(self, app):
        with app.app_context():
            repo = ParticipantRepository()
            fetched = repo.get(9999)
            assert fetched is None

    def test_update_participant(self, app):
        with app.app_context():
            repo = ParticipantRepository()
            p = repo.add("OldName")
            updated = repo.update(p.id, "NewName")
            assert updated.name == "NewName"


class TestMonthlyBillRepository:
    def test_create_bill(self, app):
        with app.app_context():
            repo = MonthlyBillRepository()
            bill = repo.create(2025, 1, 100.0, 50.0, 30.0)
            assert bill.id is not None
            assert bill.year == 2025
            assert bill.month == 1
            assert bill.electricity_amount == 100.0
            assert bill.water_amount == 50.0
            assert bill.internet_amount == 30.0

    def test_list_all_excludes_archived(self, app):
        with app.app_context():
            repo = MonthlyBillRepository()
            b1 = repo.create(2025, 1, 100.0, 50.0, 30.0)
            b2 = repo.create(2025, 2, 100.0, 50.0, 30.0)
            repo.set_archived(b1.id, True)
            bills = repo.list_all()
            assert len(bills) == 1
            assert bills[0].month == 2

    def test_list_paginated(self, app):
        with app.app_context():
            repo = MonthlyBillRepository()
            for m in range(1, 6):
                repo.create(2025, m, 100.0, 50.0, 30.0)
            page = repo.list_paginated(page=1, per_page=2)
            assert len(page.items) == 2
            assert page.total == 5

    def test_get_by_id(self, app):
        with app.app_context():
            repo = MonthlyBillRepository()
            bill = repo.create(2025, 3, 100.0, 50.0, 30.0)
            fetched = repo.get_by_id(bill.id)
            assert fetched is not None
            assert fetched.month == 3

    def test_get_previous_same_year(self, app):
        with app.app_context():
            repo = MonthlyBillRepository()
            repo.create(2025, 2, 100.0, 50.0, 30.0)
            repo.create(2025, 3, 100.0, 50.0, 30.0)
            prev = repo.get_previous(2025, 3)
            assert prev is not None
            assert prev.month == 2

    def test_get_previous_year_wrap(self, app):
        with app.app_context():
            repo = MonthlyBillRepository()
            repo.create(2024, 12, 100.0, 50.0, 30.0)
            repo.create(2025, 1, 100.0, 50.0, 30.0)
            prev = repo.get_previous(2025, 1)
            assert prev is not None
            assert prev.year == 2024
            assert prev.month == 12

    def test_find_by_year_month(self, app):
        with app.app_context():
            repo = MonthlyBillRepository()
            repo.create(2025, 6, 100.0, 50.0, 30.0)
            found = repo.find_by_year_month(2025, 6)
            assert found is not None
            assert found.month == 6
            not_found = repo.find_by_year_month(2025, 7)
            assert not_found is None

    def test_update_amounts(self, app):
        with app.app_context():
            repo = MonthlyBillRepository()
            bill = repo.create(2025, 1, 100.0, 50.0, 30.0)
            updated = repo.update_amounts(bill.id, 200.0, 100.0, 60.0)
            assert updated.electricity_amount == 200.0
            assert updated.water_amount == 100.0
            assert updated.internet_amount == 60.0

    def test_delete_bill(self, app):
        with app.app_context():
            repo = MonthlyBillRepository()
            bill = repo.create(2025, 1, 100.0, 50.0, 30.0)
            bill_id = bill.id
            repo.delete(bill_id)
            assert repo.get_by_id(bill_id) is None

    def test_set_archived(self, app):
        with app.app_context():
            repo = MonthlyBillRepository()
            bill = repo.create(2025, 1, 100.0, 50.0, 30.0)
            assert bill.archived is False
            repo.set_archived(bill.id, True)
            fetched = repo.get_by_id(bill.id)
            assert fetched.archived is True


class TestMeterReadingRepository:
    def test_upsert_creates_new(self, app):
        with app.app_context():
            p_repo = ParticipantRepository()
            b_repo = MonthlyBillRepository()
            r_repo = MeterReadingRepository()
            p = p_repo.add("Reader")
            bill = b_repo.create(2025, 1, 100.0, 50.0, 30.0)
            reading = r_repo.upsert(bill.id, p.id, 150.0, 100.0)
            assert reading.reading_current == 150.0
            assert reading.reading_previous == 100.0

    def test_upsert_updates_existing(self, app):
        with app.app_context():
            p_repo = ParticipantRepository()
            b_repo = MonthlyBillRepository()
            r_repo = MeterReadingRepository()
            p = p_repo.add("Reader")
            bill = b_repo.create(2025, 1, 100.0, 50.0, 30.0)
            r_repo.upsert(bill.id, p.id, 150.0, 100.0)
            updated = r_repo.upsert(bill.id, p.id, 200.0, 150.0)
            assert updated.reading_current == 200.0
            assert updated.reading_previous == 150.0
            # Should still be only one reading
            readings = r_repo.list_for_month(bill.id)
            assert len(readings) == 1

    def test_list_for_month(self, app):
        with app.app_context():
            p_repo = ParticipantRepository()
            b_repo = MonthlyBillRepository()
            r_repo = MeterReadingRepository()
            p1 = p_repo.add("P1")
            p2 = p_repo.add("P2")
            bill = b_repo.create(2025, 1, 100.0, 50.0, 30.0)
            r_repo.upsert(bill.id, p1.id, 100.0, 50.0)
            r_repo.upsert(bill.id, p2.id, 200.0, 100.0)
            readings = r_repo.list_for_month(bill.id)
            assert len(readings) == 2


class TestMonthParticipantRepository:
    def test_add_and_list(self, app):
        with app.app_context():
            p_repo = ParticipantRepository()
            b_repo = MonthlyBillRepository()
            mp_repo = MonthParticipantRepository()
            p = p_repo.add("Member")
            bill = b_repo.create(2025, 1, 100.0, 50.0, 30.0)
            mp_repo.add(bill.id, p.id)
            members = mp_repo.list_for_month(bill.id)
            assert len(members) == 1
            assert members[0].participant_id == p.id

    def test_add_is_idempotent(self, app):
        with app.app_context():
            p_repo = ParticipantRepository()
            b_repo = MonthlyBillRepository()
            mp_repo = MonthParticipantRepository()
            p = p_repo.add("Member")
            bill = b_repo.create(2025, 1, 100.0, 50.0, 30.0)
            mp_repo.add(bill.id, p.id)
            mp_repo.add(bill.id, p.id)  # Should not duplicate
            members = mp_repo.list_for_month(bill.id)
            assert len(members) == 1

    def test_remove(self, app):
        with app.app_context():
            p_repo = ParticipantRepository()
            b_repo = MonthlyBillRepository()
            mp_repo = MonthParticipantRepository()
            p = p_repo.add("Member")
            bill = b_repo.create(2025, 1, 100.0, 50.0, 30.0)
            mp_repo.add(bill.id, p.id)
            mp_repo.remove(bill.id, p.id)
            members = mp_repo.list_for_month(bill.id)
            assert len(members) == 0


class TestMonthlyAdjustmentRepository:
    def test_upsert_creates_new(self, app):
        with app.app_context():
            p_repo = ParticipantRepository()
            b_repo = MonthlyBillRepository()
            adj_repo = MonthlyAdjustmentRepository()
            p = p_repo.add("Adjusted")
            bill = b_repo.create(2025, 1, 100.0, 50.0, 30.0)
            adj = adj_repo.upsert(bill.id, p.id, True, False, True)
            assert adj.zero_electricity is True
            assert adj.zero_water is False
            assert adj.zero_internet is True

    def test_upsert_with_redistribution(self, app):
        with app.app_context():
            p_repo = ParticipantRepository()
            b_repo = MonthlyBillRepository()
            adj_repo = MonthlyAdjustmentRepository()
            p = p_repo.add("Adjusted")
            bill = b_repo.create(2025, 1, 100.0, 50.0, 30.0)
            redis_rule = {"mode": "percent", "targets": {2: 100}}
            adj = adj_repo.upsert(bill.id, p.id, True, False, False, redis_electricity=redis_rule)
            # JSON serialization converts int keys to strings
            assert adj.redis_electricity["mode"] == "percent"
            assert "2" in adj.redis_electricity["targets"] or 2 in adj.redis_electricity["targets"]

    def test_list_for_month(self, app):
        with app.app_context():
            p_repo = ParticipantRepository()
            b_repo = MonthlyBillRepository()
            adj_repo = MonthlyAdjustmentRepository()
            p1 = p_repo.add("P1")
            p2 = p_repo.add("P2")
            bill = b_repo.create(2025, 1, 100.0, 50.0, 30.0)
            adj_repo.upsert(bill.id, p1.id, True, False, False)
            adj_repo.upsert(bill.id, p2.id, False, True, False)
            adjs = adj_repo.list_for_month(bill.id)
            assert len(adjs) == 2

    def test_clear_for_month(self, app):
        with app.app_context():
            p_repo = ParticipantRepository()
            b_repo = MonthlyBillRepository()
            adj_repo = MonthlyAdjustmentRepository()
            p = p_repo.add("P")
            bill = b_repo.create(2025, 1, 100.0, 50.0, 30.0)
            adj_repo.upsert(bill.id, p.id, True, False, False)
            adj_repo.clear_for_month(bill.id)
            assert len(adj_repo.list_for_month(bill.id)) == 0


class TestBillComponentRepository:
    def test_add_component(self, app):
        with app.app_context():
            b_repo = MonthlyBillRepository()
            c_repo = BillComponentRepository()
            bill = b_repo.create(2025, 1, 100.0, 50.0, 30.0)
            comp = c_repo.add(bill.id, "Electricity", 150.0, "usage", position=0)
            assert comp.id is not None
            assert comp.name == "Electricity"
            assert comp.amount == 150.0
            assert comp.split_method == "usage"

    def test_add_with_distribution(self, app):
        with app.app_context():
            b_repo = MonthlyBillRepository()
            c_repo = BillComponentRepository()
            bill = b_repo.create(2025, 1, 100.0, 50.0, 30.0)
            dist = {1: 50, 2: 30, 3: 20}
            comp = c_repo.add(bill.id, "Custom", 100.0, "percentage", distribution=dist)
            # JSON serialization converts int keys to strings
            assert comp.distribution is not None
            assert len(comp.distribution) == 3
            assert sum(comp.distribution.values()) == 100

    def test_list_for_month_ordered(self, app):
        with app.app_context():
            b_repo = MonthlyBillRepository()
            c_repo = BillComponentRepository()
            bill = b_repo.create(2025, 1, 100.0, 50.0, 30.0)
            c_repo.add(bill.id, "Third", 30.0, position=2)
            c_repo.add(bill.id, "First", 10.0, position=0)
            c_repo.add(bill.id, "Second", 20.0, position=1)
            comps = c_repo.list_for_month(bill.id)
            names = [c.name for c in comps]
            assert names == ["First", "Second", "Third"]

    def test_update_component(self, app):
        with app.app_context():
            b_repo = MonthlyBillRepository()
            c_repo = BillComponentRepository()
            bill = b_repo.create(2025, 1, 100.0, 50.0, 30.0)
            comp = c_repo.add(bill.id, "Old", 100.0, "equal")
            updated = c_repo.update(comp.id, name="New", amount=200.0, split_method="usage")
            assert updated.name == "New"
            assert updated.amount == 200.0
            assert updated.split_method == "usage"

    def test_delete_component(self, app):
        with app.app_context():
            b_repo = MonthlyBillRepository()
            c_repo = BillComponentRepository()
            bill = b_repo.create(2025, 1, 100.0, 50.0, 30.0)
            comp = c_repo.add(bill.id, "ToDelete", 100.0)
            c_repo.delete(comp.id)
            comps = c_repo.list_for_month(bill.id)
            assert len(comps) == 0


class TestComponentAdjustmentRepository:
    def test_upsert_creates_new(self, app):
        with app.app_context():
            p_repo = ParticipantRepository()
            b_repo = MonthlyBillRepository()
            c_repo = BillComponentRepository()
            ca_repo = ComponentAdjustmentRepository()
            p = p_repo.add("P")
            bill = b_repo.create(2025, 1, 100.0, 50.0, 30.0)
            comp = c_repo.add(bill.id, "Electricity", 100.0)
            adj = ca_repo.upsert(bill.id, comp.id, p.id, True, {"mode": "percent", "targets": {2: 100}})
            assert adj.zero is True
            # JSON serialization converts int keys to strings
            assert adj.redis_rule["mode"] == "percent"
            assert "2" in adj.redis_rule["targets"] or 2 in adj.redis_rule["targets"]

    def test_upsert_updates_existing(self, app):
        with app.app_context():
            p_repo = ParticipantRepository()
            b_repo = MonthlyBillRepository()
            c_repo = BillComponentRepository()
            ca_repo = ComponentAdjustmentRepository()
            p = p_repo.add("P")
            bill = b_repo.create(2025, 1, 100.0, 50.0, 30.0)
            comp = c_repo.add(bill.id, "Electricity", 100.0)
            ca_repo.upsert(bill.id, comp.id, p.id, True)
            updated = ca_repo.upsert(bill.id, comp.id, p.id, False)
            assert updated.zero is False
            # Should still have only one adjustment
            adjs = ca_repo.list_for_month(bill.id)
            assert len(adjs) == 1

    def test_list_for_month(self, app):
        with app.app_context():
            p_repo = ParticipantRepository()
            b_repo = MonthlyBillRepository()
            c_repo = BillComponentRepository()
            ca_repo = ComponentAdjustmentRepository()
            p1 = p_repo.add("P1")
            p2 = p_repo.add("P2")
            bill = b_repo.create(2025, 1, 100.0, 50.0, 30.0)
            comp = c_repo.add(bill.id, "Electricity", 100.0)
            ca_repo.upsert(bill.id, comp.id, p1.id, True)
            ca_repo.upsert(bill.id, comp.id, p2.id, False)
            adjs = ca_repo.list_for_month(bill.id)
            assert len(adjs) == 2

    def test_clear_for_month(self, app):
        with app.app_context():
            p_repo = ParticipantRepository()
            b_repo = MonthlyBillRepository()
            c_repo = BillComponentRepository()
            ca_repo = ComponentAdjustmentRepository()
            p = p_repo.add("P")
            bill = b_repo.create(2025, 1, 100.0, 50.0, 30.0)
            comp = c_repo.add(bill.id, "Electricity", 100.0)
            ca_repo.upsert(bill.id, comp.id, p.id, True)
            ca_repo.clear_for_month(bill.id)
            assert len(ca_repo.list_for_month(bill.id)) == 0
