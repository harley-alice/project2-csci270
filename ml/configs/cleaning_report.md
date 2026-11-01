# Cleaning report

Seed 0. Cluster-aware stratified split, target 70/15/15 by images.

## Images

| Reason | Count |
|---|---|
| Raw images | 3391 |
| Dropped: corrupt/unreadable | 0 |
| Dropped: no boxes left after remap/cleaning | 124 |
| Dropped: exact duplicate (identical bytes) | 4 |
| Dropped: near-duplicate (phash dist <= 4 incl. h-flip, AND same class multiset) | 815 |
| &nbsp;&nbsp;of the duplicates: within the same dataset | 819 |
| &nbsp;&nbsp;of the duplicates: across datasets | 0 |
| Dropped: valid/test image within phash 2 of a train image (valid 14, test 11) | 25 |
| **Final images** | **2423** |

Largest drop-duplicate group: 16 images.

## Boxes dropped (before image-level dedup)

| Reason | Count |
|---|---|
| Class mapped to None (non-food / excluded) | 3516 |
| &nbsp;&nbsp;others | 2408 |
| &nbsp;&nbsp;soda_can | 1108 |
| Relabelled from 'others' -> apple (kept, before other box filters) | 4 |
| Relabelled from 'others' -> jar (kept, before other box filters) | 703 |
| Relabelled from 'others' -> mango (kept, before other box filters) | 277 |
| Relabelled from 'others' -> milk (kept, before other box filters) | 12 |
| Relabelled from 'others' -> orange (kept, before other box filters) | 557 |
| Relabelled from 'others' -> persimmon (kept, before other box filters) | 188 |
| Relabelled from 'others' -> pomegranate (kept, before other box filters) | 181 |
| Coordinates outside 0-1 | 50 |
| Near-zero area (side < 0.005 or area < 0.0001) | 1 |
| Duplicate box (same class, IoU > 0.9) | 3 |
| Malformed line | 0 |

Polygon labels converted to boxes: 0. Different-class box pairs overlapping at IoU > 0.9 (kept, suspicious): 0.

## Near-duplicate clusters (used for splitting)

Greedy complete-linkage: every pair inside a cluster is within phash distance <= 4 incl. h-flip, without requiring matching labels. Whole clusters are assigned to one split.

- Clusters: 2190 (175 with more than one image)
- Largest cluster: 7 images
- Clusters containing images from more than one dataset: 0
- Size histogram: 1: 2015, 2: 122, 3: 35, 4: 12, 5: 1, 6-10: 5, 11+: 0

## Same-scene exposure (single-linkage group, report only)

Single-linkage chaining (links at distance <= 4) gives 2038 groups; the largest has 287 images from {'aicook': 287}. Where those images ended up: train 179, valid 41, test 43, dropped as close to train 24.

## Leakage check

Valid/test images within phash distance 2 of a train image were dropped after the split (25 images; boxes lost: apple 2, banana 8, beef 8, blueberries 1, bread 1, butter 4, carrot 4, cheese 4, chicken 3, chocolate 1, corn 5, cream 2, egg 5, flour 6, goat_cheese 4, green_beans 5, ham 2, jar 1, lime 4, milk 4, mushrooms 2, onion 8, potato 6, shrimp 6, spinach 3, strawberries 8, sugar 5, sweet_potato 1, tomato 9).
Complete-linkage clusters cannot guarantee zero cross-split neighbours: chain links between clusters can cross splits.

- No cluster straddles train/valid/test: **PASS**
- Min phash distance (incl. h-flip) between valid/test and train images, recomputed from the written files: **4**
- Valid/test images with a train neighbour at distance <= 4: **64** of 803

## Final classes and instances per split

Images: train 1620, valid 398, test 405

