# External sources audit, v3 (fridge food images v14 + fridge v1i)

Produced by `ml/add_external.py --v3`. `data/cleaned` and `data/cleaned_v2` were only read; the build is `data/cleaned_v3` (train only, prefix `ext3_`). No photos are in this report; contact sheets are untracked files in `data/cleaned_v3/`.

## Parameters

seed 270; per-class cap of included boxes 300 (mango and pomegranate 150; overrides {'egg': 100}); boxes under 0.5% width or height dropped; an image is dropped if a skipped-class box covers at least 5% of the image or overlaps a kept box (intersection over the smaller box >= 0.1); images whose only kept box covers more than 60% are dropped; over the cap, images with boxes under 15% of the image are preferred, then random; phash Hamming distance <= 4 incl. horizontal flip.

## fridge_food_images_v14

Roboflow preprocessing/augmentation per its README: auto-orient, resize 640x640 stretch, **augmentation: 3 versions per source image, rotation -15 to +15 degrees**.

| Class | train | valid | test | Maps to |
|---|---|---|---|---|
| apple | 743 | 46 | 194 | apple |
| banana | 829 | 53 | 55 | banana |
| blue berry | 446 | 92 | 57 | blueberries |
| bread | 215 | 41 | 88 | bread |
| brinjal | 665 | 39 | 32 | None |
| butter | 1071 | 73 | 236 | butter |
| cabbage | 198 | 13 | 12 | None |
| capsicum | 373 | 23 | 17 | bell_pepper |
| carrot | 1694 | 122 | 221 | carrot |
| cheese | 1112 | 238 | 195 | cheese |
| chicken | 828 | 214 | 108 | chicken |
| chocolate | 163 | 29 | 7 | chocolate |
| corn | 1373 | 197 | 63 | corn |
| cucumber | 342 | 31 | 24 | None |
| egg | 1858 | 251 | 157 | egg |
| flour | 2157 | 192 | 627 | flour |
| fresh cream | 1071 | 195 | 322 | cream |
| ginger | 593 | 37 | 19 | None |
| green beans | 1243 | 187 | 112 | green_beans |
| green chilly | 574 | 54 | 76 | None |
| green leaves | 890 | 40 | 57 | None |
| lemon | 452 | 30 | 209 | lemon |
| meat | 1622 | 53 | 249 | None |
| milk | 1316 | 214 | 341 | milk |
| mushroom | 938 | 115 | 58 | mushrooms |
| potato | 1507 | 169 | 302 | potato |
| shrimp | 1376 | 123 | 272 | shrimp |
| stawberry | 813 | 193 | 300 | strawberries |
| sweet potato | 1632 | 360 | 162 | sweet_potato |
| tomato | 1644 | 134 | 303 | tomato |

Boxes in skipped classes (all files): brinjal 736, cabbage 223, cucumber 397, ginger 649, green chilly 704, green leaves 987, meat 1924. `meat` and `green leaves` need Ashton's approval.

Polygon label lines converted to boxes: 6266. Tiny boxes dropped: 17. Source classes not in the map: none.

| Step | Images |
|---|---|
| files in the source | 5139 |
| distinct source images (base name before `.rf.`) | 1294 |
| dropped: unlabeled_object_overlaps_kept_box | 1353 |
| dropped: large_unlabeled_object | 261 |
| dropped: no_kept_boxes | 1383 |
| dropped: single_box_over_60pct | 23 |
| files surviving the label filters | 2119 (in 605 source images) |
| one copy per source image | 605 |
| dropped: phash match with data/cleaned / data/cleaned_v2 / data/real_fridge | 132 / 132 / 0 (any: 132) |
| dropped: near-duplicate of another external image | 0 |
| remaining before caps | 473 |
| skipped for the per-class caps | 148 |
| **added to train** | **325** |

## fridge_v1i

Roboflow preprocessing/augmentation per its README: no augmentation listed; filenames still show several files per source image.

