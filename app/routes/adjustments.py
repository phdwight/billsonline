"""Adjustments routes - single responsibility: component adjustment operations."""
from __future__ import annotations

from flask import Blueprint, request, redirect, url_for, flash, current_app

from ..repositories import MonthlyBillRepository
from ..services.adjustment_service import AdjustmentService

bp = Blueprint("adjustments", __name__, url_prefix="/months/<int:bill_id>/adjustments")


def _get_bill_repo() -> MonthlyBillRepository:
    """Factory function for dependency injection."""
    return MonthlyBillRepository()


def _get_adjustment_service() -> AdjustmentService:
    """Factory function for dependency injection."""
    return AdjustmentService()


@bp.post("/")
def update(bill_id: int):
    """POST /months/<id>/adjustments - Update component adjustments for a month."""
    adjustment_service = _get_adjustment_service()

    # Log the request
    current_app.logger.info("[adjustments] start: bill=%s", bill_id)

    # Process adjustments using the service
    success, message, saved_rules = adjustment_service.process_adjustments(
        bill_id=bill_id,
        form_data=request.form,
    )

    current_app.logger.info("[adjustments] saved_rules=%s", saved_rules)

    if success:
        flash(message, "info")
    else:
        flash(message, "error")

    return redirect(url_for("months.show", bill_id=bill_id))
