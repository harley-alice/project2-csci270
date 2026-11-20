# External dataset audit (Phase 1, read-only)

Produced by `ml/audit_external.py`. `data/cleaned/` was only read. Numbers are also written to `results.json` (kept locally, not committed). No photos are included here; each dataset has an untracked `_contact.jpg` under `data/external/<name>/`.

## refrigerator_contents

Roboflow `new-workspace-32uyj/refridgerator-contents-detection`, version 1, license **CC BY 4.0**. Images per split: {'train': 769, 'valid': 221, 'test': 113}. Image sizes: {'640x640': 1103}. Boxes: 3079; images without boxes: 0; polygon label lines converted to boxes: 0.

| Class | Boxes | train/valid/test | Median box area | Boxes in eligible unique images |
|---|---|---|---|---|
| eggs | 771 | 448/210/113 | 5.56% | 771 |
| potato | 609 | 429/138/42 | 8.41% | 609 |
| tomato | 542 | 395/96/51 | 7.70% | 538 |
| milk | 398 | 255/93/50 | 12.97% | 398 |
| banana | 314 | 224/52/38 | 22.16% | 314 |
| spinach | 236 | 173/38/25 | 21.83% | 236 |
| bread | 209 | 140/37/32 | 34.44% | 209 |

**Augmentation copies:** 1103 base names; 0 groups have more than one file (0 extra copies); 0 groups span more than one split. Files per base name: all 1.

**Duplicates and scenes:** within the dataset, 75 images have a near-duplicate (phash <= 4 incl. flip); complete-linkage scene clusters: 1065 (36 with more than one image, largest 3).
Against `data/cleaned`: within distance 4 of train 3, **valid 0, test 0** (these must be excluded); any split 3. Eligible after exclusions (one file per base name, none near-duplicate of `data/cleaned`): **1100** images.

Minimum distance to `data/cleaned` (images per bucket):

| Split | 0 | 1-2 | 3-4 | 5-8 | >8 |
|---|---|---|---|---|---|
| train | 3 | 0 | 0 | 2 | 1098 |
| valid | 0 | 0 | 0 | 1 | 1102 |
| test | 0 | 0 | 0 | 0 | 1103 |

## objects_inside_a_fridge

Roboflow `shounak-mishra/objects-inside-a-fridge`, version 1, license **CC BY 4.0**. Images per split: {'train': 36, 'valid': 10, 'test': 5}. Image sizes: {'640x640': 51}. Boxes: 594; images without boxes: 0; polygon label lines converted to boxes: 1.

| Class | Boxes | train/valid/test | Median box area | Boxes in eligible unique images |
|---|---|---|---|---|
| spices | 135 | 101/26/8 | 0.43% | 27 |
| cold drinks | 87 | 64/21/2 | 1.05% | 13 |
| softdrinks | 66 | 39/13/14 | 1.33% | 16 |
| ketchup | 52 | 32/15/5 | 1.41% | 8 |
| chocolate | 43 | 30/8/5 | 1.11% | 9 |
| honey | 43 | 29/13/1 | 0.67% | 9 |
| egg tray | 43 | 33/7/3 | 5.75% | 7 |
| chesse | 27 | 19/7/1 | 1.70% | 5 |
| utensil | 25 | 17/7/1 | 1.23% | 5 |
| nan | 25 | 13/4/8 | 0.75% | 4 |
| energy drinks | 24 | 20/1/3 | 0.91% | 2 |
| jam | 21 | 17/2/2 | 1.02% | 4 |
| bottle | 2 | 2/0/0 | 0.41% | 0 |
| bread | 1 | 1/0/0 | 0.65% | 0 |

**Augmentation copies:** 10 base names; 9 groups have more than one file (41 extra copies); 8 groups span more than one split. Files per base name: [1, 2, 3, 3, 3, 6, 6, 9, 9, 9].

**Duplicates and scenes:** within the dataset, 32 images have a near-duplicate (phash <= 4 incl. flip); complete-linkage scene clusters: 36 (13 with more than one image, largest 3).
Against `data/cleaned`: within distance 4 of train 0, **valid 0, test 0** (these must be excluded); any split 0. Eligible after exclusions (one file per base name, none near-duplicate of `data/cleaned`): **10** images.

Minimum distance to `data/cleaned` (images per bucket):

