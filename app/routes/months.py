"""Months routes - single responsibility: month/bill CRUD operations."""
from __future__ import annotations

from datetime import date
from typing import Dict

from flask import Blueprint, render_template, request, redirect, url_for, flash, Response
from sqlalchemy.exc import IntegrityError

from ..extensions import db
from ..repositories import (
    ParticipantRepository,
    MonthlyBillRepository,
    MeterReadingRepository,
    BillComponentRepository,
    MonthParticipantRepository,
)
from ..forms import MonthForm
from ..services.bill_calculator import VALID_SPLIT_METHODS, DISTRIBUTION_SPLIT_METHODS
from ..services.month_service import MonthService

bp = Blueprint("months", __name__, url_prefix="/months")


def _get_month_service() -> MonthService:
    """Factory function for dependency injection."""
    return MonthService()


def _get_bill_repo() -> MonthlyBillRepository:
    """Factory function for dependency injection."""
    return MonthlyBillRepository()


def _get_participants_repo() -> ParticipantRepository:
    """Factory function for dependency injection."""
    return ParticipantRepository()


def _get_component_repo() -> BillComponentRepository:
    """Factory function for dependency injection."""
    return BillComponentRepository()


def _get_reading_repo() -> MeterReadingRepository:
    """Factory function for dependency injection."""
    return MeterReadingRepository()


def _get_month_part_repo() -> MonthParticipantRepository:
    """Factory function for dependency injection."""
    return MonthParticipantRepository()


@bp.get("/")
def index():
    """GET /months - Redirect to admin which lists months."""
    return redirect(url_for("admin.admin"))


@bp.get("/new")
def new():
    """GET /months/new - Form to create a new month."""
    participants_repo = _get_participants_repo()
    participants = participants_repo.list_all()
    form = MonthForm()
    if not form.year.data or not form.month.data:
        today = date.today()
        form.year.data = today.year
        form.month.data = today.month
    return render_template("new_month.html", form=form, participants=participants)


def _parse_component_distribution(index: int, participants, form_data) -> Dict[int, float]:
    """Parse distribution values from form data for a component."""
    dist: Dict[int, float] = {}
    for p in participants:
        raw = form_data.get(f"comp_dist_{index}_{p.id}")
        if raw is None or raw == "":
            continue
        try:
            val = float(raw)
        except ValueError:
            continue
        dist[p.id] = val
    return dist


def _parse_legacy_distribution(prefix: str, participants, form_data) -> Dict[int, float]:
    """Parse distribution values from form data for legacy fields."""
    dist: Dict[int, float] = {}
    for p in participants:
        raw = form_data.get(f"legacy_{prefix}_dist_{p.id}")
        if raw is None or raw == "":
            continue
        try:
            val = float(raw)
        except ValueError:
            continue
        dist[p.id] = val
    return dist


