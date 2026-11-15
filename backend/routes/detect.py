"""
Inference API endpoints for fridge food detection.
"""

from __future__ import annotations

import logging
from typing import Optional

from fastapi import APIRouter, File, Form, HTTPException, Query, UploadFile, status

from backend.inference import ModelNotLoadedError, inference_service
from backend.schemas import DetectResponse

router = APIRouter(prefix="/api", tags=["Inference"])
# Un-prefixed router so the same handler is also served at POST /detect (the path Alice's local_test_server.py uses)
alias_router = APIRouter(tags=["Inference"])
logger = logging.getLogger("fridge_tracker.routes.detect")


@router.post(
    "/detect",
    response_model=DetectResponse,
    summary="Detect food items in an uploaded fridge photograph",
    description="Loads raw image file, generates tensor, executes YOLO inference, and applies FoodKeeper expiration calculations."
)
async def detect_food(
    file: UploadFile = File(..., description="Raw fridge photograph (JPEG, PNG, WebP)"),
    confidence_threshold: float = Query(
        0.25, ge=0.05, le=0.99, description="Confidence threshold for bounding boxes"
    ),
    package_state: str = Query(
        "sealed", description="Package state assumption for initial scan ('sealed' or 'opened')"
    ),
    storage_location: str = Query(
        "refrigerator", description="Storage location ('refrigerator', 'freezer', 'pantry')"
    ),
):
    try:
        content = await file.read()
        if not content:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Empty image file received.",
            )

        detections = inference_service.predict(
            image_bytes=content,
            confidence_threshold=confidence_threshold,
            package_state=package_state,
            storage_location=storage_location,
        )

        return DetectResponse(
            success=True,
            count=len(detections),
            confidence_threshold=confidence_threshold,
            detections=detections,
        )
    except HTTPException:
        raise  # e.g. the 400 for an empty file; do not turn it into a 500
    except ModelNotLoadedError as mnl:
        logger.error("Detection unavailable: %s", mnl)
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=str(mnl),
        )
    except ValueError as ve:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=str(ve),
        )
    except Exception as exc:
        logger.error("Detection failure: %s", exc, exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Inference error: {exc}",
        )


@router.post(
    "/infer",
    response_model=DetectResponse,
    summary="Alias inference endpoint",
)
async def infer_alias(
    file: UploadFile = File(...),
    confidence_threshold: float = Query(0.25, ge=0.05, le=0.99),
):
    # Pass every argument explicitly: calling the handler directly would otherwise leave the
    # remaining parameters as FastAPI Query(...) objects instead of their default values.
    return await detect_food(
        file=file,
        confidence_threshold=confidence_threshold,
        package_state="sealed",
        storage_location="refrigerator",
    )


# POST /detect -> exactly the same handler as POST /api/detect
alias_router.add_api_route(
    "/detect",
    detect_food,
    methods=["POST"],
    response_model=DetectResponse,
    summary="Alias of POST /api/detect",
)
