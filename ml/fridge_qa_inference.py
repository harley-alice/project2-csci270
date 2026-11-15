"""Run baseline YOLO ONNX inference on independent refrigerator QA images."""

import csv
from pathlib import Path

from PIL import Image
from ultralytics import YOLO

# Project paths
ROOT = Path(__file__).resolve().parents[1]
IMAGE_DIR = ROOT / "data" / "qa" / "fridge_images"
MODEL_PATH = ROOT / "ml" / "export" / "food_detector_v8n_baseline.onnx"
OUTPUT_DIR = ROOT / "ml" / "runs" / "fridge_qa"

# Model settings from MODEL_CARD.md
IMAGE_SIZE = 640
CONFIDENCE = 0.25
IOU = 0.7

IMAGE_EXTENSIONS = {".jpg", ".jpeg", ".png", ".bmp", ".webp"}


def main():
    # Check that required paths exist
    if not MODEL_PATH.exists():
        raise FileNotFoundError(f"Model not found: {MODEL_PATH}")

    if not IMAGE_DIR.exists():
        raise FileNotFoundError(f"Image folder not found: {IMAGE_DIR}")

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    # Find and validate image files
    image_files = sorted(
        path for path in IMAGE_DIR.iterdir()
        if path.is_file() and path.suffix.lower() in IMAGE_EXTENSIONS
    )

    valid_images = []
    image_info = []
    invalid_images = []

    for path in image_files:
        try:
            with Image.open(path) as img:
                width, height = img.size
                img.verify()

            valid_images.append(path)

            # Flag small files/dimensions for manual review; do not discard them
            needs_review = path.stat().st_size < 10000 or min(width, height) < 256

            image_info.append({
                "image": path.name,
                "width": width,
                "height": height,
                "file_size_bytes": path.stat().st_size,
                "small_image_review": needs_review,
            })

        except Exception as error:
            invalid_images.append({
                "image": path.name,
                "error": str(error),
            })

    print(f"Image files found: {len(image_files)}")
    print(f"Valid images: {len(valid_images)}")
    print(f"Invalid images: {len(invalid_images)}")

    if not valid_images:
        print("No valid images to process.")
        return

    # Load the ONNX model once
    print("\nLoading YOLO ONNX model...")
    model = YOLO(str(MODEL_PATH), task="detect")

    detection_rows = []
    summary_rows = []

    # Run inference on each valid image
    print("\nRunning refrigerator image inference...")

    results = model.predict(
        source=[str(path) for path in valid_images],
        imgsz=IMAGE_SIZE,
        conf=CONFIDENCE,
        iou=IOU,
        device="cpu",
        save=True,
        project=str(OUTPUT_DIR),
        name="predictions",
        exist_ok=True,
        verbose=False,
                stream=True,
    )

    for result in results:
        image_name = Path(result.path).name
        boxes = result.boxes
        detection_count = 0

        if boxes is not None and len(boxes) > 0:
            class_ids = boxes.cls.cpu().tolist()
            confidences = boxes.conf.cpu().tolist()
            coordinates = boxes.xyxy.cpu().tolist()

            for class_id, confidence, box in zip(
                class_ids, confidences, coordinates
            ):
                class_name = result.names[int(class_id)]
                detection_count += 1

                detection_rows.append({
                    "image": image_name,
                    "class_name": class_name,
                    "confidence": round(float(confidence), 4),
                    "x1": round(float(box[0]), 2),
                    "y1": round(float(box[1]), 2),
                    "x2": round(float(box[2]), 2),
                    "y2": round(float(box[3]), 2),
                })

        summary_rows.append({
            "image": image_name,
            "detection_count": detection_count,
        })

        print(f"{image_name}: {detection_count} detections")

    # Save detection results
    detection_path = OUTPUT_DIR / "detections.csv"
    with detection_path.open("w", newline="", encoding="utf-8") as file:
        writer = csv.DictWriter(
            file,
            fieldnames=["image", "class_name", "confidence", "x1", "y1", "x2", "y2"]
        )
        writer.writeheader()
        writer.writerows(detection_rows)

    # Save image detection counts
    summary_path = OUTPUT_DIR / "image_summary.csv"
    with summary_path.open("w", newline="", encoding="utf-8") as file:
        writer = csv.DictWriter(
            file,
            fieldnames=["image", "detection_count"]
        )
        writer.writeheader()
        writer.writerows(summary_rows)

    # Save image quality information
    image_info_path = OUTPUT_DIR / "image_quality.csv"
    with image_info_path.open("w", newline="", encoding="utf-8") as file:
        writer = csv.DictWriter(
            file,
            fieldnames=[
                "image", "width", "height",
                "file_size_bytes", "small_image_review"
            ]
        )
        writer.writeheader()
        writer.writerows(image_info)

    # Save invalid image information
    invalid_path = OUTPUT_DIR / "invalid_images.csv"
    with invalid_path.open("w", newline="", encoding="utf-8") as file:
        writer = csv.DictWriter(
            file,
            fieldnames=["image", "error"]
        )
        writer.writeheader()
        writer.writerows(invalid_images)

    print("\nQA INFERENCE COMPLETE")
    print(f"Images processed: {len(summary_rows)}")
    print(f"Total detections: {len(detection_rows)}")
    print(f"Annotated images: {OUTPUT_DIR / 'predictions'}")
    print(f"Detection results: {detection_path}")
    print(f"Image summary: {summary_path}")
    print(f"Image quality: {image_info_path}")
    print(f"Invalid images: {invalid_path}")


if __name__ == "__main__":
    main()