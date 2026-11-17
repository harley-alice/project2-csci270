"""
Endpoints for inventory items, item verification, and storage duration updates.
"""

from __future__ import annotations

import json
import logging
import uuid
from datetime import date, datetime, timedelta
from typing import List, Optional

from fastapi import APIRouter, HTTPException, Query, status

from backend.database import get_db
from backend.rule_engine import rule_engine
from backend.schemas import (
    InventoryBatchCreate,
    InventoryItemCreate,
    InventoryItemResponse,
    InventoryItemUpdate,
    ItemVerifyRequest,
    StorageDurationUpdateRequest,
)

router = APIRouter(prefix="/api/inventory", tags=["Inventory"])
logger = logging.getLogger("fridge_tracker.routes.inventory")


def _format_row_to_response(row) -> InventoryItemResponse:
    today = date.today()
    exp_date = datetime.strptime(row["expiration_date"], "%Y-%m-%d").date()
    days_remaining = (exp_date - today).days

    bbox = None
    if row["bbox_ymin"] is not None:
        bbox = [
            row["bbox_ymin"],
            row["bbox_xmin"],
            row["bbox_ymax"],
            row["bbox_xmax"],
        ]

    is_urgent = days_remaining <= 3 and not (days_remaining < 0)
    is_expired = days_remaining < 0

    return InventoryItemResponse(
        id=row["id"],
        food_class=row["food_class"],
        display_name=row["food_class"].replace("_", " ").title(),
        custom_name=row["custom_name"],
        category_id=row["category_id"],
        category_name=row["category_name"] if "category_name" in row.keys() else None,
        package_state=row["package_state"],
        storage_location=row["storage_location"],
        is_cooked=bool(row["is_cooked"]),
        added_date=row["added_date"],
        expiration_date=row["expiration_date"],
        shelf_life_days=row["shelf_life_days"],
        days_remaining=days_remaining,
        verified=bool(row["verified"]),
        confidence=row["confidence"],
        bbox=bbox,
        safety_tier=row["safety_tier"],
        user_notes=row["user_notes"],
        usda_guidance=row["usda_guidance"] if "usda_guidance" in row.keys() else None,
        is_urgent=is_urgent,
        is_expired=is_expired,
        created_at=row["created_at"],
        updated_at=row["updated_at"],
    )


@router.get(
    "",
    response_model=List[InventoryItemResponse],
    summary="List stored inventory items",
    description="Retrieve inventory items with remaining storage days.",
)
def list_inventory(
    storage_location: Optional[str] = Query(None, description="Filter by location (e.g. refrigerator)"),
    verified: Optional[bool] = Query(None, description="Filter by verification state"),
    safety_tier: Optional[str] = Query(None, description="Filter by safety tier (tier_1, tier_2, tier_3)"),
):
    with get_db() as conn:
        query = """
            SELECT i.*, c.name as category_name, r.usda_guidance
            FROM inventory_items i
            LEFT JOIN food_categories c ON i.category_id = c.id
            LEFT JOIN storage_rules r ON (
                r.food_class = i.food_class AND
                r.package_state = i.package_state AND
                r.storage_location = i.storage_location AND
                r.is_cooked = i.is_cooked
            )
            WHERE 1=1
        """
        params = []
        if storage_location:
            query += " AND i.storage_location = ?"
            params.append(storage_location)
        if verified is not None:
            query += " AND i.verified = ?"
            params.append(1 if verified else 0)
        if safety_tier:
            query += " AND i.safety_tier = ?"
            params.append(safety_tier)

        query += " ORDER BY i.expiration_date ASC;"

        cursor = conn.execute(query, params)
        rows = cursor.fetchall()
        return [_format_row_to_response(r) for r in rows]


