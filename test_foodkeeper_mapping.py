
from ml.food_safety.hierarchy import get_all_food_classes
from ml.food_safety.foodkeeper import (
    load_foodkeeper,
    load_mapping,
    get_mapping_entry,
    get_recommendations,
    normalize_product_id,
)


# --------------------------------------------------
# Expected approved Product IDs
# --------------------------------------------------

EXPECTED_PRODUCT_IDS = {
    "beef": [34, 35, 36, 37, 38, 39, 40, 41, 42],
    "ground_beef": [43],
    "chicken": [113, 116, 117, 118],
    "shrimp": [151, 325],

    "bacon": [79, 107, 683],
    "butter": [1],
    "cheese": [3, 4, 5, 6, 7, 9, 10, 544, 546, 628],
    "cream": [],
    "egg": [21, 22, 23],
    "goat_cheese": [],
    "ham": [
        82, 83, 84, 85, 86, 87, 88, 89, 90, 91,
        92, 93, 94, 95, 96, 97, 515, 676, 677
    ],
    "milk": [27, 543, 644, 659],
    "yogurt": [33],

    "apple": [248],
    "avocado": [250],
    "banana": [251],
    "bell_pepper": [],
    "blueberries": [254],
    "bread": [195, 460, 461, 574],
    "carrot": [279, 491],
    "chocolate": [216],
    "corn": [282],
    "flour": [222, 223, 459],
    "green_beans": [],
    "lemon": [],
    "lime": [],
    "mango": [],
    "mushrooms": [292, 385],
    "onion": [294, 295],
    "orange": [],
    "persimmon": [],
    "pomegranate": [269],
    "potato": [297],
    "spinach": [291, 415],
    "strawberries": [481],
    "sugar": [239, 240, 241],
    "sweet_potato": [422],
    "tomato": [306, 600],
}


# Classes intentionally lacking an approved FoodKeeper match.
UNSUPPORTED_CLASSES = [
    "bell_pepper",
    "cream",
    "goat_cheese",
    "green_beans",
    "lemon",
    "lime",
    "mango",
    "orange",
    "persimmon",
]


# --------------------------------------------------
# Helper functions
# --------------------------------------------------

def collect_mapping_entries(node, known_classes):
    """
    Recursively collect food class entries from the YAML mapping.
    """

    entries = {}

    if isinstance(node, dict):

        for key, value in node.items():

            if key in known_classes and isinstance(value, dict):
                entries[key] = value

            else:
                entries.update(
                    collect_mapping_entries(value, known_classes)
                )

    elif isinstance(node, list):

        for item in node:
            entries.update(
                collect_mapping_entries(item, known_classes)
            )

    return entries


def normalized_ids(product_ids):
    """Normalize Product IDs for reliable comparison."""

    return sorted(
        normalize_product_id(product_id)
        for product_id in product_ids
        if normalize_product_id(product_id) is not None
    )


# --------------------------------------------------
# Load hierarchy, mapping, and FoodKeeper data
# --------------------------------------------------

food_classes = set(get_all_food_classes())
mapping = load_mapping()
records = load_foodkeeper()

mapping_entries = collect_mapping_entries(
    mapping,
    food_classes
)

mapping_classes = set(mapping_entries.keys())

print("FOODKEEPER MAPPING AUDIT")
print("=" * 55)

print("Hierarchy food classes:", len(food_classes))
print("Mapped food classes:", len(mapping_classes))
print("Loaded USDA FoodKeeper products:", len(records))


# --------------------------------------------------
# Test 1: Class coverage
# --------------------------------------------------

missing_classes = food_classes - mapping_classes
extra_classes = mapping_classes - food_classes

assert not missing_classes, (
    f"Missing food classes: {sorted(missing_classes)}"
)

assert not extra_classes, (
    f"Unexpected mapping classes: {sorted(extra_classes)}"
)

assert mapping_classes == set(EXPECTED_PRODUCT_IDS), (
    "The expected mapping class list does not match the hierarchy."
)

