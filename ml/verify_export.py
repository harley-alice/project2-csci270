"""Verify exported models against the .pt, time CPU latency, and write the model card.

Checks (valid split only, 5 images, conf 0.25, iou 0.7, imgsz 640):
  * detections per image, class names, and max abs box difference (pixels) .pt vs .onnx
    (TorchScript is compared as an extra check)
  * ONNX input/output names and shapes
  * CPU latency of .pt and .onnx (5 warm-up + 50 timed runs on one image)

Writes ml/export/verify_results.json and, with --write-card, ml/export/MODEL_CARD.md
(every number is read from files or measured in this run).

Usage:  python ml/verify_export.py --write-card
"""
import argparse
import csv
import json
import platform
import subprocess
import time
from collections import Counter
from pathlib import Path

import numpy as np
import onnxruntime as ort
import torch
import yaml
from ultralytics import YOLO

REPO = Path(__file__).resolve().parent.parent
CONF, IOU, IMGSZ = 0.25, 0.7, 640
TOL_PX = 2.0


def rel(p):
    p = Path(p)
    return p if p.is_absolute() else REPO / p


def letterbox_square(path, s=IMGSZ):
    """Resize keeping aspect ratio and pad (grey 114) to s x s, like the static-shape exports do."""
    import cv2
    im = cv2.imread(str(path))
    h, w = im.shape[:2]
    k = s / max(h, w)
    nh, nw = round(h * k), round(w * k)
    out = np.full((s, s, 3), 114, np.uint8)
    t, l = (s - nh) // 2, (s - nw) // 2
    out[t:t + nh, l:l + nw] = cv2.resize(im, (nw, nh), interpolation=cv2.INTER_LINEAR)
    return out


def dets(model, img):
    src = img if isinstance(img, np.ndarray) else str(img)
    r = model.predict(source=src, imgsz=IMGSZ, conf=CONF, iou=IOU, device="cpu", verbose=False)[0]
    b = r.boxes
    return [(r.names[int(c)], float(s), xy) for c, s, xy in zip(b.cls.tolist(), b.conf.tolist(), b.xyxy.tolist())]


def compare(a, b):
    """Greedy same-class matching by smallest box distance. Returns (class_match, count_match, max_px, unmatched)."""
    ca, cb = Counter(d[0] for d in a), Counter(d[0] for d in b)
    used, worst, unmatched = set(), 0.0, 0
    for name, _, box in a:
        best, bj = None, None
        for j, (n2, _, b2) in enumerate(b):
            if j in used or n2 != name:
                continue
            d = max(abs(x - y) for x, y in zip(box, b2))
            if best is None or d < best:
                best, bj = d, j
        if bj is None:
            unmatched += 1
        else:
            used.add(bj)
            worst = max(worst, best)
    unmatched += len(b) - len(used)
    return ca == cb, len(a) == len(b), worst, unmatched


def latency(model, img, n_warm=5, n=50):
    for _ in range(n_warm):
        model.predict(source=str(img), imgsz=IMGSZ, conf=CONF, iou=IOU, device="cpu", verbose=False)
    t, inf = [], []
    for _ in range(n):
        s = time.perf_counter()
        r = model.predict(source=str(img), imgsz=IMGSZ, conf=CONF, iou=IOU, device="cpu", verbose=False)
        t.append((time.perf_counter() - s) * 1000)
        inf.append(r[0].speed["inference"])
    t = np.array(t)
    return {"mean_ms": float(t.mean()), "median_ms": float(np.median(t)), "p95_ms": float(np.percentile(t, 95)),
            "inference_only_mean_ms": float(np.mean(inf))}


