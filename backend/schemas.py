"""
Pydantic schemas for API request and response data structures.
"""

from __future__ import annotations

from datetime import date
from typing import Any, List, Optional
from pydantic import BaseModel, Field


# --- Inference Schemas ---

class DetectionItem(BaseModel):
    id: str
    label: str
    display_name: str
    confidence: float
    # days* are None when Ashton's food-safety workflow gives no confirmed, day-based guidance
    # (confirmation still needed, or the product is unsupported). See backend/safety_adapter.py.
    days: Optional[int] = None
    days_min: Optional[int] = None
    days_max: Optional[int] = None
    bbox: List[float] = Field(..., description="[ymin, xmin, ymax, xmax] in normalized 0.0-1.0 range")
    safety_tier: str
    category_name: str
    package_state: str = "sealed"
    storage_location: str = "refrigerator"
    requires_user_detail: bool = False
    detail_prompt: Optional[str] = None
    usda_guidance: Optional[str] = None
    is_container: bool = False
    is_high_risk: bool = False
    # True until the user has confirmed the product (always True for meat/poultry/seafood and jars)
    requires_confirmation: bool = True


class DetectResponse(BaseModel):
    success: bool = True
    count: int
    confidence_threshold: float
    detections: List[DetectionItem]


# --- Rule Calculation Schemas ---

class RuleCalculationRequest(BaseModel):
    food_class: str
    package_state: str = Field("sealed", description="'sealed' or 'opened'")
    storage_location: str = Field("refrigerator", description="'refrigerator', 'freezer', or 'pantry'")
    is_cooked: bool = False
    start_date: Optional[date] = None


class RuleCalculationResponse(BaseModel):
    food_class: str
    display_name: str
    package_state: str
    storage_location: str
    is_cooked: bool
    start_date: str
    shelf_life_days_min: int
    shelf_life_days_max: int
    recommended_shelf_life_days: int
    expiration_date: str
    earliest_expiration_date: str
    latest_expiration_date: str
    safety_tier: str
    category_name: str
    requires_user_detail: bool
    detail_prompt: Optional[str] = None
    usda_guidance: Optional[str] = None
    is_container: bool
    is_high_risk: bool
    is_urgent: bool


# --- Inventory Schemas ---

class InventoryItemCreate(BaseModel):
    food_class: str
    custom_name: Optional[str] = None
    package_state: str = "sealed"
    storage_location: str = "refrigerator"
    is_cooked: bool = False
    added_date: Optional[str] = None
    expiration_date: Optional[str] = None
    shelf_life_days: Optional[int] = None
    verified: bool = False
    confidence: Optional[float] = None
    bbox: Optional[List[float]] = None
    user_notes: Optional[str] = None


class InventoryBatchCreate(BaseModel):
    items: List[InventoryItemCreate]


class InventoryItemUpdate(BaseModel):
    food_class: Optional[str] = None
    custom_name: Optional[str] = None
    package_state: Optional[str] = None
    storage_location: Optional[str] = None
    is_cooked: Optional[bool] = None
    shelf_life_days: Optional[int] = None
    expiration_date: Optional[str] = None
    verified: Optional[bool] = None
    user_notes: Optional[str] = None


class ItemVerifyRequest(BaseModel):
    confirmed_food_class: Optional[str] = Field(None, description="Corrected or confirmed food class")
    package_state: Optional[str] = Field(None, description="Confirmed package state: 'sealed' or 'opened'")
    storage_location: Optional[str] = Field(None, description="Storage location: 'refrigerator', 'freezer', 'pantry'")
    is_cooked: Optional[bool] = None
    user_notes: Optional[str] = None


class StorageDurationUpdateRequest(BaseModel):
    package_state: Optional[str] = Field(None, description="'opened' vs 'sealed'")
    storage_location: Optional[str] = Field(None, description="'refrigerator', 'freezer', 'pantry'")
    custom_shelf_life_days: Optional[int] = Field(None, description="Explicit shelf life override in days")
    is_cooked: Optional[bool] = None


class InventoryItemResponse(BaseModel):
    id: str
    food_class: str
    display_name: str
    custom_name: Optional[str] = None
    category_id: Optional[int] = None
    category_name: Optional[str] = None
    package_state: str
    storage_location: str
    is_cooked: bool
    added_date: str
    expiration_date: str
    shelf_life_days: int
    days_remaining: int
    verified: bool
    confidence: Optional[float] = None
    bbox: Optional[List[float]] = None
    safety_tier: Optional[str] = None
    user_notes: Optional[str] = None
    usda_guidance: Optional[str] = None
    is_urgent: bool
    is_expired: bool
    created_at: str
    updated_at: str


# --- Category & Storage Rule Schemas ---

class CategoryResponse(BaseModel):
    id: int
    name: str
    tier: str
    priority: int
    description: Optional[str] = None


class StorageRuleResponse(BaseModel):
    id: int
    food_class: str
    category_id: Optional[int] = None
    category_name: Optional[str] = None
    safety_tier: Optional[str] = None
    package_state: str
    storage_location: str
    is_cooked: bool
    shelf_life_days_min: int
    shelf_life_days_max: int
    recommended_shelf_life_days: int
    requires_user_detail: bool
    detail_prompt: Optional[str] = None
    usda_guidance: Optional[str] = None


# --- Model Feedback Schemas ---

class ModelFeedbackCreate(BaseModel):
    timestamp: Optional[str] = None
    type: str = Field(..., description="e.g. 'user_correction', 'false_positive_rejected'")
    image_source: Optional[str] = None
    detection_id: Optional[str] = None
    predicted_label: Optional[str] = None
    corrected_label: Optional[str] = None
    confidence: Optional[float] = None
    bbox: Optional[Any] = None


class ModelFeedbackResponse(BaseModel):
    success: bool = True
    id: int
    message: str

