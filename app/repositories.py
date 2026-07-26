from __future__ import annotations

from typing import Optional

from .extensions import db
from .models import (
    Participant, MonthlyBill, MeterReading,
    BillComponent, ComponentAdjustment, MonthParticipant, Photo
)


class ParticipantRepository:
    def add(self, name: str) -> Participant:
        p = Participant(name=name)
        db.session.add(p)
        db.session.commit()
        return p

    def list_all(self) -> list[Participant]:
        return Participant.query.order_by(Participant.name).all()

    def get(self, participant_id: int) -> Optional[Participant]:
        return db.session.get(Participant, participant_id)

    def update(self, participant_id: int, name: str) -> Participant:
        p = db.session.get(Participant, participant_id)
        if p is None:
            from flask import abort
            abort(404)
        p.name = name
        db.session.commit()
        return p

    def delete(self, participant_id: int) -> None:
        p = db.session.get(Participant, participant_id)
        if p is None:
            from flask import abort
            abort(404)
        db.session.delete(p)
        db.session.commit()


class MonthlyBillRepository:
    def create(
        self,
        year: int,
        month: int,
        electricity_amount: float,
        water_amount: float,
        internet_amount: float
    ) -> MonthlyBill:
        bill = MonthlyBill(
            year=year,
            month=month,
            electricity_amount=electricity_amount,
            water_amount=water_amount,
            internet_amount=internet_amount,
        )
        db.session.add(bill)
        db.session.commit()
        return bill

    def list_all(self) -> list[MonthlyBill]:
        return (
            MonthlyBill.query.filter_by(archived=False)
            .order_by(MonthlyBill.year.desc(), MonthlyBill.month.desc())
            .all()
        )

    def list_all_including_archived(self) -> list[MonthlyBill]:
        """List all bills including archived ones, for reports."""
        return (
            MonthlyBill.query
            .order_by(MonthlyBill.year.desc(), MonthlyBill.month.desc())
            .all()
        )

    def get_latest(self, archived: bool = False) -> Optional[MonthlyBill]:
        return (
            MonthlyBill.query.filter_by(archived=archived)
            .order_by(MonthlyBill.year.desc(), MonthlyBill.month.desc())
            .first()
        )

    def list_paginated(self, page: int, per_page: int, archived: bool = False):
        return (
            MonthlyBill.query.filter_by(archived=archived)
            .order_by(MonthlyBill.year.desc(), MonthlyBill.month.desc())
            .paginate(page=page, per_page=per_page, error_out=False)
        )

    def get_by_id(self, bill_id: int) -> Optional[MonthlyBill]:
        return db.session.get(MonthlyBill, bill_id)

    def get_previous(self, year: int, month: int) -> Optional[MonthlyBill]:
        # naive previous month calculation
        if month == 1:
            prev_year, prev_month = (year - 1, 12)
        else:
            prev_year, prev_month = (year, month - 1)
        return MonthlyBill.query.filter_by(year=prev_year, month=prev_month).first()

    def find_by_year_month(self, year: int, month: int) -> Optional[MonthlyBill]:
        return MonthlyBill.query.filter_by(year=year, month=month).first()

    def update_amounts(self, bill_id: int, electricity: float, water: float, internet: float) -> MonthlyBill:
        bill = db.session.get(MonthlyBill, bill_id)
        if bill is None:
            from flask import abort
            abort(404)
        bill.electricity_amount = electricity
        bill.water_amount = water
        bill.internet_amount = internet
        db.session.commit()
        return bill

    def delete(self, bill_id: int) -> None:
        bill = db.session.get(MonthlyBill, bill_id)
        if bill is None:
            from flask import abort
            abort(404)
        db.session.delete(bill)
        db.session.commit()

    def set_archived(self, bill_id: int, archived: bool) -> MonthlyBill:
        bill = db.session.get(MonthlyBill, bill_id)
        if bill is None:
            from flask import abort
            abort(404)
        bill.archived = archived
        db.session.commit()
        return bill


