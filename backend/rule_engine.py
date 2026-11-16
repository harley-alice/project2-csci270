"""
Hybrid AI Rule Engine.

Deterministic decision engine that takes the AI's detected food class
(e.g., 'ground_beef', 'beef', 'chicken', 'milk', 'jar'), queries the
FoodKeeper rules, and calculates dynamic expiration windows based on
package state (opened vs. sealed) and storage conditions (refrigerator,
freezer, pantry).
"""

from __future__ import annotations

import sqlite3
from datetime import date, timedelta
from typing import Any, Dict, Optional

from backend.database import get_db_connection

# Normalization map for common synonyms or model variants
CLASS_ALIASES = {
    "ground beef": "ground_beef",
    "chicken_breast": "chicken",
    "eggs": "egg",
    "tomatoes": "tomato",
    "peppers": "bell_pepper",
    "heavy_cream": "cream",
    "milk_carton": "milk",
    "yogurt_container": "yogurt",
    "soda_can": "jar",
}

# Conservative default when a food class is unknown
CONSERVATIVE_FALLBACK = {
    "food_class": "unknown",
    "package_state": "opened",
    "storage_location": "refrigerator",
    "is_cooked": False,
    "tier": "tier_2",
    "category": "Uncategorized",
    "shelf_life_days_min": 1,
    "shelf_life_days_max": 3,
    "recommended_shelf_life_days": 2,
    "requires_user_detail": True,
    "detail_prompt": "Unrecognized food item. Verify contents and inspect smell/texture before consuming.",
    "usda_guidance": "Conservative fallback: consume perishable foods within 1 to 2 days.",
}


