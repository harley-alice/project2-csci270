# Real-fridge diagnostics (baseline YOLOv8n)

All numbers below were produced by `ml/diagnose_real_fridge.py` and are saved in `results.json`. Nothing was trained.

## Setup

- **Data:** 160 annotated photos, 965 ground-truth boxes over 30 of 38 classes (26 images have no objects). An earlier message cited 96 images; the export contains 160.
- **EXIF orientation:** {'1': 67, '6': 93}. 93 images are stored sideways (raw size differs from display size).
- **Image size:** median long side 4032 px (min 660, max 5712); the model input is 640 px.
- **Class mapping:** `food_classes.txt` equals the model's 38 class names in the same order: True. Annotation class ids outside 0-37: none. Fridge/session IDs were not supplied, so images cannot be split by fridge yet.
- **Ashton's pipeline** (read from her scripts): ONNX model, imgsz 640, conf 0.25, NMS iou 0.7, images passed as file paths (Ultralytics rotates by EXIF); ground truth is scaled with PIL's raw `image.size` (no EXIF transpose); IoU >= 0.50, one-to-one matching, greedy by IoU.
- **This run:** `.pt` model, `upright` = EXIF applied, `raw` = pixels as stored (what the backend saw before the EXIF fix); raw-set boxes are rotated back into the display frame before matching. Matching is one-to-one, greedy by confidence. 'Localization' ignores class; 'end-to-end' requires the right class.

## Reproducing Ashton's numbers

Her saved `detections.csv` re-scored with my matcher, using her ground-truth frame (raw size) versus the correct frame (display size):

| GT frame | GT boxes | Localized (IoU>=0.5) | Correct class among localized | End-to-end TP |
|---|---|---|---|---|
| raw size (her script) | 965 | 67 | 15 | 15 |
| display size (upright) | 965 | 142 | 39 | 39 |

Her summary reports TP = 15 (matches the raw-frame row when it reproduces). Same predictions, different ground-truth frame.

## Settings matrix (.pt model)

IoU >= 0.50 (localization = any class; end-to-end = correct class):

| Run | Localization recall | Class-correct share | End-to-end recall | Preds/image | Mean conf (matched) |
|---|---|---|---|---|---|
| upright_640_conf0.001 | 75.1% | 16.3% | 22.9% | 161.3 | 0.138 |
| upright_960_conf0.001 | 75.9% | 19.1% | 24.0% | 183.6 | 0.152 |
| upright_1280_conf0.001 | 72.7% | 25.5% | 26.2% | 242.1 | 0.168 |
| raw_640_conf0.001 | 60.4% | 13.4% | 15.0% | 187.5 | 0.106 |
| upright_640_conf0.25 | 14.0% | 23.0% | 3.3% | 3.1 | 0.514 |

Lower IoU thresholds (localization / end-to-end recall):

| Run | IoU 0.30 | IoU 0.10 |
|---|---|---|
| upright_640_conf0.001 | 85.8% / 25.8% | 95.5% / 29.5% |
| upright_960_conf0.001 | 87.7% / 28.7% | 95.5% / 32.8% |
| upright_1280_conf0.001 | 87.0% / 30.5% | 96.3% / 36.2% |
| raw_640_conf0.001 | 73.7% / 18.4% | 91.0% / 24.0% |
| upright_640_conf0.25 | 15.6% / 3.5% | 18.1% / 3.9% |

## Ultralytics `model.val` control (upright set, conf 0.001)

| imgsz | mAP@50 | mAP@50-95 | Precision | Recall |
|---|---|---|---|---|
| 640 | 0.035 | 0.018 | 0.177 | 0.045 |
| 960 | 0.027 | 0.015 | 0.176 | 0.048 |
| 1280 | 0.037 | 0.023 | 0.276 | 0.046 |

