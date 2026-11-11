
import json
import re
from pathlib import Path
from typing import Any

import yaml


# --------------------------------------------------
# File paths
# --------------------------------------------------

PROJECT_ROOT = Path(__file__).resolve().parents[2]

DEFAULT_DATA_PATH = (
    PROJECT_ROOT / "data" / "raw" / "foodkeeper.json"
)

DEFAULT_MAPPING_PATH = (
    PROJECT_ROOT / "ml" / "configs" / "foodkeeper_mapping.yaml"
)


# --------------------------------------------------
# Text and ID normalization
# --------------------------------------------------

def normalize_text(value: Any) -> str:
    """Convert text to lowercase, normalized searchable text."""

    if value is None:
        return ""

    text = str(value).lower().strip()
    text = re.sub(r"[^a-z0-9\s]", " ", text)
    text = re.sub(r"\s+", " ", text)

    return text


def normalize_product_id(value: Any) -> str | None:
    """Normalize FoodKeeper product IDs for consistent comparison."""

    if value is None:
        return None

    text = str(value).strip()

    if not text:
        return None

    # Convert values such as 43.0 to 43.
    try:
        number = float(text)

        if number.is_integer():
            return str(int(number))

    except ValueError:
        pass

    return text


def flatten_row(row: Any) -> dict:
    """
    Convert a FoodKeeper row containing one-key dictionaries
    into a standard dictionary.
    """

    if isinstance(row, dict):
        return row.copy()

    if isinstance(row, list):
        flattened = {}

        for item in row:
            if isinstance(item, dict):
                flattened.update(item)

        return flattened

    return {}


# --------------------------------------------------
# Load USDA FoodKeeper data
# --------------------------------------------------

def load_foodkeeper(
    data_path: Path = DEFAULT_DATA_PATH
) -> list[dict]:
    """
    Load USDA FoodKeeper product records.

    Supports the root-level 'sheets' structure used by the
    downloaded FoodKeeper JSON file.
    """

    data_path = Path(data_path)

    if not data_path.exists():
        raise FileNotFoundError(
            f"FoodKeeper data file was not found: {data_path}"
        )

    with open(data_path, "r", encoding="utf-8") as file:
        data = json.load(file)

    # The downloaded FoodKeeper file stores sheets at the root.
    if isinstance(data.get("sheets"), list):
        sheets = data["sheets"]

    # Also support a nested data.sheets structure.
    elif isinstance(data.get("data"), dict):
        sheets = data["data"].get("sheets", [])

    else:
        sheets = []

    product_rows = None

    for sheet in sheets:

        if not isinstance(sheet, dict):
            continue

        sheet_name = (
            sheet.get("name")
            or sheet.get("sheetName")
            or sheet.get("title")
            or ""
        )

        if normalize_text(sheet_name) == "product":
            product_rows = (
                sheet.get("data")
                or sheet.get("rows")
                or sheet.get("values")
            )
            break

    if product_rows is None:
        raise ValueError(
            "Could not find the Product sheet in FoodKeeper JSON."
        )

    products = []

    for row in product_rows:

        record = flatten_row(row)

        if not record:
            continue

        product_id = normalize_product_id(record.get("ID"))

        if product_id is None:
            continue

        record["ID"] = product_id
        products.append(record)

    return products


# --------------------------------------------------
# Load food classification mappings
# --------------------------------------------------

def load_mapping(
    mapping_path: Path = DEFAULT_MAPPING_PATH
) -> dict:
    """Load the food-class-to-FoodKeeper mapping YAML file."""

    mapping_path = Path(mapping_path)

    if not mapping_path.exists():
        raise FileNotFoundError(
            f"FoodKeeper mapping file was not found: {mapping_path}"
        )

    with open(mapping_path, "r", encoding="utf-8") as file:
        mapping = yaml.safe_load(file)

    return mapping or {}


