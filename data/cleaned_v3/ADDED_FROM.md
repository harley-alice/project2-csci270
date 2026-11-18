# data/cleaned_v3: what was added and from where

v3 starts from `data/cleaned_v2` (copied: train, valid, test, data.yaml) and adds external images to **train only**, prefixed `ext3_`. `valid/` and `test/` are identical to `data/cleaned`. Real-fridge QA photos are not used. Rebuild with `python ml/add_external.py --v3 --overwrite`.

Per-class cap overrides on included external boxes: {'egg': 100} (default 300; mango and pomegranate 150).

## New sources (v3)

### fridge_food_images_v14

- URL: https://universe.roboflow.com/fridge-dataset/fridge-food-images/dataset/14
- Roboflow workspace/project: `fridge-dataset/fridge-food-images`, version 14.
- License: **CC BY 4.0** per Roboflow (https://creativecommons.org/licenses/by/4.0/); **check original** for the underlying photos. Attribution: provided by a Roboflow user; changes made: boxes converted to this project's classes and a subset selected.
- Source files 5139 (1294 source images); added to train: **325** images.

### fridge_v1i

- URL: https://universe.roboflow.com/imsun/fridge-5ep2w-qm8bh/dataset/1
- Roboflow workspace/project: `imsun/fridge-5ep2w-qm8bh`, version 1.
- License: **CC BY 4.0** per Roboflow (https://creativecommons.org/licenses/by/4.0/); **check original** for the underlying photos. Attribution: provided by a Roboflow user; changes made: boxes converted to this project's classes and a subset selected.
- Source files 2732 (269 source images); added to train: **56** images.

## Mapping used (source class -> my class; None = skipped, box dropped)

### fridge_food_images_v14

| Source class | Maps to |
|---|---|
| apple | apple |
| banana | banana |
| blue berry | blueberries |
| bread | bread |
| brinjal | None |
| butter | butter |
| cabbage | None |
| capsicum | bell_pepper |
| carrot | carrot |
| cheese | cheese |
| chicken | chicken |
| chocolate | chocolate |
| corn | corn |
| cucumber | None |
| egg | egg |
| flour | flour |
| fresh cream | cream |
| ginger | None |
| green beans | green_beans |
| green chilly | None |
| green leaves | None |
| lemon | lemon |
| meat | None |
| milk | milk |
| mushroom | mushrooms |
| potato | potato |
| shrimp | shrimp |
| stawberry | strawberries |
| sweet potato | sweet_potato |
| tomato | tomato |

### fridge_v1i

| Source class | Maps to |
|---|---|
| Mango | mango |
| Pomegranate | pomegranate |
| every other class | dropped (keep-only source) |

## Boxes added per class (train)

| Class | v2 train boxes | fridge_food_images_v14 | fridge_v1i | v3 train boxes |
|---|---|---|---|---|
| apple | 506 | 28 | 0 | 534 |
| banana | 238 | 18 | 0 | 256 |
| bell_pepper | 208 | 81 | 0 | 289 |
| blueberries | 115 | 13 | 0 | 128 |
| bread | 164 | 2 | 0 | 166 |
| butter | 267 | 11 | 0 | 278 |
| carrot | 144 | 153 | 0 | 297 |
| cheese | 350 | 21 | 0 | 371 |
| chicken | 210 | 12 | 0 | 222 |
| chocolate | 57 | 1 | 0 | 58 |
| corn | 144 | 20 | 0 | 164 |
| cream | 114 | 19 | 0 | 133 |
| egg | 896 | 100 | 0 | 996 |
| flour | 180 | 26 | 0 | 206 |
| green_beans | 135 | 232 | 0 | 367 |
| lemon | 286 | 29 | 0 | 315 |
| mango | 23 | 0 | 149 | 172 |
| milk | 913 | 44 | 0 | 957 |
| mushrooms | 127 | 9 | 0 | 136 |
| pomegranate | 44 | 0 | 150 | 194 |
| potato | 480 | 21 | 0 | 501 |
| shrimp | 135 | 14 | 0 | 149 |
| strawberries | 175 | 13 | 0 | 188 |
| sweet_potato | 126 | 29 | 0 | 155 |
| tomato | 478 | 255 | 0 | 733 |

---

## Earlier additions (carried over from data/cleaned_v2)


`valid/` and `test/` are byte-identical copies of `data/cleaned`. `train/` is all of `data/cleaned` train plus the external images below. Real-fridge QA photos are not used anywhere in this dataset. Rebuild with `python ml/add_external.py --overwrite`.

## Sources and licenses

### refrigerator_contents

- URL: https://universe.roboflow.com/new-workspace-32uyj/refridgerator-contents-detection
- Roboflow workspace/project: `new-workspace-32uyj/refridgerator-contents-detection`, version 1, license **CC BY 4.0** (https://creativecommons.org/licenses/by/4.0/).
- Attribution: "refridgerator-contents-detection" (Roboflow Universe, workspace new-workspace-32uyj), provided by a Roboflow user, licensed under CC BY 4.0. Changes made: the class labels were remapped to this project's 38 classes, a subset of images was selected, and no pixel changes were applied by this project (Roboflow had already resized the images to 640x640 with stretch).
- Images in the source: 1103. Added to train: **150**. Eligible before the cap: 1100. Exclusions: {'near_duplicate_of_data_cleaned': 3, 'augmentation_copy': 0, 'same_scene_cluster_as_selected': 1}.

### objects_inside_a_fridge

- URL: https://universe.roboflow.com/shounak-mishra/objects-inside-a-fridge
- Roboflow workspace/project: `shounak-mishra/objects-inside-a-fridge`, version 1, license **CC BY 4.0** (https://creativecommons.org/licenses/by/4.0/).
- Attribution: "objects-inside-a-fridge" (Roboflow Universe, workspace shounak-mishra), provided by a Roboflow user, licensed under CC BY 4.0. Changes made: the class labels were remapped to this project's 38 classes, a subset of images was selected, and no pixel changes were applied by this project (Roboflow had already resized the images to 640x640 with stretch).
- Images in the source: 51. Added to train: **0**. Eligible before the cap: 0. Exclusions: {'near_duplicate_of_data_cleaned': 0, 'augmentation_copy': 41, 'too_many_unmapped_boxes': 10}.

## Approved class mapping (external class -> my class, None = box dropped)

### refrigerator_contents

| External class | Maps to |
|---|---|
| banana | banana |
| bread | bread |
| eggs | egg |
| milk | milk |
| potato | potato |
| spinach | spinach |
| tomato | tomato |

### objects_inside_a_fridge

| External class | Maps to |
|---|---|
| bottle | None |
| bread | bread |
| chesse | cheese |
| chocolate | chocolate |
| cold drinks | None |
| egg tray | None |
| energy drinks | None |
| honey | jar |
| jam | jar |
| ketchup | jar |
| nan | None |
| softdrinks | None |
| spices | None |
| utensil | None |

Policy: an image is kept only if every one of its boxes maps to one of my classes, so no object is left unlabeled by a dropped box. Per source, at most 150 images (the default cap); ranking prefers images that contain a priority class (for refrigerator_contents: bread, banana, potato, spinach), then images with two or more boxes, then class variety, with a seeded tie-break and at most one image per near-duplicate scene cluster.

## Boxes added per class

| Class | Train boxes before | refrigerator_contents | objects_inside_a_fridge | Train boxes after |
|---|---|---|---|---|
| banana | 115 | 123 | 0 | 238 |
| bread | 93 | 71 | 0 | 164 |
| egg | 858 | 38 | 0 | 896 |
| milk | 862 | 51 | 0 | 913 |
| potato | 172 | 308 | 0 | 480 |
| spinach | 126 | 74 | 0 | 200 |
| tomato | 405 | 73 | 0 | 478 |


