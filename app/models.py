from __future__ import annotations

from datetime import date
from typing import Optional

from .extensions import db


class Participant(db.Model):
    __tablename__ = "participants"
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(80), nullable=False, unique=True)
    # include_in_internet removed; adjustments now control exclusions (column may still exist in DB for backward compatibility)

    readings = db.relationship("MeterReading", back_populates="participant", cascade="all, delete-orphan")

    def __repr__(self) -> str:  # pragma: no cover
        return f"<Participant {self.name}>"


class MonthlyBill(db.Model):
    __tablename__ = "monthly_bills"
    id = db.Column(db.Integer, primary_key=True)
    year = db.Column(db.Integer, nullable=False)
    month = db.Column(db.Integer, nullable=False)  # 1-12
    electricity_amount = db.Column(db.Float, nullable=False, default=0.0)
    water_amount = db.Column(db.Float, nullable=False, default=0.0)
    internet_amount = db.Column(db.Float, nullable=False, default=0.0)
    created_at = db.Column(db.Date, default=date.today, nullable=False)
    archived = db.Column(db.Boolean, default=False, nullable=False)

    __table_args__ = (db.UniqueConstraint("year", "month", name="uq_month"),)

    readings = db.relationship("MeterReading", back_populates="month", cascade="all, delete-orphan")

    def __repr__(self) -> str:  # pragma: no cover
        return f"<MonthlyBill {self.year}-{self.month:02d}>"


class MeterReading(db.Model):
    __tablename__ = "meter_readings"
    id = db.Column(db.Integer, primary_key=True)
    participant_id = db.Column(db.Integer, db.ForeignKey("participants.id"), nullable=False)
    month_id = db.Column(db.Integer, db.ForeignKey("monthly_bills.id"), nullable=False)
    reading_current = db.Column(db.Float, nullable=False, default=0.0)
    reading_previous = db.Column(db.Float, nullable=True)

    participant = db.relationship("Participant", back_populates="readings")
    month = db.relationship("MonthlyBill", back_populates="readings")

    def usage(self) -> float:
        if self.reading_previous is None:
            return 0.0
        return max(0.0, self.reading_current - self.reading_previous)


class MonthlyAdjustment(db.Model):
    __tablename__ = "monthly_adjustments"
    id = db.Column(db.Integer, primary_key=True)
    month_id = db.Column(db.Integer, db.ForeignKey("monthly_bills.id"), nullable=False)
    participant_id = db.Column(db.Integer, db.ForeignKey("participants.id"), nullable=False)
    zero_electricity = db.Column(db.Boolean, default=False, nullable=False)
    zero_water = db.Column(db.Boolean, default=False, nullable=False)
    zero_internet = db.Column(db.Boolean, default=False, nullable=False)

    month = db.relationship("MonthlyBill")
    participant = db.relationship("Participant")

    __table_args__ = (db.UniqueConstraint("month_id", "participant_id", name="uq_adjustment_month_participant"),)
