"""Participants routes - single responsibility: manage participants."""
from __future__ import annotations

from flask import Blueprint, render_template, request, redirect, url_for, flash
from sqlalchemy.exc import IntegrityError

from ..extensions import db
from ..repositories import ParticipantRepository

bp = Blueprint("participants", __name__, url_prefix="/participants")


def _get_participants_repo() -> ParticipantRepository:
    """Factory function for dependency injection."""
    return ParticipantRepository()


@bp.get("/")
def index():
    """GET /participants - List all participants."""
    participants_repo = _get_participants_repo()
    participants = participants_repo.list_all()
    return render_template("participants.html", participants=participants)


@bp.post("/")
def create():
    """POST /participants - Create a new participant."""
    participants_repo = _get_participants_repo()
    name = request.form.get("name", "").strip()
    if not name:
        flash("Name is required", "error")
    else:
        existing = [p for p in participants_repo.list_all() if p.name.lower() == name.lower()]
        if existing:
            flash("A participant with that name already exists", "error")
        else:
            try:
                participants_repo.add(name=name)
            except IntegrityError:
                db.session.rollback()
                flash("A participant with that name already exists", "error")
    return redirect(url_for("home.index"))


@bp.post("/<int:pid>")
def update(pid: int):
    """POST /participants/<id> - Update a participant (PUT emulation via POST)."""
    participants_repo = _get_participants_repo()
    name = request.form.get("name", "").strip()
    if not name:
        flash("Participant name is required", "error")
        return redirect(url_for("participants.index"))
    existing = [p for p in participants_repo.list_all() if p.name.lower() == name.lower() and p.id != pid]
    if existing:
        flash("Another participant already has that name", "error")
        return redirect(url_for("participants.index"))
    participants_repo.update(pid, name)
    flash("Participant updated", "info")
    return redirect(url_for("participants.index"))