@router.post(
    "",
    response_model=InventoryItemResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Add an item to fridge inventory",
    description="Adds an item. If expiration date is missing, calculates it with the rule engine.",
)
def create_inventory_item(item: InventoryItemCreate):
    today = date.today()
    added_date = datetime.strptime(item.added_date, "%Y-%m-%d").date() if item.added_date else today

    # Calculate expiration using rule engine if not specified
    rule_calc = rule_engine.calculate_expiration(
        food_class=item.food_class,
        package_state=item.package_state,
        storage_location=item.storage_location,
        is_cooked=item.is_cooked,
        start_date=added_date,
    )

    shelf_life = item.shelf_life_days if item.shelf_life_days is not None else rule_calc["recommended_shelf_life_days"]
    exp_date = item.expiration_date if item.expiration_date else (added_date + timedelta(days=shelf_life)).isoformat()
    safety_tier = rule_calc["safety_tier"]

    item_id = str(uuid.uuid4())[:8]

    ymin = item.bbox[0] if item.bbox and len(item.bbox) == 4 else None
    xmin = item.bbox[1] if item.bbox and len(item.bbox) == 4 else None
    ymax = item.bbox[2] if item.bbox and len(item.bbox) == 4 else None
    xmax = item.bbox[3] if item.bbox and len(item.bbox) == 4 else None

    with get_db() as conn:
        # Look up category identifier if present
        cat_cur = conn.execute(
            "SELECT id FROM food_categories WHERE tier = ? LIMIT 1;", (safety_tier,)
        )
        cat_row = cat_cur.fetchone()
        category_id = cat_row["id"] if cat_row else None

        conn.execute(
            """
            INSERT INTO inventory_items (
                id, food_class, custom_name, category_id, package_state,
                storage_location, is_cooked, added_date, expiration_date,
                shelf_life_days, verified, confidence, bbox_ymin, bbox_xmin,
                bbox_ymax, bbox_xmax, safety_tier, user_notes, created_at, updated_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, datetime('now'), datetime('now'));
            """,
            (
                item_id,
                rule_calc["food_class"],
                item.custom_name,
                category_id,
                item.package_state,
                item.storage_location,
                1 if item.is_cooked else 0,
                added_date.isoformat(),
                exp_date,
                shelf_life,
                1 if item.verified else 0,
                item.confidence,
                ymin,
                xmin,
                ymax,
                xmax,
                safety_tier,
                item.user_notes,
            ),
        )

        # Retrieve the newly added record
        cursor = conn.execute(
            """
            SELECT i.*, c.name as category_name, r.usda_guidance
            FROM inventory_items i
            LEFT JOIN food_categories c ON i.category_id = c.id
            LEFT JOIN storage_rules r ON (
                r.food_class = i.food_class AND
                r.package_state = i.package_state AND
                r.storage_location = i.storage_location AND
                r.is_cooked = i.is_cooked
            )
            WHERE i.id = ?;
            """,
            (item_id,),
        )
        row = cursor.fetchone()
        return _format_row_to_response(row)


@router.post(
    "/batch",
    response_model=List[InventoryItemResponse],
    status_code=status.HTTP_201_CREATED,
    summary="Add multiple items to inventory",
)
def batch_create_inventory(batch: InventoryBatchCreate):
    created = []
    for item in batch.items:
        created.append(create_inventory_item(item))
    return created


@router.get(
    "/{item_id}",
    response_model=InventoryItemResponse,
    summary="Get one inventory item by ID",
)
def get_inventory_item(item_id: str):
    with get_db() as conn:
        cursor = conn.execute(
            """
            SELECT i.*, c.name as category_name, r.usda_guidance
            FROM inventory_items i
            LEFT JOIN food_categories c ON i.category_id = c.id
            LEFT JOIN storage_rules r ON (
                r.food_class = i.food_class AND
                r.package_state = i.package_state AND
                r.storage_location = i.storage_location AND
                r.is_cooked = i.is_cooked
            )
            WHERE i.id = ?;
            """,
            (item_id,),
        )
        row = cursor.fetchone()
        if not row:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Inventory item '{item_id}' not found.",
            )
        return _format_row_to_response(row)


