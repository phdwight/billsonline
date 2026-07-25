"""Archived months must show a read-only summary of redistribution entries."""
import pytest

from app import create_app
from app.extensions import db
from app.models import (
    BillComponent,
    ComponentAdjustment,
    MonthParticipant,
    MonthlyBill,
    Participant,
)


@pytest.fixture
def arch_app():
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
def arch_client(arch_app):
    return arch_app.test_client()


@pytest.fixture
def archived_month(arch_app):
    alice = Participant(name="Alice")
    bob = Participant(name="Bob")
    db.session.add_all([alice, bob])
    db.session.flush()
    bill = MonthlyBill(year=2026, month=5, electricity_amount=0, water_amount=0,
                       internet_amount=0, archived=True)
    db.session.add(bill)
    db.session.flush()
    db.session.add_all([
        MonthParticipant(month_id=bill.id, participant_id=alice.id),
        MonthParticipant(month_id=bill.id, participant_id=bob.id),
    ])
    comp = BillComponent(month_id=bill.id, name="Internet", amount=2100.0, split_method="equal")
    db.session.add(comp)
    db.session.commit()
    return bill, comp, alice, bob


def test_archived_month_shows_redistribution_entries(arch_client, archived_month):
    bill, comp, alice, bob = archived_month
    db.session.add(ComponentAdjustment(
        month_id=bill.id, component_id=comp.id, participant_id=alice.id, zero=False,
        redis_rule={"mode": "percent", "targets": {str(bob.id): 60.0, str(alice.id): 40.0}},
        notes="Alice splits with Bob",
    ))
    db.session.commit()

    html = arch_client.get(f"/months/{bill.id}").data.decode()
    assert "Advanced redistribution" in html
    # Internet is 2100 split equally between 2 -> Alice's base share is 1050;
    # percent targets also show the derived amount of that share.
    assert "Bob: 60.00% (₱630.00)" in html
    assert "Alice: 40.00% (₱420.00)" in html
    assert "Alice splits with Bob" in html


def test_archived_month_hides_section_without_entries(arch_client, archived_month):
    bill, *_ = archived_month
    html = arch_client.get(f"/months/{bill.id}").data.decode()
    assert "Advanced redistribution" not in html


def test_archived_month_hides_empty_mode_rules(arch_client, archived_month):
    bill, comp, alice, _ = archived_month
    db.session.add(ComponentAdjustment(
        month_id=bill.id, component_id=comp.id, participant_id=alice.id,
        zero=False, redis_rule=None, notes="no rule here",
    ))
    db.session.commit()
    html = arch_client.get(f"/months/{bill.id}").data.decode()
    assert "Advanced redistribution" not in html