@bp.post("/")
def create():
    """POST /months - Create a new month."""
    participants_repo = _get_participants_repo()
    bill_repo = _get_bill_repo()
    month_part_repo = _get_month_part_repo()
    component_repo = _get_component_repo()

    form = MonthForm()
    form.check_duplicates = True
    if not form.validate_on_submit():
        flash("Please correct the errors in the form", "error")
        return redirect(url_for("home.index"))

    year = int(form.year.data)
    month = int(form.month.data)
    participants = participants_repo.list_all()

    try:
        bill = bill_repo.create(
            year, month,
            float(form.electricity_amount.data),
            float(form.water_amount.data),
            float(form.internet_amount.data)
        )
    except IntegrityError:
        db.session.rollback()
        flash(f"A month for {year}-{month:02d} already exists.", "error")
        return redirect(url_for("home.index"))

    # Get selected participants from form
    selected_participant_ids = request.form.getlist('selected_participants')
    if selected_participant_ids:
        # Convert to integers
        selected_participant_ids = [int(pid) for pid in selected_participant_ids if pid]

    # Default: if no selection was made, include all participants (backward compatibility)
    if not selected_participant_ids:
        selected_participant_ids = [p.id for p in participants]

    # Add only selected participants to the month
    try:
        for pid in selected_participant_ids:
            month_part_repo.add(bill.id, pid)
    except Exception:
        pass

    # Create dynamic components from form
    names = request.form.getlist('comp_name[]')
    amounts = request.form.getlist('comp_amount[]')
    splits = request.form.getlist('comp_split[]')
    positions = request.form.getlist('comp_position[]')

    for i, name in enumerate(names or []):
        n = (name or '').strip()
        if not n:
            continue
        try:
            amt = float((amounts[i] if i < len(amounts) else '0') or '0')
        except (ValueError, TypeError):
            amt = 0.0
        sp = (splits[i] if i < len(splits) else 'equal') or 'equal'
        if sp not in VALID_SPLIT_METHODS:
            sp = 'equal'
        try:
            pos = int((positions[i] if i < len(positions) else i) or i)
        except (ValueError, TypeError):
            pos = i
        distribution = None
        if sp in DISTRIBUTION_SPLIT_METHODS:
            distribution = _parse_component_distribution(i, participants, request.form)
        try:
            component_repo.add(
                bill.id, name=n, amount=amt, split_method=sp,
                position=pos, distribution=distribution
            )
        except IntegrityError:
            db.session.rollback()
            flash(f"Skipped duplicate component name '{n}' for this month.", "error")
            continue

    # Create default components for legacy fields
    try:
        legacy_elec_split = (request.form.get('legacy_electricity_split') or 'usage').strip()
        legacy_water_split = (request.form.get('legacy_water_split') or 'equal').strip()
        legacy_inet_split = (request.form.get('legacy_internet_split') or 'equal').strip()

        elec_dist = None
        water_dist = None
        inet_dist = None
        if legacy_elec_split in DISTRIBUTION_SPLIT_METHODS:
            elec_dist = _parse_legacy_distribution("electricity", participants, request.form)
        if legacy_water_split in DISTRIBUTION_SPLIT_METHODS:
            water_dist = _parse_legacy_distribution("water", participants, request.form)
        if legacy_inet_split in DISTRIBUTION_SPLIT_METHODS:
            inet_dist = _parse_legacy_distribution("internet", participants, request.form)

        legacy_defs = [
            ("Electricity", float(form.electricity_amount.data or 0),
             legacy_elec_split, 0, elec_dist),
            ("Water", float(form.water_amount.data or 0),
             legacy_water_split, 1, water_dist),
            ("Internet", float(form.internet_amount.data or 0),
             legacy_inet_split, 2, inet_dist),
        ]
        for (nm, amt, sp, pos, dist) in legacy_defs:
            if amt and amt > 0:
                try:
                    split = sp if sp in ("usage", "equal", "percentage", "amount") else "equal"
                    component_repo.add(
                        bill.id,
                        name=nm,
                        amount=amt,
                        split_method=split,
                        position=pos,
                        distribution=(dist or None),
                    )
                except IntegrityError:
                    db.session.rollback()
    except Exception:
        pass

    flash("Month created", "info")
    return redirect(url_for("home.index"))


@bp.get("/<int:bill_id>")
def show(bill_id: int):
    """GET /months/<id> - Show month details."""
    month_service = _get_month_service()
    data = month_service.get_month_detail_data(bill_id)

    if not data:
        flash("Month not found", "error")
        return redirect(url_for("home.index"))

    return render_template("month_detail.html", **data)


@bp.get("/<int:bill_id>/edit")
def edit(bill_id: int):
    """GET /months/<id>/edit - Form to edit a month."""
    bill_repo = _get_bill_repo()
    bill = bill_repo.get_by_id(bill_id)
    if not bill:
        flash("Month not found", "error")
        return redirect(url_for("home.index"))
    if bill.archived:
        flash("This month is archived. Unarchive to edit amounts.", "error")
        return redirect(url_for("months.show", bill_id=bill_id))
    form = MonthForm()
    form.year.data = bill.year
    form.month.data = bill.month
    form.electricity_amount.data = bill.electricity_amount
    form.water_amount.data = bill.water_amount
    form.internet_amount.data = bill.internet_amount
    return render_template("edit_month.html", bill=bill, form=form)


@bp.post("/<int:bill_id>")
def update(bill_id: int):
    """POST /months/<id> - Update a month (PUT emulation via POST)."""
    bill_repo = _get_bill_repo()
    component_repo = _get_component_repo()
    bill = bill_repo.get_by_id(bill_id)
    if not bill:
        flash("Month not found", "error")
        return redirect(url_for("home.index"))
    if bill.archived:
        flash("This month is archived. Unarchive to make changes.", "error")
        return redirect(url_for("months.show", bill_id=bill_id))
    form = MonthForm()
    if not form.validate_on_submit():
        flash("Please correct the errors in the form", "error")
        return redirect(url_for("months.edit", bill_id=bill_id))

    electricity_amount = float(form.electricity_amount.data)
    water_amount = float(form.water_amount.data)
    internet_amount = float(form.internet_amount.data)

    # Update the MonthlyBill amounts
    bill_repo.update_amounts(
        bill_id,
        electricity_amount,
        water_amount,
        internet_amount
    )

    # Also update corresponding BillComponent records if they exist
    # This ensures the computation reflects the updated amounts
    components = component_repo.list_for_month(bill_id)
    legacy_updates = {
        "Electricity": electricity_amount,
        "Water": water_amount,
        "Internet": internet_amount,
    }
    for comp in components:
        if comp.name in legacy_updates:
            component_repo.update(comp.id, amount=legacy_updates[comp.name])

    flash("Month updated", "info")
    return redirect(url_for("months.show", bill_id=bill_id))


