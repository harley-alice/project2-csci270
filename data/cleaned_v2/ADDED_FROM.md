# data/cleaned_v2: what was added and from where

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

