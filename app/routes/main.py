from __future__ import annotations

from flask import Blueprint, render_template, request, redirect, url_for, flash, Response, send_file, current_app
from sqlalchemy.exc import IntegrityError
from datetime import date
import csv
from io import StringIO
# from openpyxl import Workbook  # no longer used
from urllib.parse import urlparse, unquote

from ..extensions import db
from ..models import Participant
from ..repositories import ParticipantRepository, MonthlyBillRepository, MeterReadingRepository, MonthlyAdjustmentRepository
from ..services import BillCalculator
from ..forms import MonthForm

bp = Blueprint("main", __name__)

participants_repo = ParticipantRepository()
bill_repo = MonthlyBillRepository()
reading_repo = MeterReadingRepository()
adjust_repo = MonthlyAdjustmentRepository()
calculator = BillCalculator()


@bp.get("/")
def index():
    page = int(request.args.get("page", 1) or 1)
    per_page = 10
    pagination = bill_repo.list_paginated(page=page, per_page=per_page, archived=False)
    participants = participants_repo.list_all()
    form = MonthForm()
    if not form.year.data or not form.month.data:
        today = date.today()
        form.year.data = today.year
        form.month.data = today.month
    return render_template("index.html", pagination=pagination, months=pagination.items, participants=participants, form=form)


@bp.get("/participants")
def participants_page():
    participants = participants_repo.list_all()
    return render_template("participants.html", participants=participants)


@bp.post("/participants/<int:pid>/update")
def update_participant(pid: int):
    name = request.form.get("name", "").strip()
    if not name:
        flash("Participant name is required", "error")
        return redirect(url_for("main.participants_page"))
    # naive duplicate name check
    existing = [p for p in participants_repo.list_all() if p.name.lower() == name.lower() and p.id != pid]
    if existing:
        flash("Another participant already has that name", "error")
        return redirect(url_for("main.participants_page"))
    participants_repo.update(pid, name)
    flash("Participant updated", "info")
    return redirect(url_for("main.participants_page"))


@bp.post("/participants")
def add_participant():
    name = request.form.get("name", "").strip()
    if not name:
        flash("Name is required", "error")
    else:
        participants_repo.add(name=name)
    return redirect(url_for("main.index"))


# Removed internet toggle; use adjustments instead


@bp.post("/months")
def add_month():
    form = MonthForm()
    # Enable duplicate check inside the form
    form.check_duplicates = True
    if not form.validate_on_submit():
        flash("Please correct the errors in the form", "error")
        return redirect(url_for("main.index"))
    year = int(form.year.data)
    month = int(form.month.data)
    try:
        bill_repo.create(year, month, float(form.electricity_amount.data), float(form.water_amount.data), float(form.internet_amount.data))
    except IntegrityError:
        db.session.rollback()
        flash(f"A month for {year}-{month:02d} already exists.", "error")
        return redirect(url_for("main.index"))
    flash("Month created", "info")
    return redirect(url_for("main.index"))


@bp.get("/months/<int:bill_id>")
def month_detail(bill_id: int):
    bill = bill_repo.get_by_id(bill_id)
    if not bill:
        flash("Month not found", "error")
        return redirect(url_for("main.index"))
    participants = participants_repo.list_all()
    readings = reading_repo.list_for_month(bill.id)
    readings_by_pid = {r.participant_id: r for r in readings}
    # Pre-fill previous readings from previous month if not provided
    prev_bill = bill_repo.get_previous(bill.year, bill.month)
    prev_readings_map = {}
    if prev_bill:
        prev_readings = reading_repo.list_for_month(prev_bill.id)
        prev_readings_map = {r.participant_id: r.reading_current for r in prev_readings}
    adjustments = {a.participant_id: {
        'electricity': a.zero_electricity,
        'water': a.zero_water,
        'internet': a.zero_internet,
        'redis_electricity': a.redis_electricity,
        'redis_water': a.redis_water,
        'redis_internet': a.redis_internet,
    } for a in adjust_repo.list_for_month(bill.id)}
    contributions = calculator.compute_contributions(bill, readings, participants, adjustments)
    # Compute base amounts per component for client-side indicators
    usage_by_pid = {r.participant_id: r.usage() for r in readings}
    total_usage = sum(usage_by_pid.values())
    base_electricity_map = {p.id: ((bill.electricity_amount * (usage_by_pid.get(p.id, 0.0) / total_usage)) if total_usage > 0 else 0.0) for p in participants}
    base_water_share = (bill.water_amount / len(participants)) if participants else 0.0
    base_internet_share = (bill.internet_amount / len(participants)) if participants else 0.0
    total_bill = round(bill.electricity_amount + bill.water_amount + bill.internet_amount, 2)
    return render_template(
        "month_detail.html",
        bill=bill,
        participants=participants,
        readings=readings,
        readings_by_pid=readings_by_pid,
        prev_readings_map=prev_readings_map,
        contributions=contributions,
        adjustments=adjustments,
        participant_name_by_id={p.id: p.name for p in participants},
        base_electricity_map=base_electricity_map,
        base_water_share=base_water_share,
        base_internet_share=base_internet_share,
        total_bill=total_bill,
    )


