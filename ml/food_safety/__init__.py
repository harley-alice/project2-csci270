
"""

access to food safety hierarchy classifications
and special-category lookups.
"""

from .hierarchy import (
    HIERARCHY,
    CLASS_LOOKUP,
    SPECIAL_LOOKUP,
    load_hierarchy,
    build_class_lookup,
    build_special_lookup,
    get_safety_tier,
    get_classification,
    get_special_category,
    requires_user_confirmation,
    get_all_food_classes,
    get_all_special_categories,
    validate_classes,
)

__all__ = [
    "HIERARCHY",
    "CLASS_LOOKUP",
    "SPECIAL_LOOKUP",
    "load_hierarchy",
    "build_class_lookup",
    "build_special_lookup",
    "get_safety_tier",
    "get_classification",
    "get_special_category",
    "requires_user_confirmation",
    "get_all_food_classes",
    "get_all_special_categories",
    "validate_classes",
]
