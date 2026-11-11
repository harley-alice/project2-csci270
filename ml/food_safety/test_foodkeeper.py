"""Small offline tests for the FoodKeeper integration utilities."""

from ml.food_safety.foodkeeper import search_foodkeeper, get_record_name
from ml.food_safety.date_calculator import calculate_end_date, calculate_date_range
from datetime import date


def test_search_foodkeeper():
    sample = [
        {"Product": "Ground Beef", "Refrigerator": "1 to 2 days"},
        {"Product": "Chicken, whole", "Refrigerator": "1 to 2 days"},
        {"Product": "Milk", "Refrigerator": "5 to 7 days"},
    ]
    matches = search_foodkeeper(sample, "ground beef")
    assert len(matches) == 1
    assert get_record_name(matches[0]) == "Ground Beef"


def test_date_calculator():
    start = date(2026, 11, 8)
    assert calculate_end_date(start, 3) == date(2026, 11, 11)
    assert calculate_date_range(start, 3, 5) == (
        date(2026, 11, 11), date(2026, 11, 13)
    )


if __name__ == "__main__":
    test_search_foodkeeper()
    test_date_calculator()
    print("FoodKeeper integration utility tests passed.")
