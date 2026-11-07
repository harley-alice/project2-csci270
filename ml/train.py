"""Baseline YOLOv8n training for the CSCI 270 Food Expiration Date Predictor.

Equivalent CLI command:
    yolo detect train data=data/cleaned/data.yaml model=yolov8n.pt epochs=50 batch=16 imgsz=640

Run from any directory:
    python ml/train.py                              # full baseline
    python ml/train.py --epochs 2 --name smoke_test # quick pipeline check
"""
import argparse
from pathlib import Path

from ultralytics import YOLO

REPO_ROOT = Path(__file__).resolve().parent.parent


def main():
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--epochs", type=int, default=50)
    p.add_argument("--batch", type=int, default=16)
    p.add_argument("--imgsz", type=int, default=640)
    p.add_argument("--device", default=None, help="e.g. 0, cpu, mps (default: auto)")
    p.add_argument("--name", default="baseline_v8n")
    args = p.parse_args()

    model = YOLO(str(REPO_ROOT / "yolov8n.pt"))  # downloaded on first use
    model.train(
        data=str(REPO_ROOT / "data/cleaned/data.yaml"),
        epochs=args.epochs,
        batch=args.batch,
        imgsz=args.imgsz,
        seed=0,
        device=args.device,
        project=str(REPO_ROOT / "ml/runs"),
        name=args.name,
    )


if __name__ == "__main__":
    main()
