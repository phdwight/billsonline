"""Components routes - single responsibility: component CRUD operations."""
from __future__ import annotations

from flask import Blueprint, request, redirect, url_for, flash
from sqlalchemy.exc import IntegrityError

from ..extensions import db
from ..repositories import (
    MonthlyBillRepository,
    BillComponentRepository,
)
from ..services.bill_calculator import VALID_SPLIT_METHODS
from ..services.month_service import MonthService

bp = Blueprint("components", __name__, url_prefix="/months/<int:bill_id>/components")


def _get_bill_repo() -> MonthlyBillRepository:
    """Factory function for dependency injection."""
    return MonthlyBillRepository()


def _get_component_repo() -> BillComponentRepository:
    """Factory function for dependency injection."""
    return BillComponentRepository()


def _get_month_service() -> MonthService:
    """Factory function for dependency injection."""
    return MonthService()


@bp.post("/")
def create(bill_id: int):
    """POST /months/<id>/components - Create a new component for a month."""
    bill_repo = _get_bill_repo()
    component_repo = _get_component_repo()

    bill = bill_repo.get_by_id(bill_id)
    if not bill:
        flash("Month not found", "error")
        return redirect(url_for("home.index"))
    if bill.archived:
        flash("This month is archived. Unarchive to make changes.", "error")
        return redirect(url_for("months.show", bill_id=bill.id))

    name = (request.form.get("component_name") or "").strip()
    split = request.form.get("component_split_method") or "equal"
    try:
        amount = float(request.form.get("component_amount") or 0)
    except ValueError:
        amount = -1
    try:
        position = int(request.form.get("component_position") or 0)
    except ValueError:
        position = 0

    if not name:
        flash("Component name is required", "error")
        return redirect(url_for("months.show", bill_id=bill.id))
    if split not in VALID_SPLIT_METHODS:
        flash(f"Split method must be one of {', '.join(VALID_SPLIT_METHODS)}", "error")
        return redirect(url_for("months.show", bill_id=bill.id))
    if amount < 0:
        flash("Amount must be a non-negative number", "error")
        return redirect(url_for("months.show", bill_id=bill.id))

    try:
        component_repo.add(bill.id, name=name, amount=amount, split_method=split, position=position)
    except IntegrityError:
        db.session.rollback()
        flash("A component with that name already exists for this month.", "error")
    else:
        flash("Component added", "info")
    return redirect(url_for("months.show", bill_id=bill.id))


@bp.post("/<int:component_id>")
def update(bill_id: int, component_id: int):
    """POST /months/<id>/components/<cid> - Update a component (PUT emulation)."""
    bill_repo = _get_bill_repo()
    component_repo = _get_component_repo()

    bill = bill_repo.get_by_id(bill_id)
    if not bill:
        flash("Month not found", "error")
        return redirect(url_for("home.index"))
    if bill.archived:
        flash("This month is archived. Unarchive to make changes.", "error")
        return redirect(url_for("months.show", bill_id=bill.id))

    name = (request.form.get("name") or "").strip()
    split = request.form.get("split_method") or None
    amount = request.form.get("amount")
    position = request.form.get("position")
    amt_f = None
    pos_i = None

    if amount is not None and amount != "":
        try:
            amt_f = float(amount)
        except ValueError:
            flash("Amount must be a number", "error")
            return redirect(url_for("months.show", bill_id=bill.id))
        if amt_f < 0:
            flash("Amount must be non-negative", "error")
            return redirect(url_for("months.show", bill_id=bill.id))

    if position is not None and position != "":
        try:
            pos_i = int(position)
        except ValueError:
            flash("Position must be an integer", "error")
            return redirect(url_for("months.show", bill_id=bill.id))

    if split and split not in VALID_SPLIT_METHODS:
        flash(f"Split method must be one of {', '.join(VALID_SPLIT_METHODS)}", "error")
        return redirect(url_for("months.show", bill_id=bill.id))

    # Optional per-participant shares for 'percentage'/'amount' splits (dist_<pid> fields)
    distribution = {}
    for key, value in request.form.items():
        if not key.startswith("dist_") or value == "":
            continue
        try:
            pid = int(key.split("_", 1)[1])
            distribution[str(pid)] = float(value)
        except ValueError:
            continue

    try:
        component_repo.update(
            component_id,
            name=name or None,
            amount=amt_f,
            split_method=split,
            position=pos_i,
            distribution=(distribution or None),
        )
    except IntegrityError:
        db.session.rollback()
        flash("Component name already exists for this month.", "error")
    else:
        flash("Component updated", "info")
    return redirect(url_for("months.show", bill_id=bill.id))


@bp.post("/<int:component_id>/delete")
def delete(bill_id: int, component_id: int):
    """POST /months/<id>/components/<cid>/delete - Delete a component (DELETE emulation)."""
    bill_repo = _get_bill_repo()
    component_repo = _get_component_repo()

    bill = bill_repo.get_by_id(bill_id)
    if not bill:
        flash("Month not found", "error")
        return redirect(url_for("home.index"))
    if bill.archived:
        flash("This month is archived. Unarchive to make changes.", "error")
        return redirect(url_for("months.show", bill_id=bill.id))
    component_repo.delete(component_id)
    flash("Component deleted", "info")
    return redirect(url_for("months.show", bill_id=bill.id))


@bp.post("/convert-legacy")
def convert_legacy(bill_id: int):
    """POST /months/<id>/components/convert-legacy - Convert legacy amounts to components."""
    month_service = _get_month_service()
    success, message = month_service.convert_legacy_to_components(bill_id)

    if success:
        flash(message, "info")
    else:
        flash(message, "error")

    return redirect(url_for("months.show", bill_id=bill_id))