@router.put(
    "/{item_id}",
    response_model=InventoryItemResponse,
    summary="Update inventory item details",
)
def update_inventory_item(item_id: str, update: InventoryItemUpdate):
    with get_db() as conn:
        cursor = conn.execute("SELECT * FROM inventory_items WHERE id = ?;", (item_id,))
        existing = cursor.fetchone()
        if not existing:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Inventory item '{item_id}' not found.",
            )

        food_class = update.food_class if update.food_class is not None else existing["food_class"]
        custom_name = update.custom_name if update.custom_name is not None else existing["custom_name"]
        pkg_state = update.package_state if update.package_state is not None else existing["package_state"]
        location = update.storage_location if update.storage_location is not None else existing["storage_location"]
        is_cooked = update.is_cooked if update.is_cooked is not None else bool(existing["is_cooked"])
        user_notes = update.user_notes if update.user_notes is not None else existing["user_notes"]
        verified = update.verified if update.verified is not None else bool(existing["verified"])

        # Recalculate duration if class, package condition, or location changed
        if update.expiration_date:
            exp_date = update.expiration_date
            shelf_life = update.shelf_life_days if update.shelf_life_days is not None else existing["shelf_life_days"]
        else:
            calc = rule_engine.calculate_expiration(
                food_class=food_class,
                package_state=pkg_state,
                storage_location=location,
                is_cooked=is_cooked,
                start_date=date.today(),
            )
            shelf_life = update.shelf_life_days if update.shelf_life_days is not None else calc["recommended_shelf_life_days"]
            exp_date = (date.today() + timedelta(days=shelf_life)).isoformat()

        conn.execute(
            """
            UPDATE inventory_items
            SET food_class = ?,
                custom_name = ?,
                package_state = ?,
                storage_location = ?,
                is_cooked = ?,
                expiration_date = ?,
                shelf_life_days = ?,
                verified = ?,
                user_notes = ?,
                updated_at = datetime('now')
            WHERE id = ?;
            """,
            (
                food_class,
                custom_name,
                pkg_state,
                location,
                1 if is_cooked else 0,
                exp_date,
                shelf_life,
                1 if verified else 0,
                user_notes,
                item_id,
            ),
        )

        cursor = conn.execute(
            """
            SELECT i.*, c.name as category_name, r.usda_guidance
            FROM inventory_items i
            LEFT JOIN food_categories c ON i.category_id = c.id
            LEFT JOIN storage_rules r ON (
                r.food_class = i.food_class AND
                r.package_state = i.package_state AND
                r.storage_location = i.storage_location AND
                r.is_cooked = i.is_cooked
            )
            WHERE i.id = ?;
            """,
            (item_id,),
        )
        return _format_row_to_response(cursor.fetchone())


@router.delete(
    "/{item_id}",
    status_code=status.HTTP_200_OK,
    summary="Delete item from inventory",
)
def delete_inventory_item(item_id: str):
    with get_db() as conn:
        cursor = conn.execute("DELETE FROM inventory_items WHERE id = ?;", (item_id,))
        if cursor.rowcount == 0:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Inventory item '{item_id}' not found.",
            )
        return {"success": True, "message": f"Item '{item_id}' deleted successfully."}


