"""
Conservative date helper for FoodKeeper storage periods.

This module deliberately does not parse arbitrary FoodKeeper duration strings
yet. FoodKeeper values can be ranges, qualitative phrases, or condition-specific.
Use this helper only after the application has selected a specific numeric
recommendation and the correct starting event (purchase/opening/cooking).
"""

from datetime import date, timedelta


def calculate_end_date(start_date: date, duration_days: int) -> date:
    """
    Calculate an estimated end date from a confirmed numeric duration.

    This is calendar arithmetic only; it is not a food-safety determination.
    """
    if not isinstance(start_date, date):
        raise TypeError("start_date must be a datetime.date object")
    if not isinstance(duration_days, int) or duration_days < 0:
        raise ValueError("duration_days must be a non-negative integer")
    return start_date + timedelta(days=duration_days)


def calculate_date_range(start_date: date, minimum_days: int, maximum_days: int):
    """Return (earliest, latest) dates for a numeric FoodKeeper range."""
    if minimum_days > maximum_days:
        raise ValueError("minimum_days cannot exceed maximum_days")
    return (
        calculate_end_date(start_date, minimum_days),
        calculate_end_date(start_date, maximum_days),
    )