def _find_class_entry(
    node: Any,
    food_class: str
) -> dict | None:
    """
    Recursively find a food class entry in the mapping YAML.

    Supports mappings organized by tier or by a top-level
    foods/classes dictionary.
    """

    if isinstance(node, dict):

        # Direct class entry.
        if food_class in node and isinstance(node[food_class], dict):
            return node[food_class]

        # Search nested dictionaries.
        for value in node.values():

            result = _find_class_entry(value, food_class)

            if result is not None:
                return result

    elif isinstance(node, list):

        for item in node:

            result = _find_class_entry(item, food_class)

            if result is not None:
                return result

    return None


def get_mapping_entry(
    food_class: str,
    mapping: dict | None = None,
    mapping_path: Path = DEFAULT_MAPPING_PATH
) -> dict:
    """Get the FoodKeeper mapping entry for a detected food class."""

    if mapping is None:
        mapping = load_mapping(mapping_path)

    entry = _find_class_entry(mapping, food_class)

    if entry is None:
        raise KeyError(
            f"No FoodKeeper mapping found for food class: {food_class}"
        )

    return entry


# --------------------------------------------------
# FoodKeeper product searching
# --------------------------------------------------

def get_searchable_text(record: dict) -> str:
    """
    Combine relevant FoodKeeper fields into one searchable string.
    """

    searchable_fields = [
        "Name",
        "Name_subtitle",
        "Keywords"
    ]

    values = []

    for field in searchable_fields:

        value = record.get(field)

        if value is not None:
            values.append(str(value))

    return normalize_text(" ".join(values))


def search_foodkeeper(
    records: list[dict],
    query: str
) -> list[dict]:
    """
    Search FoodKeeper products by name, subtitle, or keywords.

    Matches either the complete normalized query or all query
    words, allowing searches such as 'ground beef' to match
    records whose keywords contain 'Beef, ground'.
    """

    normalized_query = normalize_text(query)

    if not normalized_query:
        return []

    query_words = set(normalized_query.split())

    matches = []

    for record in records:

        searchable_text = get_searchable_text(record)

        if not searchable_text:
            continue

        searchable_words = set(searchable_text.split())

        if (
            normalized_query in searchable_text
            or query_words.issubset(searchable_words)
        ):
            matches.append(record)

    return matches


def search_by_product_ids(
    records: list[dict],
    product_ids: list
) -> list[dict]:
    """Find FoodKeeper records using configured USDA Product IDs."""

    normalized_ids = {
        normalize_product_id(product_id)
        for product_id in product_ids
    }

    normalized_ids.discard(None)

    return [
        record
        for record in records
        if normalize_product_id(record.get("ID")) in normalized_ids
    ]


# --------------------------------------------------
# Get FoodKeeper recommendations
# --------------------------------------------------


def get_recommendations(
    food_class: str,
    records: list[dict] | None = None,
    query: str | None = None,
    data_path: Path = DEFAULT_DATA_PATH,
    mapping_path: Path = DEFAULT_MAPPING_PATH
) -> list[dict]:
    """
    Return FoodKeeper candidates for a detected food class.

    Configured Product IDs are checked first. If no IDs are
    configured or found, the function searches using the
    mapping's search terms.

    Classes with no configured IDs or search terms return no
    candidates. This prevents unrelated products from being
    returned through broad name searches.
    """

    if records is None:
        records = load_foodkeeper(data_path)

    mapping = load_mapping(mapping_path)

    entry = get_mapping_entry(
        food_class,
        mapping=mapping
    )

    # Get configured lookup methods.
    product_ids = entry.get("product_ids") or []

    search_terms = (
        entry.get("search_terms")
        or entry.get("terms")
        or entry.get("keywords")
        or []
    )

    if isinstance(search_terms, str):
        search_terms = [search_terms]

    # Stop if this class has no approved FoodKeeper lookup.
    if not product_ids and not search_terms:
        return []

    # First try configured USDA Product IDs.
    matches = []

    if product_ids:
        matches = search_by_product_ids(
            records,
            product_ids
        )

    # If no IDs matched, use configured search terms.
    if not matches:

        for term in search_terms:

            term_matches = search_foodkeeper(
                records,
                term
            )

            for record in term_matches:

                if record not in matches:
                    matches.append(record)

    # A user-provided query narrows the class-specific candidates.
    if query:

        query_matches = search_foodkeeper(
            records,
            query
        )

        query_ids = {
            normalize_product_id(record.get("ID"))
            for record in query_matches
        }

        matches = [
            record
            for record in matches
            if normalize_product_id(record.get("ID")) in query_ids
        ]

    return matches


