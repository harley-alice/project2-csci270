
import csv
import os
from pathlib import Path
from collections import defaultdict
from PIL import Image

ROOT = Path(__file__).resolve().parents[1]
IMAGE_DIR = Path(os.environ.get("FRIDGE_QA_IMAGE_DIR", str(ROOT / "data" / "qa" / "fridge_images_normalized")))
LABEL_DIR = ROOT / "data" / "qa" / "ground_truth"
CLASS_FILE = ROOT / "data" / "qa" / "food_classes.txt"
PREDICTION_FILE = Path(os.environ.get("FRIDGE_QA_PREDICTION_FILE", str(ROOT / "ml" / "runs" / "fridge_qa" / "detections.csv")))
OUTPUT_DIR = Path(os.environ.get("FRIDGE_QA_OUTPUT_DIR", str(ROOT / "ml" / "runs" / "fridge_qa")))

IOU_THRESHOLD = 0.50


def calculate_iou(box_a, box_b):
    ax1, ay1, ax2, ay2 = box_a
    bx1, by1, bx2, by2 = box_b

    x1 = max(ax1, bx1)
    y1 = max(ay1, by1)
    x2 = min(ax2, bx2)
    y2 = min(ay2, by2)

    intersection = max(0, x2 - x1) * max(0, y2 - y1)

    area_a = max(0, ax2 - ax1) * max(0, ay2 - ay1)
    area_b = max(0, bx2 - bx1) * max(0, by2 - by1)

    union = area_a + area_b - intersection
    return intersection / union if union > 0 else 0


def safe_divide(a, b):
    return a / b if b else 0


def read_ground_truth(label_path, image_width, image_height, class_names):
    objects = []

    for line_num, line in enumerate(
        label_path.read_text(encoding="utf-8").splitlines(), 1
    ):
        values = line.split()

        if len(values) != 5:
            raise ValueError(f"Invalid annotation: {label_path.name}, line {line_num}")

        class_id = int(values[0])
        xc, yc, width, height = map(float, values[1:])

        if not 0 <= class_id < len(class_names):
            raise ValueError(f"Invalid class ID in {label_path.name}")

        if not all(0 <= value <= 1 for value in (xc, yc, width, height)):
            raise ValueError(f"Invalid coordinates in {label_path.name}")

        objects.append({
            "class": class_names[class_id],
            "box": [
                (xc - width / 2) * image_width,
                (yc - height / 2) * image_height,
                (xc + width / 2) * image_width,
                (yc + height / 2) * image_height,
            ]
        })

    return objects