| Class | train | valid | test | Maps to |
|---|---|---|---|---|
| Apple | 160 | 26 | 125 | dropped (keep-only) |
| Banana | 152 | 49 | 26 | dropped (keep-only) |
| Beetroot | 191 | 59 | 28 | dropped (keep-only) |
| Bell pepper | 362 | 127 | 45 | dropped (keep-only) |
| Cabbage | 138 | 27 | 20 | dropped (keep-only) |
| Carrot | 248 | 73 | 41 | dropped (keep-only) |
| Cauliflower | 102 | 23 | 12 | dropped (keep-only) |
| Chili pepper | 625 | 204 | 106 | dropped (keep-only) |
| Corn | 202 | 54 | 16 | dropped (keep-only) |
| Cucumber | 300 | 49 | 55 | dropped (keep-only) |
| Eggplant | 375 | 122 | 55 | dropped (keep-only) |
| Garlic | 390 | 80 | 42 | dropped (keep-only) |
| Ginger | 105 | 34 | 10 | dropped (keep-only) |
| Grapes | 130 | 27 | 14 | dropped (keep-only) |
| Jalapeno | 245 | 58 | 31 | dropped (keep-only) |
| Kiwi | 243 | 86 | 27 | dropped (keep-only) |
| Lemon | 235 | 70 | 31 | dropped (keep-only) |
| Lettuce | 88 | 20 | 12 | dropped (keep-only) |
| Mango | 154 | 38 | 12 | mango |
| Onion | 181 | 120 | 25 | dropped (keep-only) |
| Orange | 368 | 62 | 36 | dropped (keep-only) |
| Pear | 121 | 40 | 23 | dropped (keep-only) |
| Peas | 278 | 43 | 33 | dropped (keep-only) |
| Pineapple | 165 | 26 | 13 | dropped (keep-only) |
| Pomegranate | 226 | 51 | 25 | pomegranate |
| Potato | 584 | 138 | 70 | dropped (keep-only) |
| Radish | 225 | 36 | 45 | dropped (keep-only) |
| Soybean | 89 | 25 | 9 | dropped (keep-only) |
| Spinach | 70 | 21 | 10 | dropped (keep-only) |
| Sweet potato | 241 | 53 | 28 | dropped (keep-only) |
| Tomato | 547 | 112 | 103 | dropped (keep-only) |
| Turnip | 448 | 89 | 58 | dropped (keep-only) |
| Watermelon | 425 | 92 | 40 | dropped (keep-only) |

Polygon label lines converted to boxes: 0. Tiny boxes dropped: 0. Source classes not in the map: none.

| Step | Images |
|---|---|
| files in the source | 2732 |
| distinct source images (base name before `.rf.`) | 269 |
| dropped: no_kept_boxes | 2589 |
| dropped: single_box_over_60pct | 20 |
| files surviving the label filters | 123 (in 85 source images) |
| one copy per source image | 85 |
| dropped: phash match with data/cleaned / data/cleaned_v2 / data/real_fridge | 0 / 0 / 0 (any: 0) |
| dropped: near-duplicate of another external image | 0 |
| remaining before caps | 85 |
| skipped for the per-class caps | 29 |
| **added to train** | **56** |

## Train boxes per class: v2 vs v3

| Class | v2 train | +fridge_food_images_v14 | +fridge_v1i | v3 train |
|---|---|---|---|---|
| apple | 506 | 28 | 0 | 534 |
| avocado | 342 | 0 | 0 | 342 |
| bacon | 157 | 0 | 0 | 157 |
| banana | 238 | 18 | 0 | 256 |
| beef | 160 | 0 | 0 | 160 |
| bell_pepper | 208 | 81 | 0 | 289 |
| blueberries | 115 | 13 | 0 | 128 |
| bread | 164 | 2 | 0 | 166 |
| butter | 267 | 11 | 0 | 278 |
| carrot | 144 | 153 | 0 | 297 |
| cheese | 350 | 21 | 0 | 371 |
| chicken | 210 | 12 | 0 | 222 |
| chocolate (weak) | 57 | 1 | 0 | 58 |
| corn | 144 | 20 | 0 | 164 |
| cream | 114 | 19 | 0 | 133 |
| egg | 896 | 100 | 0 | 996 |
| flour | 180 | 26 | 0 | 206 |
| goat_cheese (weak) | 71 | 0 | 0 | 71 |
| green_beans | 135 | 232 | 0 | 367 |
| ham (weak) | 46 | 0 | 0 | 46 |
| jar | 302 | 0 | 0 | 302 |
| lemon | 286 | 29 | 0 | 315 |
| lime | 114 | 0 | 0 | 114 |
| mango (weak) | 23 | 0 | 149 | 172 |
| milk | 913 | 44 | 0 | 957 |
| mushrooms | 127 | 9 | 0 | 136 |
| onion | 130 | 0 | 0 | 130 |
| orange | 234 | 0 | 0 | 234 |
| persimmon | 124 | 0 | 0 | 124 |
| pomegranate (weak) | 44 | 0 | 150 | 194 |
| potato | 480 | 21 | 0 | 501 |
| shrimp | 135 | 14 | 0 | 149 |
| spinach | 200 | 0 | 0 | 200 |
| strawberries | 175 | 13 | 0 | 188 |
| sugar | 200 | 0 | 0 | 200 |
| sweet_potato | 126 | 29 | 0 | 155 |
| tomato | 478 | 255 | 0 | 733 |
| yogurt | 747 | 0 | 0 | 747 |

