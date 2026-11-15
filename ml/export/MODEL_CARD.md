# Model card: food_detector_v8n_baseline

**Placeholder.** This is the baseline model. It will be replaced if a tuned run beats it.

## Handoff for the backend
- **Load this file:** `ml/export/food_detector_v8n_baseline.onnx` (`YOLO(path, task="detect")`).
- **Settings:** `imgsz=640`, `conf=0.25`, NMS `iou=0.7`.
- **Map detections by class NAME, not index** (use `result.names[int(cls)]`).
- **Load the model once at server startup**, not per request.
- This is a baseline placeholder and may be replaced by a tuned model. Keep the file path and class-name mapping configurable.

## Known issue: ONNX vs .pt on non-square images
ONNX predictions on non-square images can differ from `.pt` predictions. The standard `.pt`-vs-ONNX check **FAILED** (max box difference about 68 px, and one image gave 1 detection with `.pt` vs 3 with ONNX). With an identical square 640x640 letterboxed input, the same check **PASSED** (0.000 px), so the export itself is correct. The cause is preprocessing: `.pt` uses rectangular inference, while the static-shape export always pads to 640x640. Test the backend against the ONNX model, not against `.pt` results. Full numbers are in "Export check" below.

## Model
| | |
|---|---|
| Architecture | YOLOv8n (detection), 38 classes |
| Source weights | `ml/runs/baseline_v8n/weights/best.pt` (run `baseline_v8n`) |
| Trained | 2026-11-07, epochs 50, imgsz 640, seed 0 |
| Files | `food_detector_v8n_baseline.pt`, `food_detector_v8n_baseline.onnx` (FP32, static shape, simplified), `food_detector_v8n_baseline.torchscript` (FP32) |

## Classes (index: name). The backend should map detections by class NAME, not index.
```
0: apple
1: avocado
2: bacon
3: banana
4: beef
5: bell_pepper
6: blueberries
7: bread
8: butter
9: carrot
10: cheese
11: chicken
12: chocolate
13: corn
14: cream
15: egg
16: flour
17: goat_cheese
18: green_beans
19: ham
20: jar
21: lemon
22: lime
23: mango
24: milk
25: mushrooms
26: onion
27: orange
28: persimmon
29: pomegranate
30: potato
31: shrimp
32: spinach
33: strawberries
34: sugar
35: sweet_potato
36: tomato
37: yogurt
```

## Input / output
- **Input:** `images`, shape `[1, 3, 640, 640]` (NCHW), tensor(float); RGB image, pixel values scaled to 0-1, letterbox-resized (aspect ratio kept, padded) to 640x640. Ultralytics does this for you when you pass an image to `predict`.
- **Output (raw ONNX):** `output0`, shape `[1, 42, 8400]` = [batch, 4 box values (cx, cy, w, h) + 38 class scores, anchors]; NMS is not included, so use the Ultralytics `predict` API (it applies NMS and returns `xyxy` in original-image pixels).
- ONNX Runtime providers used for verification: ['CPUExecutionProvider'].

## Recommended inference settings
`imgsz=640`, `conf=0.25`, NMS `iou=0.7`. Map detections by class name.

## Validation metrics
| Metric | Value |
|---|---|
| mAP@50 | 0.930 |
| mAP@50-95 | 0.720 |
| Precision (mean) | 0.914 |
| Recall (mean) | 0.894 |

Source: `ml/runs/eval_baseline_v8n/metrics_summary.json` (valid split, 398 images / 1989 instances, conf 0.001, iou 0.6).

Caveat: the valid split shares some scenes with train (near-duplicate images), so these numbers are probably optimistic. Confirm on separate real fridge photos.

## Export check (.pt vs .onnx, 5 valid images, conf 0.25, iou 0.7)
**Standard check (each model preprocesses the original image itself): FAIL.** Max box difference 67.656 px (tolerance 2.0 px); classes and detection counts matched on 3 of 5 images. Per-image max difference (px) and image size (h, w): 2.1 at [2144, 1424]; 5.8 at [1536, 2048]; 23.0 at [1000, 2000]; 67.7 at [480, 640]; 0.0 at [640, 640].

**Same-input check (all models get an identical square 640x640 letterboxed image): PASS.** Max box difference 0.000 px, same detection counts on every image.

Explanation: the PyTorch `.pt` path uses rectangular inference (minimal padding) on non-square images, while the static-shape ONNX/TorchScript exports always pad to 640x640. The only image that matched in the standard check is the square one. So the exports are numerically equivalent to the `.pt`, but **ONNX predictions on non-square images can differ from `.pt` predictions** (here up to 68 px, and the largest count difference on one image was 1 (.pt) vs 3 (.onnx) detections). Treat the ONNX behaviour as the deployed behaviour, and test the backend against it.

## CPU latency (batch 1, imgsz 640, end-to-end `predict` including pre/post-processing; 5 warm-up + 50 timed runs on `aicook__DSC_5678_JPG_jpg_rf_d17f016b4d0f935e9af23ed03963983b.jpg`)
| Model | Mean (ms) | Median (ms) | p95 (ms) | Model inference only, mean (ms) |
|---|---|---|---|---|
| .pt (PyTorch, CPU) | 34.5 | 34.4 | 35.3 | 28.4 |
| .onnx (ONNX Runtime, CPU) | 26.0 | 25.2 | 31.3 | 18.0 |

Measured on: Apple M4 (macOS-15.6.1-arm64-arm-64bit-Mach-O), Python 3.14.3, torch 2.15.0 (8 threads), onnxruntime 1.31.1. Numbers will differ on other hardware.

## Usage
```python
from ultralytics import YOLO

model = YOLO("ml/export/food_detector_v8n_baseline.onnx", task="detect")
results = model.predict(source="fridge.jpg", imgsz=640, conf=0.25, iou=0.7)
```

FastAPI sketch (load once at startup, return class names):
```python
from contextlib import asynccontextmanager
from io import BytesIO

from fastapi import FastAPI, File, UploadFile
from PIL import Image
from ultralytics import YOLO

state = {}

@asynccontextmanager
async def lifespan(app):
    state["model"] = YOLO("ml/export/food_detector_v8n_baseline.onnx", task="detect")  # loaded once
    yield

app = FastAPI(lifespan=lifespan)

@app.post("/detect")
async def detect(file: UploadFile = File(...)):
    img = Image.open(BytesIO(await file.read())).convert("RGB")
    r = state["model"].predict(img, imgsz=640, conf=0.25, iou=0.7, verbose=False)[0]
    return [
        {"class_name": r.names[int(c)], "confidence": float(s), "box_xyxy": [float(v) for v in xy]}
        for c, s, xy in zip(r.boxes.cls.tolist(), r.boxes.conf.tolist(), r.boxes.xyxy.tolist())
    ]
```
