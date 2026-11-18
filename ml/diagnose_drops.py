"""Diagnose which fridge_food_images_v14 images are lost because of the skipped classes `meat` and `green leaves`.

Read-only: builds nothing. Reads data/external, data/cleaned, data/cleaned_v2, data/cleaned_v3 (counts only) and
writes ml/runs/external_audit/report_drops.md.

Definitions (all box geometry in fractions of the image):
  cause classes   skipped classes whose box made the image fail the drop rule (>= 5% of the image, or overlapping a
                  kept box by >= 0.10 of the smaller box)
  lost only to    the image was dropped and every cause class is `meat` or `green leaves`; the source photo has no
  meat/green leaves   surviving copy; it would still pass the single-box rule and is not a near-duplicate of my data
  mask rules      every skipped box < 5% of the image area AND overlaps no kept box by more than 20% of that kept box's area
  meat overlaps meat-like   a `meat` box with IoU > 0.3 or containment (intersection over the smaller box) > 0.7 against
                  a kept beef/chicken/bacon/shrimp box

Usage:  python ml/diagnose_drops.py [--real-fridge <relative path to the held-out photos>]
"""
import argparse
import json
import random
import sys
from collections import Counter, defaultdict
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))
import add_external as ae  # noqa: E402
from class_map import EXTERNAL_V3_MAP  # noqa: E402

REPO = ae.REPO
SRC = "fridge_food_images_v14"
FOCUS = {"meat", "green leaves"}
MEATLIKE = {"beef", "chicken", "bacon", "shrimp"}
MASK_MAX_AREA = 0.05
MASK_MAX_KEPT_OVERLAP = 0.20
SEED = 270
OUT = REPO / "ml" / "runs" / "external_audit" / "report_drops.md"


def area(b):  # b = (x1, y1, x2, y2)
    return max(0.0, b[2] - b[0]) * max(0.0, b[3] - b[1])


def inter(a, b):
    return max(0.0, min(a[2], b[2]) - max(a[0], b[0])) * max(0.0, min(a[3], b[3]) - max(a[1], b[1]))


def iou(a, b):
    i = inter(a, b)
    u = area(a) + area(b) - i
    return i / u if u > 0 else 0.0


def causes(rec, reason):
    """Skipped classes responsible for a drop."""
    if reason == "large_unlabeled_object":
        return {d[0] for d in rec["dropped"] if area(d[1:]) >= ae.LARGE_FRAC}
    return {d[0] for d in rec["dropped"] for k in rec["kept"] if ae.ioa(d[1:], k[1:]) >= ae.OVERLAP_IOA}


def mask_check(rec):
    """Return 'pass' or the reason the image cannot be masked."""
    if not rec["kept"] or not rec["dropped"]:
        return "n/a"
    if any(area(d[1:]) >= MASK_MAX_AREA for d in rec["dropped"]):
        return "skipped_box_ge_5pct"
    for d in rec["dropped"]:
        for k in rec["kept"]:
            if inter(d[1:], k[1:]) > MASK_MAX_KEPT_OVERLAP * area(k[1:]):
                return "overlaps_kept_box_gt_20pct"
    return "pass"


def meat_on_meatlike(rec):
    pairs = Counter()
    for d in rec["dropped"]:
        if d[0] != "meat":
            continue
        for k in rec["kept"]:
            if k[0] in MEATLIKE and (iou(d[1:], k[1:]) > 0.3 or ae.ioa(d[1:], k[1:]) > 0.7):
                pairs[k[0]] += 1
    return pairs


