
from ml.food_safety.foodkeeper import (
    load_foodkeeper,
    get_recommendations,
    print_record_summary
)

# Load the actual USDA FoodKeeper dataset
products = load_foodkeeper()

print(f"Loaded {len(products)} USDA FoodKeeper products.")

# Test ground beef
ground_beef = get_recommendations(
    food_class="ground_beef",
    records=products,
    query="ground beef"
)

print("\nGROUND BEEF RESULTS")
for product in ground_beef:
    print_record_summary(product)

# Test shrimp
shrimp = get_recommendations(
    food_class="shrimp",
    records=products,
    query="shrimp"
)

print("\nSHRIMP RESULTS")
for product in shrimp:
    print_record_summary(product)
