"""Export the trained detector for CPU serving (FP32 ONNX and TorchScript).

Copies best.pt to <out-dir>/<name>.pt and exports from that copy, so the outputs
land next to it as <name>.onnx / <name>.torchscript and the original run folder
is not touched. Weight files are gitignored; share them by zip or Drive.

Usage:
    python ml/export.py                      # export, then see ml/verify_export.py
    python ml/export.py --formats onnx
"""
import argparse
import shutil
from pathlib import Path

from ultralytics import YOLO

REPO = Path(__file__).resolve().parent.parent
EXT = {"onnx": ".onnx", "torchscript": ".torchscript"}


def rel(p):
    p = Path(p)
    return p if p.is_absolute() else REPO / p


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--weights", default="ml/runs/baseline_v8n/weights/best.pt")
    ap.add_argument("--out-dir", default="ml/export")
    ap.add_argument("--name", default="food_detector_v8n_baseline")
    ap.add_argument("--imgsz", type=int, default=640)
    ap.add_argument("--formats", default="onnx,torchscript")
    ap.add_argument("--device", default="cpu")
    a = ap.parse_args()

    weights, out = rel(a.weights), rel(a.out_dir)
    out.mkdir(parents=True, exist_ok=True)
    pt = out / f"{a.name}.pt"
    shutil.copy2(weights, pt)
    print(f"copied {weights.relative_to(REPO)} -> {pt.relative_to(REPO)}")

    for fmt in [f.strip() for f in a.formats.split(",") if f.strip()]:
        model = YOLO(str(pt))  # fresh load per export
        if fmt == "onnx":
            # FP32, static shape, simplified; opset left at the Ultralytics default
            produced = model.export(format="onnx", imgsz=a.imgsz, simplify=True, half=False,
                                    dynamic=False, device=a.device)
        elif fmt == "torchscript":
            produced = model.export(format="torchscript", imgsz=a.imgsz, half=False, device=a.device)
        else:
            raise SystemExit(f"unsupported format: {fmt}")
        produced = Path(produced)
        target = out / f"{a.name}{EXT[fmt]}"
        if produced.resolve() != target.resolve():
            shutil.move(str(produced), target)
        print(f"{fmt}: {target.relative_to(REPO)} ({target.stat().st_size / 1e6:.1f} MB)")


if __name__ == "__main__":
    main()
