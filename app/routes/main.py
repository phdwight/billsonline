from __future__ import annotations

import csv
from io import StringIO
from datetime import date
from urllib.parse import urlparse, unquote

from flask import Blueprint, render_template, request, redirect, url_for, flash, Response, send_file, current_app
from sqlalchemy.exc import IntegrityError

from ..extensions import db
from ..models import BillComponent
from ..repositories import (
    ParticipantRepository,
    MonthlyBillRepository,
    MeterReadingRepository,
    MonthlyAdjustmentRepository,
    BillComponentRepository,
    ComponentAdjustmentRepository,
    MonthParticipantRepository,
)
from ..services import BillCalculator
from ..forms import MonthForm

bp = Blueprint("main", __name__)

participants_repo = ParticipantRepository()
bill_repo = MonthlyBillRepository()
reading_repo = MeterReadingRepository()
adjust_repo = MonthlyAdjustmentRepository()
component_repo = BillComponentRepository()
comp_adjust_repo = ComponentAdjustmentRepository()
month_part_repo = MonthParticipantRepository()
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


@bp.get("/months/new")
def new_month():
    participants = participants_repo.list_all()
    form = MonthForm()
    if not form.year.data or not form.month.data:
        today = date.today()
        form.year.data = today.year
        form.month.data = today.month
    return render_template("new_month.html", form=form, participants=participants)


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
        # Prevent duplicates (case-insensitive)
        existing = [p for p in participants_repo.list_all() if p.name.lower() == name.lower()]
        if existing:
            flash("A participant with that name already exists", "error")
        else:
            try:
                participants_repo.add(name=name)
            except IntegrityError:
                # In case of race or DB constraint, rollback and show a friendly error
                db.session.rollback()
                flash("A participant with that name already exists", "error")
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
    participants = participants_repo.list_all()
    try:
        bill = bill_repo.create(year, month, float(form.electricity_amount.data), float(form.water_amount.data), float(form.internet_amount.data))
    except IntegrityError:
        db.session.rollback()
        flash(f"A month for {year}-{month:02d} already exists.", "error")
        return redirect(url_for("main.index"))
    # Default membership: include all current participants
    try:
        for p in participants:
            month_part_repo.add(bill.id, p.id)
    except Exception:
        # Non-fatal; membership UI can still add manually
        pass
    # Optionally create dynamic components provided in the creation form
    names = request.form.getlist('comp_name[]')
    amounts = request.form.getlist('comp_amount[]')
    splits = request.form.getlist('comp_split[]')
    positions = request.form.getlist('comp_position[]')
    created_any = False
    def parse_comp_dist(index: int) -> dict[int, float]:
        dist: dict[int, float] = {}
        for p in participants:
            raw = request.form.get(f"comp_dist_{index}_{p.id}")
            if raw is None or raw == "":
                continue
            try:
                val = float(raw)
            except ValueError:
                continue
            dist[p.id] = val
        return dist

    for i, name in enumerate(names or []):
        n = (name or '').strip()
        if not n:
            continue
        try:
            amt = float((amounts[i] if i < len(amounts) else '0') or '0')
        except (ValueError, TypeError):
            amt = 0.0
        sp = (splits[i] if i < len(splits) else 'equal') or 'equal'
        # allow usage, equal, percentage, amount
        if sp not in ('usage','equal','percentage','amount'):
            sp = 'equal'
        try:
            pos = int((positions[i] if i < len(positions) else i) or i)
        except (ValueError, TypeError):
            pos = i
        distribution = None
        if sp in ("percentage", "amount"):
            distribution = parse_comp_dist(i)
        try:
            component_repo.add(bill.id, name=n, amount=amt, split_method=sp, position=pos, distribution=distribution)
            created_any = True
        except IntegrityError:
            db.session.rollback()
            flash(f"Skipped duplicate component name '{n}' for this month.", "error")
            continue
    # Create default components for legacy three based on chosen split types
    try:
        legacy_elec_split = (request.form.get('legacy_electricity_split') or 'usage').strip()
        legacy_water_split = (request.form.get('legacy_water_split') or 'equal').strip()
        legacy_inet_split = (request.form.get('legacy_internet_split') or 'equal').strip()
        # Parse optional distributions when split is percentage or amount
        def parse_dist(prefix: str) -> dict[int, float]:
            dist: dict[int, float] = {}
            for p in participants:
                raw = request.form.get(f"legacy_{prefix}_dist_{p.id}")
                if raw is None or raw == "":
                    continue
                try:
                    val = float(raw)
                except ValueError:
                    continue
                dist[p.id] = val
            return dist
        elec_dist = parse_dist("electricity") if legacy_elec_split in ("percentage", "amount") else None
        water_dist = parse_dist("water") if legacy_water_split in ("percentage", "amount") else None
        inet_dist = parse_dist("internet") if legacy_inet_split in ("percentage", "amount") else None
        legacy_defs = [
            ("Electricity", float(form.electricity_amount.data or 0), legacy_elec_split, 0, elec_dist),
            ("Water", float(form.water_amount.data or 0), legacy_water_split, 1, water_dist),
            ("Internet", float(form.internet_amount.data or 0), legacy_inet_split, 2, inet_dist),
        ]
        for (nm, amt, sp, pos, dist) in legacy_defs:
            if amt and amt > 0:
                try:
                    component_repo.add(
                        bill.id,
                        name=nm,
                        amount=amt,
                        split_method=sp if sp in ("usage","equal","percentage","amount") else "equal",
                        position=pos,
                        distribution=(dist or None),
                    )
                except IntegrityError:
                    db.session.rollback()
                    # a same-name custom component already exists; skip silently
                    pass
    except Exception:
        # non-fatal; proceed with bill created
        pass
    flash("Month created", "info")
    return redirect(url_for("main.index"))


