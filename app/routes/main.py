from __future__ import annotations

from flask import Blueprint, render_template, request, redirect, url_for, flash, Response
from datetime import date
import csv
from io import StringIO
from openpyxl import Workbook

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
    if not form.validate_on_submit():
        flash("Please correct the errors in the form", "error")
        return redirect(url_for("main.index"))
    year = int(form.year.data)
    month = int(form.month.data)
    if bill_repo.find_by_year_month(year, month):
        flash("That month already exists", "error")
        return redirect(url_for("main.index"))
    bill_repo.create(year, month, float(form.electricity_amount.data), float(form.water_amount.data), float(form.internet_amount.data))
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
    } for a in adjust_repo.list_for_month(bill.id)}
    contributions = calculator.compute_contributions(bill, readings, participants, adjustments)
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
        total_bill=total_bill,
    )


@bp.get("/months/<int:bill_id>/edit")
def edit_month(bill_id: int):
    bill = bill_repo.get_by_id(bill_id)
    if not bill:
        flash("Month not found", "error")
        return redirect(url_for("main.index"))
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
    bill_repo.set_archived(bill_id, False)
    flash("Month unarchived", "info")
    return redirect(url_for("main.archived"))


@bp.get("/archived")
def archived():
    page = int(request.args.get("page", 1) or 1)
    per_page = 10
    pagination = bill_repo.list_paginated(page=page, per_page=per_page, archived=True)
    return render_template("archived.html", pagination=pagination, months=pagination.items)


@bp.get("/export/all.csv")
def export_all_csv():
    # Summary of all non-archived months
    months = bill_repo.list_all()
    si = StringIO()
    writer = csv.writer(si)
    writer.writerow(["Year", "Month", "Electricity", "Water", "Internet", "Total"]) 
    for m in months:
        total = m.electricity_amount + m.water_amount + m.internet_amount
        writer.writerow([m.year, m.month, f"{m.electricity_amount:.2f}", f"{m.water_amount:.2f}", f"{m.internet_amount:.2f}", f"{total:.2f}"])
    output = si.getvalue()
    return Response(output, mimetype="text/csv", headers={"Content-Disposition": "attachment; filename=months.csv"})


@bp.get("/export/all.xlsx")
def export_all_xlsx():
    # Summary of all non-archived months
    months = bill_repo.list_all()
    wb = Workbook()
    ws = wb.active
    ws.title = "Months"
    ws.append(["Year", "Month", "Electricity", "Water", "Internet", "Total"])
    for m in months:
        total = m.electricity_amount + m.water_amount + m.internet_amount
        ws.append([m.year, m.month, float(m.electricity_amount), float(m.water_amount), float(m.internet_amount), float(total)])
    from io import BytesIO
    bio = BytesIO()
    wb.save(bio)
    bio.seek(0)
    return Response(bio.getvalue(), mimetype="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet", headers={"Content-Disposition": "attachment; filename=months.xlsx"})


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
    } for a in adjust_repo.list_for_month(bill.id)}
    contributions = calculator.compute_contributions(bill, readings, participants, adjustments)

    si = StringIO()
    writer = csv.writer(si)
    writer.writerow(["Participant", "Electricity", "Water", "Internet", "Total"]) 
    for c in contributions:
        writer.writerow([c.participant.name, f"{c.electricity:.2f}", f"{c.water:.2f}", f"{c.internet:.2f}", f"{c.total:.2f}"])
    total_bill = bill.electricity_amount + bill.water_amount + bill.internet_amount
    writer.writerow([])
    writer.writerow(["Total Bill", f"{bill.electricity_amount:.2f}", f"{bill.water_amount:.2f}", f"{bill.internet_amount:.2f}", f"{total_bill:.2f}"])

    output = si.getvalue()
    filename = f"bill_{bill.year}-{bill.month:02d}.csv"
    return Response(
        output,
        mimetype="text/csv",
        headers={"Content-Disposition": f"attachment; filename={filename}"},
    )


@bp.get("/months/<int:bill_id>/export.xlsx")
def export_month_xlsx(bill_id: int):
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
    } for a in adjust_repo.list_for_month(bill.id)}
    contributions = calculator.compute_contributions(bill, readings, participants, adjustments)

    wb = Workbook()
    ws = wb.active
    ws.title = f"{bill.year}-{bill.month:02d}"
    ws.append(["Participant", "Electricity", "Water", "Internet", "Total"]) 
    for c in contributions:
        ws.append([
            c.participant.name,
            float(f"{c.electricity:.2f}"),
            float(f"{c.water:.2f}"),
            float(f"{c.internet:.2f}"),
            float(f"{c.total:.2f}"),
        ])
    total_bill = bill.electricity_amount + bill.water_amount + bill.internet_amount
    ws.append([])
    ws.append(["Total Bill", float(f"{bill.electricity_amount:.2f}"), float(f"{bill.water_amount:.2f}"), float(f"{bill.internet_amount:.2f}"), float(f"{total_bill:.2f}")])

    from io import BytesIO
    bio = BytesIO()
    wb.save(bio)
    bio.seek(0)
    filename = f"bill_{bill.year}-{bill.month:02d}.xlsx"
    return Response(
        bio.getvalue(),
        mimetype="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": f"attachment; filename={filename}"},
    )


@bp.post("/months/<int:bill_id>/readings")
def submit_readings(bill_id: int):
    bill = bill_repo.get_by_id(bill_id)
    if not bill:
        flash("Month not found", "error")
        return redirect(url_for("main.index"))

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
    participants = participants_repo.list_all()
    for p in participants:
        ze = f"adj_electricity_{p.id}" in request.form
        zw = f"adj_water_{p.id}" in request.form
        zi = f"adj_internet_{p.id}" in request.form
        adjust_repo.upsert(bill.id, p.id, zero_electricity=ze, zero_water=zw, zero_internet=zi)
    flash("Adjustments saved", "info")
    return redirect(url_for("main.month_detail", bill_id=bill.id))


@bp.post("/months/<int:bill_id>/adjustments/reset")
def reset_adjustments(bill_id: int):
    bill = bill_repo.get_by_id(bill_id)
    if not bill:
        flash("Month not found", "error")
        return redirect(url_for("main.index"))
    adjust_repo.clear_for_month(bill.id)
    flash("All adjustments cleared", "info")
    return redirect(url_for("main.month_detail", bill_id=bill.id))