| Split | 0 | 1-2 | 3-4 | 5-8 | >8 |
|---|---|---|---|---|---|
| train | 0 | 0 | 0 | 0 | 51 |
| valid | 0 | 0 | 0 | 0 | 51 |
| test | 0 | 0 | 0 | 0 | 51 |

## Box-size distribution (share of boxes by area as a share of the image)

| Bucket | refrigerator_contents | objects_inside_a_fridge | my data/cleaned train |
|---|---|---|---|
| <0.5% | 0.4% | 20.2% | 4.0% |
| 0.5-2% | 6.2% | 62.3% | 43.3% |
| 2-8% | 36.1% | 16.7% | 37.8% |
| >8% | 57.3% | 0.8% | 14.9% |

Median box area: refrigerator_contents 9.67%, objects_inside_a_fridge 0.99%, my train 2.20%. My `egg` boxes: median 1.56%; my `jar` boxes: median 3.93%.

## What the contact sheets show (reviewed by eye, 24 random images each)

- **refrigerator_contents:** stock product photography, not fridge interiors: one to a handful of items on plain, white or coloured backgrounds, with stock-photo watermarks, close-ups and very large boxes. Only a few images show items in a fridge. Eggs are boxed one by one, like my egg boxes. Images were stretched to 640x640, so shapes are distorted.
- **objects_inside_a_fridge:** one fridge seen through a wide-angle camera, repeated in all 51 images. Many frames are visibly rotated, sheared or re-lit copies of the same few shots, despite the README saying no augmentation. Dense scenes with 10 to 15 small boxes (drinks, spices, jars, chocolate). The `egg tray` box covers a whole transparent tray, and `nan` marks small unnamed items.

My own `egg` boxes (12 train images checked by eye) are drawn per egg or per small group. One of the 12 shows a large `egg` box around a tomato and packaged goods, which looks like a label error in `data/cleaned` worth a separate check.

## Proposed class mapping

Status `ASK` = **NEEDS MY APPROVAL**. `None` means the box is dropped.

### refrigerator_contents

| External class | Boxes | Maps to | Status | Reason |
|---|---|---|---|---|
| banana | 314 | banana | ok | same food |
| bread | 209 | bread | ok | same food |
| eggs | 771 | egg | NEEDS MY APPROVAL | per-egg boxes like mine (checked on 12 of my egg images and the contact sheet), but close-up scale: median box 5.56% vs my 1.56% |
| milk | 398 | milk | ok | same food |
| potato | 609 | potato | ok | same food |
| spinach | 236 | spinach | ok | same food |
| tomato | 542 | tomato | ok | same food |

### objects_inside_a_fridge

| External class | Boxes | Maps to | Status | Reason |
|---|---|---|---|---|
| bottle | 2 | None | ok | generic bottle (2 boxes); no matching class |
| bread | 1 | bread | ok | same food (1 box) |
| chesse | 27 | cheese | ok | typo of cheese |
| chocolate | 43 | chocolate | ok | same food (weak class) |
| cold drinks | 87 | None | ok | drinks are not in the 38 classes (my map also drops soda_can) |
| egg tray | 43 | None | NEEDS MY APPROVAL | one box covers a whole tray (my egg boxes are per egg), so mapping it to egg would teach a different box shape; proposed None |
| energy drinks | 24 | None | ok | drinks are not in the 38 classes |
| honey | 43 | jar | NEEDS MY APPROVAL | honey container; my jar class was relabelled from catch-all 'others' boxes |
| jam | 21 | jar | NEEDS MY APPROVAL | jam container; same question as honey |
| ketchup | 52 | jar | NEEDS MY APPROVAL | ketchup bottle/jar; same question as honey |
| nan | 25 | None | NEEDS MY APPROVAL | unnamed class: check the contact sheet before deciding |
| softdrinks | 66 | None | ok | drinks are not in the 38 classes |
| spices | 135 | None | NEEDS MY APPROVAL | spice jars at 0.43% median area (tiny, below my jar median of 3.93%); proposed None |
| utensil | 25 | None | ok | not a food |

## Policies: images kept and boxes added

Policy (a): keep images where every box maps. Policy (b): keep images where at least 90% of boxes map. 'proposed' applies the mapping above (each ASK row goes to its proposed target); 'conservative' treats every ASK row as None. Counts are after the exclusions (one file per augmentation base name, no near-duplicate of `data/cleaned`).

### refrigerator_contents

