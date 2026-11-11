
import yaml
from ml.food_safety.foodkeeper import load_foodkeeper, get_record_name

# Load USDA records and existing mappings
products = load_foodkeeper()

with open("ml/configs/foodkeeper_mapping.yaml", "r", encoding="utf-8") as file:
    mapping = yaml.safe_load(file)

# Create a lookup by USDA product ID
product_lookup = {
    product["ID"]: product
    for product in products
    if product.get("ID") is not None
}

print(f"Loaded {len(products)} USDA products.")

# Check every mapped ID
for food_class, settings in mapping.items():
    if not isinstance(settings, dict):
        continue

    product_ids = settings.get("product_ids", [])

    print(f"\n{'=' * 50}")
    print(f"FOOD CLASS: {food_class}")

    for product_id in product_ids:
        product = product_lookup.get(product_id)

        if product is None:
            print(f"  INVALID ID: {product_id}")
        else:
            print(
                f"  ID {product_id}: "
                f"{get_record_name(product)} | "
                f"Keywords: {product.get('Keywords')}"
            )

print("\nAudit complete.")