@bp.get("/months/<int:bill_id>/edit")
def edit_month(bill_id: int):
    bill = bill_repo.get_by_id(bill_id)
    if not bill:
        flash("Month not found", "error")
        return redirect(url_for("main.index"))
    if bill.archived:
        flash("This month is archived. Unarchive to edit amounts.", "error")
        return redirect(url_for("main.month_detail", bill_id=bill_id))
    form = MonthForm()
    form.year.data = bill.year
    form.month.data = bill.month
    form.electricity_amount.data = bill.electricity_amount
    form.water_amount.data = bill.water_amount
    form.internet_amount.data = bill.internet_amount
    return render_template("edit_month.html", bill=bill, form=form)


@bp.post("/months/<int:bill_id>/edit")
def update_month(bill_id: int):
    bill = bill_repo.get_by_id(bill_id)
    if not bill:
        flash("Month not found", "error")
        return redirect(url_for("main.index"))
    if bill.archived:
        flash("This month is archived. Unarchive to make changes.", "error")
        return redirect(url_for("main.month_detail", bill_id=bill_id))
    form = MonthForm()
    # Year/month are not editable post-creation; enforce hidden or ignore
    if not form.validate_on_submit():
        flash("Please correct the errors in the form", "error")
        return redirect(url_for("main.edit_month", bill_id=bill_id))
    bill_repo.update_amounts(bill_id, float(form.electricity_amount.data), float(form.water_amount.data), float(form.internet_amount.data))
    flash("Month updated", "info")
    return redirect(url_for("main.month_detail", bill_id=bill_id))


@bp.post("/months/<int:bill_id>/archive")
def archive_month(bill_id: int):
    bill_repo.set_archived(bill_id, True)
    flash("Month archived", "info")
    return redirect(url_for("main.index"))


@bp.post("/months/<int:bill_id>/unarchive")
def unarchive_month(bill_id: int):
    # Disallow unarchive permanently
    flash("Unarchiving is not allowed.", "error")
    return redirect(url_for("main.archived"))


@bp.get("/archived")
def archived():
    page = int(request.args.get("page", 1) or 1)
    per_page = 10
    pagination = bill_repo.list_paginated(page=page, per_page=per_page, archived=True)
    return render_template("archived.html", pagination=pagination, months=pagination.items)


@bp.get("/download/db")
def download_db():
    """Download the SQLite database file if using a sqlite:// URL."""
    uri = current_app.config.get("SQLALCHEMY_DATABASE_URI", "")
    parsed = urlparse(uri)
    if parsed.scheme != "sqlite":
        flash("Database download is only available when using a local SQLite database.", "error")
        return redirect(url_for("main.index"))
    # For sqlite, parsed.path holds the absolute path (may be relative in some forms)
    db_path = unquote(parsed.path)
    if db_path.startswith("//"):
        # urlparse may yield leading // for absolute paths; collapse to single leading /
        db_path = db_path[1:]
    import os
    if not os.path.isabs(db_path):
        db_path = os.path.join(os.getcwd(), db_path)
    if not os.path.exists(db_path):
        flash("Database file not found.", "error")
        return redirect(url_for("main.index"))
    return send_file(db_path, as_attachment=True, download_name="billsonline.db")