class FoodKeeperRuleEngine:
    """
    Deterministic rule engine that marries deep learning detections
    with official USDA FoodKeeper safety parameters.
    """

    def __init__(self, conn: Optional[sqlite3.Connection] = None):
        self._conn = conn

    def _get_connection(self) -> sqlite3.Connection:
        if self._conn is not None:
            return self._conn
        return get_db_connection()

    def normalize_food_class(self, food_class: str) -> str:
        """Sanitize and normalize food class name."""
        cleaned = food_class.strip().lower().replace("-", "_")
        return CLASS_ALIASES.get(cleaned, cleaned)

    def calculate_expiration(
        self,
        food_class: str,
        package_state: str = "sealed",
        storage_location: str = "refrigerator",
        is_cooked: bool = False,
        start_date: Optional[date] = None,
    ) -> Dict[str, Any]:
        """
        Calculate dynamic expiration window and safety metrics for a given food item.

        Args:
            food_class: Detected class name (e.g., 'ground_beef', 'milk', 'jar').
            package_state: 'sealed' (unopened) or 'opened'.
            storage_location: 'refrigerator', 'freezer', or 'pantry'.
            is_cooked: True if food has been cooked/prepared.
            start_date: Starting anchor date (defaults to today).

        Returns:
            Dictionary containing calculated shelf life windows, exact expiration dates,
            safety tier, and USDA guidance warnings.
        """
        if start_date is None:
            start_date = date.today()

        norm_class = self.normalize_food_class(food_class)
        norm_pkg = package_state.strip().lower()
        if norm_pkg not in ("sealed", "opened"):
            norm_pkg = "sealed"

        norm_loc = storage_location.strip().lower()
        if norm_loc not in ("refrigerator", "freezer", "pantry"):
            norm_loc = "refrigerator"

        conn = self._get_connection()
        should_close = (self._conn is None)

        try:
            # Query specific rule
            cursor = conn.execute(
                """
                SELECT r.*, c.name as category_name, c.tier as safety_tier, c.priority
                FROM storage_rules r
                LEFT JOIN food_categories c ON r.category_id = c.id
                WHERE r.food_class = ?
                  AND r.package_state = ?
                  AND r.storage_location = ?
                  AND r.is_cooked = ?
                LIMIT 1;
                """,
                (norm_class, norm_pkg, norm_loc, 1 if is_cooked else 0),
            )
            rule = cursor.fetchone()

            # Fallback 1: match without is_cooked constraint if not found
            if not rule and is_cooked:
                cursor = conn.execute(
                    """
                    SELECT r.*, c.name as category_name, c.tier as safety_tier, c.priority
                    FROM storage_rules r
                    LEFT JOIN food_categories c ON r.category_id = c.id
                    WHERE r.food_class = ?
                      AND r.package_state = ?
                      AND r.storage_location = ?
                    ORDER BY r.is_cooked DESC
                    LIMIT 1;
                    """,
                    (norm_class, norm_pkg, norm_loc),
                )
                rule = cursor.fetchone()

            # Fallback 2: match refrigerator rule if requested location not found
            if not rule and norm_loc != "refrigerator":
                cursor = conn.execute(
                    """
                    SELECT r.*, c.name as category_name, c.tier as safety_tier, c.priority
                    FROM storage_rules r
                    LEFT JOIN food_categories c ON r.category_id = c.id
                    WHERE r.food_class = ?
                      AND r.package_state = ?
                      AND r.storage_location = 'refrigerator'
                    LIMIT 1;
                    """,
                    (norm_class, norm_pkg),
                )
                rule = cursor.fetchone()

            # Fallback 3: generic match on food_class alone
            if not rule:
                cursor = conn.execute(
                    """
                    SELECT r.*, c.name as category_name, c.tier as safety_tier, c.priority
                    FROM storage_rules r
                    LEFT JOIN food_categories c ON r.category_id = c.id
                    WHERE r.food_class = ?
                    LIMIT 1;
                    """,
                    (norm_class,),
                )
                rule = cursor.fetchone()

            if rule:
                days_min = int(rule["shelf_life_days_min"])
                days_max = int(rule["shelf_life_days_max"])
                days_rec = int(rule["recommended_shelf_life_days"])
                safety_tier = rule["safety_tier"] or "tier_2"
                category_name = rule["category_name"] or "General"
                requires_detail = bool(rule["requires_user_detail"])
                prompt = rule["detail_prompt"]
                guidance = rule["usda_guidance"]
            else:
                # Conservative fallback for unknown item
                days_min = CONSERVATIVE_FALLBACK["shelf_life_days_min"]
                days_max = CONSERVATIVE_FALLBACK["shelf_life_days_max"]
                days_rec = CONSERVATIVE_FALLBACK["recommended_shelf_life_days"]
                safety_tier = CONSERVATIVE_FALLBACK["tier"]
                category_name = CONSERVATIVE_FALLBACK["category"]
                requires_detail = CONSERVATIVE_FALLBACK["requires_user_detail"]
                prompt = CONSERVATIVE_FALLBACK["detail_prompt"]
                guidance = CONSERVATIVE_FALLBACK["usda_guidance"]

            # Compute dates
            earliest_exp = start_date + timedelta(days=days_min)
            latest_exp = start_date + timedelta(days=days_max)
            rec_exp = start_date + timedelta(days=days_rec)

            is_container = (norm_class == "jar")
            is_high_risk = (safety_tier == "tier_1")
            is_urgent = (days_rec <= 3)

            return {
                "food_class": norm_class,
                "display_name": norm_class.replace("_", " ").title(),
                "package_state": norm_pkg,
                "storage_location": norm_loc,
                "is_cooked": is_cooked,
                "start_date": start_date.isoformat(),
                "shelf_life_days_min": days_min,
                "shelf_life_days_max": days_max,
                "recommended_shelf_life_days": days_rec,
                "expiration_date": rec_exp.isoformat(),
                "earliest_expiration_date": earliest_exp.isoformat(),
                "latest_expiration_date": latest_exp.isoformat(),
                "safety_tier": safety_tier,
                "category_name": category_name,
                "requires_user_detail": requires_detail or is_container,
                "detail_prompt": prompt,
                "usda_guidance": guidance,
                "is_container": is_container,
                "is_high_risk": is_high_risk,
                "is_urgent": is_urgent,
            }
        finally:
            if should_close:
                conn.close()


# Module-level singleton
rule_engine = FoodKeeperRuleEngine()

