# Baseline YOLOv8n evaluation (valid split)

All numbers below were produced by `ml/evaluate.py` (files in this folder). The test split was not used.

## Headline metrics

| Metric | Value |
|---|---|
| mAP@50 | 0.930 |
| mAP@50-95 | 0.720 |
| Mean precision | 0.914 |
| Mean recall | 0.894 |
| Images / instances evaluated | 398 / 1989 |

Run config: weights `ml/runs/baseline_v8n/weights/best.pt`, split `val` (valid/), imgsz 640, conf 0.001, iou 0.6, seed 0 (training), device mps. Precision/recall are at the confidence that maximises F1 (Ultralytics default); the confusion matrix is built in a separate pass at conf 0.25 (a deployable threshold), so its counts are not the same operating point as the P/R above.

## Convergence

| Loss | train final | val final | val mean ep26-35 | val mean last 10 | val change | train change |
|---|---|---|---|---|---|---|
| box | 0.614 | 0.726 | 0.736 | 0.728 | -1.1% | -11.0% |
| cls | 0.411 | 0.684 | 0.712 | 0.684 | -4.0% | -21.6% |
| dfl | 0.942 | 1.021 | 1.026 | 1.022 | -0.4% | -3.5% |

Validation loss is roughly flat from epoch 26 onward (all three within 5%) while training loss keeps falling, so extra epochs would mainly widen the train/val gap.

## Weak classes

| Class | Val instances | Train instances | Precision | Recall | AP50 | AP50-95 | Support |
|---|---|---|---|---|---|---|---|
| chocolate | 14 | 57 | 1.000 | 0.762 | 0.990 | 0.575 | low-support: metric unreliable |
| goat_cheese | 10 | 71 | 0.945 | 1.000 | 0.995 | 0.738 | low-support: metric unreliable |
| ham | 13 | 46 | 0.972 | 1.000 | 0.995 | 0.716 | low-support: metric unreliable |
| mango | 15 | 23 | 0.904 | 0.630 | 0.937 | 0.826 | low-support: metric unreliable |
| pomegranate | 15 | 44 | 0.585 | 0.867 | 0.869 | 0.781 | low-support: metric unreliable |

Top confusions (count) and likely cause:

- **chocolate**: true as other: none; predicted as chocolate but actually: none; missed to background: 2; false positives on background: 0. Likely cause: few training instances (57).
- **goat_cheese**: true as other: none; predicted as goat_cheese but actually: none; missed to background: 0; false positives on background: 0. Likely cause: no clear weakness on valid (AP50 0.995 and recall 1.000 are at or above the overall values); the few instances make this uncertain. Note: few training instances (71).
- **ham**: true as other: none; predicted as ham but actually: none; missed to background: 0; false positives on background: 0. Likely cause: no clear weakness on valid (AP50 0.995 and recall 1.000 are at or above the overall values); the few instances make this uncertain. Note: few training instances (46).
- **mango**: true as other: none; predicted as mango but actually: none; missed to background: 4; false positives on background: 2. Likely cause: few training instances (23); 4 missed detections.
- **pomegranate**: true as other: orange:2; predicted as pomegranate but actually: orange:1; missed to background: 0; false positives on background: 8. Likely cause: few training instances (44); true pomegranate most often predicted as orange (2); predicted pomegranate most often actually orange (1).

1 of the 5 weak classes has AP50 below the overall mAP@50 (0.930); 5 have fewer than 20 valid instances, so their per-class numbers move a lot with a few boxes.

## Safety-critical classes

| Class | Val instances | Precision | Recall | AP50 | AP50-95 | Recall vs mean recall |
|---|---|---|---|---|---|---|
| chicken | 57 | 0.966 | 0.997 | 0.977 | 0.680 | above (0.894) |
| beef | 50 | 0.839 | 0.980 | 0.976 | 0.608 | above (0.894) |
| shrimp | 35 | 0.933 | 1.000 | 0.991 | 0.658 | above (0.894) |

Where true instances go (confusion matrix, conf 0.25):

| Class | True n | Correct | Other meat | Produce/other food | Missed (background) |
|---|---|---|---|---|---|
| chicken | 57 | 57 (100.0%) | 0 (0.0%) | 0 (0.0%) | 0 (0.0%) |
| beef | 50 | 49 (98.0%) | 0 (0.0%) | 0 (0.0%) | 1 (2.0%) |
| shrimp | 35 | 35 (100.0%) | 0 (0.0%) | 0 (0.0%) | 0 (0.0%) |

What the predictions of each class actually were:

| Predicted | Predicted n | Correct | Actually other meat | Actually produce/other | Background (false positive) |
|---|---|---|---|---|---|
| chicken | 59 | 57 (96.6%) | 0 (0.0%) | 1 (1.7%) | 1 (1.7%) |
| beef | 61 | 49 (80.3%) | 0 (0.0%) | 0 (0.0%) | 12 (19.7%) |
| shrimp | 37 | 35 (94.6%) | 0 (0.0%) | 2 (5.4%) | 0 (0.0%) |

- **chicken**: recall 0.997 is above the mean recall (0.894). 0 of 57 true instances (0.0%) were the dangerous failures (missed or labelled as produce/other food; top produce/other labels: none); 0 went to another meat class.
- **beef**: recall 0.980 is above the mean recall (0.894). 1 of 50 true instances (2.0%) were the dangerous failures (missed or labelled as produce/other food; top produce/other labels: none); 0 went to another meat class.
- **shrimp**: recall 1.000 is above the mean recall (0.894). 0 of 35 true instances (0.0%) were the dangerous failures (missed or labelled as produce/other food; top produce/other labels: none); 0 went to another meat class.

## Caveats

- The valid split is small (398 images), and 6 classes have fewer than 20 valid instances.
- The cleaning report records 64 of 803 valid/test images with a train neighbour within phash distance 4, and a 287-image same-scene `aicook` group that spans all splits. These numbers are probably optimistic.
- Confirm on a separate set of real fridge photos before trusting these numbers for the app.
- The confusion matrix is at conf 0.25 while P/R use the F1-optimal threshold, so counts and rates will not match exactly.

## Files

`metrics_summary.json`, `per_class_metrics.csv`, `confusion_matrix.png`, `confusion_matrix_normalized.png`, `confusion_matrix_large.png`, `confusion_matrix_counts.csv` (rows predicted, columns true, incl. background), `weak_class_analysis.csv`, `safety_class_analysis.json`, plus Ultralytics PR/F1/P/R curve PNGs.
