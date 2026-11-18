# Drops caused by skipped classes (diagnosis only; nothing was built)

Produced by `ml/diagnose_drops.py` for `fridge_food_images_v14`. Definitions are in that script's docstring. Mask rules: every skipped box under 5% of the image area and no overlap with a kept box above 20% of that kept box's area. Meat-like overlap: IoU > 0.3 or containment > 0.7 against a kept beef/chicken/bacon/shrimp box. Seed 270.

## 0. File level versus source-photo level

Each source photo is exported as up to three augmented copies (rotation of up to 15 degrees), and the build keeps one copy per photo. 1614 files were dropped for overlap or size, but **323 of them belong to a photo that still has a surviving copy**, so the file counts overstate the photos lost. Photo-level outcome (1294 source photos):

| Outcome | Source photos |
|---|---|
| included (at least one copy survives) | 605 |
| not included: blocked only by meat / green leaves | 46 |
|   of which some copies were dropped for overlap/large | 13 |
| not included: only skipped-class boxes (no kept box) | 584 |
| not included: blocked only by other skipped classes | 57 |
| not included: other (for example single box over 60%) | 2 |

**Heavily augmented photos:** 49 source photos have more than 3 copies (up to 72 augmented versions of one shelf photo, with noise, cutouts and rotation; their copies are about phash distance 20 apart, so only base-name grouping finds them). They hold 2358 of 5139 files and 1444 of the 1614 files dropped for overlap or size, which is why the file counts look so large. Their photo-level outcome: {'blocked only by meat / green leaves': 23, 'included': 26}. These cluttered multi-item shelves are the closest thing in this dataset to real fridge photos.

## 1. Kept classes: boxes lost only to `meat` / `green leaves`

46 source photos were dropped only because of `meat` / `green leaves` (no surviving copy; they would pass the single-box rule); 25 remain after removing near-duplicates of my data. Boxes are counted from the best copy of each photo.

| Class | v2 train boxes | Added in v3 | Cap | Headroom | Lost only to meat/green leaves |
|---|---|---|---|---|---|
| apple | 506 | 37 | 300 | 263 | 15 |
| banana | 238 | 20 | 300 | 280 | 2 |
| bell_pepper | 208 | 86 | 300 | 214 | 0 |
| blueberries | 115 | 15 | 300 | 285 | 1 |
| bread | 164 | 5 | 300 | 295 | 3 |
| butter | 267 | 11 | 300 | 289 | 15 |
| carrot | 144 | 157 | 300 | 143 | 14 |
| cheese | 350 | 21 | 300 | 279 | 12 |
| chicken | 210 | 17 | 300 | 283 | 9 |
| chocolate | 57 | 1 | 300 | 299 | 3 |
| corn | 144 | 21 | 300 | 279 | 9 |
| cream | 114 | 21 | 300 | 279 | 16 |
| egg | 896 | 300 | 300 | 0 | 4 |
| flour | 180 | 29 | 300 | 271 | 32 |
| green_beans | 135 | 235 | 300 | 65 | 5 |
| lemon | 286 | 34 | 300 | 266 | 6 |
| milk | 913 | 51 | 300 | 249 | 13 |
| mushrooms | 127 | 10 | 300 | 290 | 18 |
| potato | 480 | 24 | 300 | 276 | 16 |
| shrimp | 135 | 17 | 300 | 283 | 18 |
| strawberries | 175 | 13 | 300 | 287 | 16 |
| sweet_potato | 126 | 31 | 300 | 269 | 14 |
| tomato | 478 | 256 | 300 | 44 | 15 |

Headroom is the cap minus the boxes already added; boxes lost beyond the headroom would be skipped by the cap anyway. Mango and pomegranate come from fridge v1i, not from this dataset.

## 2. Files dropped for a `meat` overlap

777 files were dropped because a `meat` box overlaps a kept box (of 1685 files containing `meat`). The kept classes those `meat` boxes overlap: {'cream': 216, 'shrimp': 162, 'milk': 145, 'sweet_potato': 128, 'blueberries': 125, 'banana': 103, 'mushrooms': 71, 'apple': 5, 'flour': 4, 'chicken': 1, 'corn': 1, 'lemon': 1}.

**0 of them have the `meat` box overlapping a kept beef/chicken/bacon/shrimp box** (IoU > 0.3 or containment > 0.7): {} (this dataset has no kept beef or bacon).

Largest overlap (containment) between a `meat` box and a kept beef/chicken/bacon/shrimp box, files per range: 0.01-0.1: 87, 0.1-0.3: 163. Overlaps exist (mostly `meat` boxes touching kept shrimp), but none reach the IoU > 0.3 or containment > 0.7 thresholds.

12 sample files (seeded): none, because no file meets the rule.


## 3. Mask rules

2152 files have at least one skipped-class box under 5% of the image and at least one kept box. Outcome of the mask rules:

| Current status | would pass | skipped box >= 5% | overlaps a kept box by > 20% of its area |
|---|---|---|---|
| currently dropped (large_unlabeled_object) | 0 | 240 | 0 |
| currently dropped (unlabeled_object_overlaps_kept_box) | 611 | 0 | 742 |
| currently kept | 559 | 0 | 0 |

'currently kept' images already pass the drop rule; masking would only clean up their small unlabeled objects. The 'currently dropped' rows are the images masking could bring back.

### Source photos masking would bring back

25 source photos have no surviving copy but a copy that passes the mask rules and the single-box rule; 19 remain after removing near-duplicates of my data. Of those, 0 have a `meat` box on a kept beef/chicken/bacon/shrimp box and would be skipped in Part 2 (listed instead of masked). Skipped classes that would be masked: meat 14, brinjal 11, green chilly 10, green leaves 7, ginger 3, cabbage 2, cucumber 1.

| Class | Boxes in those photos | Added in v3 | Cap | Boxes that fit under the cap |
|---|---|---|---|---|
| apple | 14 | 37 | 300 | 14 |
| banana | 1 | 20 | 300 | 1 |
| bell_pepper | 2 | 86 | 300 | 2 |
| blueberries | 1 | 15 | 300 | 1 |
| butter | 10 | 11 | 300 | 10 |
| carrot | 26 | 157 | 300 | 26 |
| cheese | 8 | 21 | 300 | 8 |
| chicken | 4 | 17 | 300 | 4 |
| corn | 5 | 21 | 300 | 5 |
| cream | 12 | 21 | 300 | 12 |
| egg | 8 | 300 | 300 | 0 |
| flour | 24 | 29 | 300 | 24 |
| green_beans | 8 | 235 | 300 | 8 |
| lemon | 8 | 34 | 300 | 8 |
| milk | 10 | 51 | 300 | 10 |
| mushrooms | 4 | 10 | 300 | 4 |
| potato | 8 | 24 | 300 | 8 |
| shrimp | 12 | 17 | 300 | 12 |
| strawberries | 10 | 13 | 300 | 10 |
| sweet_potato | 4 | 31 | 300 | 4 |
| tomato | 14 | 256 | 300 | 14 |