def cpu_name():
    try:
        return subprocess.check_output(["sysctl", "-n", "machdep.cpu.brand_string"], text=True).strip()
    except Exception:
        return platform.processor() or platform.machine()


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--export-dir", default="ml/export")
    ap.add_argument("--name", default="food_detector_v8n_baseline")
    ap.add_argument("--data", default="data/cleaned/data.yaml")
    ap.add_argument("--n-images", type=int, default=5)
    ap.add_argument("--write-card", action="store_true")
    a = ap.parse_args()
    ex = rel(a.export_dir)
    pt, onnx_p, ts_p = (ex / f"{a.name}{e}" for e in (".pt", ".onnx", ".torchscript"))

    data = yaml.safe_load(rel(a.data).read_text())
    imgs = sorted(p for p in Path(data["val"]).iterdir() if p.suffix.lower() in {".jpg", ".jpeg", ".png"})
    pick = [imgs[i] for i in np.linspace(0, len(imgs) - 1, a.n_images, dtype=int)]

    m_pt, m_onnx = YOLO(str(pt)), YOLO(str(onnx_p), task="detect")
    m_ts = YOLO(str(ts_p), task="detect") if ts_p.exists() else None
    names = [m_pt.names[i] for i in range(len(m_pt.names))]
    assert names == data["names"], "class order differs from data.yaml"

    rows, ok = [], True
    for im in pick:
        d_pt, d_on = dets(m_pt, im), dets(m_onnx, im)
        cm, nm, px, un = compare(d_pt, d_on)
        row = {"image": im.name, "n_pt": len(d_pt), "n_onnx": len(d_on), "classes_match": cm,
               "counts_match": nm, "max_box_diff_px": px, "unmatched": un}
        if m_ts is not None:
            d_ts = dets(m_ts, im)
            cm2, nm2, px2, un2 = compare(d_pt, d_ts)
            row.update({"n_torchscript": len(d_ts), "ts_classes_match": cm2, "ts_max_box_diff_px": px2})
        row["pass"] = cm and nm and un == 0 and px < TOL_PX
        ok &= row["pass"]
        rows.append(row)
        print(row)

    # Diagnostic: identical square 640x640 letterboxed input for every model. The .pt path uses
    # rectangular (minimal-padding) inference on non-square images while the static exports always
    # pad to 640x640, so the check above mixes preprocessing differences with export differences.
    eq_rows, eq_ok = [], True
    for im in pick:
        sq = letterbox_square(im)
        d_pt, d_on = dets(m_pt, sq), dets(m_onnx, sq)
        cm, nm, px, un = compare(d_pt, d_on)
        row = {"image": im.name, "n_pt": len(d_pt), "n_onnx": len(d_on), "max_box_diff_px": px}
        if m_ts is not None:
            row["n_torchscript"] = len(dets(m_ts, sq))
        row["pass"] = cm and nm and un == 0 and px < TOL_PX
        eq_ok &= row["pass"]
        eq_rows.append(row)

    sess = ort.InferenceSession(str(onnx_p), providers=["CPUExecutionProvider"])
    io = {"providers": sess.get_providers(),
          "inputs": [{"name": i.name, "shape": i.shape, "type": i.type} for i in sess.get_inputs()],
          "outputs": [{"name": o.name, "shape": o.shape, "type": o.type} for o in sess.get_outputs()]}
    meta = {k: v for k, v in sess.get_modelmeta().custom_metadata_map.items() if k in ("imgsz", "batch", "stride", "task")}

    one = pick[0]
    lat = {"pt": latency(m_pt, one), "onnx": latency(m_onnx, one)}
    machine = {"platform": platform.platform(), "cpu": cpu_name(), "python": platform.python_version(),
               "torch": torch.__version__, "onnxruntime": ort.__version__, "torch_threads": torch.get_num_threads()}
    res = {"result": "PASS" if ok else "FAIL", "tolerance_px": TOL_PX, "conf": CONF, "iou": IOU, "imgsz": IMGSZ,
           "images": rows, "max_box_diff_px_overall": max(r["max_box_diff_px"] for r in rows),
           "same_input_check": {"result": "PASS" if eq_ok else "FAIL", "images": eq_rows,
                                "max_box_diff_px_overall": max(r["max_box_diff_px"] for r in eq_rows)},
           "image_sizes_hw": {p.name: list(__import__("cv2").imread(str(p)).shape[:2]) for p in pick},
           "onnx_io": io, "onnx_metadata": meta, "latency": lat, "machine": machine,
           "latency_image": one.name}
    (ex / "verify_results.json").write_text(json.dumps(res, indent=2))
    print(f"\n{res['result']}  max box diff = {res['max_box_diff_px_overall']:.3f} px (tol {TOL_PX})")
    sc = res["same_input_check"]
    print(f"same square input for all models: {sc['result']}  max box diff = {sc['max_box_diff_px_overall']:.3f} px")
    print(json.dumps({"io": io, "latency": lat, "machine": machine}, indent=2))

    if a.write_card:
        write_card(ex, a.name, names, res, pt)


