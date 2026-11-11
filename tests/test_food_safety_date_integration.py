import unittest
from datetime import date

from ml.food_safety.foodkeeper import (
    load_foodkeeper,
    get_foodkeeper_selection,
)
from ml.food_safety.date_calculator import (
    calculate_confirmed_guidance_range,
)


class TestConfirmedGuidanceDates(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.records = load_foodkeeper()

    def get_cooked_shrimp_selection(self):
        return get_foodkeeper_selection(
            food_class="shrimp",
            records=self.records,
            selected_product_id=325,
            user_confirmed=True
        )

    def test_cooked_shrimp_calculates_date_range(self):
        selection = self.get_cooked_shrimp_selection()

        result = calculate_confirmed_guidance_range(
            selection=selection,
            storage_type="refrigerate",
            start_date=date(2026, 11, 11),
            start_event="cooking"
        )

        self.assertEqual(result["minimum_days"], 3)
        self.assertEqual(result["maximum_days"], 4)
        self.assertEqual(result["earliest_date"], date(2026, 11, 14))
        self.assertEqual(result["latest_date"], date(2026, 11, 15))
        self.assertEqual(result["start_event"], "cooking")

    def test_unconfirmed_selection_cannot_calculate_dates(self):
        selection = get_foodkeeper_selection(
            food_class="shrimp",
            records=self.records
        )

        with self.assertRaises(ValueError):
            calculate_confirmed_guidance_range(
                selection,
                "refrigerate",
                date(2026, 11, 11),
                "cooking"
            )

    def test_dop_recommendation_is_rejected(self):
        selection = get_foodkeeper_selection(
            food_class="ground_beef",
            records=self.records
        )

        with self.assertRaises(ValueError):
            calculate_confirmed_guidance_range(
                selection,
                "dop_refrigerate",
                date(2026, 11, 11),
                "purchase"
            )

    def test_month_based_recommendation_is_rejected(self):
        selection = {
            "food_class": "shrimp",
            "ready_for_guidance": True,
            "selected_record": {
                "Freeze_Min": 6,
                "Freeze_Max": 18,
                "Freeze_Metric": "Months"
            }
        }

        with self.assertRaises(ValueError):
            calculate_confirmed_guidance_range(
                selection,
                "freeze",
                date(2026, 11, 11),
                "purchase"
            )

    def test_cooking_recommendation_requires_cooking_date(self):
        selection = self.get_cooked_shrimp_selection()

        with self.assertRaises(ValueError):
            calculate_confirmed_guidance_range(
                selection,
                "refrigerate",
                date(2026, 11, 11),
                "purchase"
            )


if __name__ == "__main__":
    unittest.main(verbosity=2)