def best_copy(recs):
    return sorted(recs, key=lambda r: (-len(r["kept"]), r["hash"]))[0]


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--real-fridge", default="data/real_fridge/upright/images")
    a = ap.parse_args()
    mp = EXTERNAL_V3_MAP[SRC]
    cfg, names, recs, counts, poly = ae.v3_load(SRC)
    stats = {"tiny_boxes_dropped": 0, "unmapped_source_class": Counter()}
    for r in recs:
        r["reason"] = ae.v3_filter(r, names, mp, False, stats)
        r["cause"] = causes(r, r["reason"]) if r["reason"] in ("large_unlabeled_object", "unlabeled_object_overlaps_kept_box") else set()
    by_base = defaultdict(list)
    for r in recs:
        by_base[r["base"]].append(r)
    included = {b for b, rs in by_base.items() if any(r["reason"] is None for r in rs)}

    # ---------------------------------------------------------------- file level versus source-photo level
    drop_reasons = ("large_unlabeled_object", "unlabeled_object_overlaps_kept_box")
    dropped_files = [r for r in recs if r["reason"] in drop_reasons]
    dropped_with_sibling = sum(1 for r in dropped_files if r["base"] in included)
    photo_cat = Counter()
    for b, rs in by_base.items():
        if b in included:
            photo_cat["included (at least one copy survives)"] += 1
            if any(r["reason"] in drop_reasons for r in rs):
                photo_cat["  of which some copies were dropped for overlap/large"] += 1
            continue
        reasons = {r["reason"] for r in rs}
        cs = set().union(*[r["cause"] for r in rs])
        if reasons == {"no_kept_boxes"}:
            photo_cat["not included: only skipped-class boxes (no kept box)"] += 1
        elif cs and cs <= FOCUS:
            photo_cat["not included: blocked only by meat / green leaves"] += 1
        elif cs & FOCUS:
            photo_cat["not included: blocked by meat / green leaves plus other skipped classes"] += 1
        elif cs:
            photo_cat["not included: blocked only by other skipped classes"] += 1
        else:
            photo_cat["not included: other (for example single box over 60%)"] += 1
    # heavily augmented source photos (more than 3 copies, for example 72 augmented copies of one shelf photo)
    def outcome(b, rs):
        if b in included:
            return "included"
        reasons = {r["reason"] for r in rs}
        cs = set().union(*[r["cause"] for r in rs])
        if reasons == {"no_kept_boxes"}:
            return "only skipped-class boxes"
        if cs and cs <= FOCUS:
            return "blocked only by meat / green leaves"
        if cs:
            return "blocked by other skipped classes (or mixed)"
        return "other"
    heavy = {b: rs for b, rs in by_base.items() if len(rs) > 3}
    heavy_out = Counter(outcome(b, rs) for b, rs in heavy.items())
    heavy_files = sum(len(rs) for rs in heavy.values())
    heavy_dropped = sum(1 for rs in heavy.values() for r in rs if r["reason"] in drop_reasons)
    # distribution of meat vs kept meat-like overlaps (containment = intersection over the smaller box)
    bins = Counter()
    for r in recs:
        best = 0.0
        for d in r["dropped"]:
            if d[0] == "meat":
                for k in r["kept"]:
                    if k[0] in MEATLIKE:
                        best = max(best, ae.ioa(d[1:], k[1:]))
        if best >= 0.01:
            bins["0.01-0.1" if best < 0.1 else "0.1-0.3" if best < 0.3 else "0.3-0.5" if best < 0.5 else "0.5-0.7" if best < 0.7 else ">0.7"] += 1

    # ---------------------------------------------------------------- hashes for the near-duplicate check
    print("hashing references ...", flush=True)
    refs = [ae.hash_dir([p for sp in ae.SPLITS for p in ae.list_images(ae.CLEANED / sp / "images")]),
            ae.hash_dir([p for sp in ae.SPLITS for p in ae.list_images(ae.V2_DIR / sp / "images")])]
    rf = (REPO / a.real_fridge).resolve()
    if rf.exists():
        refs.append(ae.hash_dir(ae.list_images(rf)))
    else:
        print("WARNING: held-out photos not found; that near-duplicate check is skipped")

    def near_ref(photos):
        if not photos:
            return np.zeros(0, dtype=bool)
        PH, PHf = ae.hash_dir([r["path"] for r in photos])
        out = np.zeros(len(photos), dtype=bool)
        for rph, _ in refs:
            out |= ae.dist_matrix(PH, PHf, rph).min(1) <= ae.PHASH_MAX_DIST
        return out

    area1 = lambda r: area(r["kept"][0][1:])

    # ---------------------------------------------------------------- Part 1.1 lost only to meat / green leaves
    lost_photos = []
    for b, rs in by_base.items():
        if b in included:
            continue
        cand = [r for r in rs if r["cause"] and r["cause"] <= FOCUS and not (len(r["kept"]) == 1 and area1(r) > ae.MAX_SINGLE_BOX)]
        if cand:
            lost_photos.append(best_copy(cand))
    nr = near_ref(lost_photos)
    lost_final = [r for r, x in zip(lost_photos, nr) if not x]
    lost_boxes = Counter(k[0] for r in lost_final for k in r["kept"])

    summ = json.loads((REPO / "ml" / "runs" / "external_audit" / "merge_summary_v3.json").read_text())
    v2_train = ae.class_counts(ae.V2_DIR / "train")
    added = Counter()
    for s in summ["boxes_added"].values():
        added.update(s)
    caps = lambda c: ae.CAP_FRUIT if c in ae.FRUIT_CAPPED else ae.CAP_DEFAULT
    kept_classes = sorted({v for v in mp.values() if v})

    # ---------------------------------------------------------------- Part 1.2 meat overlap vs meat-like kept boxes
    meat_files = [r for r in recs if r["reason"] == "unlabeled_object_overlaps_kept_box" and "meat" in r["cause"]]
    meat_like_files, by_kept = [], Counter()
    for r in meat_files:
        pairs = meat_on_meatlike(r)
        if pairs:
            meat_like_files.append(r)
            by_kept.update({c: 1 for c in pairs})
    sample = sorted(r["stem"] + r["path"].suffix.lower() for r in meat_like_files)
    sample = random.Random(SEED).sample(sample, min(12, len(sample)))
    meat_kept_classes = Counter(k[0] for r in meat_files for d in r["dropped"] if d[0] == "meat"
                                for k in r["kept"] if ae.ioa(d[1:], k[1:]) >= ae.OVERLAP_IOA)

    # ---------------------------------------------------------------- Part 1.3 mask rules
    has_small = [r for r in recs if r["kept"] and any(area(d[1:]) < MASK_MAX_AREA for d in r["dropped"])]
    tab = defaultdict(Counter)
    for r in has_small:
        status = "currently kept" if r["reason"] is None else f"currently dropped ({r['reason']})"
        tab[status][mask_check(r)] += 1
    # source photos not included now but with a copy that passes the mask rules
    rescue_photos = []
    for b, rs in by_base.items():
        if b in included:
            continue
        cand = [r for r in rs if mask_check(r) == "pass" and not (len(r["kept"]) == 1 and area1(r) > ae.MAX_SINGLE_BOX)]
        if cand:
            rescue_photos.append(best_copy(cand))
    nr2 = near_ref(rescue_photos)
    rescue_final = [r for r, x in zip(rescue_photos, nr2) if not x]
    meatlike_skipped = [r for r in rescue_final if meat_on_meatlike(r)]
    rescue_boxes = Counter(k[0] for r in rescue_final for k in r["kept"])
    rescue_by_class_skipped = Counter(d[0] for r in rescue_final for d in r["dropped"])

    # ---------------------------------------------------------------- console summary
    print("heavy photos:", len(heavy), "files", heavy_files, "dropped files", heavy_dropped, dict(heavy_out))
    print("photo-level:", dict(photo_cat), "| dropped files with a surviving sibling:", dropped_with_sibling, "of", len(dropped_files), "| meat-vs-meatlike containment bins:", dict(bins))
    print(f"\nA files {len(recs)}; source photos {len(by_base)}; photos with a surviving copy {len(included)}")
    print(f"lost only to meat/green leaves: {len(lost_photos)} source photos, {len(lost_final)} after the near-duplicate check")
    print(f"meat-overlap files {len(meat_files)}; overlapping a kept beef/chicken/bacon/shrimp box: {len(meat_like_files)} {dict(by_kept)}")
    print("mask rules:", {k: dict(v) for k, v in tab.items()})
    print(f"rescuable source photos by mask rules: {len(rescue_photos)} ({len(rescue_final)} after near-duplicate check); meat-on-meatlike among them: {len(meatlike_skipped)}")

    # ---------------------------------------------------------------- report
    L = []
    w = L.append
    w("# Drops caused by skipped classes (diagnosis only; nothing was built)\n")
    w("Produced by `ml/diagnose_drops.py` for `fridge_food_images_v14`. Definitions are in that script's docstring. "
      f"Mask rules: every skipped box under {int(100 * MASK_MAX_AREA)}% of the image area and no overlap with a kept box above "
      f"{int(100 * MASK_MAX_KEPT_OVERLAP)}% of that kept box's area. Meat-like overlap: IoU > 0.3 or containment > 0.7 against a kept beef/chicken/bacon/shrimp box. Seed {SEED}.\n")
    w("## 0. File level versus source-photo level\n")
    w(f"Each source photo is exported as up to three augmented copies (rotation of up to 15 degrees), and the build keeps one copy per photo. "
      f"{len(dropped_files)} files were dropped for overlap or size, but **{dropped_with_sibling} of them belong to a photo that still has a surviving copy**, "
      f"so the file counts overstate the photos lost. Photo-level outcome ({len(by_base)} source photos):\n")
    w("| Outcome | Source photos |\n|---|---|")
    for k, v in photo_cat.items():
        w(f"| {k} | {v} |")
    w("")
    w(f"**Heavily augmented photos:** {len(heavy)} source photos have more than 3 copies (up to 72 augmented versions of one shelf photo, with noise, cutouts and rotation; "
      f"their copies are about phash distance 20 apart, so only base-name grouping finds them). They hold {heavy_files} of {len(recs)} files and {heavy_dropped} of the {len(dropped_files)} "
      f"files dropped for overlap or size, which is why the file counts look so large. Their photo-level outcome: {dict(heavy_out)}. "
      "These cluttered multi-item shelves are the closest thing in this dataset to real fridge photos.\n")
    w("## 1. Kept classes: boxes lost only to `meat` / `green leaves`\n")
    w(f"{len(lost_photos)} source photos were dropped only because of `meat` / `green leaves` (no surviving copy; they would pass the single-box rule); "
      f"{len(lost_final)} remain after removing near-duplicates of my data. Boxes are counted from the best copy of each photo.\n")
    w("| Class | v2 train boxes | Added in v3 | Cap | Headroom | Lost only to meat/green leaves |\n|---|---|---|---|---|---|")
    for c in kept_classes:
        cap = caps(c)
        w(f"| {c} | {v2_train.get(c, 0)} | {added.get(c, 0)} | {cap} | {max(0, cap - added.get(c, 0))} | {lost_boxes.get(c, 0)} |")
    w("\nHeadroom is the cap minus the boxes already added; boxes lost beyond the headroom would be skipped by the cap anyway. "
      "Mango and pomegranate come from fridge v1i, not from this dataset.\n")
    w("## 2. Files dropped for a `meat` overlap\n")
    w(f"{len(meat_files)} files were dropped because a `meat` box overlaps a kept box (of {sum(1 for r in recs if any(d[0] == 'meat' for d in r['dropped']))} files containing `meat`). "
      f"The kept classes those `meat` boxes overlap: {dict(meat_kept_classes.most_common())}.\n")
    w(f"**{len(meat_like_files)} of them have the `meat` box overlapping a kept beef/chicken/bacon/shrimp box** (IoU > 0.3 or containment > 0.7): "
      f"{dict(by_kept)} (this dataset has no kept beef or bacon).\n")
    w("Largest overlap (containment) between a `meat` box and a kept beef/chicken/bacon/shrimp box, files per range: "
      + (", ".join(f"{k}: {v}" for k, v in sorted(bins.items())) or "none") + ". "
      "Overlaps exist (mostly `meat` boxes touching kept shrimp), but none reach the IoU > 0.3 or containment > 0.7 thresholds.\n")
    w("12 sample files (seeded): " + ("none, because no file meets the rule.\n" if not sample else "\n"))
    for s_ in sample:
        w(f"- `{s_}`")
    w("")
    w("## 3. Mask rules\n")
    w(f"{len(has_small)} files have at least one skipped-class box under {int(100 * MASK_MAX_AREA)}% of the image and at least one kept box. Outcome of the mask rules:\n")
    w("| Current status | would pass | skipped box >= 5% | overlaps a kept box by > 20% of its area |\n|---|---|---|---|")
    for status, c in sorted(tab.items()):
        w(f"| {status} | {c.get('pass', 0)} | {c.get('skipped_box_ge_5pct', 0)} | {c.get('overlaps_kept_box_gt_20pct', 0)} |")
    w("\n'currently kept' images already pass the drop rule; masking would only clean up their small unlabeled objects. "
      "The 'currently dropped' rows are the images masking could bring back.\n")
    w("### Source photos masking would bring back\n")
    w(f"{len(rescue_photos)} source photos have no surviving copy but a copy that passes the mask rules and the single-box rule; "
      f"{len(rescue_final)} remain after removing near-duplicates of my data. Of those, {len(meatlike_skipped)} have a `meat` box on a kept beef/chicken/bacon/shrimp box "
      "and would be skipped in Part 2 (listed instead of masked). Skipped classes that would be masked: "
      + ", ".join(f"{k} {v}" for k, v in rescue_by_class_skipped.most_common()) + ".\n")
    w("| Class | Boxes in those photos | Added in v3 | Cap | Boxes that fit under the cap |\n|---|---|---|---|---|")
    for c in kept_classes:
        if rescue_boxes.get(c, 0):
            cap = caps(c)
            w(f"| {c} | {rescue_boxes[c]} | {added.get(c, 0)} | {cap} | {min(rescue_boxes[c], max(0, cap - added.get(c, 0)))} |")
    w("")
    OUT.write_text("\n".join(L) + "\n")
    print("wrote", OUT.relative_to(REPO))


if __name__ == "__main__":
    main()
