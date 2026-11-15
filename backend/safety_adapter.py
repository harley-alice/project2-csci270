"""
Thin adapter between the backend and Ashton's food-safety package (ml/food_safety/).

Ashton's package is the AUTHORITY for, per detected class:
  * safety_tier           -> ml.food_safety.hierarchy (food_safety_tiers.yaml)
  * requires_confirmation -> hierarchy special categories (e.g. jar) and the FoodKeeper
                             confirmation workflow (get_foodkeeper_selection)
  * shelf-life days       -> only AFTER her workflow says the guidance is ready, via
                             get_confirmed_storage_guidance + calculate_confirmed_guidance_range

This module only calls her public functions; it does not change or re-implement her logic.
Anything her code does not provide is returned as None (never guessed).

Which source wins (see also backend/inference.py):
  * detection responses (POST /api/detect, /detect): Ashton's package, via this adapter.
  * backend/rule_engine.py (CJ's SQLite seed table) is kept for the storage-duration endpoints
    (/api/rules/*, /api/inventory/*/duration) and for display-only fields (display name, category).
    Its hand-entered day counts are NOT used for detections, because they bypass her confirmation
    requirements and unsupported-product exclusions.

TODO (needs Ashton / CJ): her workflow is two-phase (detect -> user picks a USDA product and confirms
-> guidance), but the app currently has only the one-shot detect call. Until a confirmation endpoint
exists (sending selected_product_id + user_confirmed to get_foodkeeper_selection), every class that
needs confirmation returns days=None. See the integration report.
"""

from __future__ import annotations

import logging
from datetime import date
from typing import Any, Dict, Optional

from ml.food_safety import hierarchy
from ml.food_safety.date_calculator import calculate_confirmed_guidance_range
from ml.food_safety.foodkeeper import (
    DEFAULT_DATA_PATH,
    get_confirmed_storage_guidance,
    get_foodkeeper_selection,
    get_mapping_entry,
    load_foodkeeper,
)

logger = logging.getLogger("fridge_tracker.safety_adapter")

# Policy floor: meat / poultry / seafood always ask the user to confirm, unless Ashton's own
# mapping explicitly says no detail is needed (requires_user_detail: false) AND her workflow agrees.
MEAT_CLASSES = frozenset({"chicken", "beef", "shrimp", "bacon", "ham"})

# (storage_location, package_state) -> (FoodKeeper storage type, start event) for her date calculator
_STORAGE_TYPES = {
    ("refrigerator", "sealed"): ("refrigerate", "purchase"),
    ("refrigerator", "opened"): ("refrigerate_after_opening", "opening"),
    ("freezer", "sealed"): ("freeze", "purchase"),
    ("freezer", "opened"): ("freeze", "purchase"),
    ("pantry", "sealed"): ("pantry", "purchase"),
    ("pantry", "opened"): ("pantry_after_opening", "opening"),
}

_UNCLASSIFIED_TIER = "unclassified"
_SPECIAL_TIER = "special_category"

_records_cache: Dict[str, Any] = {"loaded": False, "records": None}


def get_records(reload: bool = False) -> Optional[list]:
    """FoodKeeper product records from data/raw/foodkeeper.json, or None if the file is missing."""
    if reload or not _records_cache["loaded"]:
        try:
            _records_cache["records"] = load_foodkeeper()
        except FileNotFoundError:
            logger.warning(
                "FoodKeeper data file not found at %s. All items will require confirmation and have "
                "no shelf-life days until it is provided.",
                DEFAULT_DATA_PATH,
            )
            _records_cache["records"] = None
        _records_cache["loaded"] = True
    return _records_cache["records"]


def foodkeeper_status() -> Dict[str, Any]:
    """Used by /api/health."""
    return {
        "foodkeeper_data": "loaded" if get_records() is not None else "not_loaded",
        "foodkeeper_data_path": str(DEFAULT_DATA_PATH),
    }


def _result(
    tier: str,
    requires_confirmation: bool,
    prompt: Optional[str] = None,
    guidance_supported: Optional[bool] = None,
    days: Optional[int] = None,
    days_min: Optional[int] = None,
    days_max: Optional[int] = None,
) -> Dict[str, Any]:
    return {
        "safety_tier": tier,
        "requires_confirmation": requires_confirmation,
        "confirmation_prompt": prompt,
        "guidance_supported": guidance_supported,
        "days": days,
        "days_min": days_min,
        "days_max": days_max,
    }


def assess(
    food_class: str,
    package_state: str = "sealed",
    storage_location: str = "refrigerator",
    records: Optional[list] = None,
) -> Dict[str, Any]:
    """
    Return Ashton's safety assessment for one detected class.

    Keys: safety_tier, requires_confirmation, confirmation_prompt, guidance_supported
    (True/False, or None when it could not be determined), days, days_min, days_max
    (None unless her workflow has confirmed guidance and it is day-based).

    `records` can be passed for tests; by default the FoodKeeper JSON is loaded (and cached).
    """
    name = food_class.strip().lower().replace("-", "_")
    tier = hierarchy.get_safety_tier(name)
    special = hierarchy.get_special_category(name)

    # Special categories (e.g. jar): a container, not a food. Her hierarchy says to ask what is inside.
    if special is not None:
        return _result(
            tier or _SPECIAL_TIER,
            hierarchy.requires_user_confirmation(name),
            prompt=(special.get("description") or "").strip() or None,
            guidance_supported=False,
        )

    tier = tier or _UNCLASSIFIED_TIER

    # Classes with no mapping at all are unsupported: no guidance, always confirm.
    try:
        entry = get_mapping_entry(name)
    except KeyError:
        return _result(tier, True, "This item is not supported for storage guidance.", guidance_supported=False)

    if records is None:
        records = get_records()
    if records is None:
        # Cannot run her workflow without the FoodKeeper data: be conservative, give no days.
        return _result(
            tier,
            True,
            entry.get("detail_prompt") or "Please confirm this item.",
            guidance_supported=None,
        )

    try:
        selection = get_foodkeeper_selection(name, records=records)
    except Exception as exc:  # her code raises ValueError/KeyError on bad input; stay conservative
        logger.error("FoodKeeper selection failed for %s: %s", name, exc)
        return _result(tier, True, "Please confirm this item.", guidance_supported=None)

    requires_confirmation = bool(selection["requires_confirmation"])
    prompt = selection.get("confirmation_prompt")
    supported = bool(selection["candidates"])

    # Meat floor (see MEAT_CLASSES): only her explicit "no detail needed" can lift it.
    if name in MEAT_CLASSES and not requires_confirmation and entry.get("requires_user_detail", True):
        requires_confirmation = True

    days = days_min = days_max = None
    if selection["ready_for_guidance"]:
        storage_type, start_event = _STORAGE_TYPES.get(
            (storage_location.strip().lower(), package_state.strip().lower()),
            ("refrigerate", "purchase"),
        )
        try:
            get_confirmed_storage_guidance(selection)  # raises unless confirmed
            calc = calculate_confirmed_guidance_range(selection, storage_type, date.today(), start_event)
            # Conservative: report the low end of her range as the shelf life.
            days, days_min, days_max = calc["minimum_days"], calc["minimum_days"], calc["maximum_days"]
        except ValueError as exc:
            logger.info("No day-based guidance for %s (%s): %s", name, storage_type, exc)

    if requires_confirmation:
        days = days_min = days_max = None

    return _result(tier, requires_confirmation, prompt, supported, days, days_min, days_max)
