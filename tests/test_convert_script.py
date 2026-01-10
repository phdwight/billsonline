from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app import create_app
from app.extensions import db
from app.models import MonthlyBill, BillComponent
from scripts.convert_legacy_to_components import convert_month
from app.repositories import BillComponentRepository


def test_convert_month_idempotent(tmp_path, monkeypatch):
    app = create_app()
    with app.app_context():
        db.drop_all()
        db.create_all()
        # Create a month with legacy amounts but no components
        bill = MonthlyBill(year=2025, month=10, electricity_amount=100.0, water_amount=90.0, internet_amount=80.0)
        db.session.add(bill)
        db.session.commit()
        repo = BillComponentRepository()
        created, skipped = convert_month(bill, repo)
        assert created == 3
        assert skipped == 0
        comps = BillComponent.query.filter_by(month_id=bill.id).order_by(BillComponent.position.asc()).all()
        assert [c.name for c in comps] == ['Electricity', 'Water', 'Internet']
        assert [c.split_method for c in comps] == ['usage', 'equal', 'equal']
        # Run again: should skip
        created2, skipped2 = convert_month(bill, repo)
        assert created2 == 0
        assert skipped2 == 1
