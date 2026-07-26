"""Tests for month photos: component bill photos (max 2) and meter reading photos."""
import io
import sqlite3

import pytest
from PIL import Image

from app import create_app
from app.extensions import db
from app.models import BillComponent, MonthParticipant, MonthlyBill, Participant, Photo
from app.repositories import migrate_component_images_to_photos
from app.services.image_service import MAX_DIMENSION, ImageError, compress_image


@pytest.fixture
def img_app():
    app = create_app()
    app.config.update({
        "TESTING": True,
        "SQLALCHEMY_DATABASE_URI": "sqlite:///:memory:",
        "WTF_CSRF_ENABLED": False,
    })
    with app.app_context():
        db.create_all()
        yield app
        db.session.remove()
        db.drop_all()


@pytest.fixture
def img_client(img_app):
    return img_app.test_client()


@pytest.fixture
def month_with_component(img_app):
    alice = Participant(name="Alice")
    db.session.add(alice)
    db.session.flush()
    bill = MonthlyBill(year=2026, month=7, electricity_amount=0, water_amount=0, internet_amount=0)
    db.session.add(bill)
    db.session.flush()
    db.session.add(MonthParticipant(month_id=bill.id, participant_id=alice.id))
    comp = BillComponent(month_id=bill.id, name="Water", amount=500.0, split_method="equal")
    db.session.add(comp)
    db.session.commit()
    return bill, comp, alice


def make_photo_bytes(width=3000, height=2000) -> bytes:
    """A photo-like (noisy) high-quality JPEG, similar in weight to a camera shot."""
    import random

    rng = random.Random(42)
    noise = bytes(rng.getrandbits(8) for _ in range(64 * 64 * 3))
    tile = Image.frombytes("RGB", (64, 64), noise).resize((256, 256))
    img = Image.new("RGB", (width, height))
    for x in range(0, width, 256):
        for y in range(0, height, 256):
            img.paste(tile, (x, y))
    out = io.BytesIO()
    img.save(out, format="JPEG", quality=95)
    return out.getvalue()


def upload_component(client, bill, comp, payload, filename="bill.jpg"):
    return client.post(
        f"/months/{bill.id}/components/{comp.id}/photos",
        data={"photo": (io.BytesIO(payload), filename)},
        content_type="multipart/form-data",
    )


def upload_reading(client, bill, payload, filename="meter.jpg"):
    return client.post(
        f"/months/{bill.id}/reading-photo",
        data={"photo": (io.BytesIO(payload), filename)},
        content_type="multipart/form-data",
    )


def component_photos(comp):
    return Photo.query.filter_by(kind="component", ref_id=comp.id).order_by(Photo.position).all()


class TestCompressImage:
    def test_downscales_and_reencodes_as_smaller_jpeg(self):
        raw = make_photo_bytes(3000, 2000)
        data, width, height = compress_image(raw)
        assert (width, height) == (1600, 1067)
        assert len(data) < len(raw)
        assert Image.open(io.BytesIO(data)).format == "JPEG"

    def test_small_images_keep_their_size(self):
        raw = make_photo_bytes(640, 480)
        _, width, height = compress_image(raw)
        assert (width, height) == (640, 480)
        assert max(width, height) <= MAX_DIMENSION

    def test_transparency_is_flattened(self):
        img = Image.new("RGBA", (100, 100), (255, 0, 0, 0))
        out = io.BytesIO()
        img.save(out, format="PNG")
        data, _, _ = compress_image(out.getvalue())
        assert Image.open(io.BytesIO(data)).mode == "RGB"

    def test_accepts_heic(self):
        import pillow_heif

        img = Image.new("RGB", (1200, 900), (90, 120, 150))
        out = io.BytesIO()
        pillow_heif.register_heif_opener()
        img.save(out, format="HEIF", quality=90)
        data, width, height = compress_image(out.getvalue())
        assert (width, height) == (1200, 900)
        assert Image.open(io.BytesIO(data)).format == "JPEG"

    def test_rejects_non_image(self):
        with pytest.raises(ImageError):
            compress_image(b"definitely not an image")

    def test_rejects_empty(self):
        with pytest.raises(ImageError):
            compress_image(b"")