def main():
    class_names = CLASS_FILE.read_text(encoding="utf-8").splitlines()

    if len(class_names) != 38:
        raise ValueError(f"Expected 38 classes, found {len(class_names)}")

    images = {
        p.name: p for p in IMAGE_DIR.iterdir()
        if p.is_file() and p.suffix.lower() in {".jpg", ".jpeg", ".png"}
    }

    labels = {p.stem: p for p in LABEL_DIR.glob("*.txt")}

    if len(images) == 0:
        raise ValueError("No QA images found")

    if set(labels) != {Path(name).stem for name in images}:
        raise ValueError("Image and annotation filenames do not match.")

    ground_truth = {}
    predictions = defaultdict(list)

    # Read ground-truth annotations.
    for image_name, image_path in images.items():
        label_path = labels[image_path.stem]

        with Image.open(image_path) as image:
            width, height = image.size

        ground_truth[image_name] = read_ground_truth(
            label_path, width, height, class_names
        )

    # Read model predictions.
    with PREDICTION_FILE.open(
        "r", newline="", encoding="utf-8-sig"
    ) as file:
        reader = csv.DictReader(file)

        required = {"image", "class_name", "confidence", "x1", "y1", "x2", "y2"}
        if not required.issubset(reader.fieldnames or []):
            raise ValueError("Prediction CSV is missing required columns.")

        for row in reader:
            image_name = Path(row["image"]).name

            if image_name not in images:
                raise ValueError(f"Prediction references unknown image: {image_name}")

            if row["class_name"] not in class_names:
                raise ValueError(f"Unknown predicted class: {row['class_name']}")

            predictions[image_name].append({
                "class": row["class_name"],
                "confidence": float(row["confidence"]),
                "box": [
                    float(row["x1"]), float(row["y1"]),
                    float(row["x2"]), float(row["y2"])
                ]
            })

    # Initialize class-level counts.
    counts = {
        name: {"TP": 0, "FP": 0, "FN": 0}
        for name in class_names
    }

    total = {"TP": 0, "FP": 0, "FN":     0}
    image_results     = []
    detection_results     = []
    localization_results     = []

    localization_total = {
        "localized": 0,
        "missed": 0,
        "unmatched_predictions": 0,
        "correct_class": 0,
        "wrong_class": 0
}

    # Match predictions to ground truth, independently per image.
    for image_name in sorted(images):
        gt_objects = ground_truth[image_name]
        pred_objects = predictions[image_name]

        candidates = []

        for gt_index, gt in enumerate(gt_objects):
            for pred_index, pred in enumerate(pred_objects):
                if gt["class"] != pred["class"]:
                    continue

                iou = calculate_iou(gt["box"], pred["box"])

                if iou >= IOU_THRESHOLD:
                    candidates.append((iou, gt_index, pred_index))

        # Highest-IoU match first; each object can match only once.
        candidates.sort(reverse=True)

        matched_gt = set()
        matched_pred = set()

        for iou, gt_index, pred_index in candidates:
            if gt_index in matched_gt or pred_index in matched_pred:
                continue

            matched_gt.add(gt_index)
            matched_pred.add(pred_index)

            class_name = gt_objects[gt_index]["class"]
            counts[class_name]["TP"] += 1
            total["TP"] += 1

            detection_results.append({
                "image": image_name,
                "class": class_name,
                "result": "TP",
                "confidence": pred_objects[pred_index]["confidence"],
                "IoU": round(iou, 4)
            })

        # Unmatched predictions are false positives.
        for index, pred in enumerate(pred_objects):
            if index not in matched_pred:
                class_name = pred["class"]
                counts[class_name]["FP"] += 1
                total["FP"] += 1

                detection_results.append({
                    "image": image_name,
                    "class": class_name,
                    "result": "FP",
                    "confidence": pred["confidence"],
                    "IoU": ""
                })

        # Unmatched ground-truth objects are false negatives.
        for index, gt in enumerate(gt_objects):
            if index not in matched_gt:
                class_name = gt["class"]
                counts[class_name]["FN"] += 1
                total["FN"] += 1

                detection_results.append({
                    "image": image_name,
                    "class": class_name,
                    "result": "FN",
                    "confidence": "",
                    "IoU": ""
                })

        tp = len(matched_gt)
        fp = len(pred_objects) - len(matched_pred)
        fn = len(gt_objects) - len(matched_gt)

        image_results.append({
            "image": image_name,
            "ground_truth_count": len(gt_objects),
            "prediction_count": len(pred_objects),
            "TP": tp,
            "FP": fp,
            "FN": fn,
            "negative_image": len(gt_objects) == 0,
            "false_positives_on_negative_image": fp if not gt_objects else 0
        })

    # Evaluate localization independently of predicted class.
    for image_name in sorted(images):
        gt_objects = ground_truth[image_name]
        pred_objects = predictions[image_name]

        candidates = []

        for gt_index, gt in enumerate(gt_objects):
            for pred_index, pred in enumerate(pred_objects):
                iou = calculate_iou(gt["box"], pred["box"])

                if iou >= IOU_THRESHOLD:
                    candidates.append((iou, gt_index, pred_index))

        candidates.sort(reverse=True)

        matched_gt = set()
        matched_pred = set()

        for iou, gt_index, pred_index in candidates:
            if gt_index in matched_gt or pred_index in matched_pred:
                continue

            matched_gt.add(gt_index)
            matched_pred.add(pred_index)

            gt_class = gt_objects[gt_index]["class"]
            pred_class = pred_objects[pred_index]["class"]

            correct_class = gt_class == pred_class

            localization_total["localized"] += 1

            if correct_class:
                localization_total["correct_class"] += 1
            else:
                localization_total["wrong_class"] += 1

            localization_results.append({
                "image": image_name,
                "ground_truth_class": gt_class,
                "predicted_class": pred_class,
                "classification": "correct" if correct_class else "incorrect",
                "confidence": pred_objects[pred_index]["confidence"],
                "IoU": round(iou, 4)
            })

        localization_total["missed"] += len(gt_objects) - len(matched_gt)
        localization_total["unmatched_predictions"] += len(pred_objects) - len(matched_pred)

    # Calculate localization metrics.
    localization_recall = safe_divide(
        localization_total["localized"],
        localization_total["localized"] + localization_total["missed"]
    )

    classification_accuracy = safe_divide(
        localization_total["correct_class"],
        localization_total["localized"]
    )

    # Overall metrics.
    precision = safe_divide(total["TP"], total["TP"] + total["FP"])
    recall = safe_divide(total["TP"], total["TP"] + total["FN"])
    f1 = safe_divide(2 * precision * recall, precision + recall)

    summary = [
        {"metric": "Images evaluated", "value": len(images)},
        {"metric": "Ground-truth objects", "value": sum(len(x) for x in ground_truth.values())},
        {"metric": "Model predictions", "value": sum(len(x) for x in predictions.values())},
        {"metric": "True positives", "value": total["TP"]},
        {"metric": "False positives", "value": total["FP"]},
        {"metric": "False negatives", "value": total["FN"]},
        {"metric": "Precision", "value": round(precision, 4)},
        {"metric": "Recall", "value": round(recall, 4)},
        {"metric": "F1", "value": round(f1, 4)},
        {"metric": "IoU threshold", "value": IOU_THRESHOLD},
    ]

    print("\nCLASS-INDEPENDENT LOCALIZATION")
    print("=" * 45)
    print("Localized objects:", localization_total["localized"])
    print("Missed objects:", localization_total["missed"])
    print("Unmatched predictions:", localization_total["unmatched_predictions"])
    print("Correctly classified localized objects:", localization_total["correct_class"])
    print("Incorrectly classified localized objects:", localization_total["wrong_class"])
    print("Localization recall:", round(localization_recall, 4))
    print("Classification accuracy among localized objects:", round(classification_accuracy, 4))

    # Per-class metrics.
    class_results = []

    for name in class_names:
        c = counts[name]
        p = safe_divide(c["TP"], c["TP"] + c["FP"])
        r = safe_divide(c["TP"], c["TP"] + c["FN"])
        f = safe_divide(2 * p * r, p + r)

        class_results.append({
            "class": name,
            "ground_truth_count": c["TP"] + c["FN"],
            "prediction_count": c["TP"] + c["FP"],
            "TP": c["TP"],
            "FP": c["FP"],
            "FN": c["FN"],
            "precision": round(p, 4),
            "recall": round(r, 4),
            "F1": round(f, 4)
        })

    def save_csv(filename, rows):
        if not rows:
            return

        with (OUTPUT_DIR / filename).open(
            "w", newline="", encoding="utf-8"
        ) as file:
            writer = csv.DictWriter(file, fieldnames=rows[0].keys())
            writer.writeheader()
            writer.writerows(rows)

    save_csv("evaluation_summary.csv", summary)
    save_csv("per_class_metrics.csv", class_results)
    save_csv("per_image_metrics.csv", image_results)
    save_csv("detection_matches.csv", detection_results)
    save_csv("localization_analysis.csv", localization_results)

    print("\nFRIDGE QA EVALUATION")
    print("=" * 45)

    for row in summary:
        print(f"{row['metric']}: {row['value']}")

    print("\nResults saved to:", OUTPUT_DIR)


if __name__ == "__main__":
    main()