@bp.get("/months/<int:bill_id>")
def month_detail(bill_id: int):
    bill = bill_repo.get_by_id(bill_id)
    if not bill:
        flash("Month not found", "error")
        return redirect(url_for("main.index"))
    participants = participants_repo.list_all()
    # Participants linked to this month (membership)
    month_members = month_part_repo.list_for_month(bill.id)
    member_ids = {m.participant_id for m in month_members}
    # Backfill default membership for legacy months without entries
    if not member_ids and participants:
        try:
            for p in participants:
                month_part_repo.add(bill.id, p.id)
            member_ids = {p.id for p in participants}
        except Exception:
            # If seeding fails, fall back to treating all participants as members without persisting
            member_ids = {p.id for p in participants}
    readings = reading_repo.list_for_month(bill.id)
    readings_by_pid = {r.participant_id: r for r in readings}
    # Pre-fill previous readings from previous month if not provided
    prev_bill = bill_repo.get_previous(bill.year, bill.month)
    prev_readings_map = {}
    if prev_bill:
        prev_readings = reading_repo.list_for_month(prev_bill.id)
        prev_readings_map = {r.participant_id: r.reading_current for r in prev_readings}
    # Contributions are computed only via dynamic components.
    # Dynamic components (if any exist for the month)
    components = component_repo.list_for_month(bill.id)
    dynamic_contributions = None
    comp_adjustments_map = {}
    dynamic_base_maps = {}
    if components:
        comp_adjs = comp_adjust_repo.list_for_month(bill.id)
        # Build adjustments map: {component_id: {participant_id: {zero, rule}}}
        for a in comp_adjs:
            comp_adjustments_map.setdefault(a.component_id, {})[a.participant_id] = {
                'zero': bool(a.zero),
                'rule': a.redis_rule or None,
            }
        # Compute base maps per component for client validation
        usage_by_pid = {r.participant_id: r.usage() for r in readings}
        total_usage = sum(usage_by_pid.values())
        # Use members for base maps to keep UI aligned with who is included
        member_participants = [p for p in participants if not member_ids or p.id in member_ids]
        for comp in components:
            base_map = {}
            if comp.split_method == 'usage':
                for p in member_participants:
                    u = usage_by_pid.get(p.id, 0.0)
                    base_map[p.id] = (comp.amount * (u / total_usage)) if total_usage > 0 else 0.0
            else:
                share = (comp.amount / len(member_participants)) if member_participants else 0.0
                for p in member_participants:
                    base_map[p.id] = share
            dynamic_base_maps[comp.id] = base_map
        # Filter participants to only those linked to this month if membership exists
        parts_for_calc = member_participants
        dynamic_contributions = calculator.compute_contributions_dynamic(
            bill=bill,
            components=components,
            readings=readings,
            participants=parts_for_calc,
            component_adjustments=comp_adjs,
        )
    # Compute base amounts per component for client-side indicators
    usage_by_pid = {r.participant_id: r.usage() for r in readings}
    total_usage = sum(usage_by_pid.values())
    base_electricity_map = {}
    base_water_share = 0.0
    base_internet_share = 0.0
    total_bill = 0.0
    return render_template(
        "month_detail.html",
        bill=bill,
        participants=participants,
        member_ids=member_ids,
        readings=readings,
        readings_by_pid=readings_by_pid,
        prev_readings_map=prev_readings_map,
        contributions=None,
        components=components,
        dynamic_contributions=dynamic_contributions,
        comp_adjustments=comp_adjustments_map,
        dynamic_base_maps=dynamic_base_maps,
        adjustments={},
        participant_name_by_id={p.id: p.name for p in participants},
        base_electricity_map=base_electricity_map,
        base_water_share=base_water_share,
        base_internet_share=base_internet_share,
        total_bill=total_bill,
    )