# Removed global export-all endpoints in favor of per-month contributions downloads


@bp.post("/months/<int:bill_id>/delete")
def delete_month(bill_id: int):
    bill_repo.delete(bill_id)
    flash("Month deleted", "info")
    return redirect(url_for("main.index"))


@bp.get("/months/<int:bill_id>/export.csv")
def export_month_csv(bill_id: int):
    bill = bill_repo.get_by_id(bill_id)
    if not bill:
        flash("Month not found", "error")
        return redirect(url_for("main.index"))
    participants = participants_repo.list_all()
    readings = reading_repo.list_for_month(bill.id)
    adjustments = {a.participant_id: {
        'electricity': a.zero_electricity,
        'water': a.zero_water,
        'internet': a.zero_internet,
        'redis_electricity': a.redis_electricity,
        'redis_water': a.redis_water,
        'redis_internet': a.redis_internet,
    } for a in adjust_repo.list_for_month(bill.id)}
    contributions = calculator.compute_contributions(bill, readings, participants, adjustments)

    si = StringIO()
    writer = csv.writer(si)
    # Contributions table only
    writer.writerow(["Participant", "Electricity", "Water", "Internet", "Total"]) 
    for c in contributions:
        writer.writerow([
            c.participant.name,
            f"{c.electricity:.2f}",
            f"{c.water:.2f}",
            f"{c.internet:.2f}",
            f"{c.total:.2f}",
        ])
    # Totals row
    total_bill = bill.electricity_amount + bill.water_amount + bill.internet_amount
    writer.writerow(["Totals", f"{bill.electricity_amount:.2f}", f"{bill.water_amount:.2f}", f"{bill.internet_amount:.2f}", f"{total_bill:.2f}"])

    output = si.getvalue()
    month_names = ["January","February","March","April","May","June","July","August","September","October","November","December"]
    filename = f"bill_{bill.year}-{month_names[bill.month-1]}.csv"
    return Response(
        output,
        mimetype="text/csv",
        headers={"Content-Disposition": f"attachment; filename={filename}"},
    )




@bp.post("/months/<int:bill_id>/readings")
def submit_readings(bill_id: int):
    bill = bill_repo.get_by_id(bill_id)
    if not bill:
        flash("Month not found", "error")
        return redirect(url_for("main.index"))
    if bill.archived:
        flash("This month is archived. Unarchive to make changes.", "error")
        return redirect(url_for("main.month_detail", bill_id=bill.id))

    # Expect form fields like current_<pid> and previous_<pid>
    for key, value in request.form.items():
        if key.startswith("current_"):
            pid = int(key.split("_", 1)[1])
            current_val = float(value or 0)
            prev_val_raw = request.form.get(f"previous_{pid}")
            prev_val = float(prev_val_raw) if prev_val_raw not in (None, "") else None
            reading_repo.upsert(bill.id, pid, current_val, prev_val)

    return redirect(url_for("main.month_detail", bill_id=bill.id))


