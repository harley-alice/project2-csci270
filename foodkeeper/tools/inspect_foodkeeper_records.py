
from foodkeeper.ml.food_safety.foodkeeper import load_foodkeeper, get_storage_guidance

products = load_foodkeeper()

# USDA product IDs to inspect
target_ids = [43, 151, 325, 417]

for product in products:
    if product.get("ID") in target_ids:
        print("\n" + "=" * 60)
        print("USDA PRODUCT ID:", product.get("ID"))
        print("NAME:", product.get("Name"))
        print("SUBTITLE:", product.get("Name_subtitle"))
        print("KEYWORDS:", product.get("Keywords"))
        print("CATEGORY ID:", product.get("Category_ID"))

        print("\nSTORAGE GUIDANCE:")
        for field, value in get_storage_guidance(product).items():
            if value is not None:
                print(f"{field}: {value}")