@bp.post("/months/<int:bill_id>/components/add")
def add_component(bill_id: int):
    bill = bill_repo.get_by_id(bill_id)
    if not bill:
        flash("Month not found", "error")
        return redirect(url_for("main.index"))
    if bill.archived:
        flash("This month is archived. Unarchive to make changes.", "error")
        return redirect(url_for("main.month_detail", bill_id=bill.id))
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
        return redirect(url_for("main.month_detail", bill_id=bill.id))
    if split not in ("usage", "equal"):
        flash("Split method must be 'usage' or 'equal'", "error")
        return redirect(url_for("main.month_detail", bill_id=bill.id))
    if amount < 0:
        flash("Amount must be a non-negative number", "error")
        return redirect(url_for("main.month_detail", bill_id=bill.id))
    try:
        component_repo.add(bill.id, name=name, amount=amount, split_method=split, position=position)
    except IntegrityError:
        db.session.rollback()
        flash("A component with that name already exists for this month.", "error")
    else:
        flash("Component added", "info")
    return redirect(url_for("main.month_detail", bill_id=bill.id))


@bp.post("/months/<int:bill_id>/participants/add")
def add_month_participant(bill_id: int):
    bill = bill_repo.get_by_id(bill_id)
    if not bill:
        flash("Month not found", "error")
        return redirect(url_for("main.index"))
    if bill.archived:
        flash("This month is archived. Unarchive to make changes.", "error")
        return redirect(url_for("main.month_detail", bill_id=bill.id))
    try:
        pid = int(request.form.get("participant_id") or 0)
    except ValueError:
        pid = 0
    if not pid:
        flash("Select a participant", "error")
        return redirect(url_for("main.month_detail", bill_id=bill.id))
    month_part_repo.add(bill.id, pid)
    flash("Participant linked to month", "info")
    return redirect(url_for("main.month_detail", bill_id=bill.id))


@bp.post("/months/<int:bill_id>/participants/<int:pid>/remove")
def remove_month_participant(bill_id: int, pid: int):
    bill = bill_repo.get_by_id(bill_id)
    if not bill:
        flash("Month not found", "error")
        return redirect(url_for("main.index"))
    if bill.archived:
        flash("This month is archived. Unarchive to make changes.", "error")
        return redirect(url_for("main.month_detail", bill_id=bill.id))
    month_part_repo.remove(bill.id, pid)
    flash("Participant unlinked from month", "info")
    return redirect(url_for("main.month_detail", bill_id=bill.id))


@bp.post("/months/<int:bill_id>/components/<int:component_id>/update")
def update_component(bill_id: int, component_id: int):
    bill = bill_repo.get_by_id(bill_id)
    if not bill:
        flash("Month not found", "error")
        return redirect(url_for("main.index"))
    if bill.archived:
        flash("This month is archived. Unarchive to make changes.", "error")
        return redirect(url_for("main.month_detail", bill_id=bill.id))
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
            return redirect(url_for("main.month_detail", bill_id=bill.id))
        if amt_f < 0:
            flash("Amount must be non-negative", "error")
            return redirect(url_for("main.month_detail", bill_id=bill.id))
    if position is not None and position != "":
        try:
            pos_i = int(position)
        except ValueError:
            flash("Position must be an integer", "error")
            return redirect(url_for("main.month_detail", bill_id=bill.id))
    if split and split not in ("usage", "equal"):
        flash("Split method must be 'usage' or 'equal'", "error")
        return redirect(url_for("main.month_detail", bill_id=bill.id))
    try:
        component_repo.update(component_id, name=name or None, amount=amt_f, split_method=split, position=pos_i)
    except IntegrityError:
        db.session.rollback()
        flash("Component name already exists for this month.", "error")
    else:
        flash("Component updated", "info")
    return redirect(url_for("main.month_detail", bill_id=bill.id))


