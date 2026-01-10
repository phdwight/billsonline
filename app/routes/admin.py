"""Admin routes - single responsibility: admin page and management."""
from __future__ import annotations

from datetime import date

from flask import Blueprint, render_template, request

from ..repositories import MonthlyBillRepository, ParticipantRepository
from ..forms import MonthForm

bp = Blueprint("admin", __name__)


def _get_bill_repo() -> MonthlyBillRepository:
    """Factory function for dependency injection."""
    return MonthlyBillRepository()


def _get_participants_repo() -> ParticipantRepository:
    """Factory function for dependency injection."""
    return ParticipantRepository()


@bp.get("/admin")
def admin():
    """Admin page with all management features."""
    bill_repo = _get_bill_repo()
    participants_repo = _get_participants_repo()

    page = int(request.args.get("page", 1) or 1)
    per_page = 10
    pagination = bill_repo.list_paginated(page=page, per_page=per_page, archived=False)
    participants = participants_repo.list_all()
    form = MonthForm()
    if not form.year.data or not form.month.data:
        today = date.today()
        form.year.data = today.year
        form.month.data = today.month
    return render_template(
        "admin.html",
        pagination=pagination,
        months=pagination.items,
        participants=participants,
        form=form
    )
