# Egg label audit

Produced by `ml/audit_egg.py`. External = egg boxes in the `ext3_` files of `data/cleaned_v3` train; v2 = all egg boxes in `data/cleaned_v2` train (which includes the 150 earlier `ext_` images). Heuristics are described in the script docstring. The two contact sheets (`egg_audit_ext.png`, `egg_audit_v2.png`) show 30 seeded random egg boxes each, in context: red = the audited box, orange = other egg boxes, blue = other classes. The sheets contain photo crops and are not committed.

## Heuristic flags over every egg box

| Flag | External | v2 train |
|---|---|---|
| egg boxes | 100 | 896 |
| very_large | 0 (0.0%) | 102 (11.4%) |
| tiny | 0 (0.0%) | 1 (0.1%) |
| odd_aspect | 0 (0.0%) | 13 (1.5%) |
| duplicate | 0 (0.0%) | 0 (0.0%) |
| overlaps_other_class | 0 (0.0%) | 13 (1.5%) |
| any_flag | 0 (0.0%) | 117 (13.1%) |
| median box area | 6.70% of the image | 1.63% |

## The 30 sampled boxes per source

Heuristic flags among the 30 sampled boxes: external 0 of 30, v2 5 of 30.

**Looked wrong by eye (box does not fit one egg or one tight group, wrong object, or box around other items):** external 2 of 30, v2 6 of 30.

Notes: These sheets show the capped set (100 external egg boxes) and a new random v2 sample. External: tile 26 is an unclear blurred streak and tile 28 a closed white carton; about 25 of the 30 tiles are the same blue egg tray with large white eggs. v2: tiles 6, 8, 10 and 24 box whole egg cartons or packages, tile 21 boxes a package plus other items, tile 9 is an unclear blur. Counts are from 256 px crops, so treat them as rough.

## Decision for the external egg cap

The cap was lowered to 100 on the first audit, run before the rebuild on the original 300 external egg boxes: 1.7% of them were flagged by the heuristics versus 13.1% in v2, but by eye 4 of 30 external boxes (egg cartons or trays boxed as egg, one unclear blur) and 4 of 30 v2 boxes looked wrong, over the bar of at most 3, so they did not count as clearly clean. This report was regenerated after the rebuild, so its rates and sheets describe the capped 100-box set and a new random sample. By the rule alone the capped set would now count as clean, but the cap stays at 100 because the original audit was not clearly clean and the capped set is dominated by one scene (a blue egg tray with large white eggs). Separately, Ashton's labels box whole cartons (see below), so the carton-sized boxes counted as wrong here may match the convention the app needs.

## How Ashton boxes eggs (held-out photos, `data/real_fridge`)

92 egg boxes in her 160 labels; median box area 0.79% of the image (my v2 train 1.63%, external 6.70%); 0 boxes cover more than 25% of the image; 68 photos contain at least one egg box (median 1 egg boxes per photo). Sheet of 15 seeded random boxes: `egg_audit_ashton.png` (photo crops, not committed).

**Looked at by eye (15 boxes): whole carton or tray 14, individual eggs or a small group of visible eggs 0, unclear 1.**

Ashton boxes the whole carton or tray (grey pulp, yellow foam, clear plastic and teal trays), including clear cartons with visible eggs; tile 4 is a single egg-like shape inside clear packaging and counts as unclear. This is the opposite of the per-egg convention in the external and most v2 labels. The app needs one egg convention (individual eggs or cartons) before any real-photo fine-tune.