Total train boxes 9342 -> 10792; train images 1770 -> 2151 (valid and test unchanged).

## Mango and pomegranate sample files (for checking by eye)

**mango** (12 files):

- `ext3_fv1i_Image_38_jpg_rf_9f8701ab73e14682d826791d3d68216a.jpg`
- `ext3_fv1i_Image_55_JPG_rf_abe8aceac05cb6b5fb7cca5cf8808ab7.jpg`
- `ext3_fv1i_Image_27_jpg_rf_4cd7b880dced9fc8a549ab463290caf5.jpg`
- `ext3_fv1i_Image_49_jpg_rf_8f65a04e1d06b36ba3f1da74b6929bd5.jpg`
- `ext3_fv1i_Image_11_png_rf_aa6d990a0f111dc59771bb1a79b362f1.jpg`
- `ext3_fv1i_Image_48_jpg_rf_3a3ba278653d50b8f3bf05f2c92f5c95.jpg`
- `ext3_fv1i_Image_79_png_rf_747bd5f2e8b3ca6807363f69c6078898.jpg`
- `ext3_fv1i_Image_52_jpg_rf_4a3ab726eadcb2b42bee2752a13f65a1.jpg`
- `ext3_fv1i_Image_73_jpg_rf_97e5970cb65a5473be34e888fcd9b93c.jpg`
- `ext3_fv1i_Image_25_jpg_rf_e66384f0d8034ba80a471a10f88352f4.jpg`
- `ext3_fv1i_Image_85_jpg_rf_46effcd022d8d13b2b7b571d27d8658f.jpg`
- `ext3_fv1i_Image_45_jpg_rf_a2f3b5fbdaa5238e6e2ed3d779b6c7f0.jpg`

**pomegranate** (12 files):

- `ext3_fv1i_Image_31_jpg_rf_1aac13da86b8ce9d6e549b60a0b54a09.jpg`
- `ext3_fv1i_Image_60_jpg_rf_7634b1510238154a9eb1ed9247961574.jpg`
- `ext3_fv1i_Image_20_jpg_rf_e77874d1fe909fd75c0614c18c04a34b.jpg`
- `ext3_fv1i_Image_51_jpg_rf_35c37965e3f0ae24c287dea20cb4af60.jpg`
- `ext3_fv1i_Image_14_jpg_rf_5059333c2eaae969684141e1eb719967.jpg`
- `ext3_fv1i_Image_72_jpg_rf_3926c18ce15fb9f229da54e1cf9f800f.jpg`
- `ext3_fv1i_Image_58_jpg_rf_01a74d9bde6abe897ece6edf52332102.jpg`
- `ext3_fv1i_Image_79_jpg_rf_64ea803e460e4f29d37eeb21e6868016.jpg`
- `ext3_fv1i_Image_71_jpg_rf_652c77c6e87a5857c7dad463b12bc6d0.jpg`
- `ext3_fv1i_Image_3_jpg_rf_aeabd22ad92c7c5c72ef9a9fc4eb4687.jpg`
- `ext3_fv1i_Image_43_jpg_rf_84bed45fac48b212419d23b62e1fbf49.jpg`
- `ext3_fv1i_Image_2_jpg_rf_2aaa0d6de157d1c3494fe7a05d52c721.jpg`

Untracked contact sheets of the selected images: `data/cleaned_v3/_contact_A_fridge_food_images_v14.jpg`, `data/cleaned_v3/_contact_B_mango.jpg`, `data/cleaned_v3/_contact_B_pomegranate.jpg`.

## Validation

| Check | Result | Detail |
|---|---|---|
| every image has a label file | PASS | 0 missing |
| every label line has 5 values | PASS | 0 bad |
| class ids within 0-37 | PASS | 0 out of range |
| boxes within [0,1] | PASS | 0 outside |
| no duplicate filenames in train | PASS |  |
| no image in both train and valid/test (checksum) | PASS |  |
| added images vs valid/test: phash distance > 4 | PASS |  |
| valid/test identical to data/cleaned (checksum) | PASS |  |
| data/cleaned and data/cleaned_v2 unchanged | PASS |  |
| data.yaml: relative paths, same class order | PASS |  |
| added files carry the ext3_ prefix | PASS | 381 files |
| no added file from data/real_fridge | PASS |  |
