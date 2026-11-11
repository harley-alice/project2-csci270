
"""Small offline tests for the FoodKeeper integration utilities."""

from ml.food_safety.foodkeeper import search_foodkeeper, get_record_name
from ml.food_safety.date_calculator import calculate_end_date, calculate_date_range
from datetime import date


def test_search_foodkeeper():
    sample = [
        {
            "ID": 43,
            "Name": "Beef",
            "Name_subtitle": None,
            "Keywords": "Beef,ground"
        },
        {
            "ID": 113,
            "Name": "Chicken",
            "Name_subtitle": "Whole",
            "Keywords": "Chicken,whole"
        },
        {
            "ID": 27,
            "Name": "Milk",
            "Name_subtitle": None,
            "Keywords": "Milk"
        },
    ]

    matches = search_foodkeeper(sample, "ground beef")

    assert len(matches) == 1
    assert matches[0]["ID"] == 43
    assert get_record_name(matches[0]) == "Beef"

    print("FoodKeeper search test passed.")


def test_date_calculator():
    start = date(2026, 11, 8)

    assert calculate_end_date(start, 3) == date(2026, 11, 11)

    assert calculate_date_range(start, 3, 5) == (
        date(2026, 11, 11),
        date(2026, 11, 13)
    )

    print("Date calculator test passed.")


if __name__ == "__main__":
    test_search_foodkeeper()
    test_date_calculator()

    print("\nAll FoodKeeper integration utility tests passed.")
