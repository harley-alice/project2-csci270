
"""Small offline tests for the FoodKeeper integration utilities."""

from foodkeeper.ml.food_safety.foodkeeper import (
    search_foodkeeper,
    get_record_name,
    get_recommendations,
    get_foodkeeper_selection,
    get_confirmed_storage_guidance,
)
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


def test_unidentified_containers():
    """Verify jars and cans are blocked from FoodKeeper matches and storage guidance."""
    sample = [
        {"ID": 100, "Name": "Jam & Jelly", "Keywords": "jar,jam"},
        {"ID": 200, "Name": "Soda", "Keywords": "soda,can"},
    ]
    for container in ["jar", "soda_can"]:
        # Block recommendations
        matches = get_recommendations(food_class=container, records=sample)
        assert matches == [], f"Expected no recommendations for {container}"

        # Selection workflow requires confirmation and has no candidates
        selection = get_foodkeeper_selection(food_class=container, records=sample)
        assert selection["candidates"] == []
        assert selection["requires_confirmation"] is True
        assert selection["ready_for_guidance"] is False
        assert selection["selected_record"] is None

        # Cannot retrieve storage guidance
        try:
            get_confirmed_storage_guidance(selection)
            assert False, f"Expected get_confirmed_storage_guidance to raise for {container}"
        except ValueError:
            pass

    print("Unidentified containers test passed.")


if __name__ == "__main__":
    test_search_foodkeeper()
    test_date_calculator()
    test_unidentified_containers()

    print("\nAll FoodKeeper integration utility tests passed.")


# Tests ensuring containers are not treated as food items.

import pytest


@pytest.mark.parametrize("food_class", ["jar", "soda_can"])
def test_containers_have_no_foodkeeper_recommendations(food_class):
    from foodkeeper.ml.food_safety.foodkeeper import get_recommendations

    assert get_recommendations(food_class) == []


@pytest.mark.parametrize("food_class", ["jar", "soda_can"])
def test_containers_require_content_identification(food_class):
    from foodkeeper.ml.food_safety.foodkeeper import get_foodkeeper_selection

    selection = get_foodkeeper_selection(food_class)

    assert selection["candidates"] == []
    assert selection["requires_confirmation"] is True
    assert selection["selected_record"] is None
    assert selection["ready_for_guidance"] is False


@pytest.mark.parametrize("food_class", ["jar", "soda_can"])
def test_containers_cannot_receive_storage_guidance(food_class):
    from foodkeeper.ml.food_safety.foodkeeper import get_confirmed_storage_guidance

    selection = {
        "food_class": food_class,
        "ready_for_guidance": True,
        "selected_record": {"food_name": "Example"},
    }

    with pytest.raises(ValueError, match="unidentified container"):
        get_confirmed_storage_guidance(selection)

def test_milk_still_receives_foodkeeper_guidance(tmp_path):
    """Verify normal food items still receive storage guidance."""

    from foodkeeper.ml.food_safety.foodkeeper import (
        get_foodkeeper_selection,
        get_confirmed_storage_guidance,
    )

    # Create a temporary mapping for milk.
    mapping_path = tmp_path / "foodkeeper_mapping.yaml"
    mapping_path.write_text(
        "foods:\n"
        "  milk:\n"
        "    search_terms:\n"
        "      - milk\n",
        encoding="utf-8",
    )

    # Sample FoodKeeper milk record.
    sample = [
        {
            "ID": "27",
            "Name": "Milk",
            "Keywords": "Milk",
            "Refrigerate_Min": 7,
            "Refrigerate_Max": 10,
            "Refrigerate_Metric": "Days",
        }
    ]

    # Retrieve the milk selection.
    selection = get_foodkeeper_selection(
        food_class="milk",
        records=sample,
        mapping_path=mapping_path,
    )

    assert len(selection["candidates"]) == 1
    assert selection["ready_for_guidance"] is True
    assert selection["selected_record"]["Name"] == "Milk"

    # Confirm that storage guidance is still available.
    guidance = get_confirmed_storage_guidance(selection)

    assert "refrigerate" in guidance
    assert guidance["refrigerate"]["minimum"] == 7
    assert guidance["refrigerate"]["maximum"] == 10
    assert guidance["refrigerate"]["metric"] == "Days"

def test_milk_still_receives_foodkeeper_guidance(tmp_path):
    """Verify normal food items still receive storage guidance."""

    from foodkeeper.ml.food_safety.foodkeeper import (
        get_foodkeeper_selection,
        get_confirmed_storage_guidance,
    )

    # Create a temporary mapping for milk.
    mapping_path = tmp_path / "foodkeeper_mapping.yaml"
    mapping_path.write_text(
        "foods:\n"
        "  milk:\n"
        "    search_terms:\n"
        "      - milk\n",
        encoding="utf-8",
    )

    # Sample FoodKeeper milk record.
    sample = [
        {
            "ID": "27",
            "Name": "Milk",
            "Keywords": "Milk",
            "Refrigerate_Min": 7,
            "Refrigerate_Max": 10,
            "Refrigerate_Metric": "Days",
        }
    ]

    # Retrieve the milk selection.
    selection = get_foodkeeper_selection(
        food_class="milk",
        records=sample,
        mapping_path=mapping_path,
    )

    assert len(selection["candidates"]) == 1
    assert selection["ready_for_guidance"] is True
    assert selection["selected_record"]["Name"] == "Milk"

    # Confirm that storage guidance is still available.
    guidance = get_confirmed_storage_guidance(selection)

    assert "refrigerate" in guidance
    assert guidance["refrigerate"]["minimum"] == 7
    assert guidance["refrigerate"]["maximum"] == 10
    assert guidance["refrigerate"]["metric"] == "Days"