# --------------------------------------------------
# User confirmation workflow
# --------------------------------------------------

def get_foodkeeper_selection(
    food_class: str,
    records: list[dict] | None = None,
    query: str | None = None,
    selected_product_id: int | str | None = None,
    user_confirmed: bool = False,
    data_path: Path = DEFAULT_DATA_PATH,
    mapping_path: Path = DEFAULT_MAPPING_PATH
) -> dict:
    """
    Return FoodKeeper candidates and require confirmation
    before storage guidance can be used.

    selected_product_id:
        The USDA Product ID selected by the user.

    user_confirmed:
        True only after the user confirms the selected product
        and any additional details requested by the application.

    A class with requires_user_detail=True must have both a
    selected Product ID and explicit user confirmation.
    """

    if records is None:
        records = load_foodkeeper(data_path)

    mapping = load_mapping(mapping_path)

    entry = get_mapping_entry(
        food_class,
        mapping=mapping
    )

    candidates = get_recommendations(
        food_class=food_class,
        records=records,
        query=query,
        data_path=data_path,
        mapping_path=mapping_path
    )

    requires_user_detail = bool(
        entry.get("requires_user_detail", False)
    )

    detail_prompt = entry.get("detail_prompt")

    selected_record = None

    # No matching records: do not provide guidance.
    if not candidates:

        return {
            "food_class": food_class,
            "candidates": [],
            "requires_confirmation": True,
            "confirmation_prompt": (
                "No matching FoodKeeper products were found. "
                "Please provide more details about this food."
            ),
            "selected_record": None,
            "ready_for_guidance": False
        }

    # Validate a Product ID selected by the user.
    if selected_product_id is not None:

        selected_id = normalize_product_id(
            selected_product_id
        )

        if selected_id is None:
            raise ValueError(
                "The selected USDA Product ID is invalid."
            )

        selected_record = next(
            (
                record
                for record in candidates
                if normalize_product_id(record.get("ID")) == selected_id
            ),
            None
        )

        if selected_record is None:
            raise ValueError(
                f"Product ID {selected_id} is not a valid candidate "
                f"for food class '{food_class}'."
            )

    # Some food classes require additional user details.
    if requires_user_detail:

        ready_for_guidance = (
            selected_record is not None
            and user_confirmed
        )

        return {
            "food_class": food_class,
            "candidates": candidates,
            "requires_confirmation": not ready_for_guidance,
            "confirmation_prompt": (
                None
                if ready_for_guidance
                else (
                    detail_prompt
                    or "Please confirm the correct food product "
                       "and its condition."
                )
            ),
            "selected_record": (
                selected_record
                if ready_for_guidance
                else None
            ),
            "ready_for_guidance": ready_for_guidance
        }

    # Only automatically select when there is exactly one candidate.
    if len(candidates) == 1 and selected_record is None:
        selected_record = candidates[0]

    ready_for_guidance = selected_record is not None

    return {
        "food_class": food_class,
        "candidates": candidates,
        "requires_confirmation": not ready_for_guidance,
        "confirmation_prompt": (
            None
            if ready_for_guidance
            else "Please select the correct FoodKeeper product."
        ),
        "selected_record": (
            selected_record
            if ready_for_guidance
            else None
        ),
        "ready_for_guidance": ready_for_guidance
    }


