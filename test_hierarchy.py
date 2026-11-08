
# Test the food safety hierarchy

from ml.food_safety import (
    get_safety_tier,
    get_classification,
    get_special_category,
    requires_user_confirmation,
    get_all_food_classes,
    get_all_special_categories
)

# --------------------------------
# Test 1: Food safety tier lookup
# --------------------------------

assert get_safety_tier("chicken") == "tier_1"
assert get_safety_tier("milk") == "tier_2"
assert get_safety_tier("apple") == "tier_3"

print("Test 1 passed: Food tier lookup works.")

# --------------------------------
# Test 2: Individual classification
# --------------------------------

chicken = get_classification("chicken")

assert chicken is not None
assert chicken["tier"] == "tier_1"
assert chicken["name"] == "High safety priority"

print("Test 2 passed: Food classification works.")

# --------------------------------
# Test 3: Ground beef distinction
# --------------------------------

from ml.food_safety.hierarchy import CLASS_LOOKUP, CONFIG_PATH

print("\nLoaded YAML file:", CONFIG_PATH)
print("Ground beef in lookup:", "ground_beef" in CLASS_LOOKUP)
print("Beef classification:", CLASS_LOOKUP.get("beef"))
print("Ground beef classification:", CLASS_LOOKUP.get("ground_beef"))

assert get_safety_tier("beef") == "tier_1"
assert get_safety_tier("ground_beef") == "tier_1"

assert get_classification("beef") is not None
assert get_classification("ground_beef") is not None

print("Test 3 passed: Beef classes are recognized separately.")

# --------------------------------
# Test 4: Special categories
# --------------------------------

assert get_special_category("jar") is not None
assert requires_user_confirmation("jar") == True

print("Test 4 passed: Special categories work.")

# --------------------------------
# Test 5: Unknown food classes
# --------------------------------

assert get_safety_tier("unknown_food") is None
assert get_classification("unknown_food") is None

print("Test 5 passed: Unknown classes are handled.")

# --------------------------------
# Test 6: Retrieve all classes
# --------------------------------

food_classes = get_all_food_classes()
special_classes = get_all_special_categories()

assert len(food_classes) == 38
assert "jar" in special_classes

print("Test 6 passed: Food and special classes retrieved.")
print("Number of food classes:", len(food_classes))
print("Special categories:", special_classes)

print("\nAll hierarchy tests passed!")