| Class | My train boxes | proposed a_all_boxes_map | proposed b_90pct_map | conservative a_all_boxes_map | conservative b_90pct_map |
|---|---|---|---|---|---|
| **images kept** | 1620 images | 1100 | 1100 | 911 | 916 |
| chocolate (weak) | 57 | 0 | 0 | 0 | 0 |
| goat_cheese (weak) | 71 | 0 | 0 | 0 | 0 |
| ham (weak) | 46 | 0 | 0 | 0 | 0 |
| mango (weak) | 23 | 0 | 0 | 0 | 0 |
| pomegranate (weak) | 44 | 0 | 0 | 0 | 0 |
| bread | 93 | 209 | 209 | 178 | 183 |
| cheese | 350 | 0 | 0 | 0 | 0 |
| egg | 858 | 771 | 771 | 0 | 0 |
| milk | 862 | 398 | 398 | 355 | 365 |
| butter | 267 | 0 | 0 | 0 | 0 |
| yogurt | 747 | 0 | 0 | 0 | 0 |
| banana | 115 | 314 | 314 | 266 | 271 |
| potato | 172 | 609 | 609 | 569 | 579 |
| spinach | 126 | 236 | 236 | 213 | 218 |
| tomato | 405 | 538 | 538 | 486 | 506 |
| unlabeled boxes left in kept images | | 0 | 0 | 0 | 5 |

### objects_inside_a_fridge

| Class | My train boxes | proposed a_all_boxes_map | proposed b_90pct_map | conservative a_all_boxes_map | conservative b_90pct_map |
|---|---|---|---|---|---|
| **images kept** | 1620 images | 0 | 0 | 0 | 0 |
| chocolate (weak) | 57 | 0 | 0 | 0 | 0 |
| goat_cheese (weak) | 71 | 0 | 0 | 0 | 0 |
| ham (weak) | 46 | 0 | 0 | 0 | 0 |
| mango (weak) | 23 | 0 | 0 | 0 | 0 |
| pomegranate (weak) | 44 | 0 | 0 | 0 | 0 |
| bread | 93 | 0 | 0 | 0 | 0 |
| cheese | 350 | 0 | 0 | 0 | 0 |
| egg | 858 | 0 | 0 | 0 | 0 |
| milk | 862 | 0 | 0 | 0 | 0 |
| butter | 267 | 0 | 0 | 0 | 0 |
| yogurt | 747 | 0 | 0 | 0 | 0 |
| unlabeled boxes left in kept images | | 0 | 0 | 0 | 0 |

Risk: dropping an unmapped box (None) leaves that object unlabeled in a kept image, which teaches the model to treat it as background. The last row of each table counts those boxes.

## Recommendations

**refrigerator_contents: use a subset.** 1100 eligible images, no augmentation copies (0), no near-duplicate of my valid or test (0 and 0), CC BY 4.0 (attribution required). All 7 classes map to my classes; the only ASK row is `eggs` (per-egg boxes, so compatible). It more than doubles my train boxes for bread, banana, potato, spinach (policy a adds bread +209 on 93, banana +314 on 115, potato +609 on 172, spinach +236 on 126), while egg, milk, tomato already have 858, 862, 405 train boxes. Against that: 57.3% of its boxes cover more than 8% of the image (my train 14.9%) and only 0.4% are under 0.5% (my train 4.0%), and the images are stock photos, so it pushes the box-size distribution away from cluttered real fridge photos. It adds 0 boxes to chocolate, goat_cheese, ham, mango, pomegranate, cheese, butter, yogurt, jar. Suggested cap: the default 150 images, taken from images that contain bread, banana, potato or spinach and have two or more boxes. Dropping the ASK class (`eggs`) costs 189 of 1100 images under policy (a).

**objects_inside_a_fridge: skip.** It has 10 unique photos behind 51 files (41 extra copies; 8 of 9 multi-file groups span splits), all from one fridge. No image passes policy (b) with the proposed mapping, and it adds nothing to the weak classes: `chocolate` has 43 boxes in the files but 9 in the unique photos, and those photos' drinks, spices and utensils would be left unlabeled. It matches the real-fridge box size better (20.2% of boxes under 0.5%), but one fridge and 10 scenes would mainly teach that fridge.

Neither dataset adds `butter`, `cream` or `yogurt`, and together they add 0 `jar` boxes under policy (b), the classes that the real-fridge diagnostics (branch `ml/real-fridge-diagnostics`) found weakest. Additional real fridge photos, split by fridge, are likely worth more than either source.

