"""
Endpoints for categories and storage duration rules.
"""

from __future__ import annotations

from typing import List, Optional

from fastapi import APIRouter, Query

from backend.database import get_db
from backend.rule_engine import rule_engine
from backend.schemas import (
    CategoryResponse,
    RuleCalculationRequest,
    RuleCalculationResponse,
    StorageRuleResponse,
)

router = APIRouter(prefix="/api", tags=["Rules & Categories"])


@router.get(
    "/categories",
    response_model=List[CategoryResponse],
    summary="List all food categories and safety tiers",
)
def list_categories():
    with get_db() as conn:
        cursor = conn.execute(
            "SELECT * FROM food_categories ORDER BY priority ASC, id ASC;"
        )
        rows = cursor.fetchall()
        return [
            CategoryResponse(
                id=r["id"],
                name=r["name"],
                tier=r["tier"],
                priority=r["priority"],
                description=r["description"],
            )
            for r in rows
        ]


@router.get(
    "/rules",
    response_model=List[StorageRuleResponse],
    summary="List food storage duration rules",
)
def list_rules(
    food_class: Optional[str] = Query(None, description="Filter by food class"),
    package_state: Optional[str] = Query(None, description="Filter by package condition ('sealed' or 'opened')"),
    storage_location: Optional[str] = Query(None, description="Filter by storage location"),
):
    with get_db() as conn:
        query = """
            SELECT r.*, c.name as category_name, c.tier as safety_tier
            FROM storage_rules r
            LEFT JOIN food_categories c ON r.category_id = c.id
            WHERE 1=1
        """
        params = []
        if food_class:
            query += " AND r.food_class = ?"
            params.append(rule_engine.normalize_food_class(food_class))
        if package_state:
            query += " AND r.package_state = ?"
            params.append(package_state)
        if storage_location:
            query += " AND r.storage_location = ?"
            params.append(storage_location)

        query += " ORDER BY r.food_class ASC, r.is_cooked ASC, r.package_state ASC;"
        cursor = conn.execute(query, params)
        rows = cursor.fetchall()

        return [
            StorageRuleResponse(
                id=r["id"],
                food_class=r["food_class"],
                category_id=r["category_id"],
                category_name=r["category_name"],
                safety_tier=r["safety_tier"],
                package_state=r["package_state"],
                storage_location=r["storage_location"],
                is_cooked=bool(r["is_cooked"]),
                shelf_life_days_min=r["shelf_life_days_min"],
                shelf_life_days_max=r["shelf_life_days_max"],
                recommended_shelf_life_days=r["recommended_shelf_life_days"],
                requires_user_detail=bool(r["requires_user_detail"]),
                detail_prompt=r["detail_prompt"],
                usda_guidance=r["usda_guidance"],
            )
            for r in rows
        ]


@router.post(
    "/rules/calculate",
    response_model=RuleCalculationResponse,
    summary="Calculate storage durations using food safety rules",
)
def calculate_rule(req: RuleCalculationRequest):
    result = rule_engine.calculate_expiration(
        food_class=req.food_class,
        package_state=req.package_state,
        storage_location=req.storage_location,
        is_cooked=req.is_cooked,
        start_date=req.start_date,
    )
    return RuleCalculationResponse(**result)


