"""Home routes - single responsibility: handle home/index pages."""
from __future__ import annotations

from flask import Blueprint, render_template, request

from ..repositories import (
    BillComponentRepository,
    MonthlyBillRepository,
    MonthParticipantRepository,
)

bp = Blueprint("home", __name__)

MONTH_NAMES = [
    "January", "February", "March", "April", "May", "June",
    "July", "August", "September", "October", "November", "December",
]

PER_PAGE = 12


def _get_bill_repo() -> MonthlyBillRepository:
    """Factory function for dependency injection."""
    return MonthlyBillRepository()


def _get_component_repo() -> BillComponentRepository:
    """Factory function for dependency injection."""
    return BillComponentRepository()


def _get_month_part_repo() -> MonthParticipantRepository:
    """Factory function for dependency injection."""
    return MonthParticipantRepository()


def _grand_total(bill, components) -> float:
    """Grand total for a month: sum of components, else legacy amounts."""
    if components:
        return sum(float(c.amount or 0) for c in components)
    return (
        float(bill.electricity_amount or 0)
        + float(bill.water_amount or 0)
        + float(bill.internet_amount or 0)
    )


@bp.get("/")
def index():
    """Home page: billing periods as a card grid (Industry redesign)."""
    bill_repo = _get_bill_repo()
    component_repo = _get_component_repo()
    month_part_repo = _get_month_part_repo()

    bills = bill_repo.list_all_including_archived()

    try:
        page = max(1, int(request.args.get("page", 1) or 1))
    except ValueError:
        page = 1
    total_pages = max(1, (len(bills) + PER_PAGE - 1) // PER_PAGE)
    page = min(page, total_pages)
    page_bills = bills[(page - 1) * PER_PAGE: page * PER_PAGE]

    cards = []
    for bill in page_bills:
        components = component_repo.list_for_month(bill.id)
        members = month_part_repo.list_for_month(bill.id)
        cards.append({
            "bill": bill,
            "label": f"{MONTH_NAMES[bill.month - 1]} {bill.year}",
            "total": _grand_total(bill, components),
            "participant_count": len(members),
            "component_count": len(components),
        })

    return render_template(
        "index.html",
        cards=cards,
        page=page,
        total_pages=total_pages,
    )