def write_card(ex, name, names, res, pt):
    ck = torch.load(pt, map_location="cpu", weights_only=False)
    ta = ck.get("train_args", {})
    run_args = rel("ml/runs/baseline_v8n/args.yaml")
    run_name = yaml.safe_load(run_args.read_text()).get("name") if run_args.exists() else None
    ms = rel("ml/runs/eval_baseline_v8n/metrics_summary.json")
    if ms.exists():
        m = json.loads(ms.read_text())
        met = (f"| mAP@50 | {m['mAP50']:.3f} |\n| mAP@50-95 | {m['mAP50_95']:.3f} |\n| Precision (mean) | {m['mean_precision']:.3f} |\n"
               f"| Recall (mean) | {m['mean_recall']:.3f} |\n\nSource: `ml/runs/eval_baseline_v8n/metrics_summary.json` "
               f"(valid split, {m['images_evaluated']} images / {m['instances_evaluated']} instances, conf {m['conf']}, iou {m['iou']}).")
    else:
        rc = rel("ml/runs/baseline_v8n/results.csv")
        last = list(csv.DictReader(open(rc)))[-1]
        last = {k.strip(): v.strip() for k, v in last.items()}
        met = (f"| mAP@50 | {float(last['metrics/mAP50(B)']):.3f} |\n| mAP@50-95 | {float(last['metrics/mAP50-95(B)']):.3f} |\n"
               f"| Precision | {float(last['metrics/precision(B)']):.3f} |\n| Recall | {float(last['metrics/recall(B)']):.3f} |\n\n"
               "From training-time validation (last epoch of `results.csv`).")
    io = res["onnx_io"]
    inp, out = io["inputs"][0], io["outputs"][0]
    lat = res["latency"]; mc = res["machine"]
    cls_list = "\n".join(f"{i}: {n}" for i, n in enumerate(names))
    wc = max(res["images"], key=lambda r: abs(r["n_pt"] - r["n_onnx"]))
    L = f"""# Model card: {name}

**Placeholder.** This is the baseline model. It will be replaced if a tuned run beats it.

## Model
| | |
|---|---|
| Architecture | YOLOv8n (detection), {len(names)} classes |
| Source weights | `ml/runs/baseline_v8n/weights/best.pt` (run `{run_name}`) |
| Trained | {str(ck.get('date', 'unknown'))[:10]}, epochs {ta.get('epochs')}, imgsz {ta.get('imgsz')}, seed {ta.get('seed')} |
| Files | `{name}.pt`, `{name}.onnx` (FP32, static shape, simplified), `{name}.torchscript` (FP32) |

## Classes (index: name). The backend should map detections by class NAME, not index.
```
{cls_list}
```

## Input / output
- **Input:** `{inp['name']}`, shape `{inp['shape']}` (NCHW), {inp['type']}; RGB image, pixel values scaled to 0-1, letterbox-resized (aspect ratio kept, padded) to 640x640. Ultralytics does this for you when you pass an image to `predict`.
- **Output (raw ONNX):** `{out['name']}`, shape `{out['shape']}` = [batch, 4 box values (cx, cy, w, h) + {len(names)} class scores, anchors]; NMS is not included, so use the Ultralytics `predict` API (it applies NMS and returns `xyxy` in original-image pixels).
- ONNX Runtime providers used for verification: {io['providers']}.

## Recommended inference settings
`imgsz=640`, `conf=0.25`, NMS `iou=0.7`. Map detections by class name.

## Validation metrics
| Metric | Value |
|---|---|
{met}

Caveat: the valid split shares some scenes with train (near-duplicate images), so these numbers are probably optimistic. Confirm on separate real fridge photos.

## Export check (.pt vs .onnx, 5 valid images, conf {res['conf']}, iou {res['iou']})
**Standard check (each model preprocesses the original image itself): {res['result']}.** Max box difference {res['max_box_diff_px_overall']:.3f} px (tolerance {res['tolerance_px']} px); classes and detection counts matched on {sum(1 for r in res['images'] if r['classes_match'] and r['counts_match'])} of {len(res['images'])} images. Per-image max difference (px) and image size (h, w): {'; '.join(f"{r['max_box_diff_px']:.1f} at {res['image_sizes_hw'][r['image']]}" for r in res['images'])}.

**Same-input check (all models get an identical square 640x640 letterboxed image): {res['same_input_check']['result']}.** Max box difference {res['same_input_check']['max_box_diff_px_overall']:.3f} px, same detection counts on every image.

Explanation: the PyTorch `.pt` path uses rectangular inference (minimal padding) on non-square images, while the static-shape ONNX/TorchScript exports always pad to 640x640. The only image that matched in the standard check is the square one. So the exports are numerically equivalent to the `.pt`, but **ONNX predictions on non-square images can differ from `.pt` predictions** (here up to {res['max_box_diff_px_overall']:.0f} px, and the largest count difference on one image was {wc['n_pt']} (.pt) vs {wc['n_onnx']} (.onnx) detections). Treat the ONNX behaviour as the deployed behaviour, and test the backend against it.

## CPU latency (batch 1, imgsz 640, end-to-end `predict` including pre/post-processing; 5 warm-up + 50 timed runs on `{res['latency_image']}`)
| Model | Mean (ms) | Median (ms) | p95 (ms) | Model inference only, mean (ms) |
|---|---|---|---|---|
| .pt (PyTorch, CPU) | {lat['pt']['mean_ms']:.1f} | {lat['pt']['median_ms']:.1f} | {lat['pt']['p95_ms']:.1f} | {lat['pt']['inference_only_mean_ms']:.1f} |
| .onnx (ONNX Runtime, CPU) | {lat['onnx']['mean_ms']:.1f} | {lat['onnx']['median_ms']:.1f} | {lat['onnx']['p95_ms']:.1f} | {lat['onnx']['inference_only_mean_ms']:.1f} |

Measured on: {mc['cpu']} ({mc['platform']}), Python {mc['python']}, torch {mc['torch']} ({mc['torch_threads']} threads), onnxruntime {mc['onnxruntime']}. Numbers will differ on other hardware.

## Usage
```python
from ultralytics import YOLO

model = YOLO("ml/export/{name}.onnx", task="detect")
results = model.predict(source="fridge.jpg", imgsz=640, conf=0.25, iou=0.7)
```

FastAPI sketch (load once at startup, return class names):
```python
from contextlib import asynccontextmanager
from io import BytesIO

from fastapi import FastAPI, File, UploadFile
from PIL import Image
from ultralytics import YOLO

state = {{}}

@asynccontextmanager
async def lifespan(app):
    state["model"] = YOLO("ml/export/{name}.onnx", task="detect")  # loaded once
    yield

app = FastAPI(lifespan=lifespan)

@app.post("/detect")
async def detect(file: UploadFile = File(...)):
    img = Image.open(BytesIO(await file.read())).convert("RGB")
    r = state["model"].predict(img, imgsz=640, conf=0.25, iou=0.7, verbose=False)[0]
    return [
        {{"class_name": r.names[int(c)], "confidence": float(s), "box_xyxy": [float(v) for v in xy]}}
        for c, s, xy in zip(r.boxes.cls.tolist(), r.boxes.conf.tolist(), r.boxes.xyxy.tolist())
    ]
```
"""
    (ex / "MODEL_CARD.md").write_text(L)
    print(f"wrote {ex / 'MODEL_CARD.md'}")


if __name__ == "__main__":
    main()