print("\nPASS: All hierarchy classes have mapping entries.")
print("PASS: No unexpected mapping classes.")


# --------------------------------------------------
# Test 2: Configured Product IDs exist
# --------------------------------------------------

available_ids = {
    normalize_product_id(record.get("ID"))
    for record in records
}

for food_class, settings in mapping_entries.items():

    configured_ids = settings.get("product_ids") or []

    for product_id in configured_ids:

        normalized_id = normalize_product_id(product_id)

        assert normalized_id in available_ids, (
            f"Invalid FoodKeeper Product ID {product_id} "
            f"for {food_class}"
        )

print("PASS: All configured USDA Product IDs exist.")


# --------------------------------------------------
# Test 3: Verify exact approved Product ID mappings
# --------------------------------------------------

for food_class, expected_ids in EXPECTED_PRODUCT_IDS.items():

    settings = get_mapping_entry(
        food_class,
        mapping=mapping
    )

    actual_ids = settings.get("product_ids") or []

    assert normalized_ids(actual_ids) == normalized_ids(expected_ids), (
        f"Incorrect Product IDs for {food_class}. "
        f"Expected {expected_ids}, got {actual_ids}"
    )

print("PASS: All Product ID mappings match the audited list.")


# --------------------------------------------------
# Test 4: Classes without a direct match require confirmation
# --------------------------------------------------

for food_class in UNSUPPORTED_CLASSES:

    settings = get_mapping_entry(
        food_class,
        mapping=mapping
    )

    assert not settings.get("product_ids"), (
        f"{food_class} should not have Product IDs."
    )

    search_terms = (
        settings.get("search_terms")
        or settings.get("terms")
        or settings.get("keywords")
        or []
    )

    assert not search_terms, (
        f"{food_class} should not have broad search terms."
    )

    assert settings.get("requires_user_detail") is True, (
        f"{food_class} must require user confirmation."
    )

    print(
        f"PASS: {food_class} has no approved match "
        "and requires confirmation."
    )


# --------------------------------------------------
# Test 5: Every class has a lookup or requires confirmation
# --------------------------------------------------

for food_class, settings in mapping_entries.items():

    product_ids = settings.get("product_ids") or []

    search_terms = (
        settings.get("search_terms")
        or settings.get("terms")
        or settings.get("keywords")
        or []
    )

    if isinstance(search_terms, str):
        search_terms = [search_terms]

    if not product_ids and not search_terms:

        assert settings.get("requires_user_detail") is True, (
            f"{food_class} has no lookup configured "
            "but does not require user confirmation."
        )

print("PASS: Every class has an approved lookup or confirmation requirement.")


# --------------------------------------------------
# Test 6: Known misleading Product IDs are excluded
# --------------------------------------------------

for food_class, forbidden_ids in {
    "goat_cheese": [7],
    "cream": [29, 30],
    "lemon": [256],
    "lime": [256],
    "orange": [256],
    "mango": [265],
    "bell_pepper": [458],
    "green_beans": [273],
}.items():

    settings = get_mapping_entry(
        food_class,
        mapping=mapping
    )

    actual_ids = normalized_ids(
        settings.get("product_ids") or []
    )

    for forbidden_id in forbidden_ids:

        assert normalize_product_id(forbidden_id) not in actual_ids, (
            f"Misleading Product ID {forbidden_id} "
            f"was assigned to {food_class}."
        )

print("PASS: Known misleading Product IDs are excluded.")


# --------------------------------------------------
# Test 7: Unsupported classes return no candidates
# --------------------------------------------------

for food_class in UNSUPPORTED_CLASSES:

    candidates = get_recommendations(
        food_class=food_class,
        records=records
    )

    assert candidates == [], (
        f"{food_class} returned unsupported FoodKeeper candidates."
    )

    print(
        f"PASS: {food_class} returns no unsupported candidates."
    )


# --------------------------------------------------
# Final result
# --------------------------------------------------

print("\n" + "=" * 55)
print("ALL FOODKEEPER MAPPING AUDIT TESTS PASSED.")
