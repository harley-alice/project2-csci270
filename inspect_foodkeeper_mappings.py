
from ml.food_safety.foodkeeper import (
    load_foodkeeper,
    load_mapping,
    normalize_product_id,
    get_record_name,
)

records = load_foodkeeper()
mapping = load_mapping()

# Create a lookup of USDA Product IDs.
products_by_id = {
    normalize_product_id(record.get("ID")): record
    for record in records
    if record.get("ID") is not None
}

print(f"Loaded {len(records)} USDA products.")
print(f"Auditing {len(mapping)} food classes.\n")

for food_class, settings in mapping.items():

    print("=" * 65)
    print(f"FOOD CLASS: {food_class}")

    product_ids = settings.get("product_ids", [])
    search_terms = settings.get("search_terms", [])

    print("Search terms:", search_terms)
    print("Requires user detail:", settings.get(
        "requires_user_detail", False
    ))

    if settings.get("detail_prompt"):
        print("Detail prompt:", settings["detail_prompt"])

    if not product_ids:
        print("No specific Product IDs configured.")
        continue

    print("\nConfigured USDA products:")

    for product_id in product_ids:

        normalized_id = normalize_product_id(product_id)
        record = products_by_id.get(normalized_id)

        if record is None:
            print(f"  ERROR: Product ID {product_id} not found.")
            continue

        print(
            f"  ID {normalized_id}: "
            f"{get_record_name(record)}"
        )

        keywords = record.get("Keywords")

        if keywords:
            print(f"    Keywords: {keywords}")

print("\nAudit listing complete.")
