"""
Wiring tests for POST /api/detect, the /detect alias and /api/health.

Uses the real model when ml/export/food_detector_v8n_baseline.pt exists; the missing-model tests patch
the service so they pass either way. Run from the repo root: python -m pytest tests/test_detect_wiring.py
"""
from __future__ import annotations

import io
import os
import tempfile
import unittest
from unittest import mock

from PIL import Image
from fastapi.testclient import TestClient

_db = tempfile.NamedTemporaryFile(suffix=".sqlite", delete=False)
_db.close()
os.environ["FRIDGE_DB_PATH"] = _db.name

from backend.database import get_db, init_db  # noqa: E402
from backend.foodkeeper_data import seed_database  # noqa: E402
from backend.inference import inference_service  # noqa: E402
from backend.main import app  # noqa: E402

MEAT = {"chicken", "beef", "shrimp", "bacon", "ham"}


def jpeg(size=(320, 240), color=(120, 90, 60)) -> bytes:
    buf = io.BytesIO()
    Image.new("RGB", size, color).save(buf, format="JPEG")
    return buf.getvalue()


class TestDetectWiring(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        init_db()
        with get_db() as conn:
            seed_database(conn)
        cls.client = TestClient(app)

    @classmethod
    def tearDownClass(cls):
        try:
            os.remove(_db.name)
        except OSError:
            pass

    # ---- missing model -> 503 and honest health
    def test_missing_model_returns_503_on_both_routes(self):
        with mock.patch.object(inference_service, "model", None):
            for path in ("/api/detect", "/detect"):
                with self.subTest(path=path):
                    r = self.client.post(path, files={"file": ("a.jpg", jpeg(), "image/jpeg")})
                    self.assertEqual(r.status_code, 503)
                    self.assertIn("Model weights not found", r.json()["detail"])
                    self.assertIn("model_export.zip", r.json()["detail"])

    def test_health_reports_not_loaded_when_model_missing(self):
        with mock.patch.object(inference_service, "model", None):
            h = self.client.get("/api/health").json()
        self.assertEqual(h["yolo_model"], "not_loaded")
        self.assertEqual(h["status"], "degraded")
        self.assertIn("food_detector_v8n_baseline.pt", h["weights_path"])

    def test_health_reports_loaded_only_when_model_object_exists(self):
        with mock.patch.object(inference_service, "model", object()):
            self.assertEqual(self.client.get("/api/health").json()["yolo_model"], "loaded")

    # ---- bad uploads give clean 4xx, never 500
    def test_empty_and_non_image_uploads_are_client_errors(self):
        with mock.patch.object(inference_service, "model", object()):
            empty = self.client.post("/api/detect", files={"file": ("a.jpg", b"", "image/jpeg")})
            self.assertEqual(empty.status_code, 400)
            bad = self.client.post("/api/detect", files={"file": ("a.txt", b"not an image", "text/plain")})
            self.assertEqual(bad.status_code, 422)
            self.assertEqual(self.client.post("/api/detect").status_code, 422)  # no file at all

    def test_confidence_threshold_bounds(self):
        for bad in (0.01, 1.5):
            r = self.client.post("/api/detect", params={"confidence_threshold": bad},
                                 files={"file": ("a.jpg", jpeg(), "image/jpeg")})
            self.assertEqual(r.status_code, 422)

    # ---- real model, if the weights are present
    @unittest.skipUnless(inference_service.model_loaded, "model weights not present")
    def test_detect_and_alias_return_the_same_valid_shape(self):
        for path in ("/api/detect", "/detect", "/api/infer"):
            with self.subTest(path=path):
                r = self.client.post(path, params={"confidence_threshold": 0.05} if path != "/api/infer" else {},
                                     files={"file": ("a.jpg", jpeg(), "image/jpeg")})
                self.assertEqual(r.status_code, 200)
                body = r.json()
                self.assertEqual(body["count"], len(body["detections"]))
                for d in body["detections"]:
                    ymin, xmin, ymax, xmax = d["bbox"]
                    self.assertTrue(0 <= ymin <= ymax <= 1 and 0 <= xmin <= xmax <= 1, d["bbox"])
                    self.assertIn("requires_confirmation", d)
                    if d["label"] in MEAT:
                        self.assertTrue(d["requires_confirmation"])


if __name__ == "__main__":
    unittest.main()
