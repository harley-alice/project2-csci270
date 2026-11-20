
from foodkeeper.ml.food_safety.foodkeeper import (
    load_foodkeeper,
    load_mapping,
    get_recommendations,
    normalize_product_id,
    get_record_name,
)

records = load_foodkeeper()
mapping = load_mapping()

print("SEARCH-ONLY FOODKEEPER MAPPING AUDIT")
print("=" * 65)

for food_class, settings in mapping.items():

    # Skip classes that already have configured Product IDs.
    if settings.get("product_ids"):
        continue

    print(f"\nFOOD CLASS: {food_class}")
    print("Search terms:", settings.get("search_terms", []))

    candidates = get_recommendations(
        food_class=food_class,
        records=records
    )

    print(f"Candidates found: {len(candidates)}")

    if not candidates:
        print("  WARNING: No matching products found.")
        continue

    for record in candidates[:10]:

        product_id = normalize_product_id(
            record.get("ID")
        )

        print(
            f"  ID {product_id}: "
            f"{get_record_name(record)}"
        )

    if len(candidates) > 10:
        print(f"  ... and {len(candidates) - 10} more")

print("\nSearch-only audit complete.")
