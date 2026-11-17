"""
EXIF orientation handling for uploaded photos (backend/inference.py).

Phone photos store rotation in EXIF metadata. process_raw_image() must return the upright image,
survive missing or broken EXIF, and predict() must normalize boxes to the ROTATED image size.
Run from the repo root: python -m pytest tests/test_exif_orientation.py
"""
from __future__ import annotations

import io
import os
import tempfile
import unittest
from unittest import mock

from PIL import Image

# Same temp-database setup as tests/test_detect_wiring.py (predict() queries the rule database)
_db = tempfile.NamedTemporaryFile(suffix=".sqlite", delete=False)
_db.close()
os.environ["FRIDGE_DB_PATH"] = _db.name

from backend import inference as inference_module  # noqa: E402
from backend.database import get_db, init_db  # noqa: E402
from backend.foodkeeper_data import seed_database  # noqa: E402
from backend.inference import inference_service  # noqa: E402

W, H = 200, 100  # stored (landscape) size; left half red, right half blue
RED, BLUE = (230, 20, 20), (20, 20, 230)


def stored_image() -> Image.Image:
    img = Image.new("RGB", (W, H), BLUE)
    img.paste(Image.new("RGB", (W // 2, H), RED), (0, 0))
    return img


def jpeg_with_orientation(orientation: int | None) -> bytes:
    img = stored_image()
    buf = io.BytesIO()
    if orientation is None:
        img.save(buf, format="JPEG", quality=95)
    else:
        exif = Image.Exif()
        exif[0x0112] = orientation
        img.save(buf, format="JPEG", quality=95, exif=exif.tobytes())
    return buf.getvalue()


def jpeg_with_corrupt_exif() -> bytes:
    buf = io.BytesIO()
    stored_image().save(buf, format="JPEG", quality=95, exif=b"Exif\x00\x00MM\x00*\xff\xff\xff\xff\x00garbage")
    return buf.getvalue()


def close(px, target, tol=60):
    return all(abs(a - b) <= tol for a, b in zip(px, target))


class _Tensor:
    def __init__(self, v):
        self._v = v

    def item(self):
        return self._v


class _Box:
    def __init__(self, cls_id, conf, xyxy):
        self.cls, self.conf, self.xyxy = _Tensor(cls_id), _Tensor(conf), [_List(xyxy)]


class _List:
    def __init__(self, v):
        self._v = v

    def tolist(self):
        return list(self._v)


class _StubModel:
    """Records the image it is given and returns one fixed box in that image's pixel space."""

    names = {0: "apple"}

    def __init__(self, xyxy):
        self.xyxy = xyxy
        self.seen_size = None

    def predict(self, source, **kwargs):
        self.seen_size = source.size
        result = mock.Mock()
        result.boxes = [_Box(0, 0.9, self.xyxy)]
        return [result]


class TestProcessRawImage(unittest.TestCase):
    def test_orientation_6_rotates_90_and_swaps_dimensions(self):
        img = inference_service.process_raw_image(jpeg_with_orientation(6))
        self.assertEqual(img.size, (H, W))
        # stored-left (red) ends up at the top after rotating 90 degrees clockwise
        self.assertTrue(close(img.getpixel((H // 2, 20)), RED))
        self.assertTrue(close(img.getpixel((H // 2, W - 20)), BLUE))

    def test_orientation_8_rotates_90_and_swaps_dimensions(self):
        img = inference_service.process_raw_image(jpeg_with_orientation(8))
        self.assertEqual(img.size, (H, W))
        # stored-left (red) ends up at the bottom after rotating 90 degrees counter-clockwise
        self.assertTrue(close(img.getpixel((H // 2, W - 20)), RED))
        self.assertTrue(close(img.getpixel((H // 2, 20)), BLUE))

    def test_orientation_3_keeps_dimensions_and_flips_180(self):
        img = inference_service.process_raw_image(jpeg_with_orientation(3))
        self.assertEqual(img.size, (W, H))
        self.assertTrue(close(img.getpixel((W - 20, H // 2)), RED))  # red moved to the right
        self.assertTrue(close(img.getpixel((20, H // 2)), BLUE))

    def test_no_exif_is_unchanged(self):
        img = inference_service.process_raw_image(jpeg_with_orientation(None))
        self.assertEqual(img.size, (W, H))
        self.assertTrue(close(img.getpixel((20, H // 2)), RED))
        self.assertEqual(img.mode, "RGB")

    def test_orientation_1_is_unchanged(self):
        self.assertEqual(inference_service.process_raw_image(jpeg_with_orientation(1)).size, (W, H))

    def test_corrupted_exif_does_not_crash(self):
        img = inference_service.process_raw_image(jpeg_with_corrupt_exif())
        self.assertEqual(img.size, (W, H))
        self.assertEqual(img.mode, "RGB")

    def test_exif_transpose_failure_falls_back_to_unrotated_image(self):
        with mock.patch.object(inference_module.ImageOps, "exif_transpose", side_effect=ValueError("bad exif")):
            img = inference_service.process_raw_image(jpeg_with_orientation(6))
        self.assertEqual(img.size, (W, H))  # not rotated, but no exception

    def test_non_image_bytes_still_raise_value_error(self):
        with self.assertRaises(ValueError):
            inference_service.process_raw_image(b"not an image")
        with self.assertRaises(ValueError):
            inference_service.process_raw_image(b"")


class TestPredictNormalizesToRotatedImage(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        init_db()
        with get_db() as conn:
            seed_database(conn)

    @classmethod
    def tearDownClass(cls):
        try:
            os.remove(_db.name)
        except OSError:
            pass

    def test_boxes_use_rotated_dimensions(self):
        # Orientation 6: stored 200x100 becomes 100 wide x 200 high. Box in the model's (rotated) pixels.
        stub = _StubModel([10, 20, 60, 120])
        with mock.patch.object(inference_service, "model", stub):
            dets = inference_service.predict(jpeg_with_orientation(6))
        self.assertEqual(stub.seen_size, (H, W))  # the model received the upright image
        self.assertEqual(len(dets), 1)
        ymin, xmin, ymax, xmax = dets[0]["bbox"]
        self.assertAlmostEqual(ymin, 20 / W, places=4)   # divided by rotated height (200)
        self.assertAlmostEqual(xmin, 10 / H, places=4)   # divided by rotated width (100)
        self.assertAlmostEqual(ymax, 120 / W, places=4)
        self.assertAlmostEqual(xmax, 60 / H, places=4)
        for v in dets[0]["bbox"]:
            self.assertTrue(0.0 <= v <= 1.0)

    def test_unrotated_image_still_normalizes_by_stored_size(self):
        stub = _StubModel([10, 20, 60, 80])
        with mock.patch.object(inference_service, "model", stub):
            dets = inference_service.predict(jpeg_with_orientation(None))
        self.assertEqual(stub.seen_size, (W, H))
        ymin, xmin, ymax, xmax = dets[0]["bbox"]
        self.assertAlmostEqual(ymin, 20 / H, places=4)
        self.assertAlmostEqual(xmax, 60 / W, places=4)


if __name__ == "__main__":
    unittest.main()