def get_confirmed_storage_guidance(
    selection: dict
) -> dict:
    """
    Return storage guidance only after a specific FoodKeeper
    product has passed the confirmation workflow.
    """

    if not selection.get("ready_for_guidance"):
        raise ValueError(
            "Storage guidance cannot be retrieved until the "
            "food product and required details are confirmed."
        )

    record = selection.get("selected_record")

    if not record:
        raise ValueError(
            "No confirmed FoodKeeper record was selected."
        )

    return get_storage_guidance(record)


# --------------------------------------------------
# Extract storage guidance
# --------------------------------------------------


def get_storage_guidance(record: dict) -> dict:
    """
    Extract FoodKeeper storage guidance.

    Keeps normal storage, DOP storage, and after-opening/
    after-thawing recommendations separate.
    """

    storage_types = {
        "pantry": "Pantry",
        "refrigerate": "Refrigerate",
        "freeze": "Freeze",
        "dop_pantry": "DOP_Pantry",
        "dop_refrigerate": "DOP_Refrigerate",
        "dop_freeze": "DOP_Freeze",
        "pantry_after_opening": "Pantry_After_Opening",
        "refrigerate_after_opening": "Refrigerate_After_Opening",
        "refrigerate_after_thawing": "Refrigerate_After_Thawing"
    }

    guidance = {}

    for label, prefix in storage_types.items():

        minimum = record.get(f"{prefix}_Min")
        maximum = record.get(f"{prefix}_Max")
        metric = record.get(f"{prefix}_Metric")

        # Include a recommendation only when at least one
        # of its values is present.
        if any(value is not None for value in [minimum, maximum, metric]):

            guidance[label] = {
                "minimum": minimum,
                "maximum": maximum,
                "metric": metric
            }

        # Include storage tips when available.
        tips_field = (
            f"{prefix}_tips"
            if prefix in ["Pantry", "DOP_Pantry",
                          "Refrigerate", "DOP_Refrigerate"]
            else f"{prefix}_Tips"
        )

        tips = record.get(tips_field)

        if tips is not None and str(tips).strip():

            if label not in guidance:
                guidance[label] = {}

            guidance[label]["tips"] = tips

    return guidance



# --------------------------------------------------
# Product names and display helpers
# --------------------------------------------------

def get_record_name(record: dict) -> str:
    """Return a readable FoodKeeper product name."""

    name = record.get("Name", "Unknown food")

    subtitle = record.get("Name_subtitle")

    if subtitle:
        return f"{name} - {subtitle}"

    return str(name)



def print_record_summary(record: dict) -> None:
    """Print a readable summary of a FoodKeeper product."""

    print(f"Product ID: {record.get('ID', 'Unknown')}")
    print(f"Product: {get_record_name(record)}")

    keywords = record.get("Keywords")

    if keywords:
        print(f"Keywords: {keywords}")

    guidance = get_storage_guidance(record)

    print("Storage guidance:")

    if not guidance:
        print("  No storage guidance available.")
        return

    for storage_type, details in guidance.items():

        print(f"  {storage_type}:")

        minimum = details.get("minimum")
        maximum = details.get("maximum")
        metric = details.get("metric")

        if minimum is not None or maximum is not None:
            if minimum == maximum:
                print(f"    Duration: {minimum} {metric}")
            else:
                print(f"    Duration: {minimum}–{maximum} {metric}")

        if metric == "Not Recommended":
            print("    Storage is not recommended.")

        tips = details.get("tips")

        if tips:
            print(f"    Tips: {tips}")



# --------------------------------------------------
# Convenience function
# --------------------------------------------------

def find_foodkeeper_products(
    food_class: str,
    query: str | None = None
) -> list[dict]:
    """
    Load FoodKeeper data and find candidates for a food class.

    This function returns candidates only. Use
    get_foodkeeper_selection() to enforce confirmation before
    retrieving storage guidance.
    """

    records = load_foodkeeper()

    return get_recommendations(
        food_class=food_class,
        records=records,
        query=query
    )