class MeterReadingRepository:
    def upsert(
        self,
        month_id: int,
        participant_id: int,
        reading_current: float,
        reading_previous: float | None
    ) -> MeterReading:
        reading = MeterReading.query.filter_by(month_id=month_id, participant_id=participant_id).first()
        if reading is None:
            reading = MeterReading(month_id=month_id, participant_id=participant_id)
            db.session.add(reading)
        reading.reading_current = reading_current
        reading.reading_previous = reading_previous
        db.session.commit()
        return reading

    def list_for_month(self, month_id: int) -> list[MeterReading]:
        return MeterReading.query.filter_by(month_id=month_id).all()


class MonthParticipantRepository:
    def add(self, month_id: int, participant_id: int) -> MonthParticipant:
        mp = MonthParticipant.query.filter_by(month_id=month_id, participant_id=participant_id).first()
        if mp is None:
            mp = MonthParticipant(month_id=month_id, participant_id=participant_id)
            db.session.add(mp)
            db.session.commit()
        return mp

    def remove(self, month_id: int, participant_id: int) -> None:
        MonthParticipant.query.filter_by(month_id=month_id, participant_id=participant_id).delete()
        db.session.commit()

    def list_for_month(self, month_id: int) -> list[MonthParticipant]:
        return MonthParticipant.query.filter_by(month_id=month_id).all()


class BillComponentRepository:
    def list_for_month(self, month_id: int) -> list[BillComponent]:
        return (
            BillComponent.query.filter_by(month_id=month_id)
            .order_by(BillComponent.position.asc(), BillComponent.id.asc())
            .all()
        )

    def add(
        self,
        month_id: int,
        name: str,
        amount: float,
        split_method: str = "equal",
        position: int | None = None,
        distribution=None
    ) -> BillComponent:
        comp = BillComponent(
            month_id=month_id,
            name=name.strip(),
            amount=float(amount),
            split_method=split_method
        )
        if position is not None:
            comp.position = position
        if distribution is not None:
            comp.distribution = distribution
        db.session.add(comp)
        db.session.commit()
        return comp

    def update(
        self,
        component_id: int,
        name: str | None = None,
        amount: float | None = None,
        split_method: str | None = None,
        position: int | None = None,
        distribution=None
    ) -> BillComponent:
        comp = db.session.get(BillComponent, component_id)
        if comp is None:
            from flask import abort
            abort(404)
        if name is not None:
            comp.name = name.strip()
        if amount is not None:
            comp.amount = float(amount)
        if split_method is not None:
            comp.split_method = split_method
        if position is not None:
            comp.position = position
        if distribution is not None:
            comp.distribution = distribution
        db.session.commit()
        return comp

    def delete(self, component_id: int) -> None:
        comp = db.session.get(BillComponent, component_id)
        if comp is None:
            from flask import abort
            abort(404)
        db.session.delete(comp)
        db.session.commit()


class ComponentAdjustmentRepository:
    def upsert(
        self,
        month_id: int,
        component_id: int,
        participant_id: int,
        zero: bool,
        redis_rule=None,
        notes: str = None
    ) -> ComponentAdjustment:
        adj = ComponentAdjustment.query.filter_by(
            month_id=month_id, component_id=component_id, participant_id=participant_id
        ).first()
        if adj is None:
            adj = ComponentAdjustment(
                month_id=month_id,
                component_id=component_id,
                participant_id=participant_id
            )
            db.session.add(adj)
        adj.zero = bool(zero)
        # Always set redis_rule; allow clearing by passing None
        adj.redis_rule = redis_rule
        # Set notes (can be None or empty string to clear)
        adj.notes = notes.strip() if notes else None
        db.session.commit()
        return adj

    def list_for_month(self, month_id: int) -> list[ComponentAdjustment]:
        return ComponentAdjustment.query.filter_by(month_id=month_id).all()

    def clear_for_month(self, month_id: int) -> None:
        ComponentAdjustment.query.filter_by(month_id=month_id).delete()
        db.session.commit()