@bp.post("/<int:bill_id>/delete")
def delete(bill_id: int):
    """POST /months/<id>/delete - Delete a month (DELETE emulation via POST)."""
    bill_repo = _get_bill_repo()
    bill_repo.delete(bill_id)
    flash("Month deleted", "info")
    return redirect(url_for("home.index"))


@bp.post("/<int:bill_id>/archive")
def archive(bill_id: int):
    """POST /months/<id>/archive - Archive a month."""
    bill_repo = _get_bill_repo()
    bill_repo.set_archived(bill_id, True)
    flash("Month archived", "info")
    return redirect(url_for("home.index"))


@bp.post("/<int:bill_id>/unarchive")
def unarchive(bill_id: int):
    """POST /months/<id>/unarchive - Unarchive a month."""
    bill_repo = _get_bill_repo()
    bill_repo.set_archived(bill_id, False)
    flash("Month unarchived", "info")
    return redirect(url_for("months.show", bill_id=bill_id))


@bp.get("/archived")
def archived():
    """GET /months/archived - List archived months."""
    bill_repo = _get_bill_repo()
    page = int(request.args.get("page", 1) or 1)
    per_page = 10
    pagination = bill_repo.list_paginated(page=page, per_page=per_page, archived=True)
    return render_template("archived.html", pagination=pagination, months=pagination.items)


@bp.get("/<int:bill_id>/export.pdf")
def export_pdf(bill_id: int):
    """GET /months/<id>/export.pdf - Printable month summary PDF."""
    from ..services.pdf_service import MONTH_NAMES, build_month_pdf

    month_service = _get_month_service()
    data = month_service.get_month_detail_data(bill_id)
    if not data:
        flash("Month not found", "error")
        return redirect(url_for("home.index"))

    bill = data["bill"]
    pdf = build_month_pdf(data)
    filename = f"bill_{bill.year}-{MONTH_NAMES[bill.month - 1]}.pdf"
    return Response(
        pdf,
        mimetype="application/pdf",
        headers={
            "Content-Disposition": f"attachment; filename={filename}",
            # .pdf is on Cloudflare's default cache-by-extension list; without
            # this, edges serve stale exports after the data (or app) changes.
            "Cache-Control": "no-store",
        },
    )


# =============================================================================
# MONTH READINGS
# =============================================================================

@bp.post("/<int:bill_id>/readings")
def readings_update(bill_id: int):
    """POST /months/<id>/readings - Update meter readings for a month."""
    bill_repo = _get_bill_repo()
    reading_repo = _get_reading_repo()

    bill = bill_repo.get_by_id(bill_id)
    if not bill:
        flash("Month not found", "error")
        return redirect(url_for("home.index"))
    if bill.archived:
        flash("This month is archived. Unarchive to make changes.", "error")
        return redirect(url_for("months.show", bill_id=bill.id))

    for key, value in request.form.items():
        if key.startswith("current_"):
            pid = int(key.split("_", 1)[1])
            current_val = float(value or 0)
            prev_val_raw = request.form.get(f"previous_{pid}")
            prev_val = float(prev_val_raw) if prev_val_raw not in (None, "") else None
            reading_repo.upsert(bill.id, pid, current_val, prev_val)

    return redirect(url_for("months.show", bill_id=bill.id, saved=1))


# =============================================================================
# MONTH PARTICIPANTS (MEMBERSHIP)
# =============================================================================

@bp.post("/<int:bill_id>/participants")
def participants_create(bill_id: int):
    """POST /months/<id>/participants - Add a participant to a month."""
    bill_repo = _get_bill_repo()
    month_part_repo = _get_month_part_repo()

    bill = bill_repo.get_by_id(bill_id)
    if not bill:
        flash("Month not found", "error")
        return redirect(url_for("home.index"))
    if bill.archived:
        flash("This month is archived. Unarchive to make changes.", "error")
        return redirect(url_for("months.show", bill_id=bill.id))
    try:
        pid = int(request.form.get("participant_id") or 0)
    except ValueError:
        pid = 0
    if not pid:
        flash("Select a participant", "error")
        return redirect(url_for("months.show", bill_id=bill.id))
    month_part_repo.add(bill.id, pid)
    flash("Participant linked to month", "info")
    return redirect(url_for("months.show", bill_id=bill.id))


@bp.post("/<int:bill_id>/participants/<int:pid>/delete")
def participants_delete(bill_id: int, pid: int):
    """POST /months/<id>/participants/<pid>/delete - Remove participant from month."""
    bill_repo = _get_bill_repo()
    month_part_repo = _get_month_part_repo()

    bill = bill_repo.get_by_id(bill_id)
    if not bill:
        flash("Month not found", "error")
        return redirect(url_for("home.index"))
    if bill.archived:
        flash("This month is archived. Unarchive to make changes.", "error")
        return redirect(url_for("months.show", bill_id=bill.id))
    month_part_repo.remove(bill.id, pid)
    flash("Participant unlinked from month", "info")
    return redirect(url_for("months.show", bill_id=bill.id))
