import unittest
from datetime import date

from ml.food_safety.hierarchy import (
    get_safety_tier,
    get_classification,
    get_all_food_classes,
)
from ml.food_safety.foodkeeper import (
    load_foodkeeper,
    get_recommendations,
    get_foodkeeper_selection,
    get_confirmed_storage_guidance,
)
from ml.food_safety.date_calculator import (
    calculate_end_date,
    calculate_date_range,
)


class TestFoodSafetyIntegration(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        # Load FoodKeeper data once for all integration tests.
        cls.records = load_foodkeeper()

    # -----------------------------------------------
    # Hierarchy tests
    # -----------------------------------------------

    def test_ground_beef_hierarchy(self):
        self.assertIsNotNone(get_safety_tier("ground_beef"))
        self.assertIsNotNone(get_classification("ground_beef"))

    def test_all_hierarchy_classes_exist(self):
        self.assertEqual(len(get_all_food_classes()), 38)

    # -----------------------------------------------
    # FoodKeeper lookup and confirmation tests
    # -----------------------------------------------

    def test_ground_beef_selects_single_candidate(self):
        selection = get_foodkeeper_selection(
            food_class="ground_beef",
            records=self.records
        )

        self.assertTrue(selection["ready_for_guidance"])
        self.assertIsNotNone(selection["selected_record"])
        self.assertEqual(
            str(selection["selected_record"]["ID"]).split(".")[0],
            "43"
        )

    def test_ground_beef_returns_confirmed_guidance(self):
        selection = get_foodkeeper_selection(
            food_class="ground_beef",
            records=self.records
        )

        guidance = get_confirmed_storage_guidance(selection)

        self.assertIn("dop_refrigerate", guidance)
        self.assertIn("dop_freeze", guidance)

    def test_shrimp_requires_confirmation(self):
        selection = get_foodkeeper_selection(
            food_class="shrimp",
            records=self.records
        )

        self.assertTrue(selection["requires_confirmation"])
        self.assertFalse(selection["ready_for_guidance"])
        self.assertIsNone(selection["selected_record"])

        candidate_ids = {
            str(record["ID"]).split(".")[0]
            for record in selection["candidates"]
        }

        self.assertIn("151", candidate_ids)
        self.assertIn("325", candidate_ids)

    def test_unconfirmed_shrimp_guidance_is_blocked(self):
        selection = get_foodkeeper_selection(
            food_class="shrimp",
            records=self.records,
            selected_product_id=151,
            user_confirmed=False
        )

        self.assertFalse(selection["ready_for_guidance"])

        with self.assertRaises(ValueError):
            get_confirmed_storage_guidance(selection)

    def test_confirmed_shrimp_returns_guidance(self):
        selection = get_foodkeeper_selection(
            food_class="shrimp",
            records=self.records,
            selected_product_id=151,
            user_confirmed=True
        )

        self.assertTrue(selection["ready_for_guidance"])

        guidance = get_confirmed_storage_guidance(selection)

        self.assertIn("dop_refrigerate", guidance)
        self.assertIn("dop_freeze", guidance)

    def test_invalid_foodkeeper_product_id_is_rejected(self):
        with self.assertRaises(ValueError):
            get_foodkeeper_selection(
                food_class="shrimp",
                records=self.records,
                selected_product_id=999999,
                user_confirmed=True
            )

    def test_unsupported_class_returns_no_candidates(self):
        candidates = get_recommendations(
            food_class="bell_pepper",
            records=self.records
        )

        self.assertEqual(candidates, [])

    def test_unsupported_class_cannot_provide_guidance(self):
        selection = get_foodkeeper_selection(
            food_class="bell_pepper",
            records=self.records
        )

        self.assertFalse(selection["ready_for_guidance"])
        self.assertIsNone(selection["selected_record"])

        with self.assertRaises(ValueError):
            get_confirmed_storage_guidance(selection)

    # -----------------------------------------------
    # Date calculator tests
    # -----------------------------------------------

    def test_ground_beef_date_calculation(self):
        start = date(2026, 11, 11)
        result = calculate_end_date(start, 2)

        self.assertEqual(result, date(2026, 11, 13))

    def test_date_range_calculation(self):
        start = date(2026, 11, 11)

        earliest, latest = calculate_date_range(
            start,
            1,
            2
        )

        self.assertEqual(earliest, date(2026, 11, 12))
        self.assertEqual(latest, date(2026, 11, 13))

    def test_invalid_duration_rejected(self):
        with self.assertRaises(ValueError):
            calculate_end_date(date(2026, 11, 11), -1)

    def test_invalid_date_range_rejected(self):
        with self.assertRaises(ValueError):
            calculate_date_range(date(2026, 11, 11), 5, 2)


if __name__ == "__main__":
    unittest.main(verbosity=2)