class PhotoRepository:
    MAX_COMPONENT_PHOTOS = 2
    MAX_READING_PHOTOS = 1

    def get(self, photo_id: int) -> Optional[Photo]:
        return db.session.get(Photo, photo_id)

    def list_for(self, month_id: int, kind: str, ref_id: int) -> list[Photo]:
        return (
            Photo.query.filter_by(month_id=month_id, kind=kind, ref_id=ref_id)
            .order_by(Photo.position, Photo.id)
            .all()
        )

    def add(
        self,
        month_id: int,
        kind: str,
        ref_id: int,
        data: bytes,
        mime: str,
        width: int,
        height: int,
    ) -> Photo:
        existing = self.list_for(month_id, kind, ref_id)
        photo = Photo(
            month_id=month_id, kind=kind, ref_id=ref_id,
            position=(existing[-1].position + 1 if existing else 0),
            data=data, mime=mime, width=width, height=height, size_bytes=len(data),
        )
        db.session.add(photo)
        db.session.commit()
        return photo

    def replace_single(
        self,
        month_id: int,
        kind: str,
        ref_id: int,
        data: bytes,
        mime: str,
        width: int,
        height: int,
    ) -> Photo:
        """Upsert semantics for single-photo slots (meter reading photos)."""
        for old in self.list_for(month_id, kind, ref_id):
            db.session.delete(old)
        return self.add(month_id, kind, ref_id, data, mime, width, height)

    def delete(self, photo_id: int) -> bool:
        photo = self.get(photo_id)
        if photo is None:
            return False
        db.session.delete(photo)
        db.session.commit()
        return True

    def delete_for(self, month_id: int, kind: str, ref_id: int) -> None:
        Photo.query.filter_by(month_id=month_id, kind=kind, ref_id=ref_id).delete()
        db.session.commit()

    def delete_for_component(self, component_id: int) -> None:
        Photo.query.filter_by(kind=Photo.KIND_COMPONENT, ref_id=component_id).delete()
        db.session.commit()

    def ids_by_ref_for_month(self, month_id: int, kind: str) -> dict[int, list[int]]:
        """{ref_id: [photo_id, ...]} for a month/kind, without loading blobs."""
        rows = (
            db.session.query(Photo.ref_id, Photo.id)
            .filter_by(month_id=month_id, kind=kind)
            .order_by(Photo.position, Photo.id)
            .all()
        )
        out: dict[int, list[int]] = {}
        for ref_id, photo_id in rows:
            out.setdefault(ref_id, []).append(photo_id)
        return out

    def list_for_month(self, month_id: int) -> list[Photo]:
        return (
            Photo.query.filter_by(month_id=month_id)
            .order_by(Photo.kind, Photo.ref_id, Photo.position, Photo.id)
            .all()
        )


def migrate_component_images_to_photos() -> None:
    """One-time copy of the legacy component_images table into photos.

    Runs at startup and after a database restore, so backups taken while
    the old single-photo table existed keep their photos. Drops the legacy
    table once copied.
    """
    from sqlalchemy import inspect as sa_inspect, text

    try:
        if "component_images" not in sa_inspect(db.engine).get_table_names():
            return
        rows = db.session.execute(text(
            "SELECT component_id, mime, data, width, height FROM component_images"
        )).fetchall()
        for component_id, mime, data, width, height in rows:
            comp = db.session.get(BillComponent, component_id)
            if comp is None:
                continue
            already = Photo.query.filter_by(
                kind=Photo.KIND_COMPONENT, ref_id=component_id
            ).first()
            if already is not None:
                continue
            db.session.add(Photo(
                month_id=comp.month_id, kind=Photo.KIND_COMPONENT, ref_id=component_id,
                position=0, mime=mime, data=data, width=width, height=height,
                size_bytes=len(data),
            ))
        db.session.commit()
        db.session.execute(text("DROP TABLE component_images"))
        db.session.commit()
    except Exception:
        db.session.rollback()
