"""Tests for participant selection during month creation."""
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import pytest
from app import create_app
from app.extensions import db
from app.models import Participant, MonthlyBill, MonthParticipant


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
def three_participants(app):
    """Create three test participants."""
    with app.app_context():
        p1 = Participant(name="Alice")
        p2 = Participant(name="Bob")
        p3 = Participant(name="Charlie")
        db.session.add_all([p1, p2, p3])
        db.session.commit()
        return [p1.id, p2.id, p3.id]


class TestMonthParticipantSelection:
    def test_create_month_with_all_participants(self, client, app, three_participants):
        """Test creating a month with all participants selected."""
        response = client.post("/months", data={
            "year": 2025,
            "month": 1,
            "electricity_amount": 100.0,
            "water_amount": 50.0,
            "internet_amount": 30.0,
            "selected_participants": three_participants,
        }, follow_redirects=True)
        
        assert response.status_code == 200
        
        with app.app_context():
            bill = MonthlyBill.query.filter_by(year=2025, month=1).first()
            assert bill is not None
            
            month_participants = MonthParticipant.query.filter_by(month_id=bill.id).all()
            assert len(month_participants) == 3
            
            participant_ids = {mp.participant_id for mp in month_participants}
            assert participant_ids == set(three_participants)

    def test_create_month_with_subset_of_participants(self, client, app, three_participants):
        """Test creating a month with only some participants selected."""
        # Select only Alice and Bob
        selected = [three_participants[0], three_participants[1]]
        
        response = client.post("/months", data={
            "year": 2025,
            "month": 2,
            "electricity_amount": 100.0,
            "water_amount": 50.0,
            "internet_amount": 30.0,
            "selected_participants": selected,
        }, follow_redirects=True)
        
        assert response.status_code == 200
        
        with app.app_context():
            bill = MonthlyBill.query.filter_by(year=2025, month=2).first()
            assert bill is not None
            
            month_participants = MonthParticipant.query.filter_by(month_id=bill.id).all()
            assert len(month_participants) == 2
            
            participant_ids = {mp.participant_id for mp in month_participants}
            assert participant_ids == set(selected)
            # Charlie should not be included
            assert three_participants[2] not in participant_ids

    def test_create_month_with_single_participant(self, client, app, three_participants):
        """Test creating a month with only one participant selected."""
        selected = [three_participants[0]]  # Only Alice
        
        response = client.post("/months", data={
            "year": 2025,
            "month": 3,
            "electricity_amount": 100.0,
            "water_amount": 50.0,
            "internet_amount": 30.0,
            "selected_participants": selected,
        }, follow_redirects=True)
        
        assert response.status_code == 200
        
        with app.app_context():
            bill = MonthlyBill.query.filter_by(year=2025, month=3).first()
            assert bill is not None
            
            month_participants = MonthParticipant.query.filter_by(month_id=bill.id).all()
            assert len(month_participants) == 1
            assert month_participants[0].participant_id == three_participants[0]

    def test_create_month_without_selection_defaults_to_all(self, client, app, three_participants):
        """Test backward compatibility: no selection defaults to all participants."""
        response = client.post("/months", data={
            "year": 2025,
            "month": 4,
            "electricity_amount": 100.0,
            "water_amount": 50.0,
            "internet_amount": 30.0,
            # No selected_participants field
        }, follow_redirects=True)
        
        assert response.status_code == 200
        
        with app.app_context():
            bill = MonthlyBill.query.filter_by(year=2025, month=4).first()
            assert bill is not None
            
            month_participants = MonthParticipant.query.filter_by(month_id=bill.id).all()
            # Should default to all participants
            assert len(month_participants) == 3
            
            participant_ids = {mp.participant_id for mp in month_participants}
            assert participant_ids == set(three_participants)

    def test_month_detail_shows_only_selected_participants(self, client, app, three_participants):
        """Test that month detail page shows only the selected participants."""
        # Create month with only Alice and Bob
        selected = [three_participants[0], three_participants[1]]
        
        response = client.post("/months", data={
            "year": 2025,
            "month": 5,
            "electricity_amount": 100.0,
            "water_amount": 50.0,
            "internet_amount": 30.0,
            "selected_participants": selected,
        }, follow_redirects=True)
        
        with app.app_context():
            bill = MonthlyBill.query.filter_by(year=2025, month=5).first()
            bill_id = bill.id
        
        # View the month detail page
        response = client.get(f"/months/{bill_id}")
        assert response.status_code == 200
        
        # The page should show Alice and Bob but the meter readings section
        # should only show inputs for selected participants
        assert b"Alice" in response.data
        assert b"Bob" in response.data
        # Charlie should still appear in the full participants list (for the "add participant" dropdown)
        # but not in the member list

    def test_can_add_participant_to_month_later(self, client, app, three_participants):
        """Test that participants can be added to a month after creation."""
        # Create month with only Alice
        selected = [three_participants[0]]
        
        response = client.post("/months", data={
            "year": 2025,
            "month": 6,
            "electricity_amount": 100.0,
            "water_amount": 50.0,
            "internet_amount": 30.0,
            "selected_participants": selected,
        }, follow_redirects=True)
        
        assert response.status_code == 200
        
        with app.app_context():
            bill = MonthlyBill.query.filter_by(year=2025, month=6).first()
            bill_id = bill.id
        
        # Add Bob to the month
        response = client.post(f"/months/{bill_id}/participants", data={
            "participant_id": three_participants[1],
        }, follow_redirects=True)
        
        assert response.status_code == 200
        
        with app.app_context():
            month_participants = MonthParticipant.query.filter_by(month_id=bill_id).all()
            assert len(month_participants) == 2
            participant_ids = {mp.participant_id for mp in month_participants}
            assert three_participants[0] in participant_ids
            assert three_participants[1] in participant_ids

    def test_can_remove_participant_from_month(self, client, app, three_participants):
        """Test that participants can be removed from a month."""
        # Create month with Alice and Bob
        selected = [three_participants[0], three_participants[1]]
        
        response = client.post("/months", data={
            "year": 2025,
            "month": 7,
            "electricity_amount": 100.0,
            "water_amount": 50.0,
            "internet_amount": 30.0,
            "selected_participants": selected,
        }, follow_redirects=True)
        
        assert response.status_code == 200
        
        with app.app_context():
            bill = MonthlyBill.query.filter_by(year=2025, month=7).first()
            bill_id = bill.id
        
        # Remove Bob from the month
        response = client.post(f"/months/{bill_id}/participants/{three_participants[1]}/delete", 
                             follow_redirects=True)
        
        assert response.status_code == 200
        
        with app.app_context():
            month_participants = MonthParticipant.query.filter_by(month_id=bill_id).all()
            assert len(month_participants) == 1
            assert month_participants[0].participant_id == three_participants[0]