@bp.post("/months/<int:bill_id>/components/<int:component_id>/delete")
def delete_component(bill_id: int, component_id: int):
    bill = bill_repo.get_by_id(bill_id)
    if not bill:
        flash("Month not found", "error")
        return redirect(url_for("main.index"))
    if bill.archived:
        flash("This month is archived. Unarchive to make changes.", "error")
        return redirect(url_for("main.month_detail", bill_id=bill.id))
    component_repo.delete(component_id)
    flash("Component deleted", "info")
    return redirect(url_for("main.month_detail", bill_id=bill.id))


@bp.post("/months/<int:bill_id>/components/adjustments")
def save_component_adjustments(bill_id: int):
    bill = bill_repo.get_by_id(bill_id)
    if not bill:
        flash("Month not found", "error")
        return redirect(url_for("main.index"))
    if bill.archived:
        flash("This month is archived. Unarchive to make changes.", "error")
        return redirect(url_for("main.month_detail", bill_id=bill.id))

    # Use month membership for adjustments targets
    participants = participants_repo.list_all()
    member_ids = {m.participant_id for m in month_part_repo.list_for_month(bill.id)}
    if not member_ids:
        member_ids = {p.id for p in participants}
    pids = [p.id for p in participants if p.id in member_ids]
    components = component_repo.list_for_month(bill.id)
    readings = reading_repo.list_for_month(bill.id)
    usage_by_pid = {r.participant_id: r.usage() for r in readings}
    total_usage = sum(usage_by_pid.values())

    def base_for(comp, pid):
        if comp.split_method == 'equal':
            return (comp.amount / len(pids)) if pids else 0.0
        # usage
        u = usage_by_pid.get(pid, 0.0)
        return (comp.amount * (u / total_usage)) if total_usage > 0 else 0.0

    def validate_rule(comp, pid, rule, participant_name: str):
        if not rule or not isinstance(rule, dict):
            return True, None
        mode = rule.get('mode')
        targets = rule.get('targets') or {}
        try:
            vals = [float(v) for v in targets.values()]
        except (TypeError, ValueError):
            vals = []
        if mode == 'percent':
            tot = sum(vals)
            if abs(tot - 100.0) > 0.01:
                return False, f"{comp.name}: {participant_name}'s redistribution must sum to 100% (currently {tot:.2f}%)"
        elif mode == 'amount':
            tot = sum(vals)
            base_amt = base_for(comp, pid)
            if abs(tot - float(base_amt)) > 0.01:
                return False, f"{comp.name}: {participant_name}'s redistribution must sum to ₱{base_amt:.2f} (currently ₱{tot:.2f})"
        return True, None

    saved_rules = 0
    current_app.logger.info("[adjustments] start: bill=%s comps=%s pids=%s", bill.id, [c.id for c in components], pids)
    # Iterate all components and participants (members only)
    for comp in components:
        for pid in pids:
            # no explicit zero checkbox anymore; zero derives from a valid rule
            zero = False

            # Parse rule inputs (only consider when zero)
            rule = None
            # Collect mode/targets (we'll validate before enabling zero by default)
            mode = request.form.get(f"mode_comp_{comp.id}_{pid}")
            # Gather targets regardless of mode to support defaulting
            targets = {}
            for tpid in pids:
                if tpid == pid:
                    continue
                raw = request.form.get(f"redis_comp_{comp.id}_{pid}_{tpid}")
                if raw is None or raw == "":
                    continue
                try:
                    val = float(raw)
                except ValueError:
                    continue
                if val > 0:
                    targets[tpid] = val
            attempted_rule = bool(targets) or (mode in ("percent", "amount"))
            if targets and mode in ("percent", "amount"):
                rule = {"mode": mode, "targets": targets}
                current_app.logger.info("[adjustments] parsed rule comp=%s pid=%s mode=%s targets=%s", comp.id, pid, mode, targets)

            # Validate
            if rule:
                # translate pid to name for readable messages
                name = next((p.name for p in participants if p.id == pid), str(pid))
                ok, err = validate_rule(comp, pid, rule, name)
                if not ok:
                    flash(err, "error")
                    rule = None  # drop invalid rule
            # Only auto-enable zero when a valid rule exists
            if rule:
                zero = True

            # Persist adjustment
            comp_adjust_repo.upsert(bill.id, comp.id, pid, zero=zero, redis_rule=rule)
            if rule:
                saved_rules += 1

    current_app.logger.info("[adjustments] saved_rules=%s", saved_rules)
    if saved_rules:
        flash(f"Component adjustments saved ({saved_rules} redistribution rule(s) updated)", "info")
    else:
        flash("Component adjustments saved", "info")
    return redirect(url_for("main.month_detail", bill_id=bill.id))


