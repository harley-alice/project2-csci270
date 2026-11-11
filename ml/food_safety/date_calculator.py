"""
Conservative date helpers for confirmed FoodKeeper recommendations.

These functions perform calendar arithmetic only. They do not independently
determine whether food is safe to eat.
"""

from datetime import date, timedelta

from ml.food_safety.foodkeeper import get_confirmed_storage_guidance


def calculate_end_date(start_date: date, duration_days: int) -> date:
    """Calculate an estimated date from a numeric duration in days."""
    if not isinstance(start_date, date):
        raise TypeError("start_date must be a datetime.date object")

    if not isinstance(duration_days, int) or isinstance(duration_days, bool) or duration_days < 0:
        raise ValueError("duration_days must be a non-negative integer")

    return start_date + timedelta(days=duration_days)


def calculate_date_range(start_date: date, minimum_days: int, maximum_days: int):
    """Return earliest and latest dates for a numeric duration range."""
    if minimum_days > maximum_days:
        raise ValueError("minimum_days cannot exceed maximum_days")

    return (
        calculate_end_date(start_date, minimum_days),
        calculate_end_date(start_date, maximum_days),
    )


def calculate_confirmed_guidance_range(
    selection: dict,
    storage_type: str,
    start_date: date,
    start_event: str,
) -> dict:
    """
    Calculate a date range from a confirmed FoodKeeper recommendation.

    Only non-DOP recommendations measured in whole days are supported.

    The caller must establish that start_date corresponds to the correct
    starting event for the selected recommendation. Supported event labels
    are purchase, opening, cooking, and thawing.
    """

    # This also blocks unconfirmed or invalid selections.
    guidance = get_confirmed_storage_guidance(selection)

    if not isinstance(start_date, date):
        raise TypeError("start_date must be a datetime.date object")

    valid_events = {"purchase", "opening", "cooking", "thawing"}
    start_event = str(start_event).strip().lower()

    if start_event not in valid_events:
        raise ValueError(
            "start_event must be purchase, opening, cooking, or thawing."
        )

    storage_type = str(storage_type).strip().lower()

    if storage_type.startswith("dop_"):
        raise ValueError(
            "DOP recommendations are not supported until their "
            "starting-event meaning has been verified."
        )

    if storage_type not in guidance:
        raise ValueError(
            f"No '{storage_type}' recommendation is available."
        )

    recommendation = guidance[storage_type]

    metric = str(recommendation.get("metric") or "").strip().lower()

    if metric not in {"day", "days"}:
        raise ValueError(
            f"Unsupported duration unit: {recommendation.get('metric')!r}. "
            "Only day-based recommendations are currently supported."
        )

    tips = str(recommendation.get("tips") or "").lower()

    if "after cooking" in tips and start_event != "cooking":
        raise ValueError(
            "This recommendation is for storage after cooking. "
            "Use the cooking date as the starting event."
        )

    minimum = recommendation.get("minimum")
    maximum = recommendation.get("maximum")

    if minimum is None or maximum is None:
        raise ValueError("A complete minimum and maximum duration is required.")

    try:
        minimum_number = float(minimum)
        maximum_number = float(maximum)
    except (TypeError, ValueError):
        raise ValueError("FoodKeeper durations must be numeric.")

    if (
        not minimum_number.is_integer()
        or not maximum_number.is_integer()
    ):
        raise ValueError("Only whole-number day durations are supported.")

    minimum_days = int(minimum_number)
    maximum_days = int(maximum_number)

    if minimum_days < 0 or maximum_days < 0:
        raise ValueError("FoodKeeper durations cannot be negative.")

    if minimum_days > maximum_days:
        raise ValueError("Minimum duration cannot exceed maximum duration.")

    earliest, latest = calculate_date_range(
        start_date,
        minimum_days,
        maximum_days
    )

    return {
        "food_class": selection.get("food_class"),
        "storage_type": storage_type,
        "start_date": start_date,
        "start_event": start_event,
        "minimum_days": minimum_days,
        "maximum_days": maximum_days,
        "earliest_date": earliest,
        "latest_date": latest,
        "metric": "Days",
    }
