"""
End-to-end unit and integration test suite for Fridge Tracker backend:
  1. FastAPI model inference & tensor processing
  2. Hybrid AI Rule Engine (opened vs sealed dynamic windows, tier prioritization)
  3. SQLite schema integrity (inventory_items, food_categories, storage_rules)
  4. CRUD inventory endpoints
  5. Item verification endpoint with dynamic recalculation
  6. Storage duration update endpoint
  7. Model feedback telemetry
"""

from __future__ import annotations

import io
import os
import tempfile
import unittest
from datetime import date
from PIL import Image
from fastapi.testclient import TestClient

# Use temporary database for test isolation
temp_db = tempfile.NamedTemporaryFile(suffix=".sqlite", delete=False)
temp_db.close()
os.environ["FRIDGE_DB_PATH"] = temp_db.name

from backend.database import get_db, init_db
from backend.foodkeeper_data import seed_database
from backend.inference import ModelNotLoadedError, inference_service
from backend.main import app
from backend.rule_engine import rule_engine


class TestFridgeTrackerBackend(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        init_db()
        with get_db() as conn:
            seed_database(conn)
        cls.client = TestClient(app)

    @classmethod
    def tearDownClass(cls):
        if os.path.exists(temp_db.name):
            try:
                os.remove(temp_db.name)
            except OSError:
                pass

    def test_01_schema_tables_exist(self):
        """Verify SQLite tables: inventory_items, food_categories, storage_rules, model_feedback."""
        with get_db() as conn:
            cursor = conn.execute(
                "SELECT name FROM sqlite_master WHERE type='table' ORDER BY name;"
            )
            tables = {row["name"] for row in cursor.fetchall()}
            self.assertIn("food_categories", tables)
            self.assertIn("storage_rules", tables)
            self.assertIn("inventory_items", tables)
            self.assertIn("model_feedback", tables)

    def test_02_hybrid_rule_engine_package_state_dynamics(self):
        """
        Verify dynamic expiration calculation based on package state (opened vs. sealed)
        for high safety (ground_beef), dairy (milk), and produce (apple).
        """
        # 1. Ground Beef: Tier 1 high risk
        gb_sealed = rule_engine.calculate_expiration("ground_beef", package_state="sealed")
        gb_opened = rule_engine.calculate_expiration("ground_beef", package_state="opened")

        self.assertEqual(gb_sealed["safety_tier"], "tier_1")
        self.assertTrue(gb_sealed["is_high_risk"])
        self.assertEqual(gb_sealed["recommended_shelf_life_days"], 2)
        self.assertEqual(gb_opened["recommended_shelf_life_days"], 1)
        self.assertTrue(gb_opened["is_urgent"])

        # 2. Milk: Tier 2 refrigeration-sensitive
        milk_sealed = rule_engine.calculate_expiration("milk", package_state="sealed")
        milk_opened = rule_engine.calculate_expiration("milk", package_state="opened")

        self.assertEqual(milk_sealed["safety_tier"], "tier_2")
        self.assertEqual(milk_sealed["recommended_shelf_life_days"], 7)
        self.assertEqual(milk_opened["recommended_shelf_life_days"], 5)
        self.assertLess(milk_opened["expiration_date"], milk_sealed["expiration_date"])

        # 3. Jar: Special container requiring user confirmation
        jar_rule = rule_engine.calculate_expiration("jar", package_state="sealed")
        self.assertTrue(jar_rule["is_container"])
        self.assertTrue(jar_rule["requires_user_detail"])

    def test_03_inference_raw_image_to_tensor(self):
        """Test raw image upload processing, tensor transformation, and inference pipeline."""
        img = Image.new("RGB", (320, 320), color=(200, 100, 50))
        buf = io.BytesIO()
        img.save(buf, format="JPEG")
        raw_bytes = buf.getvalue()

        processed_pil = inference_service.process_raw_image(raw_bytes)
        self.assertEqual(processed_pil.size, (320, 320))

        # Empty bytes error handling
        with self.assertRaises(ValueError):
            inference_service.process_raw_image(b"")

        # Predict call (without weights the service now fails loudly instead of returning [])
        if inference_service.model_loaded:
            detections = inference_service.predict(raw_bytes, confidence_threshold=0.5)
            self.assertIsInstance(detections, list)
        else:
            with self.assertRaises(ModelNotLoadedError):
                inference_service.predict(raw_bytes, confidence_threshold=0.5)

    def test_04_fastapi_detect_endpoint(self):
        """Test POST /api/detect with simulated image upload."""
        img = Image.new("RGB", (400, 400), color=(50, 150, 200))
        buf = io.BytesIO()
        img.save(buf, format="JPEG")
        buf.seek(0)

        response = self.client.post(
            "/api/detect",
            files={"file": ("fridge.jpg", buf, "image/jpeg")},
            params={"confidence_threshold": 0.20, "package_state": "sealed"},
        )
        if not inference_service.model_loaded:
            self.assertEqual(response.status_code, 503)
            return
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertTrue(data["success"])
        self.assertIn("detections", data)
        self.assertEqual(data["confidence_threshold"], 0.20)

    def test_05_inventory_crud_lifecycle(self):
        """Test complete inventory CRUD cycle: create, read, update, delete."""
        # 1. Create item
        payload = {
            "food_class": "chicken",
            "custom_name": "Organic Chicken Breasts",
            "package_state": "sealed",
            "storage_location": "refrigerator",
            "is_cooked": False,
            "confidence": 0.95,
            "bbox": [0.1, 0.2, 0.5, 0.6],
        }
        create_res = self.client.post("/api/inventory", json=payload)
        self.assertEqual(create_res.status_code, 201)
        item = create_res.json()
        item_id = item["id"]
        self.assertEqual(item["food_class"], "chicken")
        self.assertEqual(item["shelf_life_days"], 2)  # USDA 1-2 days raw chicken
        self.assertEqual(item["safety_tier"], "tier_1")
        self.assertTrue(item["is_urgent"])

        # 2. Get item
        get_res = self.client.get(f"/api/inventory/{item_id}")
        self.assertEqual(get_res.status_code, 200)
        self.assertEqual(get_res.json()["custom_name"], "Organic Chicken Breasts")

        # 3. List inventory
        list_res = self.client.get("/api/inventory")
        self.assertEqual(list_res.status_code, 200)
        self.assertTrue(any(i["id"] == item_id for i in list_res.json()))

        # 4. Update item
        update_payload = {"custom_name": "Marinated Chicken Breasts"}
        update_res = self.client.put(f"/api/inventory/{item_id}", json=update_payload)
        self.assertEqual(update_res.status_code, 200)
        self.assertEqual(update_res.json()["custom_name"], "Marinated Chicken Breasts")

        # 5. Delete item
        del_res = self.client.delete(f"/api/inventory/{item_id}")
        self.assertEqual(del_res.status_code, 200)
        self.assertTrue(del_res.json()["success"])

        # 6. Verify 404 after deletion
        get_after_del = self.client.get(f"/api/inventory/{item_id}")
        self.assertEqual(get_after_del.status_code, 404)

    def test_06_item_verification_endpoint(self):
        """
        Test user confirmation and correction via /api/inventory/{id}/verify:
        Verify AI detected 'beef' corrected to 'ground_beef' dynamically updates expiration.
        """
        # Create item with generic 'beef'
        create_res = self.client.post(
            "/api/inventory",
            json={"food_class": "beef", "package_state": "sealed", "confidence": 0.88},
        )
        item = create_res.json()
        item_id = item["id"]
        self.assertEqual(item["shelf_life_days"], 4)  # Steaks/roasts 3-5 days

        # User confirms item is actually ground_beef
        verify_res = self.client.post(
            f"/api/inventory/{item_id}/verify",
            json={
                "confirmed_food_class": "ground_beef",
                "package_state": "opened",
                "user_notes": "Opened 80/20 ground chuck",
            },
        )
        self.assertEqual(verify_res.status_code, 200)
        verified_item = verify_res.json()
        self.assertEqual(verified_item["food_class"], "ground_beef")
        self.assertEqual(verified_item["package_state"], "opened")
        self.assertTrue(verified_item["verified"])
        self.assertEqual(verified_item["shelf_life_days"], 1)  # Opened ground beef: 1 day
        self.assertTrue(verified_item["is_urgent"])

        # Verify model_feedback table recorded correction
        with get_db() as conn:
            cur = conn.execute(
                "SELECT * FROM model_feedback WHERE detection_id = ?;", (item_id,)
            )
            fb = cur.fetchone()
            self.assertIsNotNone(fb)
            self.assertEqual(fb["predicted_label"], "beef")
            self.assertEqual(fb["corrected_label"], "ground_beef")

    def test_07_storage_duration_update_endpoint(self):
        """
        Test dynamic storage duration updates (/api/inventory/{id}/storage-duration):
        Toggling package_state from sealed -> opened or moving to freezer.
        """
        # Create sealed milk
        create_res = self.client.post(
            "/api/inventory",
            json={"food_class": "milk", "package_state": "sealed"},
        )
        item_id = create_res.json()["id"]
        self.assertEqual(create_res.json()["shelf_life_days"], 7)

        # Mark as opened
        opened_res = self.client.patch(
            f"/api/inventory/{item_id}/duration",
            json={"package_state": "opened"},
        )
        self.assertEqual(opened_res.status_code, 200)
        self.assertEqual(opened_res.json()["package_state"], "opened")
        self.assertEqual(opened_res.json()["shelf_life_days"], 5)

        # Move to freezer
        freezer_res = self.client.put(
            f"/api/inventory/{item_id}/storage-duration",
            json={"storage_location": "freezer"},
        )
        self.assertEqual(freezer_res.status_code, 200)
        self.assertEqual(freezer_res.json()["storage_location"], "freezer")
        self.assertEqual(freezer_res.json()["shelf_life_days"], 90)  # Frozen milk 3 months

    def test_08_model_feedback_endpoint(self):
        """Test POST /api/feedback from frontend review."""
        fb_payload = {
            "timestamp": date.today().isoformat(),
            "type": "user_correction",
            "image_source": "upload",
            "detection_id": "test_det_1",
            "predicted_label": "egg",
            "corrected_label": "lemon",
            "confidence": 0.62,
            "bbox": [0.1, 0.1, 0.3, 0.3],
        }
        res = self.client.post("/api/feedback", json=fb_payload)
        self.assertEqual(res.status_code, 201)
        self.assertTrue(res.json()["success"])


if __name__ == "__main__":
    unittest.main()
