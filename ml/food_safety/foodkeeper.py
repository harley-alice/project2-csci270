"""
FoodKeeper lookup utilities.

Loads the USDA FSIS FoodKeeper JSON file and searches for records that
correspond to the normalized classes in class_map.py.

This module preserves FoodKeeper's original storage wording. 
"""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any

import yaml

PROJECT_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_DATA_PATH = PROJECT_ROOT / "data" / "raw" / "foodkeeper.json"
DEFAULT_MAPPING_PATH = PROJECT_ROOT / "ml" / "configs" / "foodkeeper_mapping.yaml"

# Likely field names used for the product title in FoodKeeper exports.
NAME_FIELDS = (
    "Product", "product", "ProductName", "product_name",
    "Food", "food", "Name", "name", "Item", "item",
)


def _normalise(value: str) -> str:
    """Normalize text for forgiving name comparisons."""
    return re.sub(r"[^a-z0-9]+", " ", str(value).lower()).strip()


def _walk_records(value: Any):
    """
    Recursively find dictionaries that appear to represent FoodKeeper items.
    The original dictionary is yielded unchanged so all storage fields remain
    available, even if the USDA export adds fields in a future version.
    """
    if isinstance(value, dict):
        if any(key in value and isinstance(value[key], (str, int, float))
               for key in NAME_FIELDS):
            yield value
        for child in value.values():
            yield from _walk_records(child)
    elif isinstance(value, list):
        for child in value:
            yield from _walk_records(child)


def _get_name(record: dict) -> str | None:
    for key in NAME_FIELDS:
        value = record.get(key)
        if isinstance(value, str) and value.strip():
            return value.strip()
    return None


def load_foodkeeper(data_path: str | Path = DEFAULT_DATA_PATH) -> list[dict]:
    """Load raw FoodKeeper JSON and return its product records."""
    path = Path(data_path)
    if not path.exists():
        raise FileNotFoundError(
            f"FoodKeeper JSON not found at {path}. "
            "Download the English JSON file and save it there; see README."
        )

    with path.open("r", encoding="utf-8-sig") as file:
        payload = json.load(file)

    records = []
    seen = set()
    for record in _walk_records(payload):
        name = _get_name(record)
        if not name:
            continue
        # Avoid duplicate references to the same record during recursive walk.
        marker = (name, json.dumps(record, sort_keys=True, default=str))
        if marker not in seen:
            seen.add(marker)
            records.append(record)

    if not records:
        raise ValueError(
            "No FoodKeeper product records were recognized. "
            "The USDA JSON schema may have changed; inspect the JSON structure."
        )
    return records


def load_mapping(mapping_path: str | Path = DEFAULT_MAPPING_PATH) -> dict:
    """Load normalized model-class to FoodKeeper search-term mappings."""
    path = Path(mapping_path)
    with path.open("r", encoding="utf-8") as file:
        mapping = yaml.safe_load(file) or {}
    return mapping.get("foodkeeper_mapping", {})


def search_foodkeeper(
    records: list[dict],
    search_term: str,
    exact: bool = False,
) -> list[dict]:
    """Search FoodKeeper product names and return matching original records."""
    query = _normalise(search_term)
    matches = []
    for record in records:
        name = _get_name(record)
        if not name:
            continue
        candidate = _normalise(name)
        if (candidate == query) if exact else (query in candidate):
            matches.append(record)
    return matches


def get_recommendations(
    food_class: str,
    records: list[dict] | None = None,
    query: str | None = None,
    data_path: str | Path = DEFAULT_DATA_PATH,
    mapping_path: str | Path = DEFAULT_MAPPING_PATH,
) -> list[dict]:
    """
    Find candidate FoodKeeper records for a normalized model class.

    `query` can narrow a broad class to a user-confirmed subtype, e.g.
    query="ground beef" or query="chicken, raw". Multiple results are returned
    rather than silently selecting an arbitrary product variant.
    """
    food_class = food_class.strip().lower()
    if records is None:
        records = load_foodkeeper(data_path)

    mapping = load_mapping(mapping_path)
    if food_class not in mapping:
        return []

    terms = [query] if query else mapping[food_class].get("search_terms", [])
    results = []
    seen = set()
    for term in terms:
        for record in search_foodkeeper(records, term):
            name = _get_name(record)
            marker = (name, json.dumps(record, sort_keys=True, default=str))
            if marker not in seen:
                seen.add(marker)
                results.append(record)
    return results


def get_record_name(record: dict) -> str | None:
    """Public helper to retrieve a product name from a returned record."""
    return _get_name(record)


def print_record_summary(records: list[dict]) -> None:
    """Print candidate names and available fields for initial data inspection."""
    for index, record in enumerate(records, start=1):
        print(f"{index}. {_get_name(record)}")
        print("   Available fields:", ", ".join(map(str, record.keys())))
