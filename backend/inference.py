"""
PyTorch & Ultralytics YOLOv8 backend inference handler.

Loads the trained food detection weights, processes raw image uploads into tensors,
runs inference, formats normalized bounding boxes, and integrates with the
Hybrid AI Rule Engine to compute dynamic expiration windows.
"""

from __future__ import annotations

import io
import logging
import uuid
from pathlib import Path
from typing import Any, Dict, List, Optional

import torch
from PIL import Image
from ultralytics import YOLO

from backend.rule_engine import rule_engine
from backend.safety_adapter import assess as assess_safety

logger = logging.getLogger("fridge_tracker.inference")

PROJECT_ROOT = Path(__file__).resolve().parent.parent
DEFAULT_WEIGHTS_PATH = PROJECT_ROOT / "ml" / "export" / "food_detector_v8n_baseline.pt"


class ModelNotLoadedError(RuntimeError):
    """Raised when detection is requested but the YOLO weights are missing or failed to load."""


class FoodInferenceService:
    """
    Manages model loading, raw image transformation into tensors,
    and post-processing detection outputs combined with FoodKeeper rules.
    """

    def __init__(self, weights_path: Path | str = DEFAULT_WEIGHTS_PATH):
        self.weights_path = Path(weights_path)
        self.model: Optional[YOLO] = None
        self.load_error: Optional[str] = None
        self.device = "cuda" if torch.cuda.is_available() else ("mps" if torch.backends.mps.is_available() else "cpu")
        self._load_model()

    def _load_model(self) -> None:
        """Load trained Ultralytics YOLOv8 weights into device."""
        if not self.weights_path.exists():
            self.load_error = f"Model weights not found at {self.weights_path}."
            logger.error("%s Detection requests will return HTTP 503.", self.load_error)
            return

        try:
            logger.info("Loading YOLO weights from %s onto %s...", self.weights_path, self.device)
            self.model = YOLO(str(self.weights_path))
            logger.info("YOLO model loaded successfully. Classes: %d", len(self.model.names))
        except Exception as exc:
            logger.error("Failed to load YOLO model: %s", exc)
            self.model = None
            self.load_error = f"Model weights at {self.weights_path} could not be loaded: {exc}"

    @property
    def model_loaded(self) -> bool:
        return self.model is not None

    def status(self) -> Dict[str, Any]:
        """Real model state for /api/health."""
        return {
            "yolo_model": "loaded" if self.model_loaded else "not_loaded",
            "weights_path": str(self.weights_path),
            "weights_exists": self.weights_path.exists(),
        }

    def process_raw_image(self, image_bytes: bytes) -> Image.Image:
        """
        Validate and preprocess raw image bytes into an RGB PIL Image.
        Raises ValueError if bytes do not represent a valid image.
        """
        if not image_bytes:
            raise ValueError("Uploaded image file is empty.")

        try:
            image = Image.open(io.BytesIO(image_bytes))
            image.verify()  # verify integrity
            # Reopen because verify() closes the file pointer
            image = Image.open(io.BytesIO(image_bytes)).convert("RGB")
            return image
        except Exception as exc:
            raise ValueError(f"Invalid or corrupted image format: {exc}") from exc

    def predict(
        self,
        image_bytes: bytes,
        confidence_threshold: float = 0.25,
        iou_threshold: float = 0.45,
        package_state: str = "sealed",
        storage_location: str = "refrigerator",
    ) -> List[Dict[str, Any]]:
        """
        Run inference on raw image bytes.

        1. Converts raw image bytes into an RGB tensor.
        2. Executes YOLO forward pass with NMS and confidence thresholding.
        3. Normalizes bounding boxes to [ymin, xmin, ymax, xmax] relative to image dimensions.
        4. Queries Hybrid AI Rule Engine to enrich each detected object with dynamic
           FoodKeeper shelf life windows based on package state.
        """
        if self.model is None:
            msg = self.load_error or f"Model weights not found at {self.weights_path}."
            raise ModelNotLoadedError(f"{msg} Unzip model_export.zip at the repo root.")

        image = self.process_raw_image(image_bytes)
        img_w, img_h = image.size

        # Run inference through Ultralytics YOLO
        # Passing PIL.Image converts internally to PyTorch tensor on self.device
        results = self.model.predict(
            source=image,
            conf=confidence_threshold,
            iou=iou_threshold,
            device=self.device,
            verbose=False,
        )

        detections: List[Dict[str, Any]] = []

        if not results:
            return detections

        first_res = results[0]
        boxes = first_res.boxes

        if boxes is None or len(boxes) == 0:
            return detections

        for idx, box in enumerate(boxes):
            cls_id = int(box.cls.item())
            raw_label = self.model.names.get(cls_id, f"unknown_{cls_id}")
            conf = float(box.conf.item())

            # Ultralytics xyxy coordinates [xmin, ymin, xmax, ymax]
            xyxy = box.xyxy[0].tolist()
            xmin, ymin, xmax, ymax = xyxy

            # Normalize to [ymin, xmin, ymax, xmax] between 0.0 and 1.0 (matching frontend format)
            norm_ymin = max(0.0, min(1.0, ymin / img_h))
            norm_xmin = max(0.0, min(1.0, xmin / img_w))
            norm_ymax = max(0.0, min(1.0, ymax / img_h))
            norm_xmax = max(0.0, min(1.0, xmax / img_w))

            # Display-only fields (name, category, container flag) come from CJ's rule engine.
            rule_info = rule_engine.calculate_expiration(
                food_class=raw_label,
                package_state=package_state,
                storage_location=storage_location,
            )
            # Source of truth for safety (Ashton's ml/food_safety via the adapter): tier,
            # requires_confirmation and shelf-life days. Her days are None until the product is
            # confirmed or when she does not support the product; rule_engine's hand-entered day
            # counts are deliberately NOT used for detections (they bypass her confirmation gate).
            safety = assess_safety(
                rule_info["food_class"],
                package_state=package_state,
                storage_location=storage_location,
            )

            det_id = str(uuid.uuid4())[:8]

            detections.append({
                "id": det_id,
                "label": rule_info["food_class"],
                "display_name": rule_info["display_name"],
                "confidence": round(conf, 4),
                "days": safety["days"],
                "days_min": safety["days_min"],
                "days_max": safety["days_max"],
                "bbox": [
                    round(norm_ymin, 4),
                    round(norm_xmin, 4),
                    round(norm_ymax, 4),
                    round(norm_xmax, 4),
                ],
                "safety_tier": safety["safety_tier"],
                "category_name": rule_info["category_name"],
                "package_state": package_state,
                "storage_location": storage_location,
                "requires_user_detail": safety["requires_confirmation"],
                "detail_prompt": safety["confirmation_prompt"],
                # CJ's guidance text quotes day counts, so only show it once Ashton gives days
                "usda_guidance": rule_info["usda_guidance"] if safety["days"] is not None else None,
                "is_container": rule_info["is_container"],
                "is_high_risk": safety["safety_tier"] == "tier_1",
                "requires_confirmation": safety["requires_confirmation"],
            })

        return detections


# Singleton instance
inference_service = FoodInferenceService()

