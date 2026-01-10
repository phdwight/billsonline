"""Tests for Flask routes (HTTP endpoints)."""
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import pytest
from app import create_app
from app.extensions import db
from app.models import Participant, MonthlyBill, BillComponent, MonthParticipant


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
def sample_participant(app):
    """Create a sample participant."""
    with app.app_context():
        p = Participant(name="TestUser")
        db.session.add(p)
        db.session.commit()
        return p.id


@pytest.fixture
def sample_bill(app):
    """Create a sample monthly bill."""
    with app.app_context():
        bill = MonthlyBill(
            year=2025, month=1,
            electricity_amount=100.0,
            water_amount=50.0,
            internet_amount=30.0
        )
        db.session.add(bill)
        db.session.commit()
        return bill.id


class TestIndexRoute:
    def test_index_redirects_to_admin_when_no_bills(self, client, app):
        """Home should redirect to admin when there are no bills."""
        # Ensure no bills exist
        with app.app_context():
            from app.models import MonthlyBill
            MonthlyBill.query.delete()
            db.session.commit()
        response = client.get("/")
        assert response.status_code == 302
        assert "/admin" in response.location

    def test_index_redirects_to_latest_month(self, client, app):
        """Home should redirect to the latest month detail."""
        with app.app_context():
            bill = MonthlyBill(year=2025, month=6, electricity_amount=100, water_amount=50, internet_amount=30)
            db.session.add(bill)
            db.session.commit()
            bill_id = bill.id
        response = client.get("/")
        assert response.status_code == 302
        assert f"/months/{bill_id}" in response.location


class TestAdminRoute:
    def test_admin_returns_200(self, client):
        response = client.get("/admin")
        assert response.status_code == 200
        assert b"Admin" in response.data

    def test_admin_pagination(self, client, app):
        # Create some bills
        with app.app_context():
            for m in range(1, 6):
                bill = MonthlyBill(year=2025, month=m, electricity_amount=100, water_amount=50, internet_amount=30)
                db.session.add(bill)
            db.session.commit()
        response = client.get("/admin?page=1")
        assert response.status_code == 200


class TestParticipantRoutes:
    def test_participants_page(self, client):
        response = client.get("/participants/")
        assert response.status_code == 200

    def test_add_participant(self, client, app):
        response = client.post("/participants/", data={"name": "Alice"}, follow_redirects=True)
        assert response.status_code == 200
        with app.app_context():
            p = Participant.query.filter_by(name="Alice").first()
            assert p is not None

    def test_add_participant_empty_name(self, client):
        response = client.post("/participants/", data={"name": ""}, follow_redirects=True)
        assert response.status_code == 200
        assert b"Name is required" in response.data or b"error" in response.data.lower()

    def test_add_duplicate_participant(self, client, app):
        client.post("/participants/", data={"name": "Bob"})
        response = client.post("/participants/", data={"name": "bob"}, follow_redirects=True)  # Case insensitive
        assert response.status_code == 200
        with app.app_context():
            count = Participant.query.filter_by(name="Bob").count()
            assert count == 1

    def test_update_participant(self, client, app, sample_participant):
        response = client.post(
            f"/participants/{sample_participant}",
            data={"name": "UpdatedName"},
            follow_redirects=True
        )
        assert response.status_code == 200
        with app.app_context():
            p = db.session.get(Participant, sample_participant)
            assert p.name == "UpdatedName"

    def test_update_participant_empty_name(self, client, sample_participant):
        response = client.post(
            f"/participants/{sample_participant}",
            data={"name": ""},
            follow_redirects=True
        )
        assert response.status_code == 200
        assert b"required" in response.data.lower()


class TestMonthRoutes:
    def test_new_month_page(self, client):
        response = client.get("/months/new")
        assert response.status_code == 200

    def test_add_month(self, client, app):
        response = client.post("/months", data={
            "year": 2025,
            "month": 6,
            "electricity_amount": 100.0,
            "water_amount": 50.0,
            "internet_amount": 30.0,
        }, follow_redirects=True)
        assert response.status_code == 200
        with app.app_context():
            bill = MonthlyBill.query.filter_by(year=2025, month=6).first()
            assert bill is not None
            assert bill.electricity_amount == 100.0

    def test_add_duplicate_month(self, client, app):
        # Create first
        client.post("/months", data={
            "year": 2025, "month": 7,
            "electricity_amount": 100.0, "water_amount": 50.0, "internet_amount": 30.0,
        })
        # Try duplicate
        response = client.post("/months", data={
            "year": 2025, "month": 7,
            "electricity_amount": 200.0, "water_amount": 100.0, "internet_amount": 60.0,
        }, follow_redirects=True)
        assert response.status_code == 200
        # Should still have only one
        with app.app_context():
            count = MonthlyBill.query.filter_by(year=2025, month=7).count()
            assert count == 1

    def test_month_detail(self, client, sample_bill):
        response = client.get(f"/months/{sample_bill}")
        assert response.status_code == 200

    def test_month_detail_not_found(self, client):
        response = client.get("/months/9999", follow_redirects=True)
        assert response.status_code == 200
        assert b"not found" in response.data.lower()

    def test_edit_month_page(self, client, sample_bill):
        response = client.get(f"/months/{sample_bill}/edit")
        assert response.status_code == 200

    def test_edit_month_archived(self, client, app, sample_bill):
        with app.app_context():
            bill = db.session.get(MonthlyBill, sample_bill)
            bill.archived = True
            db.session.commit()
        response = client.get(f"/months/{sample_bill}/edit", follow_redirects=True)
        assert response.status_code == 200
        assert b"archived" in response.data.lower()