@bp.post("/months/<int:bill_id>/adjustments")
def save_adjustments(bill_id: int):
    bill = bill_repo.get_by_id(bill_id)
    if not bill:
        flash("Month not found", "error")
        return redirect(url_for("main.index"))
    if bill.archived:
        flash("This month is archived. Unarchive to make changes.", "error")
        return redirect(url_for("main.month_detail", bill_id=bill.id))
    participants = participants_repo.list_all()
    # Build base amounts per component for validation
    readings = reading_repo.list_for_month(bill.id)
    usage_by_pid = {r.participant_id: r.usage() for r in readings}
    total_usage = sum(usage_by_pid.values())
    elec_base = {p.id: ((bill.electricity_amount * (usage_by_pid.get(p.id, 0.0) / total_usage)) if total_usage > 0 else 0.0) for p in participants}
    water_share = (bill.water_amount / len(participants)) if participants else 0.0
    internet_share = (bill.internet_amount / len(participants)) if participants else 0.0
    water_base = {p.id: water_share for p in participants}
    internet_base = {p.id: internet_share for p in participants}

    def validate_rule(component: str, zpid: int, rule: dict | None) -> tuple[bool, str | None]:
        if not rule or not isinstance(rule, dict):
            return True, None  # nothing to validate
        mode = rule.get('mode')
        targets = rule.get('targets') or {}
        # Resolve base for this participant/component
        if component == 'electricity':
            base_amount = elec_base.get(zpid, 0.0)
        elif component == 'water':
            base_amount = water_base.get(zpid, 0.0)
        else:
            base_amount = internet_base.get(zpid, 0.0)
        try:
            values = [float(v) for v in targets.values()]
        except (TypeError, ValueError):
            values = []
        if mode == 'percent':
            total_pct = sum(values)
            if abs(total_pct - 100.0) > 0.01:
                return False, f"{component.title()} redistribution for {zpid} must total 100%, got {total_pct:.2f}%"
        elif mode == 'amount':
            total_amt = sum(values)
            if abs(total_amt - float(base_amount)) > 0.01:
                return False, f"{component.title()} redistribution for {zpid} must total {base_amount:.2f}, got {total_amt:.2f}"
        return True, None
    for p in participants:
        ze = f"adj_electricity_{p.id}" in request.form
        zw = f"adj_water_{p.id}" in request.form
        zi = f"adj_internet_{p.id}" in request.form

        def parse_rule(component: str):
            mode = request.form.get(f"mode_{component}_{p.id}")
            if mode not in ("percent", "amount"):
                return None
            targets: dict[int, float] = {}
            for t in participants:
                if t.id == p.id:
                    continue
                key = f"redis_{component}_{p.id}_{t.id}"
                raw = request.form.get(key)
                if raw is None or raw == "":
                    continue
                try:
                    val = float(raw)
                except ValueError:
                    continue
                if val > 0:
                    targets[t.id] = val
            if not targets:
                return None
            return {"mode": mode, "targets": targets}

        re_rule = parse_rule("electricity")
        rw_rule = parse_rule("water")
        ri_rule = parse_rule("internet")
        # Validate rules: percent must sum to 100; amount must equal base amount for the zeroed participant
        re_valid, re_err = (True, None)
        rw_valid, rw_err = (True, None)
        ri_valid, ri_err = (True, None)
        if ze and re_rule:
            re_valid, re_err = validate_rule('electricity', p.id, re_rule)
        if zw and rw_rule:
            rw_valid, rw_err = validate_rule('water', p.id, rw_rule)
        if zi and ri_rule:
            ri_valid, ri_err = validate_rule('internet', p.id, ri_rule)
        # Emit errors and drop invalid rules (keep zero flag so leftover splits equally)
        if re_err:
            flash(re_err.replace(str(p.id), p.name), "error")
        if rw_err:
            flash(rw_err.replace(str(p.id), p.name), "error")
        if ri_err:
            flash(ri_err.replace(str(p.id), p.name), "error")
        # Only persist valid rules, else store None so DB clears them
        re_payload = re_rule if (ze and re_rule and re_valid) else None
        rw_payload = rw_rule if (zw and rw_rule and rw_valid) else None
        ri_payload = ri_rule if (zi and ri_rule and ri_valid) else None

        adjust_repo.upsert(
            bill.id,
            p.id,
            zero_electricity=ze,
            zero_water=zw,
            zero_internet=zi,
            redis_electricity=re_payload,
            redis_water=rw_payload,
            redis_internet=ri_payload,
        )
    flash("Adjustments saved", "info")
    return redirect(url_for("main.month_detail", bill_id=bill.id))


@bp.post("/months/<int:bill_id>/adjustments/reset")
def reset_adjustments(bill_id: int):
    bill = bill_repo.get_by_id(bill_id)
    if not bill:
        flash("Month not found", "error")
        return redirect(url_for("main.index"))
    if bill.archived:
        flash("This month is archived. Unarchive to make changes.", "error")
        return redirect(url_for("main.month_detail", bill_id=bill.id))
    adjust_repo.clear_for_month(bill.id)
    flash("All adjustments cleared", "info")
    return redirect(url_for("main.month_detail", bill_id=bill.id))
