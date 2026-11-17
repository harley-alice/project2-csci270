"""
Endpoints for user feedback and correction records.
"""

from __future__ import annotations

import json
import logging
from typing import List

from fastapi import APIRouter, status

from backend.database import get_db
from backend.schemas import ModelFeedbackCreate, ModelFeedbackResponse

router = APIRouter(prefix="/api/feedback", tags=["Feedback & Telemetry"])
logger = logging.getLogger("fridge_tracker.routes.feedback")


@router.post(
    "",
    response_model=ModelFeedbackResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Record user correction or rejected item",
)
def record_feedback(feedback: ModelFeedbackCreate):
    bbox_str = json.dumps(feedback.bbox) if feedback.bbox is not None else None

    with get_db() as conn:
        cursor = conn.execute(
            """
            INSERT INTO model_feedback (
                timestamp, feedback_type, image_source, detection_id,
                predicted_label, corrected_label, confidence, bbox_json
            ) VALUES (COALESCE(?, datetime('now')), ?, ?, ?, ?, ?, ?, ?)
            RETURNING id;
            """,
            (
                feedback.timestamp,
                feedback.type,
                feedback.image_source,
                feedback.detection_id,
                feedback.predicted_label,
                feedback.corrected_label,
                feedback.confidence,
                bbox_str,
            ),
        )
        row = cursor.fetchone()
        feedback_id = row[0]

        logger.info(
            "Logged model feedback #%d [%s]: predicted='%s' -> corrected='%s'",
            feedback_id,
            feedback.type,
            feedback.predicted_label,
            feedback.corrected_label,
        )

        return ModelFeedbackResponse(
            success=True,
            id=feedback_id,
            message="Feedback telemetry successfully recorded.",
        )


@router.get(
    "",
    summary="List feedback entries",
)
def list_feedback(limit: int = 100):
    with get_db() as conn:
        cursor = conn.execute(
            """
            SELECT * FROM model_feedback
            ORDER BY id DESC
            LIMIT ?;
            """,
            (limit,),
        )
        rows = cursor.fetchall()
        return [dict(r) for r in rows]


