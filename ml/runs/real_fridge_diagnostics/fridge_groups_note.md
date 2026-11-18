# Proposed pseudo-fridge groups (not confirmed)

Produced by `ml/propose_fridge_groups.py` for the 160 held-out photos. **Ashton should confirm these groups.** They come from visual similarity only (colour histograms plus phash), because fridge IDs were not supplied, and they are **not used for any split yet**. Output: `data/real_fridge/fridge_groups_proposed.csv`.

## Cut sensitivity (average linkage on the combined distance)

| Cut | Groups | Singletons | Largest group | Groups with 5+ photos |
|---|---|---|---|---|
| 0.65 | 85 | 40 | 5 | 2 |
| 0.7 | 55 | 12 | 10 | 8 |
| 0.72 | 43 | 7 | 13 | 13 |
| 0.74 | 30 | 5 | 41 | 9 |
| 0.76 | 23 | 5 | 61 | 9 |
| 0.8 | 8 | 2 | 148 | 1 |

Proposed groups use the 0.72 cut (43 groups: sizes [13, 10, 8, 8, 7, 7, 7, 6, 6, 6, 6, 5, 5, 4, 4, 4, 3, 3, 3, 3, 3, 3, 3, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 1, 1, 1, 1, 1, 1, 1]); `coarse_group` uses the 0.76 cut (23 groups). Above about 0.74 one giant cluster forms, so the cut cannot be raised much.

## Sanity check against EXIF hints (not used for clustering)

Photos with a camera model: 102 of 160; with a capture day: 105 of 160.

| Hint | Pairs inside a proposed group that agree | All pairs that agree | Same measure with shuffled group labels |
|---|---|---|---|
| camera model | 16% (178 pairs) | 12% (5151 pairs) | 18% |
| capture day | 57% (194 pairs) | 60% (5460 pairs) | 57% |

**Result:** pairs inside a proposed group agree on camera model and capture day no more often than pairs with shuffled labels (camera 16% vs 18%, day 57% vs 57%), so this check gives **no support** that the groups follow fridges. The check is also weak by nature: one person with one phone can photograph several fridges on one day, so agreement is not proof either way. The groups can over-split one fridge (shelves look different) and can merge two fridges with similar white interiors. Treat them only as a starting point for Ashton to correct; they are not fridge IDs and must not be used for a split until she confirms.