@bp.post("/months/<int:bill_id>/components/convert-from-legacy")
def convert_legacy_to_dynamic(bill_id: int):
    """Create dynamic components for Electricity (usage), Water (equal), Internet (equal)
    using the legacy amounts, if no components exist yet."""
    bill = bill_repo.get_by_id(bill_id)
    if not bill:
        flash("Month not found", "error")
        return redirect(url_for("main.index"))
    if bill.archived:
        flash("This month is archived. Unarchive to make changes.", "error")
        return redirect(url_for("main.month_detail", bill_id=bill.id))
    existing = component_repo.list_for_month(bill.id)
    if existing:
        flash("This month already has components.", "error")
        return redirect(url_for("main.month_detail", bill_id=bill.id))
    position = 0
    if bill.electricity_amount and bill.electricity_amount > 0:
        component_repo.add(bill.id, name="Electricity", amount=float(bill.electricity_amount), split_method="usage", position=position)
        position += 1
    if bill.water_amount and bill.water_amount > 0:
        component_repo.add(bill.id, name="Water", amount=float(bill.water_amount), split_method="equal", position=position)
        position += 1
    if bill.internet_amount and bill.internet_amount > 0:
        component_repo.add(bill.id, name="Internet", amount=float(bill.internet_amount), split_method="equal", position=position)
        position += 1
    if position == 0:
        flash("No legacy amounts found to convert.", "error")
    else:
        flash("Legacy amounts converted to components.", "info")
    return redirect(url_for("main.month_detail", bill_id=bill.id))


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
    # Check for dynamic components first
    components = component_repo.list_for_month(bill.id)
    si = StringIO()
    writer = csv.writer(si)

    # If no components exist, synthesize dynamic components from legacy amounts
    synth_components = []
    if not components:
        pos = 0
        if bill.electricity_amount and bill.electricity_amount > 0:
            c = BillComponent(month_id=bill.id, name="Electricity", amount=float(bill.electricity_amount), split_method="usage", position=pos)
            c.id = 1
            synth_components.append(c)
            pos += 1
        if bill.water_amount and bill.water_amount > 0:
            c = BillComponent(month_id=bill.id, name="Water", amount=float(bill.water_amount), split_method="equal", position=pos)
            c.id = 2
            synth_components.append(c)
            pos += 1
        if bill.internet_amount and bill.internet_amount > 0:
            c = BillComponent(month_id=bill.id, name="Internet", amount=float(bill.internet_amount), split_method="equal", position=pos)
            c.id = 3
            synth_components.append(c)
            pos += 1
    effective_components = components or synth_components

    comp_adjs = comp_adjust_repo.list_for_month(bill.id) if components else []
    dyn = calculator.compute_contributions_dynamic(
        bill=bill,
        components=effective_components,
        readings=readings,
        participants=participants,
        component_adjustments=comp_adjs,
    )
    ordered_names = [c.name for c in effective_components]
    # Header
    writer.writerow(["Participant", *ordered_names, "Total"]) 
    # Rows
    for c in dyn:
        row = [c.participant.name]
        total = 0.0
        for name in ordered_names:
            val = round(float(c.components.get(name, 0.0)), 2)
            row.append(f"{val:.2f}")
            total += val
        row.append(f"{total:.2f}")
        writer.writerow(row)
    # Totals row from component definitions
    comp_totals = [float(c.amount) for c in effective_components]
    grand_total = sum(comp_totals)
    writer.writerow(["Totals", *[f"{amt:.2f}" for amt in comp_totals], f"{grand_total:.2f}"])

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


# Legacy adjustments routes removed: adjustments are per-component only.
