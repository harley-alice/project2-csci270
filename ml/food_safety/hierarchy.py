
"""
Food Safety Hierarchy

Loads the food safety hierarchy from food_safety_tiers.yaml
and provides functions for retrieving food classifications.

The hierarchy assigns safety priorities.
"""

from pathlib import Path
import yaml


# --------------------------------------------------
# Configuration
# --------------------------------------------------

# Locate the YAML file relative to this Python file.
CONFIG_PATH = (
    Path(__file__).resolve().parent.parent
    / "configs"
    / "food_safety_tiers.yaml"
)


# --------------------------------------------------
# Load hierarchy configuration
# --------------------------------------------------

def load_hierarchy(config_path=CONFIG_PATH):
    """
    Load the food safety hierarchy from a YAML file.

    Returns:
        dict: Parsed hierarchy configuration.
    """

    config_path = Path(config_path)

    if not config_path.exists():
        raise FileNotFoundError(
            f"Food safety hierarchy not found: {config_path}"
        )

    with config_path.open("r", encoding="utf-8") as file:
        hierarchy = yaml.safe_load(file)

    if not isinstance(hierarchy, dict):
        raise ValueError("Invalid hierarchy YAML structure.")

    if "tiers" not in hierarchy:
        raise ValueError("Hierarchy configuration is missing 'tiers'.")

    return hierarchy


# Load configuration when this module is imported.
HIERARCHY = load_hierarchy()


# --------------------------------------------------
# Build class lookup dictionaries
# --------------------------------------------------

def build_class_lookup(hierarchy=HIERARCHY):
    """
    Create a lookup dictionary connecting each food class
    to its assigned safety tier.

    Returns:
        dict: Food class -> tier information.
    """

    lookup = {}

    for tier_id, tier_data in hierarchy["tiers"].items():

        for food_class in tier_data.get("classes", []):

            if food_class in lookup:
                raise ValueError(
                    f"Food class '{food_class}' appears in multiple tiers."
                )

            lookup[food_class] = {
                "tier": tier_id,
                "name": tier_data["name"],
                "description": tier_data["description"]
            }

    return lookup


CLASS_LOOKUP = build_class_lookup()


# --------------------------------------------------
# Build special category lookup
# --------------------------------------------------

def build_special_lookup(hierarchy=HIERARCHY):
    """
    Create a lookup dictionary for non-food or special
    categories requiring additional user input.

    Returns:
        dict: Special class -> category information.
    """

    return {
        item["class"]: item
        for item in hierarchy.get("special_categories", [])
    }


SPECIAL_LOOKUP = build_special_lookup()


# --------------------------------------------------
# Retrieve food safety classification
# --------------------------------------------------

def get_safety_tier(food_class):
    """
    Return the safety tier assigned to a food class.

    Example:
        get_safety_tier("chicken")

        Returns:
            "tier_1"

    Returns None if the class is not found.
    """

    food_class = food_class.strip().lower()

    result = CLASS_LOOKUP.get(food_class)

    if result is None:
        return None

    return result["tier"]


def get_classification(food_class):
    """
    Return the complete safety classification for a food.

    Example:
        get_classification("ground_beef")

        Returns:
            {
                "tier": "tier_1",
                "name": "High safety priority",
                "description": "..."
            }

    Returns None if the class is not found.
    """

    food_class = food_class.strip().lower()

    return CLASS_LOOKUP.get(food_class)


def get_special_category(food_class):
    """
    Check whether a detected object belongs to a special
    category rather than a standard food safety tier.

    Example:
        get_special_category("jar")

    Returns:
        Special category information or None.
    """

    food_class = food_class.strip().lower()

    return SPECIAL_LOOKUP.get(food_class)


def requires_user_confirmation(food_class):
    """
    Determine whether a detected class requires user
    confirmation before applying food safety guidance.

    Returns:
        bool: True if confirmation is required.
    """

    special = get_special_category(food_class)

    if special is not None:
        return special.get("requires_user_confirmation", False)

    return False


# --------------------------------------------------
# Retrieve all available classes
# --------------------------------------------------

def get_all_food_classes():
    """
    Return all food classes assigned to safety tiers.

    Special categories such as jars are excluded.
    """

    return list(CLASS_LOOKUP.keys())


def get_all_special_categories():
    """
    Return all special categories.
    """

    return list(SPECIAL_LOOKUP.keys())


# --------------------------------------------------
# Validate hierarchy against computer vision classes
# --------------------------------------------------

def validate_classes(model_classes):
    """
    Compare the hierarchy classes against the final
    computer vision classes from class_map.py.

    Args:
        model_classes: Iterable of model class names.

    Returns:
        dict: Missing and unexpected classes.

    Raises:
        ValueError: If the class lists do not match.
    """

    model_classes = set(model_classes)
    hierarchy_classes = set(CLASS_LOOKUP.keys())

    missing_from_hierarchy = model_classes - hierarchy_classes
    missing_from_model = hierarchy_classes - model_classes

    result = {
        "missing_from_hierarchy": sorted(missing_from_hierarchy),
        "missing_from_model": sorted(missing_from_model)
    }

    if missing_from_hierarchy or missing_from_model:
        raise ValueError(
            "Food safety hierarchy does not match model classes.\n"
            f"Missing from hierarchy: {result['missing_from_hierarchy']}\n"
            f"Missing from model: {result['missing_from_model']}"
        )

    return result
