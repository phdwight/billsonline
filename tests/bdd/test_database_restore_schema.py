"""Restoring an old backup must upgrade its schema to the current one.

Regression test for the production incident where restoring a backup that
predated the component_images table made every month page 500 with
"no such table: component_images" until the app was restarted.
"""
import io
import os
import sqlite3
import tempfile

import pytest

from app import create_app
from app.config import Config
from app.extensions import db
from app.models import BillComponent, MonthParticipant, MonthlyBill, Participant


@pytest.fixture
def restore_app():
    fd, db_path = tempfile.mkstemp(suffix=".db")
    os.close(fd)
    # The engine binds to the URI at create_app time (config updates after
    # that don't rebind it), so the temp file must go in via the config object.
    cfg = Config()
    cfg.SQLALCHEMY_DATABASE_URI = f"sqlite:///{db_path}"
    app = create_app(cfg)
    app.config.update({
        "TESTING": True,
        "WTF_CSRF_ENABLED": False,
    })
    with app.app_context():
        db.create_all()
        yield app, db_path
        db.session.remove()
        db.engine.dispose()
    for f in [db_path] + [db_path + s for s in ("-wal", "-shm")]:
        if os.path.exists(f):
            os.unlink(f)


def _seed(bill_year=2026, bill_month=6):
    p = Participant(name="Alice")
    db.session.add(p)
    db.session.flush()
    bill = MonthlyBill(year=bill_year, month=bill_month, electricity_amount=0,
                       water_amount=0, internet_amount=0)
    db.session.add(bill)
    db.session.flush()
    db.session.add(MonthParticipant(month_id=bill.id, participant_id=p.id))
    db.session.add(BillComponent(month_id=bill.id, name="Water", amount=500.0, split_method="equal"))
    db.session.commit()
    return bill.id


def test_restoring_old_backup_upgrades_schema(restore_app):
    app, db_path = restore_app
    with app.app_context():
        bill_id = _seed()
        client = app.test_client()

        # Build a "backup from before the component_images table existed":
        # copy the live db and drop the new table from the copy.
        fd, backup_path = tempfile.mkstemp(suffix=".db")
        os.close(fd)
        src = sqlite3.connect(db_path)
        dst = sqlite3.connect(backup_path)
        src.backup(dst)
        src.close()
        dst.execute("DROP TABLE IF EXISTS component_images")
        dst.commit()
        dst.close()

        with open(backup_path, "rb") as f:
            payload = f.read()
        os.unlink(backup_path)

        resp = client.post(
            "/settings/database",
            data={"database": (io.BytesIO(payload), "backup.db")},
            content_type="multipart/form-data",
            follow_redirects=True,
        )
        assert resp.status_code == 200

        # The month page must work immediately — no restart required.
        month_page = client.get(f"/months/{bill_id}")
        assert month_page.status_code == 200
        assert b"Water" in month_page.data
        assert b"schema updated" in resp.data
