"""Tests for optional bill photos on components (upload, compress, serve, delete)."""
import io

import pytest
from PIL import Image

from app import create_app
from app.extensions import db
from app.models import BillComponent, ComponentImage, MonthlyBill
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
    bill = MonthlyBill(year=2026, month=7, electricity_amount=0, water_amount=0, internet_amount=0)
    db.session.add(bill)
    db.session.flush()
    comp = BillComponent(month_id=bill.id, name="Water", amount=500.0, split_method="equal")
    db.session.add(comp)
    db.session.commit()
    return bill, comp


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


def upload(client, bill, comp, payload, filename="bill.jpg"):
    return client.post(
        f"/months/{bill.id}/components/{comp.id}/image",
        data={"photo": (io.BytesIO(payload), filename)},
        content_type="multipart/form-data",
    )


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

    def test_rejects_non_image(self):
        with pytest.raises(ImageError):
            compress_image(b"definitely not an image")

    def test_rejects_empty(self):
        with pytest.raises(ImageError):
            compress_image(b"")


class TestImageRoutes:
    def test_upload_stores_compressed_jpeg(self, img_client, month_with_component):
        bill, comp = month_with_component
        raw = make_photo_bytes()
        resp = upload(img_client, bill, comp, raw)
        assert resp.status_code == 302

        img = ComponentImage.query.filter_by(component_id=comp.id).one()
        assert img.mime == "image/jpeg"
        assert img.size_bytes == len(img.data)
        assert img.size_bytes < len(raw)
        assert max(img.width, img.height) <= MAX_DIMENSION

    def test_view_serves_stored_image(self, img_client, month_with_component):
        bill, comp = month_with_component
        upload(img_client, bill, comp, make_photo_bytes())
        resp = img_client.get(f"/months/{bill.id}/components/{comp.id}/image")
        assert resp.status_code == 200
        assert resp.mimetype == "image/jpeg"
        assert Image.open(io.BytesIO(resp.data)).format == "JPEG"

    def test_view_404s_without_image(self, img_client, month_with_component):
        bill, comp = month_with_component
        assert img_client.get(f"/months/{bill.id}/components/{comp.id}/image").status_code == 404

    def test_reupload_replaces_single_row(self, img_client, month_with_component):
        bill, comp = month_with_component
        upload(img_client, bill, comp, make_photo_bytes(3000, 2000))
        upload(img_client, bill, comp, make_photo_bytes(800, 600))
        images = ComponentImage.query.filter_by(component_id=comp.id).all()
        assert len(images) == 1
        assert (images[0].width, images[0].height) == (800, 600)

    def test_delete_removes_image(self, img_client, month_with_component):
        bill, comp = month_with_component
        upload(img_client, bill, comp, make_photo_bytes())
        resp = img_client.post(f"/months/{bill.id}/components/{comp.id}/image/delete")
        assert resp.status_code == 302
        assert ComponentImage.query.filter_by(component_id=comp.id).count() == 0

    def test_upload_rejected_when_archived(self, img_client, month_with_component):
        bill, comp = month_with_component
        bill.archived = True
        db.session.commit()
        upload(img_client, bill, comp, make_photo_bytes())
        assert ComponentImage.query.filter_by(component_id=comp.id).count() == 0

    def test_non_image_upload_stores_nothing(self, img_client, month_with_component):
        bill, comp = month_with_component
        upload(img_client, bill, comp, b"not an image", filename="bill.txt")
        assert ComponentImage.query.filter_by(component_id=comp.id).count() == 0

    def test_component_month_mismatch_404s(self, img_client, month_with_component):
        bill, comp = month_with_component
        other = MonthlyBill(year=2026, month=8, electricity_amount=0, water_amount=0, internet_amount=0)
        db.session.add(other)
        db.session.commit()
        assert img_client.get(f"/months/{other.id}/components/{comp.id}/image").status_code == 404

    def test_deleting_component_cascades_image(self, img_client, month_with_component):
        bill, comp = month_with_component
        upload(img_client, bill, comp, make_photo_bytes())
        img_client.post(f"/months/{bill.id}/components/{comp.id}/delete")
        assert ComponentImage.query.count() == 0