Ultralytics' recall at its own F1-optimal confidence (0.045 at 640 px) is the same order as my end-to-end recall at the deployed conf 0.25 (3.3%) and far below my end-to-end recall at conf 0.001 (22.9%). The mAP is low (0.027-0.037) because correct-class matches carry low confidence (mean confidence of matched boxes 0.138 at 640 px). mAP does not follow my recall ordering across image sizes, so treat small differences between sizes as noise. The control reads the same labels with the same class order and shows the same low end-to-end picture, and my localization recall (75.1% at 640 px) shows the boxes line up with the photos, so there is no sign of a label-format or class-order bug.

## Object size

Ground-truth boxes by share of image area; recall at IoU >= 0.50 (localization / end-to-end), upright set, conf 0.001:

| Size bucket | GT boxes | upright_640_conf0.001 | upright_960_conf0.001 | upright_1280_conf0.001 |
|---|---|---|---|---|
| <0.5% | 289 | 56.4% / 15.9% | 65.4% / 22.1% | 68.2% / 28.7% |
| 0.5-2% | 501 | 80.8% / 23.4% | 80.0% / 22.6% | 74.7% / 23.6% |
| 2-8% | 173 | 89.6% / 32.4% | 80.9% / 31.2% | 74.6% / 28.9% |
| >8% | 2 | 100.0% / 100.0% | 100.0% / 50.0% | 100.0% / 100.0% |

Box-size distribution, training labels versus the real-fridge photos (share of boxes per bucket):

| Bucket | Training labels | Real fridge |
|---|---|---|
| <0.5% | 4.0% | 29.9% |
| 0.5-2% | 43.3% | 51.9% |
| 2-8% | 37.8% | 17.9% |
| >8% | 14.9% | 0.2% |

Median box area: training 2.20% of the image (8604 boxes) versus real fridge 0.92% (965 boxes). Median real box side at 640 input: 51 px.

## Per-class results (upright, conf 0.001; localization / end-to-end recall)

| Class | GT boxes | 960 px | 640 px | Note |
|---|---|---|---|---|
| milk | 91 | 81.3% / 63.7% | 85.7% / 58.2% |  |
| egg | 92 | 82.6% / 48.9% | 82.6% / 41.3% |  |
| jar | 302 | 80.1% / 10.9% | 77.8% / 7.9% |  |
| cream | 54 | 85.2% / 0.0% | 94.4% / 11.1% |  |
| butter | 63 | 71.4% / 11.1% | 66.7% / 20.6% |  |
| yogurt | 76 | 76.3% / 48.7% | 71.1% / 34.2% |  |
| chicken | 12 | 100.0% / 8.3% | 91.7% / 16.7% |  |
| beef | 9 | 77.8% / 22.2% | 88.9% / 11.1% | low-support (<10 boxes) |
| cheese | 94 | 74.5% / 22.3% | 76.6% / 35.1% |  |
| apple | 51 | 49.0% / 15.7% | 35.3% / 3.9% |  |
| avocado | 16 | 43.8% / 0.0% | 43.8% / 6.2% |  |
| spinach | 15 | 80.0% / 13.3% | 80.0% / 13.3% |  |
| tomato | 11 | 72.7% / 72.7% | 90.9% / 72.7% |  |
| lemon | 10 | 100.0% / 40.0% | 90.0% / 40.0% |  |
| onion | 9 | 77.8% / 0.0% | 88.9% / 0.0% | low-support (<10 boxes) |
| strawberries | 9 | 77.8% / 33.3% | 100.0% / 44.4% | low-support (<10 boxes) |
| bell_pepper | 7 | 85.7% / 0.0% | 71.4% / 14.3% | low-support (<10 boxes) |
| chocolate | 7 | 71.4% / 0.0% | 85.7% / 0.0% | low-support (<10 boxes) |
| bread | 6 | 100.0% / 33.3% | 100.0% / 16.7% | low-support (<10 boxes) |
| lime | 5 | 20.0% / 0.0% | 20.0% / 20.0% | low-support (<10 boxes) |
| orange | 5 | 20.0% / 0.0% | 0.0% / 0.0% | low-support (<10 boxes) |
| carrot | 5 | 40.0% / 0.0% | 20.0% / 0.0% | low-support (<10 boxes) |
| blueberries | 5 | 60.0% / 20.0% | 20.0% / 20.0% | low-support (<10 boxes) |
| mushrooms | 3 | 66.7% / 0.0% | 100.0% / 0.0% | low-support (<10 boxes) |
| pomegranate | 2 | 0.0% / 0.0% | 0.0% / 0.0% | low-support (<10 boxes) |
| bacon | 2 | 0.0% / 0.0% | 0.0% / 0.0% | low-support (<10 boxes) |
| banana | 1 | 0.0% / 0.0% | 100.0% / 0.0% | low-support (<10 boxes) |
| corn | 1 | 0.0% / 0.0% | 0.0% / 0.0% | low-support (<10 boxes) |
| ham | 1 | 0.0% / 0.0% | 100.0% / 0.0% | low-support (<10 boxes) |
| mango | 1 | 0.0% / 0.0% | 0.0% / 0.0% | low-support (<10 boxes) |
| shrimp | 0 | n/a | n/a | no ground-truth boxes |

