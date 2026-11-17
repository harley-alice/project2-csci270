"""
Model inference processing module.
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

logger = logging.getLogger("fridge_tracker.inference")

PROJECT_ROOT = Path(__file__).resolve().parent.parent
DEFAULT_WEIGHTS_PATH = PROJECT_ROOT / "ml" / "export" / "food_detector_v8n_baseline.pt"


class FoodInferenceService:
    """
    Load model weights and process images to identify food items.
    """

    def __init__(self, weights_path: Path | str = DEFAULT_WEIGHTS_PATH):
        self.weights_path = Path(weights_path)
        self.model: Optional[YOLO] = None
        self.device = "cuda" if torch.cuda.is_available() else ("mps" if torch.backends.mps.is_available() else "cpu")
        self._load_model()

    def _load_model(self) -> None:
        """Load the model file onto the computing device."""
        if not self.weights_path.exists():
            logger.warning(
                "Model weights not found at %s. Inference service will operate in mock mode.",
                self.weights_path,
            )
            return

        try:
            logger.info("Loading YOLO weights from %s onto %s...", self.weights_path, self.device)
            self.model = YOLO(str(self.weights_path))
            logger.info("YOLO model loaded successfully. Classes: %d", len(self.model.names))
            # Run one test frame to prepare the device
            try:
                dummy_img = Image.new("RGB", (640, 640), color=(128, 128, 128))
                self.model.predict(source=dummy_img, imgsz=640, device=self.device, verbose=False)
                logger.info("YOLO model warm-up pass complete.")
            except Exception as warmup_err:
                logger.debug("Warm-up pass skipped: %s", warmup_err)
        except Exception as exc:
            logger.error("Failed to load YOLO model: %s", exc)
            self.model = None

    def process_raw_image(self, image_bytes: bytes) -> Image.Image:
        """
        Validate and convert raw image bytes into an RGB image object.
        """
        if not image_bytes:
            raise ValueError("Uploaded image file is empty.")

        try:
            image = Image.open(io.BytesIO(image_bytes))
            image.verify()  # Check that file data is complete
            # Reopen the image because verify closes the byte stream
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
        Identify food items in raw image bytes:
        1. Convert image bytes to an RGB image.
        2. Run object detection with certainty thresholding.
        3. Convert bounding box coordinates to values between 0.0 and 1.0.
        4. Calculate storage durations from the rule engine.
        """
        image = self.process_raw_image(image_bytes)
        img_w, img_h = image.size

        if self.model is None:
            logger.warning("YOLO model not loaded; returning empty detections.")
            return []

        # Execute object detection with fixed 640 pixel size
        results = self.model.predict(
            source=image,
            conf=confidence_threshold,
            iou=iou_threshold,
            imgsz=640,
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

            # Bounding box coordinates: [xmin, ymin, xmax, ymax]
            xyxy = box.xyxy[0].tolist()
            xmin, ymin, xmax, ymax = xyxy

            # Normalize coordinates to values between 0.0 and 1.0
            norm_ymin = max(0.0, min(1.0, ymin / img_h))
            norm_xmin = max(0.0, min(1.0, xmin / img_w))
            norm_ymax = max(0.0, min(1.0, ymax / img_h))
            norm_xmax = max(0.0, min(1.0, xmax / img_w))

            # Look up food safety rules
            rule_info = rule_engine.calculate_expiration(
                food_class=raw_label,
                package_state=package_state,
                storage_location=storage_location,
            )

            det_id = str(uuid.uuid4())[:8]

            detections.append({
                "id": det_id,
                "label": rule_info["food_class"],
                "display_name": rule_info["display_name"],
                "confidence": round(conf, 4),
                "days": rule_info["recommended_shelf_life_days"],
                "days_min": rule_info["shelf_life_days_min"],
                "days_max": rule_info["shelf_life_days_max"],
                "bbox": [
                    round(norm_ymin, 4),
                    round(norm_xmin, 4),
                    round(norm_ymax, 4),
                    round(norm_xmax, 4),
                ],
                "safety_tier": rule_info["safety_tier"],
                "category_name": rule_info["category_name"],
                "package_state": package_state,
                "storage_location": storage_location,
                "requires_user_detail": rule_info["requires_user_detail"],
                "detail_prompt": rule_info["detail_prompt"],
                "usda_guidance": rule_info["usda_guidance"],
                "is_container": rule_info["is_container"],
                "is_high_risk": rule_info["is_high_risk"],
            })

        return detections


# Service instance
inference_service = FoodInferenceService()