class TestComponentPhotoRoutes:
    def test_upload_stores_compressed_jpeg(self, img_client, month_with_component):
        bill, comp, _ = month_with_component
        raw = make_photo_bytes()
        resp = upload_component(img_client, bill, comp, raw)
        assert resp.status_code == 302

        [photo] = component_photos(comp)
        assert photo.mime == "image/jpeg"
        assert photo.size_bytes == len(photo.data) < len(raw)
        assert max(photo.width, photo.height) <= MAX_DIMENSION

    def test_two_photos_allowed_third_rejected(self, img_client, month_with_component):
        bill, comp, _ = month_with_component
        upload_component(img_client, bill, comp, make_photo_bytes(800, 600))
        upload_component(img_client, bill, comp, make_photo_bytes(640, 480))
        photos = component_photos(comp)
        assert len(photos) == 2
        assert [p.position for p in photos] == [0, 1]

        resp = upload_component(img_client, bill, comp, make_photo_bytes(320, 240),
                                filename="third.jpg")
        assert resp.status_code == 302
        assert len(component_photos(comp)) == 2  # third refused

    def test_view_serves_stored_photo(self, img_client, month_with_component):
        bill, comp, _ = month_with_component
        upload_component(img_client, bill, comp, make_photo_bytes())
        [photo] = component_photos(comp)
        resp = img_client.get(f"/months/{bill.id}/components/{comp.id}/photos/{photo.id}")
        assert resp.status_code == 200
        assert resp.mimetype == "image/jpeg"

    def test_view_404s_for_wrong_component(self, img_client, month_with_component):
        bill, comp, _ = month_with_component
        upload_component(img_client, bill, comp, make_photo_bytes())
        [photo] = component_photos(comp)
        other = BillComponent(month_id=bill.id, name="Gas", amount=100.0, split_method="equal")
        db.session.add(other)
        db.session.commit()
        assert img_client.get(
            f"/months/{bill.id}/components/{other.id}/photos/{photo.id}"
        ).status_code == 404

    def test_delete_removes_single_photo(self, img_client, month_with_component):
        bill, comp, _ = month_with_component
        upload_component(img_client, bill, comp, make_photo_bytes(800, 600))
        upload_component(img_client, bill, comp, make_photo_bytes(640, 480))
        first, second = component_photos(comp)
        img_client.post(f"/months/{bill.id}/components/{comp.id}/photos/{first.id}/delete")
        remaining = component_photos(comp)
        assert [p.id for p in remaining] == [second.id]

    def test_upload_rejected_when_archived(self, img_client, month_with_component):
        bill, comp, _ = month_with_component
        bill.archived = True
        db.session.commit()
        upload_component(img_client, bill, comp, make_photo_bytes())
        assert component_photos(comp) == []

    def test_non_image_upload_stores_nothing(self, img_client, month_with_component):
        bill, comp, _ = month_with_component
        upload_component(img_client, bill, comp, b"not an image", filename="bill.txt")
        assert component_photos(comp) == []

    def test_deleting_component_removes_its_photos(self, img_client, month_with_component):
        bill, comp, _ = month_with_component
        upload_component(img_client, bill, comp, make_photo_bytes())
        img_client.post(f"/months/{bill.id}/components/{comp.id}/delete")
        assert Photo.query.count() == 0


class TestReadingPhotoRoutes:
    def test_upload_and_serve(self, img_client, month_with_component):
        bill, _, _ = month_with_component
        raw = make_photo_bytes(3000, 2000)
        resp = upload_reading(img_client, bill, raw)
        assert resp.status_code == 302
        # stored downscaled and recompressed, never the raw upload
        [photo] = Photo.query.filter_by(kind="reading", month_id=bill.id).all()
        assert max(photo.width, photo.height) <= MAX_DIMENSION
        assert photo.size_bytes < len(raw)
        resp = img_client.get(f"/months/{bill.id}/reading-photo")
        assert resp.status_code == 200
        assert resp.mimetype == "image/jpeg"

    def test_reupload_replaces_single_photo(self, img_client, month_with_component):
        bill, _, _ = month_with_component
        upload_reading(img_client, bill, make_photo_bytes(800, 600))
        upload_reading(img_client, bill, make_photo_bytes(640, 480))
        photos = Photo.query.filter_by(kind="reading", month_id=bill.id).all()
        assert len(photos) == 1
        assert (photos[0].width, photos[0].height) == (640, 480)

    def test_upload_rejected_when_archived(self, img_client, month_with_component):
        bill, _, _ = month_with_component
        bill.archived = True
        db.session.commit()
        upload_reading(img_client, bill, make_photo_bytes())
        assert Photo.query.filter_by(kind="reading", month_id=bill.id).count() == 0

    def test_delete_removes_photo(self, img_client, month_with_component):
        bill, _, _ = month_with_component
        upload_reading(img_client, bill, make_photo_bytes())
        img_client.post(f"/months/{bill.id}/reading-photo/delete")
        assert img_client.get(f"/months/{bill.id}/reading-photo").status_code == 404

    def test_deleting_month_removes_photos(self, img_client, month_with_component):
        bill, comp, _ = month_with_component
        upload_component(img_client, bill, comp, make_photo_bytes())
        upload_reading(img_client, bill, make_photo_bytes())
        img_client.post(f"/months/{bill.id}/delete")
        assert Photo.query.count() == 0


class TestLegacyMigration:
    def test_component_images_rows_move_to_photos(self, img_app, month_with_component):
        bill, comp, _ = month_with_component
        data, w, h = compress_image(make_photo_bytes(640, 480))
        # simulate the pre-photos schema alongside current tables
        raw = sqlite3.connect(":memory:")  # placeholder to satisfy lint
        raw.close()
        db.session.execute(db.text(
            "CREATE TABLE component_images (id INTEGER PRIMARY KEY, component_id INTEGER, "
            "mime VARCHAR(32), data BLOB, width INTEGER, height INTEGER, size_bytes INTEGER, "
            "created_at DATE)"
        ))
        db.session.execute(
            db.text("INSERT INTO component_images (component_id, mime, data, width, height, size_bytes) "
                    "VALUES (:cid, 'image/jpeg', :data, :w, :h, :size)"),
            {"cid": comp.id, "data": data, "w": w, "h": h, "size": len(data)},
        )
        db.session.commit()

        migrate_component_images_to_photos()

        photos = component_photos(comp)
        assert len(photos) == 1
        assert photos[0].month_id == bill.id
        assert photos[0].width == w
        # legacy table dropped afterwards
        from sqlalchemy import inspect as sa_inspect
        assert "component_images" not in sa_inspect(db.engine).get_table_names()