class TestComponentRoutes:
    def test_add_component(self, client, app, sample_bill):
        response = client.post(f"/months/{sample_bill}/components", data={
            "component_name": "Gas",
            "component_amount": 75.0,
            "component_split_method": "equal",
            "component_position": 0,
        }, follow_redirects=True)
        assert response.status_code == 200
        with app.app_context():
            comp = BillComponent.query.filter_by(month_id=sample_bill, name="Gas").first()
            assert comp is not None
            assert comp.amount == 75.0

    def test_add_component_empty_name(self, client, sample_bill):
        response = client.post(f"/months/{sample_bill}/components", data={
            "component_name": "",
            "component_amount": 75.0,
            "component_split_method": "equal",
        }, follow_redirects=True)
        assert response.status_code == 200
        assert b"required" in response.data.lower()

    def test_add_component_invalid_split(self, client, sample_bill):
        response = client.post(f"/months/{sample_bill}/components", data={
            "component_name": "Invalid",
            "component_amount": 75.0,
            "component_split_method": "invalid_method",
        }, follow_redirects=True)
        assert response.status_code == 200
        assert b"usage" in response.data.lower() or b"equal" in response.data.lower()

    def test_add_component_to_archived_month(self, client, app, sample_bill):
        with app.app_context():
            bill = db.session.get(MonthlyBill, sample_bill)
            bill.archived = True
            db.session.commit()
        response = client.post(f"/months/{sample_bill}/components", data={
            "component_name": "NewComp",
            "component_amount": 100.0,
            "component_split_method": "equal",
        }, follow_redirects=True)
        assert response.status_code == 200
        assert b"archived" in response.data.lower()

    def test_update_component(self, client, app, sample_bill):
        with app.app_context():
            comp = BillComponent(month_id=sample_bill, name="Original", amount=100.0, split_method="equal")
            db.session.add(comp)
            db.session.commit()
            comp_id = comp.id
        response = client.post(f"/months/{sample_bill}/components/{comp_id}", data={
            "name": "Updated",
            "amount": 200.0,
            "split_method": "usage",
        }, follow_redirects=True)
        assert response.status_code == 200
        with app.app_context():
            comp = db.session.get(BillComponent, comp_id)
            assert comp.name == "Updated"
            assert comp.amount == 200.0

    def test_delete_component(self, client, app, sample_bill):
        with app.app_context():
            comp = BillComponent(month_id=sample_bill, name="ToDelete", amount=100.0, split_method="equal")
            db.session.add(comp)
            db.session.commit()
            comp_id = comp.id
        response = client.post(f"/months/{sample_bill}/components/{comp_id}/delete", follow_redirects=True)
        assert response.status_code == 200
        with app.app_context():
            comp = db.session.get(BillComponent, comp_id)
            assert comp is None


class TestMonthParticipantRoutes:
    def test_add_month_participant(self, client, app, sample_bill, sample_participant):
        response = client.post(f"/months/{sample_bill}/participants", data={
            "participant_id": sample_participant,
        }, follow_redirects=True)
        assert response.status_code == 200
        with app.app_context():
            mp = MonthParticipant.query.filter_by(month_id=sample_bill, participant_id=sample_participant).first()
            assert mp is not None

    def test_remove_month_participant(self, client, app, sample_bill, sample_participant):
        # First add through proper repository to ensure it works
        client.post(f"/months/{sample_bill}/participants", data={
            "participant_id": sample_participant,
        })
        # Then remove
        response = client.post(f"/months/{sample_bill}/participants/{sample_participant}/delete", follow_redirects=True)
        assert response.status_code == 200
        assert b"unlinked" in response.data.lower()

    def test_add_participant_to_archived_month(self, client, app, sample_bill, sample_participant):
        with app.app_context():
            bill = db.session.get(MonthlyBill, sample_bill)
            bill.archived = True
            db.session.commit()
        response = client.post(f"/months/{sample_bill}/participants", data={
            "participant_id": sample_participant,
        }, follow_redirects=True)
        assert response.status_code == 200
        assert b"archived" in response.data.lower()


