"""Compare YOLO performance across original and preprocessed QA images."""

import csv
import os
import subprocess
import sys
from pathlib import Path

from ultralytics import YOLO

ROOT = Path(__file__).resolve().parents[1]

MODEL_PATH = ROOT / "ml" / "export" / "food_detector_v8n_baseline.onnx"
GROUND_TRUTH_DIR = ROOT / "data" / "qa" / "ground_truth"
OUTPUT_ROOT = ROOT / "ml" / "runs" / "fridge_qa_preprocessing"
EVALUATOR = ROOT / "ml" / "evaluate_fridge_qa.py"

IMAGE_SIZE = 640
CONFIDENCE = 0.25
IOU = 0.7

IMAGE_EXTENSIONS = {".jpg", ".jpeg", ".png"}

VARIANTS = {
    "baseline": ROOT / "data" / "qa" / "fridge_images",
    "brightness": ROOT / "data" / "qa" / "preprocessed" / "brightness",
    "clahe": ROOT / "data" / "qa" / "preprocessed" / "clahe",
    "white_balance": ROOT / "data" / "qa" / "preprocessed" / "white_balance",
    "brightness_clahe": ROOT / "data" / "qa" / "preprocessed" / "brightness_clahe",
}


def get_images(folder):
    return sorted(
        path for path in folder.iterdir()
        if path.is_file() and path.suffix.lower() in IMAGE_EXTENSIONS
    )


def save_predictions(rows, output_path):
    fields = [
        "image", "class_name", "confidence",
        "x1", "y1", "x2", "y2"
    ]

    with output_path.open("w", newline="", encoding="utf-8") as file:
        writer = csv.DictWriter(file, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)


def main():
    if not MODEL_PATH.exists():
        raise FileNotFoundError(f"Model not found: {MODEL_PATH}")

    if not EVALUATOR.exists():
        raise FileNotFoundError(f"Evaluator not found: {EVALUATOR}")

    for name, folder in VARIANTS.items():
        if not folder.exists():
            raise FileNotFoundError(f"Image folder not found: {folder}")

    # Confirm every experiment uses the same image filenames.
    baseline_names = {p.name for p in get_images(VARIANTS["baseline"])}

    if not baseline_names:
        raise ValueError("No baseline images found.")

    for name, folder in VARIANTS.items():
        names = {p.name for p in get_images(folder)}

        if names != baseline_names:
            raise ValueError(
                f"{name} does not contain exactly the same image filenames as baseline."
            )

    print(f"Images per experiment: {len(baseline_names)}")

    # Load the model once for all five experiments.
    print("\nLoading YOLO ONNX model...")
    model = YOLO(str(MODEL_PATH), task="detect")

    for name, folder in VARIANTS.items():
        print("\n" + "=" * 55)
        print(f"RUNNING: {name}")
        print("=" * 55)

        image_files = get_images(folder)

        output_dir = OUTPUT_ROOT / name
        output_dir.mkdir(parents=True, exist_ok=True)

        prediction_path = output_dir / "detections.csv"

        detection_rows = []

        results = model.predict(
            source=[str(path) for path in image_files],
            imgsz=IMAGE_SIZE,
            conf=CONFIDENCE,
            iou=IOU,
            device="cpu",
            save=False,
            verbose=False,
            stream=True,
        )

        for result in results:
            image_name = Path(result.path).name
            boxes = result.boxes

            if boxes is None or len(boxes) == 0:
                continue

            class_ids = boxes.cls.cpu().tolist()
            confidences = boxes.conf.cpu().tolist()
            coordinates = boxes.xyxy.cpu().tolist()

            for class_id, confidence, box in zip(
                class_ids, confidences, coordinates
            ):
                detection_rows.append({
                    "image": image_name,
                    "class_name": result.names[int(class_id)],
                    "confidence": round(float(confidence), 4),
                    "x1": round(float(box[0]), 2),
                    "y1": round(float(box[1]), 2),
                    "x2": round(float(box[2]), 2),
                    "y2": round(float(box[3]), 2),
                })

        save_predictions(detection_rows, prediction_path)

        print(f"Images processed: {len(image_files)}")
        print(f"Predictions generated: {len(detection_rows)}")

        # Run the same evaluator against the original ground-truth labels.
        environment = os.environ.copy()
        environment["FRIDGE_QA_IMAGE_DIR"] = str(folder)
        environment["FRIDGE_QA_PREDICTION_FILE"] = str(prediction_path)
        environment["FRIDGE_QA_OUTPUT_DIR"] = str(output_dir)

        print(f"Evaluating {name}...")

        subprocess.run(
            [sys.executable, str(EVALUATOR)],
            check=True,
            env=environment,
        )

    print("\n" + "=" * 55)
    print("ALL PREPROCESSING EXPERIMENTS COMPLETE")
    print("=" * 55)
    print(f"Results saved in: {OUTPUT_ROOT}")


if __name__ == "__main__":
    main()
