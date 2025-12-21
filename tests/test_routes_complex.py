"""Complex integration tests for Flask routes - components, adjustments, readings, CSV export."""
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import pytest
from app import create_app
from app.extensions import db
from app.models import (
    Participant, MonthlyBill, MeterReading, BillComponent,
    ComponentAdjustment, MonthParticipant
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


@pytest.fixture
def setup_bill_with_participants(app):
    """Create a bill with participants and components for complex tests."""
    with app.app_context():
        # Create participants
        p1 = Participant(name="Alice")
        p2 = Participant(name="Bob")
        p3 = Participant(name="Cara")
        db.session.add_all([p1, p2, p3])
        db.session.commit()

        # Create bill
        bill = MonthlyBill(
            year=2025, month=3,
            electricity_amount=300.0,
            water_amount=90.0,
            internet_amount=60.0
        )
        db.session.add(bill)
        db.session.commit()

        # Link participants to month
        for p in [p1, p2, p3]:
            mp = MonthParticipant(month_id=bill.id, participant_id=p.id)
            db.session.add(mp)
        db.session.commit()

        return {
            "bill_id": bill.id,
            "participant_ids": [p1.id, p2.id, p3.id],
            "participant_names": ["Alice", "Bob", "Cara"]
        }


class TestAddMonthWithComponents:
    """Test creating months with dynamic components."""

    def test_add_month_with_legacy_components(self, client, app):
        """Test that legacy electricity/water/internet become components."""
        # First create a participant
        client.post("/participants", data={"name": "TestUser"})
        
        response = client.post("/months", data={
            "year": 2025,
            "month": 4,
            "electricity_amount": 150.0,
            "water_amount": 75.0,
            "internet_amount": 45.0,
        }, follow_redirects=True)
        assert response.status_code == 200
        
        with app.app_context():
            bill = MonthlyBill.query.filter_by(year=2025, month=4).first()
            assert bill is not None
            components = BillComponent.query.filter_by(month_id=bill.id).all()
            names = {c.name for c in components}
            assert "Electricity" in names
            assert "Water" in names
            assert "Internet" in names

    def test_add_month_with_custom_components(self, client, app):
        """Test adding a month with custom components via form arrays."""
        client.post("/participants", data={"name": "TestUser"})
        
        response = client.post("/months", data={
            "year": 2025,
            "month": 5,
            "electricity_amount": 0,
            "water_amount": 0,
            "internet_amount": 0,
            "comp_name[]": ["Gas", "Maintenance"],
            "comp_amount[]": ["80.0", "120.0"],
            "comp_split[]": ["equal", "equal"],
            "comp_position[]": ["0", "1"],
        }, follow_redirects=True)
        assert response.status_code == 200
        
        with app.app_context():
            bill = MonthlyBill.query.filter_by(year=2025, month=5).first()
            assert bill is not None
            components = BillComponent.query.filter_by(month_id=bill.id).all()
            comp_names = {c.name for c in components}
            assert "Gas" in comp_names
            assert "Maintenance" in comp_names

    def test_add_month_with_percentage_split(self, client, app):
        """Test creating a month with percentage-based component."""
        # Create participants first
        client.post("/participants", data={"name": "Alice"})
        client.post("/participants", data={"name": "Bob"})
        
        with app.app_context():
            participants = Participant.query.all()
            p1_id, p2_id = participants[0].id, participants[1].id
        
        response = client.post("/months", data={
            "year": 2025,
            "month": 6,
            "electricity_amount": 100.0,
            "water_amount": 50.0,
            "internet_amount": 30.0,
            "legacy_electricity_split": "percentage",
            f"legacy_electricity_dist_{p1_id}": "60",
            f"legacy_electricity_dist_{p2_id}": "40",
        }, follow_redirects=True)
        assert response.status_code == 200
        
        with app.app_context():
            bill = MonthlyBill.query.filter_by(year=2025, month=6).first()
            elec = BillComponent.query.filter_by(month_id=bill.id, name="Electricity").first()
            assert elec is not None
            assert elec.split_method == "percentage"
            assert elec.distribution is not None

    def test_add_month_skips_empty_component_names(self, client, app):
        """Test that empty component names are skipped."""
        client.post("/participants", data={"name": "TestUser"})
        
        response = client.post("/months", data={
            "year": 2025,
            "month": 7,
            "electricity_amount": 100.0,
            "water_amount": 50.0,
            "internet_amount": 30.0,
            "comp_name[]": ["", "ValidName", ""],
            "comp_amount[]": ["100", "200", "300"],
            "comp_split[]": ["equal", "equal", "equal"],
        }, follow_redirects=True)
        assert response.status_code == 200
        
        with app.app_context():
            bill = MonthlyBill.query.filter_by(year=2025, month=7).first()
            custom_comps = BillComponent.query.filter_by(month_id=bill.id, name="ValidName").all()
            assert len(custom_comps) == 1


class TestMeterReadings:
    """Test meter reading submission."""

    def test_submit_readings(self, client, app, setup_bill_with_participants):
        """Test submitting meter readings for participants."""
        setup = setup_bill_with_participants
        bill_id = setup["bill_id"]
        p1, p2, p3 = setup["participant_ids"]
        
        response = client.post(f"/months/{bill_id}/readings", data={
            f"current_{p1}": "200",
            f"previous_{p1}": "100",
            f"current_{p2}": "150",
            f"previous_{p2}": "100",
            f"current_{p3}": "100",
            f"previous_{p3}": "100",
        }, follow_redirects=True)
        assert response.status_code == 200
        
        with app.app_context():
            readings = MeterReading.query.filter_by(month_id=bill_id).all()
            assert len(readings) == 3
            readings_by_pid = {r.participant_id: r for r in readings}
            assert readings_by_pid[p1].reading_current == 200.0
            assert readings_by_pid[p1].reading_previous == 100.0
            assert readings_by_pid[p1].usage() == 100.0

    def test_submit_readings_without_previous(self, client, app, setup_bill_with_participants):
        """Test submitting readings where previous is empty."""
        setup = setup_bill_with_participants
        bill_id = setup["bill_id"]
        p1 = setup["participant_ids"][0]
        
        response = client.post(f"/months/{bill_id}/readings", data={
            f"current_{p1}": "200",
            f"previous_{p1}": "",  # Empty previous
        }, follow_redirects=True)
        assert response.status_code == 200
        
        with app.app_context():
            reading = MeterReading.query.filter_by(month_id=bill_id, participant_id=p1).first()
            assert reading is not None
            assert reading.reading_current == 200.0
            assert reading.reading_previous is None
            assert reading.usage() == 0.0

    def test_submit_readings_archived_month(self, client, app, setup_bill_with_participants):
        """Test that readings cannot be submitted to archived month."""
        setup = setup_bill_with_participants
        bill_id = setup["bill_id"]
        
        with app.app_context():
            bill = db.session.get(MonthlyBill, bill_id)
            bill.archived = True
            db.session.commit()
        
        response = client.post(f"/months/{bill_id}/readings", data={
            f"current_{setup['participant_ids'][0]}": "200",
        }, follow_redirects=True)
        assert response.status_code == 200
        assert b"archived" in response.data.lower()

    def test_submit_readings_not_found(self, client):
        """Test submitting readings to non-existent month."""
        response = client.post("/months/9999/readings", data={}, follow_redirects=True)
        assert response.status_code == 200
        assert b"not found" in response.data.lower()


class TestComponentAdjustments:
    """Test saving component adjustments with redistribution rules."""

    def test_save_adjustments_no_rules(self, client, app, setup_bill_with_participants):
        """Test saving adjustments without any redistribution rules."""
        setup = setup_bill_with_participants
        bill_id = setup["bill_id"]
        
        # First add a component
        with app.app_context():
            comp = BillComponent(month_id=bill_id, name="Water", amount=90.0, split_method="equal")
            db.session.add(comp)
            db.session.commit()
        
        response = client.post(f"/months/{bill_id}/components/adjustments", data={}, follow_redirects=True)
        assert response.status_code == 200
        assert b"adjustments saved" in response.data.lower()

    def test_save_adjustments_with_percent_rule(self, client, app, setup_bill_with_participants):
        """Test saving redistribution with percent mode."""
        setup = setup_bill_with_participants
        bill_id = setup["bill_id"]
        p1, p2, p3 = setup["participant_ids"]
        
        with app.app_context():
            comp = BillComponent(month_id=bill_id, name="Water", amount=90.0, split_method="equal")
            db.session.add(comp)
            db.session.commit()
            comp_id = comp.id
        
        # Zero out p1's water and redistribute 60% to p2, 40% to p3
        response = client.post(f"/months/{bill_id}/components/adjustments", data={
            f"mode_comp_{comp_id}_{p1}": "percent",
            f"redis_comp_{comp_id}_{p1}_{p2}": "60",
            f"redis_comp_{comp_id}_{p1}_{p3}": "40",
        }, follow_redirects=True)
        assert response.status_code == 200
        assert b"redistribution rule" in response.data.lower()
        
        with app.app_context():
            adj = ComponentAdjustment.query.filter_by(
                month_id=bill_id, component_id=comp_id, participant_id=p1
            ).first()
            assert adj is not None
            assert adj.zero is True
            assert adj.redis_rule["mode"] == "percent"

    def test_save_adjustments_invalid_percent_sum(self, client, app, setup_bill_with_participants):
        """Test that invalid percent sum shows error."""
        setup = setup_bill_with_participants
        bill_id = setup["bill_id"]
        p1, p2, p3 = setup["participant_ids"]
        
        with app.app_context():
            comp = BillComponent(month_id=bill_id, name="Water", amount=90.0, split_method="equal")
            db.session.add(comp)
            db.session.commit()
            comp_id = comp.id
        
        # Invalid: percentages don't sum to 100
        response = client.post(f"/months/{bill_id}/components/adjustments", data={
            f"mode_comp_{comp_id}_{p1}": "percent",
            f"redis_comp_{comp_id}_{p1}_{p2}": "30",
            f"redis_comp_{comp_id}_{p1}_{p3}": "30",  # Only 60%, not 100%
        }, follow_redirects=True)
        assert response.status_code == 200
        assert b"must sum to 100%" in response.data.lower()

    def test_save_adjustments_archived_month(self, client, app, setup_bill_with_participants):
        """Test that adjustments cannot be saved to archived month."""
        setup = setup_bill_with_participants
        bill_id = setup["bill_id"]
        
        with app.app_context():
            bill = db.session.get(MonthlyBill, bill_id)
            bill.archived = True
            db.session.commit()
        
        response = client.post(f"/months/{bill_id}/components/adjustments", data={}, follow_redirects=True)
        assert response.status_code == 200
        assert b"archived" in response.data.lower()


class TestCSVExport:
    """Test CSV export functionality."""

    def test_export_csv_with_components(self, client, app, setup_bill_with_participants):
        """Test CSV export for a month with components."""
        setup = setup_bill_with_participants
        bill_id = setup["bill_id"]
        p1, p2, p3 = setup["participant_ids"]
        
        # Add components and readings
        with app.app_context():
            bill = db.session.get(MonthlyBill, bill_id)
            # Add components
            c1 = BillComponent(month_id=bill_id, name="Electricity", amount=300.0, split_method="usage", position=0)
            c2 = BillComponent(month_id=bill_id, name="Water", amount=90.0, split_method="equal", position=1)
            db.session.add_all([c1, c2])
            db.session.commit()
            
            # Add readings for usage-based split
            r1 = MeterReading(month_id=bill_id, participant_id=p1, reading_current=200, reading_previous=100)
            r2 = MeterReading(month_id=bill_id, participant_id=p2, reading_current=150, reading_previous=100)
            r3 = MeterReading(month_id=bill_id, participant_id=p3, reading_current=100, reading_previous=100)
            db.session.add_all([r1, r2, r3])
            db.session.commit()
        
        response = client.get(f"/months/{bill_id}/export.csv")
        assert response.status_code == 200
        assert "text/csv" in response.content_type
        assert b"Participant" in response.data
        assert b"Electricity" in response.data
        assert b"Water" in response.data
        assert b"Alice" in response.data
        assert b"Bob" in response.data
        assert b"Cara" in response.data

    def test_export_csv_synthesizes_legacy_components(self, client, app):
        """Test CSV export synthesizes components from legacy amounts."""
        with app.app_context():
            p = Participant(name="Solo")
            db.session.add(p)
            db.session.commit()
            
            # Bill without explicit components
            bill = MonthlyBill(
                year=2025, month=8,
                electricity_amount=100.0,
                water_amount=50.0,
                internet_amount=30.0
            )
            db.session.add(bill)
            db.session.commit()
            bill_id = bill.id
        
        response = client.get(f"/months/{bill_id}/export.csv")
        assert response.status_code == 200
        assert "text/csv" in response.content_type
        # Should synthesize Electricity, Water, Internet from legacy amounts
        assert b"Electricity" in response.data
        assert b"Water" in response.data
        assert b"Internet" in response.data

    def test_export_csv_not_found(self, client):
        """Test CSV export for non-existent month."""
        response = client.get("/months/9999/export.csv", follow_redirects=True)
        assert response.status_code == 200
        assert b"not found" in response.data.lower()

    def test_export_csv_filename(self, client, app):
        """Test CSV export has correct filename."""
        with app.app_context():
            p = Participant(name="Test")
            db.session.add(p)
            db.session.commit()
            
            bill = MonthlyBill(year=2025, month=3, electricity_amount=100, water_amount=50, internet_amount=30)
            db.session.add(bill)
            db.session.commit()
            bill_id = bill.id
        
        response = client.get(f"/months/{bill_id}/export.csv")
        assert response.status_code == 200
        content_disp = response.headers.get("Content-Disposition", "")
        assert "bill_2025-March.csv" in content_disp


class TestUpdateMonth:
    """Test updating month amounts."""

    def test_update_month_amounts(self, client, app, setup_bill_with_participants):
        """Test updating electricity/water/internet amounts."""
        setup = setup_bill_with_participants
        bill_id = setup["bill_id"]
        
        response = client.post(f"/months/{bill_id}/edit", data={
            "year": 2025,
            "month": 3,
            "electricity_amount": 400.0,
            "water_amount": 120.0,
            "internet_amount": 80.0,
        }, follow_redirects=True)
        assert response.status_code == 200
        
        with app.app_context():
            bill = db.session.get(MonthlyBill, bill_id)
            assert bill.electricity_amount == 400.0
            assert bill.water_amount == 120.0
            assert bill.internet_amount == 80.0

    def test_update_month_archived(self, client, app, setup_bill_with_participants):
        """Test that archived months cannot be updated."""
        setup = setup_bill_with_participants
        bill_id = setup["bill_id"]
        
        with app.app_context():
            bill = db.session.get(MonthlyBill, bill_id)
            bill.archived = True
            db.session.commit()
        
        response = client.post(f"/months/{bill_id}/edit", data={
            "year": 2025,
            "month": 3,
            "electricity_amount": 999.0,
            "water_amount": 999.0,
            "internet_amount": 999.0,
        }, follow_redirects=True)
        assert response.status_code == 200
        assert b"archived" in response.data.lower()


class TestComponentUpdateValidation:
    """Test component update edge cases."""

    def test_update_component_invalid_amount(self, client, app, setup_bill_with_participants):
        """Test updating component with invalid amount."""
        setup = setup_bill_with_participants
        bill_id = setup["bill_id"]
        
        with app.app_context():
            comp = BillComponent(month_id=bill_id, name="Test", amount=100.0, split_method="equal")
            db.session.add(comp)
            db.session.commit()
            comp_id = comp.id
        
        response = client.post(f"/months/{bill_id}/components/{comp_id}/update", data={
            "amount": "not_a_number",
        }, follow_redirects=True)
        assert response.status_code == 200
        assert b"number" in response.data.lower()

    def test_update_component_negative_amount(self, client, app, setup_bill_with_participants):
        """Test updating component with negative amount."""
        setup = setup_bill_with_participants
        bill_id = setup["bill_id"]
        
        with app.app_context():
            comp = BillComponent(month_id=bill_id, name="Test", amount=100.0, split_method="equal")
            db.session.add(comp)
            db.session.commit()
            comp_id = comp.id
        
        response = client.post(f"/months/{bill_id}/components/{comp_id}/update", data={
            "amount": "-50",
        }, follow_redirects=True)
        assert response.status_code == 200
        assert b"non-negative" in response.data.lower()

    def test_update_component_invalid_position(self, client, app, setup_bill_with_participants):
        """Test updating component with invalid position."""
        setup = setup_bill_with_participants
        bill_id = setup["bill_id"]
        
        with app.app_context():
            comp = BillComponent(month_id=bill_id, name="Test", amount=100.0, split_method="equal")
            db.session.add(comp)
            db.session.commit()
            comp_id = comp.id
        
        response = client.post(f"/months/{bill_id}/components/{comp_id}/update", data={
            "position": "not_an_int",
        }, follow_redirects=True)
        assert response.status_code == 200
        assert b"integer" in response.data.lower()

    def test_update_component_invalid_split_method(self, client, app, setup_bill_with_participants):
        """Test updating component with invalid split method."""
        setup = setup_bill_with_participants
        bill_id = setup["bill_id"]
        
        with app.app_context():
            comp = BillComponent(month_id=bill_id, name="Test", amount=100.0, split_method="equal")
            db.session.add(comp)
            db.session.commit()
            comp_id = comp.id
        
        response = client.post(f"/months/{bill_id}/components/{comp_id}/update", data={
            "split_method": "invalid_method",
        }, follow_redirects=True)
        assert response.status_code == 200
        # Should show error about valid split methods
        assert b"usage" in response.data.lower() or b"equal" in response.data.lower()


class TestConvertLegacyEdgeCases:
    """Test edge cases for legacy conversion."""

    def test_convert_legacy_no_amounts(self, client, app):
        """Test converting a month with all zero amounts."""
        with app.app_context():
            bill = MonthlyBill(year=2025, month=9, electricity_amount=0, water_amount=0, internet_amount=0)
            db.session.add(bill)
            db.session.commit()
            bill_id = bill.id
        
        response = client.post(f"/months/{bill_id}/components/convert-from-legacy", follow_redirects=True)
        assert response.status_code == 200
        assert b"no legacy amounts" in response.data.lower()


class TestParticipantEdgeCases:
    """Test participant-related edge cases."""

    def test_add_participant_no_participant_id(self, client, app, setup_bill_with_participants):
        """Test adding participant to month without selecting one."""
        setup = setup_bill_with_participants
        bill_id = setup["bill_id"]
        
        response = client.post(f"/months/{bill_id}/participants/add", data={
            "participant_id": "",
        }, follow_redirects=True)
        assert response.status_code == 200
        assert b"select" in response.data.lower()

    def test_update_participant_duplicate_name(self, client, app):
        """Test updating participant to a name that already exists."""
        client.post("/participants", data={"name": "Alice"})
        client.post("/participants", data={"name": "Bob"})
        
        with app.app_context():
            bob = Participant.query.filter_by(name="Bob").first()
            bob_id = bob.id
        
        response = client.post(f"/participants/{bob_id}/update", data={
            "name": "Alice",  # Already exists
        }, follow_redirects=True)
        assert response.status_code == 200
        assert b"already has that name" in response.data.lower()