class TestConvertLegacyRoute:
    def test_convert_legacy_to_dynamic(self, client, app):
        # Create a bill without components
        with app.app_context():
            bill = MonthlyBill(year=2025, month=8, electricity_amount=300, water_amount=90, internet_amount=60)
            db.session.add(bill)
            db.session.commit()
            bill_id = bill.id
        response = client.post(f"/months/{bill_id}/components/convert-legacy", follow_redirects=True)
        assert response.status_code == 200
        with app.app_context():
            comps = BillComponent.query.filter_by(month_id=bill_id).all()
            assert len(comps) == 3
            names = {c.name for c in comps}
            assert "Electricity" in names
            assert "Water" in names
            assert "Internet" in names

    def test_convert_legacy_already_has_components(self, client, app, sample_bill):
        # Add a component first
        with app.app_context():
            comp = BillComponent(month_id=sample_bill, name="Existing", amount=100.0, split_method="equal")
            db.session.add(comp)
            db.session.commit()
        response = client.post(f"/months/{sample_bill}/components/convert-legacy", follow_redirects=True)
        assert response.status_code == 200
        assert b"already has components" in response.data.lower()

    def test_convert_legacy_archived(self, client, app, sample_bill):
        with app.app_context():
            bill = db.session.get(MonthlyBill, sample_bill)
            bill.archived = True
            db.session.commit()
        response = client.post(f"/months/{sample_bill}/components/convert-legacy", follow_redirects=True)
        assert response.status_code == 200
        assert b"archived" in response.data.lower()


class TestArchiveRoutes:
    def test_archive_month(self, client, app, sample_bill):
        response = client.post(f"/months/{sample_bill}/archive", follow_redirects=True)
        assert response.status_code == 200
        with app.app_context():
            bill = db.session.get(MonthlyBill, sample_bill)
            assert bill.archived is True

    def test_unarchive_month_disabled(self, client, app, sample_bill):
        # First archive
        with app.app_context():
            bill = db.session.get(MonthlyBill, sample_bill)
            bill.archived = True
            db.session.commit()
        response = client.post(f"/months/{sample_bill}/unarchive", follow_redirects=True)
        assert response.status_code == 200
        # Unarchiving is disabled - should still be archived
        assert b"not allowed" in response.data.lower()
        with app.app_context():
            bill = db.session.get(MonthlyBill, sample_bill)
            assert bill.archived is True

    def test_archived_page(self, client, app):
        with app.app_context():
            bill = MonthlyBill(year=2025, month=9, electricity_amount=100, water_amount=50, internet_amount=30, archived=True)
            db.session.add(bill)
            db.session.commit()
        response = client.get("/months/archived")
        assert response.status_code == 200


class TestDeleteRoute:
    def test_delete_month(self, client, app, sample_bill):
        response = client.post(f"/months/{sample_bill}/delete", follow_redirects=True)
        assert response.status_code == 200
        with app.app_context():
            bill = db.session.get(MonthlyBill, sample_bill)
            assert bill is None


class TestSettingsRoute:
    def test_settings_page_returns_200(self, client):
        response = client.get("/settings/")
        assert response.status_code == 200
        assert b"Settings" in response.data
        assert b"Database" in response.data

    def test_settings_page_has_download_link(self, client):
        response = client.get("/settings/")
        assert b"Download Database" in response.data

    def test_settings_page_has_upload_form(self, client):
        response = client.get("/settings/")
        assert b"Restore" in response.data
        assert b'enctype="multipart/form-data"' in response.data
        # File input for select
        assert b"Select .db file" in response.data

    def test_settings_page_has_upload_indicator(self, client):
        response = client.get("/settings/")
        assert b"upload-indicator" in response.data
        assert b"Uploading..." in response.data


class TestDatabaseDownloadRoute:
    def test_download_database_redirects_for_memory_db(self, client):
        """In-memory database cannot be downloaded, should redirect with error."""
        response = client.get("/settings/database", follow_redirects=True)
        assert response.status_code == 200
        # Should redirect to settings with error flash


class TestDatabaseUploadRoute:
    def test_upload_no_file(self, client):
        response = client.post("/settings/database", follow_redirects=True)
        assert response.status_code == 200
        assert b"No file uploaded" in response.data

    def test_upload_empty_filename(self, client):
        from io import BytesIO
        data = {"database": (BytesIO(b""), "")}
        response = client.post("/settings/database", data=data, content_type="multipart/form-data", follow_redirects=True)
        assert response.status_code == 200
        assert b"No file selected" in response.data

    def test_upload_invalid_file_type(self, client):
        from io import BytesIO
        data = {"database": (BytesIO(b"test content"), "test.txt")}
        response = client.post("/settings/database", data=data, content_type="multipart/form-data", follow_redirects=True)
        assert response.status_code == 200
        assert b"Invalid file type" in response.data


class TestVersionDisplay:
    def test_version_in_page(self, client):
        """Version should be displayed on every page."""
        response = client.get("/admin")
        assert response.status_code == 200
        # Check for version footer
        assert b"version-footer" in response.data
        # Version should start with 'v' followed by numbers
        assert b">v" in response.data
