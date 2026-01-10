"""Home routes - single responsibility: handle home/index pages."""
from __future__ import annotations

from flask import Blueprint, redirect, url_for

from ..repositories import MonthlyBillRepository

bp = Blueprint("home", __name__)


def _get_bill_repo() -> MonthlyBillRepository:
    """Factory function for dependency injection."""
    return MonthlyBillRepository()


@bp.get("/")
def index():
    """Home page showing the latest month's details."""
    bill_repo = _get_bill_repo()
    latest_bill = bill_repo.get_latest(archived=False)
    if not latest_bill:
        return redirect(url_for("admin.admin"))
    return redirect(url_for("months.show", bill_id=latest_bill.id))
