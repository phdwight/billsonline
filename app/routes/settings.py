"""Settings routes - single responsibility: application settings and database management."""
from __future__ import annotations

import os
import shutil
from datetime import datetime

from flask import Blueprint, render_template, request, redirect, url_for, flash, send_file, current_app

from ..extensions import db

bp = Blueprint("settings", __name__, url_prefix="/settings")


@bp.get("/")
def index():
    """GET /settings - Settings page."""
    return render_template("settings.html")


@bp.get("/database")
def database_download():
    """GET /settings/database - Download the database file."""
    db_uri = current_app.config.get("SQLALCHEMY_DATABASE_URI", "")
    if db_uri.startswith("sqlite:///"):
        db_path = db_uri.replace("sqlite:///", "")
        if os.path.exists(db_path):
            return send_file(
                db_path,
                as_attachment=True,
                download_name=f"billsonline_backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}.db"
            )
    flash("Database file not found or not using SQLite", "error")
    return redirect(url_for("settings.index"))


@bp.post("/database")
def database_upload():
    """POST /settings/database - Upload and replace the database file."""
    if "database" not in request.files:
        flash("No file uploaded", "error")
        return redirect(url_for("settings.index"))

    file = request.files["database"]
    if file.filename == "":
        flash("No file selected", "error")
        return redirect(url_for("settings.index"))

    if not file.filename.endswith(".db"):
        flash("Invalid file type. Please upload a .db file", "error")
        return redirect(url_for("settings.index"))

    db_uri = current_app.config.get("SQLALCHEMY_DATABASE_URI", "")
    if not db_uri.startswith("sqlite:///"):
        flash("Database replacement only supported for SQLite", "error")
        return redirect(url_for("settings.index"))

    db_path = db_uri.replace("sqlite:///", "")

    if os.path.exists(db_path):
        backup_path = f"{db_path}.backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        shutil.copy2(db_path, backup_path)

    db.session.remove()
    db.engine.dispose()

    try:
        file.save(db_path)
        flash("Database replaced successfully! Please refresh the page.", "success")
    except Exception as e:
        flash(f"Error replacing database: {str(e)}", "error")

    return redirect(url_for("settings.index"))
