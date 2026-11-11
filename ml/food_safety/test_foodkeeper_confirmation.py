
from ml.food_safety.foodkeeper import (
    load_foodkeeper,
    get_recommendations,
    get_foodkeeper_selection,
    get_confirmed_storage_guidance,
)

# Load the USDA FoodKeeper dataset.
records = load_foodkeeper()


# TEST 1: Shrimp should return multiple possible products.
shrimp_candidates = get_recommendations(
    food_class="shrimp",
    records=records
)

shrimp_ids = {
    str(record["ID"]).split(".")[0]
    for record in shrimp_candidates
}

assert "151" in shrimp_ids, "Shrimp Product ID 151 missing."
assert "325" in shrimp_ids, "Shrimp Product ID 325 missing."

print("PASS: Shrimp returns expected FoodKeeper candidates.")


# TEST 2: Shrimp should not be ready without confirmation.
shrimp_selection = get_foodkeeper_selection(
    food_class="shrimp",
    records=records
)

assert shrimp_selection["requires_confirmation"] is True
assert shrimp_selection["ready_for_guidance"] is False
assert shrimp_selection["selected_record"] is None

print("PASS: Shrimp requires user confirmation.")


# TEST 3: Storage guidance should be blocked before confirmation.
try:
    get_confirmed_storage_guidance(shrimp_selection)
    raise AssertionError(
        "Storage guidance was incorrectly provided before confirmation."
    )
except ValueError:
    print("PASS: Unconfirmed storage guidance is blocked.")


# TEST 4: Selecting shrimp without confirming should remain blocked.
shrimp_unconfirmed = get_foodkeeper_selection(
    food_class="shrimp",
    records=records,
    selected_product_id=151,
    user_confirmed=False
)

assert shrimp_unconfirmed["ready_for_guidance"] is False

print("PASS: Selecting a product alone is not sufficient.")


# TEST 5: Confirming a selected shrimp product should allow guidance.
shrimp_confirmed = get_foodkeeper_selection(
    food_class="shrimp",
    records=records,
    selected_product_id=151,
    user_confirmed=True
)

assert shrimp_confirmed["ready_for_guidance"] is True
assert shrimp_confirmed["selected_record"] is not None

shrimp_guidance = get_confirmed_storage_guidance(
    shrimp_confirmed
)

assert "dop_refrigerate" in shrimp_guidance
assert "dop_freeze" in shrimp_guidance

print("PASS: Confirmed shrimp returns storage guidance.")


# TEST 6: An invalid product ID should be rejected.
try:
    get_foodkeeper_selection(
        food_class="shrimp",
        records=records,
        selected_product_id=999999,
        user_confirmed=True
    )
    raise AssertionError(
        "An invalid FoodKeeper Product ID was accepted."
    )
except ValueError:
    print("PASS: Invalid product selections are rejected.")


# TEST 7: Ground beef should automatically select its single candidate.
beef_selection = get_foodkeeper_selection(
    food_class="ground_beef",
    records=records
)

assert beef_selection["ready_for_guidance"] is True
assert beef_selection["selected_record"] is not None

beef_guidance = get_confirmed_storage_guidance(
    beef_selection
)

assert "dop_refrigerate" in beef_guidance
assert "dop_freeze" in beef_guidance

print("PASS: Ground beef single-candidate lookup works.")

print("\nAll confirmation workflow tests passed.")