## Most common wrong-class predictions (matched boxes, upright 960, conf 0.001)

| True class | Predicted | Count |
|---|---|---|
| jar | milk | 63 |
| jar | flour | 36 |
| cream | milk | 33 |
| jar | yogurt | 31 |
| jar | sugar | 23 |

## What explains the missing recall

1. **Confidence threshold (0.001 vs 0.25, 640 px upright):** end-to-end recall moves +19.6 points.
2. **EXIF orientation (model input rotated vs sideways, 640 px):** end-to-end recall moves +7.9 points.
3. **Image size (1280 vs 640 px, conf 0.001 upright):** end-to-end recall moves +3.3 points.
4. **Evaluation frame (ground truth scaled by display vs raw size, Ashton's saved predictions):** end-to-end recall moves +2.5 points.
- **Object size:** at 1280 px, end-to-end recall is <0.5%: 28.7%, 0.5-2%: 23.6%, 2-8%: 28.9%, >8%: 100.0% (GT counts 289, 501, 173, 2).
- **Class definitions:** at the best size, localization recall is 72.7% but end-to-end recall is 26.2%; among localized boxes 25.5% have the right class, so 46.5% of all ground-truth boxes are found but mislabeled.
- **How to read the ranking:** conf 0.001 is a recall ceiling, not a deployable setting. It returns 161 boxes per image against 6.0 ground-truth boxes per image, at mean matched confidence 0.138. At the deployed conf 0.25 the model returns 3.1 boxes per image and end-to-end recall is 3.3%. The EXIF row was measured at conf 0.001 only.

## Overlays (`overlays/`)

Six random images per set with ground-truth boxes drawn from the normalized labels. EXIF orientation of the picks: upright set [6, 1, 1, 1, 6, 1], raw set [6, 6, 1, 1, 6, 6]. Reviewed by eye (only these four): `upright_0`, `upright_3`, `raw_0`, `raw_3`. In the two upright images the boxes sit on the objects. In the raw set the boxes fit for an EXIF-1 photo (`raw_3`) and land on unrelated regions for an EXIF-6 photo (`raw_0`), because the photo is stored sideways while the labels follow the upright view. In the images reviewed, many visible items are not annotated, and `jar` covers glass food containers, bottles and jars.

## Caveats

- Scores come from one set of 160 photos from a small number of fridges, with no fridge IDs, so classes with few boxes are noisy.
- `.pt` rectangular inference is used here; the deployed ONNX model pads to a square (see `ml/export/MODEL_CARD.md`), so ONNX numbers can differ slightly.
- Ground truth was drawn by a person; box tightness is not checked here.
