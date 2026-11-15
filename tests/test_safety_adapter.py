"""
Tests for backend/safety_adapter.py (the bridge to Ashton's ml/food_safety package).

The real FoodKeeper JSON (data/raw/foodkeeper.json) is gitignored, so these tests use small synthetic
records and pass them in explicitly. Run from the repo root: python -m pytest tests/test_safety_adapter.py
"""
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from backend import safety_adapter  # noqa: E402
from backend.safety_adapter import MEAT_CLASSES, assess  # noqa: E402

# Product IDs match ml/configs/foodkeeper_mapping.yaml (butter: [1], chicken: [113, 116, 117, 118]).
RECORDS = [
    {"ID": 1, "Name": "Butter", "Refrigerate_Min": 30, "Refrigerate_Max": 90, "Refrigerate_Metric": "Days",
     "Refrigerate_After_Opening_Min": 14, "Refrigerate_After_Opening_Max": 30, "Refrigerate_After_Opening_Metric": "Days"},
    {"ID": 113, "Name": "Chicken, whole", "Refrigerate_Min": 1, "Refrigerate_Max": 2, "Refrigerate_Metric": "Days"},
    {"ID": 116, "Name": "Chicken, bone-in", "Refrigerate_Min": 1, "Refrigerate_Max": 2, "Refrigerate_Metric": "Days"},
]


class TestSafetyAdapter(unittest.TestCase):
    def test_meat_always_requires_confirmation_with_and_without_data(self):
        for cls in MEAT_CLASSES:
            for records in (None, RECORDS):
                with self.subTest(cls=cls, data=records is not None):
                    r = assess(cls, records=records) if records else assess(cls)
                    self.assertTrue(r["requires_confirmation"])
                    self.assertIsNone(r["days"])

    def test_tiers_come_from_ashtons_hierarchy(self):
        self.assertEqual(assess("chicken", records=RECORDS)["safety_tier"], "tier_1")
        self.assertEqual(assess("milk", records=RECORDS)["safety_tier"], "tier_2")
        self.assertEqual(assess("apple", records=RECORDS)["safety_tier"], "tier_3")

    def test_jar_is_a_special_category_that_needs_confirmation(self):
        r = assess("jar", records=RECORDS)
        self.assertTrue(r["requires_confirmation"])
        self.assertIs(r["guidance_supported"], False)
        self.assertIsNone(r["days"])

    def test_unknown_class_is_unsupported_and_unclassified(self):
        r = assess("not_a_food", records=RECORDS)
        self.assertEqual(r["safety_tier"], "unclassified")
        self.assertTrue(r["requires_confirmation"])
        self.assertIsNone(r["days"])

    def test_class_without_approved_foodkeeper_product_gives_no_days(self):
        r = assess("cream", records=RECORDS)  # mapping has no product ids
        self.assertTrue(r["requires_confirmation"])
        self.assertIs(r["guidance_supported"], False)
        self.assertIsNone(r["days"])

    def test_confirmed_single_product_class_gets_days_from_her_calculator(self):
        r = assess("butter", records=RECORDS)  # one product, requires_user_detail: false -> ready
        self.assertFalse(r["requires_confirmation"])
        self.assertEqual((r["days"], r["days_min"], r["days_max"]), (30, 30, 90))
        opened = assess("butter", package_state="opened", records=RECORDS)
        self.assertEqual((opened["days_min"], opened["days_max"]), (14, 30))

    def test_missing_data_file_is_conservative(self):
        saved = dict(safety_adapter._records_cache)
        try:
            safety_adapter._records_cache.update(loaded=True, records=None)
            r = assess("butter")
            self.assertTrue(r["requires_confirmation"])
            self.assertIsNone(r["days"])
            self.assertEqual(safety_adapter.foodkeeper_status()["foodkeeper_data"], "not_loaded")
        finally:
            safety_adapter._records_cache.update(saved)


if __name__ == "__main__":
    unittest.main()