@router.post(
    "/{item_id}/verify",
    response_model=InventoryItemResponse,
    summary="Confirm or correct an inventory item",
    description="Marks item as verified, updates the food class, and recalculates expiration dates.",
)
@router.put(
    "/{item_id}/verify",
    response_model=InventoryItemResponse,
    summary="Confirm or correct an inventory item (PUT alias)",
)
def verify_inventory_item(item_id: str, req: ItemVerifyRequest):
    """
    User verification workflow:
    1. Read the stored item.
    2. Update values confirmed by user.
    3. Run rule calculations for new expiration dates.
    4. Save verification telemetry to feedback table.
    """
    with get_db() as conn:
        cursor = conn.execute("SELECT * FROM inventory_items WHERE id = ?;", (item_id,))
        item = cursor.fetchone()
        if not item:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Inventory item '{item_id}' not found.",
            )

        orig_class = item["food_class"]
        target_class = req.confirmed_food_class or orig_class
        pkg_state = req.package_state or item["package_state"]
        location = req.storage_location or item["storage_location"]
        is_cooked = req.is_cooked if req.is_cooked is not None else bool(item["is_cooked"])

        # Calculate new expiration window from verified data
        calc = rule_engine.calculate_expiration(
            food_class=target_class,
            package_state=pkg_state,
            storage_location=location,
            is_cooked=is_cooked,
            start_date=date.today(),
        )

        new_shelf_life = calc["recommended_shelf_life_days"]
        new_exp_date = calc["expiration_date"]
        new_tier = calc["safety_tier"]

        conn.execute(
            """
            UPDATE inventory_items
            SET food_class = ?,
                package_state = ?,
                storage_location = ?,
                is_cooked = ?,
                shelf_life_days = ?,
                expiration_date = ?,
                safety_tier = ?,
                verified = 1,
                user_notes = COALESCE(?, user_notes),
                updated_at = datetime('now')
            WHERE id = ?;
            """,
            (
                calc["food_class"],
                pkg_state,
                location,
                1 if is_cooked else 0,
                new_shelf_life,
                new_exp_date,
                new_tier,
                req.user_notes,
                item_id,
            ),
        )

        # Record feedback record if class was changed
        if target_class != orig_class:
            bbox_json = None
            if item["bbox_ymin"] is not None:
                bbox_json = json.dumps([
                    item["bbox_ymin"], item["bbox_xmin"],
                    item["bbox_ymax"], item["bbox_xmax"]
                ])

            conn.execute(
                """
                INSERT INTO model_feedback (
                    feedback_type, image_source, detection_id,
                    predicted_label, corrected_label, confidence, bbox_json
                ) VALUES (?, 'inventory_verification', ?, ?, ?, ?, ?);
                """,
                (
                    "user_correction",
                    item_id,
                    orig_class,
                    target_class,
                    item["confidence"],
                    bbox_json,
                ),
            )

        cursor = conn.execute(
            """
            SELECT i.*, c.name as category_name, r.usda_guidance
            FROM inventory_items i
            LEFT JOIN food_categories c ON i.category_id = c.id
            LEFT JOIN storage_rules r ON (
                r.food_class = i.food_class AND
                r.package_state = i.package_state AND
                r.storage_location = i.storage_location AND
                r.is_cooked = i.is_cooked
            )
            WHERE i.id = ?;
            """,
            (item_id,),
        )
        return _format_row_to_response(cursor.fetchone())


@router.patch(
    "/{item_id}/duration",
    response_model=InventoryItemResponse,
    summary="Update package state and storage duration",
    description="Updates expiration dates when package state or storage location changes.",
)
@router.put(
    "/{item_id}/storage-duration",
    response_model=InventoryItemResponse,
    summary="Update package state and storage duration (PUT alias)",
)
def update_storage_duration(item_id: str, req: StorageDurationUpdateRequest):
    """
    Handle storage duration changes:
    - User marks item opened -> calculate opened storage duration.
    - User moves item to freezer -> calculate freezer duration.
    - User enters custom duration override.
    """
    with get_db() as conn:
        cursor = conn.execute("SELECT * FROM inventory_items WHERE id = ?;", (item_id,))
        item = cursor.fetchone()
        if not item:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Inventory item '{item_id}' not found.",
            )

        pkg_state = req.package_state if req.package_state is not None else item["package_state"]
        location = req.storage_location if req.storage_location is not None else item["storage_location"]
        is_cooked = req.is_cooked if req.is_cooked is not None else bool(item["is_cooked"])

        if req.custom_shelf_life_days is not None:
            shelf_life = max(1, req.custom_shelf_life_days)
            exp_date = (date.today() + timedelta(days=shelf_life)).isoformat()
        else:
            calc = rule_engine.calculate_expiration(
                food_class=item["food_class"],
                package_state=pkg_state,
                storage_location=location,
                is_cooked=is_cooked,
                start_date=date.today(),
            )
            shelf_life = calc["recommended_shelf_life_days"]
            exp_date = calc["expiration_date"]

        conn.execute(
            """
            UPDATE inventory_items
            SET package_state = ?,
                storage_location = ?,
                is_cooked = ?,
                shelf_life_days = ?,
                expiration_date = ?,
                updated_at = datetime('now')
            WHERE id = ?;
            """,
            (
                pkg_state,
                location,
                1 if is_cooked else 0,
                shelf_life,
                exp_date,
                item_id,
            ),
        )

        cursor = conn.execute(
            """
            SELECT i.*, c.name as category_name, r.usda_guidance
            FROM inventory_items i
            LEFT JOIN food_categories c ON i.category_id = c.id
            LEFT JOIN storage_rules r ON (
                r.food_class = i.food_class AND
                r.package_state = i.package_state AND
                r.storage_location = i.storage_location AND
                r.is_cooked = i.is_cooked
            )
            WHERE i.id = ?;
            """,
            (item_id,),
        )
        return _format_row_to_response(cursor.fetchone())