| id | class | train | valid | test | total | clusters | size flag | split flag |
|---|---|---|---|---|---|---|---|---|
| 0 | apple | 506 | 111 | 117 | 734 | 413 |  |  |
| 1 | avocado | 342 | 71 | 71 | 484 | 166 |  |  |
| 2 | bacon | 157 | 30 | 31 | 218 | 166 |  |  |
| 3 | banana | 115 | 40 | 37 | 192 | 135 |  |  |
| 4 | beef | 160 | 50 | 48 | 258 | 159 |  |  |
| 5 | bell_pepper | 208 | 43 | 39 | 290 | 139 |  |  |
| 6 | blueberries | 115 | 37 | 40 | 192 | 140 |  |  |
| 7 | bread | 93 | 22 | 25 | 140 | 109 |  |  |
| 8 | butter | 267 | 62 | 66 | 395 | 286 |  |  |
| 9 | carrot | 144 | 29 | 36 | 209 | 130 |  |  |
| 10 | cheese | 350 | 89 | 93 | 532 | 363 |  |  |
| 11 | chicken | 210 | 57 | 70 | 337 | 204 |  |  |
| 12 | chocolate | 57 | 14 | 15 | 86 | 77 | WEAK | THIN-SPLIT |
| 13 | corn | 144 | 32 | 38 | 214 | 152 |  |  |
| 14 | cream | 114 | 33 | 36 | 183 | 131 |  |  |
| 15 | egg | 858 | 194 | 193 | 1245 | 595 |  |  |
| 16 | flour | 180 | 41 | 53 | 274 | 178 |  |  |
| 17 | goat_cheese | 71 | 10 | 12 | 93 | 55 | WEAK | THIN-SPLIT |
| 18 | green_beans | 135 | 37 | 50 | 222 | 161 |  |  |
| 19 | ham | 46 | 13 | 18 | 77 | 49 | WEAK | THIN-SPLIT |
| 20 | jar | 302 | 55 | 51 | 408 | 387 |  |  |
| 21 | lemon | 286 | 63 | 60 | 409 | 154 |  |  |
| 22 | lime | 114 | 25 | 35 | 174 | 102 |  |  |
| 23 | mango | 23 | 15 | 15 | 53 | 39 | WEAK |  |
| 24 | milk | 862 | 196 | 203 | 1261 | 691 |  |  |
| 25 | mushrooms | 127 | 41 | 41 | 209 | 154 |  |  |
| 26 | onion | 130 | 32 | 39 | 201 | 136 |  |  |
| 27 | orange | 234 | 22 | 26 | 282 | 268 |  |  |
| 28 | persimmon | 124 | 15 | 15 | 154 | 154 |  |  |
| 29 | pomegranate | 44 | 15 | 15 | 74 | 69 | WEAK |  |
| 30 | potato | 172 | 48 | 56 | 276 | 190 |  |  |
| 31 | shrimp | 135 | 35 | 40 | 210 | 158 |  |  |
| 32 | spinach | 126 | 32 | 31 | 189 | 134 |  |  |
| 33 | strawberries | 175 | 48 | 54 | 277 | 180 |  |  |
| 34 | sugar | 200 | 44 | 48 | 292 | 171 |  |  |
| 35 | sweet_potato | 126 | 29 | 34 | 189 | 122 |  |  |
| 36 | tomato | 405 | 100 | 101 | 606 | 343 |  |  |
| 37 | yogurt | 747 | 159 | 153 | 1059 | 474 |  |  |

## Flagged classes

WEAK: total < 100 boxes. VERY WEAK: total < 50. THIN-SPLIT: any split has < 15 boxes.

| class | flags | reason | unique clusters |
|---|---|---|---|
| chocolate | WEAK, THIN-SPLIT | 86 boxes total (<100); fewer than 15 boxes in valid (14) | 77 |
| goat_cheese | WEAK, THIN-SPLIT | 93 boxes total (<100); fewer than 15 boxes in valid (10), test (12) | 55 |
| ham | WEAK, THIN-SPLIT | 77 boxes total (<100); fewer than 15 boxes in valid (13) | 49 |
| mango | WEAK | 53 boxes total (<100) | 39 |
| pomegranate | WEAK | 74 boxes total (<100) | 69 |

Classes drawn from fewer than 30 clusters (many boxes from few clusters is weaker than it looks): none.

## Comparison with previous split (cleaning_report_v3_old.md)

| split | images old | images new | boxes old | boxes new |
|---|---|---|---|---|
| train | 1682 | 1620 | 9341 | 8604 |
| valid | 383 | 398 | 1855 | 1989 |
| test | 383 | 405 | 1795 | 2105 |

Per-class valid/test counts that changed by more than 5 boxes:

| class | valid old -> new | test old -> new |
|---|---|---|
| apple | 111 -> 111 | 106 -> 117 |
| banana | 29 -> 40 | 19 -> 37 |
| beef | 45 -> 50 | 41 -> 48 |
| blueberries | 31 -> 37 | 27 -> 40 |
| butter | 59 -> 62 | 55 -> 66 |
| carrot | 21 -> 29 | 24 -> 36 |
| cheese | 82 -> 89 | 77 -> 93 |
| chicken | 50 -> 57 | 45 -> 70 |
| corn | 28 -> 32 | 32 -> 38 |
| cream | 28 -> 33 | 25 -> 36 |
| egg | 188 -> 194 | 188 -> 193 |
| flour | 40 -> 41 | 36 -> 53 |
| goat_cheese | 2 -> 10 | 2 -> 12 |
| green_beans | 34 -> 37 | 31 -> 50 |
| ham | 7 -> 13 | 5 -> 18 |
| lime | 20 -> 25 | 20 -> 35 |
| milk | 191 -> 196 | 190 -> 203 |
| mushrooms | 37 -> 41 | 34 -> 41 |
| onion | 29 -> 32 | 25 -> 39 |
| potato | 44 -> 48 | 44 -> 56 |
| shrimp | 38 -> 35 | 31 -> 40 |
| strawberries | 35 -> 48 | 34 -> 54 |
| sugar | 36 -> 44 | 32 -> 48 |
| sweet_potato | 25 -> 29 | 24 -> 34 |
| tomato | 97 -> 100 | 90 -> 101 |
| yogurt | 153 -> 159 | 157 -> 153 |
