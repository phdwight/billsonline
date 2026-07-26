"""Tests for the printable month summary PDF export."""
import pytest

from app import create_app
from app.extensions import db
from app.models import (
    BillComponent,
    ComponentAdjustment,
    MeterReading,
    MonthParticipant,
    MonthlyBill,
    Participant,
)


@pytest.fixture
def pdf_app():
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
def pdf_client(pdf_app):
    return pdf_app.test_client()


@pytest.fixture
def full_month(pdf_app):
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
                     reading_previous=100, reading_current=150),
        MeterReading(month_id=bill.id, participant_id=bob.id,
                     reading_previous=200, reading_current=350),
    ])
    elec = BillComponent(month_id=bill.id, name="Electricity", amount=2000.0,
                         split_method="usage", position=0)
    net = BillComponent(month_id=bill.id, name="Internet", amount=1000.0,
                        split_method="equal", position=1)
    water = BillComponent(month_id=bill.id, name="Water", amount=500.0,
                          split_method="percentage", position=2,
                          distribution={str(alice.id): 60.0, str(bob.id): 40.0})
    db.session.add_all([elec, net, water])
    db.session.flush()
    db.session.add(ComponentAdjustment(
        month_id=bill.id, component_id=net.id, participant_id=alice.id, zero=False,
        redis_rule={"mode": "percent", "targets": {str(bob.id): 100.0}},
        notes="Bob covers Alice's internet",
    ))
    db.session.commit()
    return bill


def _pdf_text(data: bytes) -> str:
    import io
    from pypdf import PdfReader
    raw = "\n".join(page.extract_text() for page in PdfReader(io.BytesIO(data)).pages)
    # Table cells wrap; collapse whitespace so assertions match across breaks
    return " ".join(raw.split())


def test_pdf_downloads_with_filename(pdf_client, full_month):
    resp = pdf_client.get(f"/months/{full_month.id}/export.pdf")
    assert resp.status_code == 200
    assert resp.mimetype == "application/pdf"
    assert resp.data.startswith(b"%PDF")
    assert "bill_2026-June.pdf" in resp.headers["Content-Disposition"]
    # Cloudflare caches .pdf/.csv by extension unless told not to
    assert resp.headers["Cache-Control"] == "no-store"


def test_pdf_contains_all_sections(pdf_client, full_month):
    text = _pdf_text(pdf_client.get(f"/months/{full_month.id}/export.pdf").data)
    # header
    assert "June 2026" in text
    # consumption + raw usage cost before adjustments
    assert "Meter Readings" in text
    assert "Alice" in text and "Bob" in text
    assert "20.00" in text  # total usage 5 + 15 kWh (meter deltas / 10)
    assert "₱100.00/kWh" in text  # 2000 / 20 kWh
    assert "Base cost" in text
    # Alice 5/20 x 2000 = 500, Bob 15/20 x 2000 = 1500 (before adjustments)
    assert "1,500.00" in text
    # components
    assert "Bill Components" in text
    assert "Electricity" in text and "Internet" in text
    assert "₱3,500.00" in text  # grand total
    # percent custom shares show the derived amount (60% of 500 = 300)
    assert "Alice: 60.00% (₱300.00)" in text
    assert "Bob: 40.00% (₱200.00)" in text
    # redistribution
    assert "Advanced Redistribution" in text
    assert "Bob covers Alice's internet" in text
    assert "100.00%" in text
    # final computation: Alice elec 500 (usage 50/200) + water 300, internet to Bob
    assert "Final Computation" in text
    assert "₱800.00" in text  # Alice's total
    assert "₱2,700.00" in text  # Bob's total


def test_pdf_omits_redistribution_without_entries(pdf_client, full_month):
    ComponentAdjustment.query.delete()
    db.session.commit()
    text = _pdf_text(pdf_client.get(f"/months/{full_month.id}/export.pdf").data)
    assert "Advanced Redistribution" not in text


def test_pdf_missing_month_redirects(pdf_client):
    resp = pdf_client.get("/months/999/export.pdf")
    assert resp.status_code == 302
