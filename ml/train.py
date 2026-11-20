"""YOLOv8n training for the CSCI 270 Food Expiration Date Predictor.

Equivalent CLI command for the baseline:
    yolo detect train data=data/cleaned/data.yaml model=yolov8n.pt epochs=50 batch=16 imgsz=640

Run from any directory (paths are resolved from the repo root):
    python ml/train.py                                              # baseline on data/cleaned
    python ml/train.py --epochs 2 --name smoke_test                 # quick pipeline check
    python ml/train.py --data data/cleaned_v3/data.yaml --imgsz 640 --name B_v3_v8n_640
    python ml/train.py --data data/cleaned_v3/data.yaml --imgsz 960 --scale 0.9 --name B960_v3_v8n_960_scale0.9

--scale is the Ultralytics scale-augmentation range (0.9 = images randomly scaled by up to +/-90%; the Ultralytics default is 0.5).
After training, run `python ml/sanitize_paths.py` so the run's args.yaml contains repo-relative paths before it is committed.
"""
import argparse
from pathlib import Path

from ultralytics import YOLO

REPO_ROOT = Path(__file__).resolve().parent.parent


def main():
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--data", default="data/cleaned/data.yaml", help="dataset yaml, relative to the repo root")
    p.add_argument("--epochs", type=int, default=50)
    p.add_argument("--batch", type=int, default=16)
    p.add_argument("--imgsz", type=int, default=640)
    p.add_argument("--scale", type=float, default=None, help="scale augmentation range (default: Ultralytics default 0.5)")
    p.add_argument("--device", default=None, help="e.g. 0, cpu, mps (default: auto)")
    p.add_argument("--name", default="baseline_v8n")
    args = p.parse_args()

    data = Path(args.data)
    data = data if data.is_absolute() else REPO_ROOT / data
    if not data.exists():
        raise SystemExit(f"dataset yaml not found: {args.data}")

    weights = REPO_ROOT / "yolov8n.pt"
    model = YOLO(str(weights) if weights.exists() else "yolov8n.pt")  # downloaded on first use
    extra = {} if args.scale is None else {"scale": args.scale}
    model.train(
        data=str(data),
        epochs=args.epochs,
        batch=args.batch,
        imgsz=args.imgsz,
        seed=0,
        device=args.device,
        project=str(REPO_ROOT / "ml/runs"),
        name=args.name,
        **extra,
    )


if __name__ == "__main__":
    main()
