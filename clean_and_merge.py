"""Clean and merge the raw Roboflow datasets into ./data/cleaned/ (re-runnable, seed 0)."""
import hashlib
import random
import re
import shutil
from collections import Counter, defaultdict
from pathlib import Path

import imagehash
import numpy as np
import yaml
from PIL import Image

import json

from class_map import (CLASS_MAP, EXTRA_CLASSES, FINAL_CLASSES, OTHERS_BOXMAP_FILE,
                       OTHERS_CLASS, OTHERS_DATASET)

SEED = 0
ROOT = Path(__file__).resolve().parent
RAW = ROOT / "data" / "raw"
OUT = ROOT / "data" / "cleaned"
SRC_SPLITS = ["train", "valid", "test"]
IMG_EXT = {".jpg", ".jpeg", ".png", ".bmp", ".webp"}
COORD_TOL = 1e-3        # tolerated overshoot outside [0,1] before a box is dropped (clipped otherwise)
MIN_SIDE = 0.005        # box narrower/shorter than this (fraction of image) is "near-zero"
MIN_AREA = 1e-4
DUP_BOX_IOU = 0.9       # same-class boxes above this IoU are the same object
PHASH_MAX_DIST = 4      # Hamming distance (of 64 bits) counted as a near-duplicate image
SPLIT_FRAC = (0.70, 0.15, 0.15)
OUT_SPLITS = ["train", "valid", "test"]
LEAK_DROP_DIST = 2      # valid/test images this close (incl. h-flip) to a train image are dropped
MIN_EVAL_BOXES = 15     # per-class floor aimed for in valid and test

CID = {c: i for i, c in enumerate(FINAL_CLASSES)}


def slug(folder):
    return re.sub(r"[^A-Za-z0-9]+", "_", folder.split(".v")[0]).strip("_").lower()


def iou(a, b):
    ax1, ay1, ax2, ay2 = a[0] - a[2] / 2, a[1] - a[3] / 2, a[0] + a[2] / 2, a[1] + a[3] / 2
    bx1, by1, bx2, by2 = b[0] - b[2] / 2, b[1] - b[3] / 2, b[0] + b[2] / 2, b[1] + b[3] / 2
    iw, ih = min(ax2, bx2) - max(ax1, bx1), min(ay2, by2) - max(ay1, by1)
    if iw <= 0 or ih <= 0:
        return 0.0
    inter = iw * ih
    return inter / (a[2] * a[3] + b[2] * b[3] - inter)


def parse_label(path, names, mapping, stats, override=None, split=None):
    """Return list of (cid, cx, cy, w, h) after remap and box-level cleaning."""
    boxes = []
    if not path.exists():
        return boxes
    for li, line in enumerate(path.read_text().splitlines()):
        p = line.split()
        if not p:
            continue
        try:
            src = names[int(float(p[0]))]
            vals = [float(x) for x in p[1:]]
        except (ValueError, IndexError):
            stats["boxes_malformed"] += 1
            continue
        if len(vals) == 4:
            cx, cy, w, h = vals
        elif len(vals) >= 6 and len(vals) % 2 == 0:  # polygon -> bounding box
            xs, ys = vals[0::2], vals[1::2]
            if min(xs + ys) < -COORD_TOL or max(xs + ys) > 1 + COORD_TOL:
                stats["boxes_out_of_range"] += 1
                continue
            x1, x2, y1, y2 = min(xs), max(xs), min(ys), max(ys)
            cx, cy, w, h = (x1 + x2) / 2, (y1 + y2) / 2, x2 - x1, y2 - y1
            stats["polygons_converted"] += 1
        else:
            stats["boxes_malformed"] += 1
            continue
        dst = mapping[src]
        if override is not None and src == OTHERS_CLASS:
            dst = override.get(f"{split}/{path.stem}/{li}")
            if dst:
                stats[f"boxes_relabelled:{dst}"] += 1
        if dst is None:
            stats["boxes_dropped_class"] += 1
            stats[f"boxes_dropped_class:{src}"] += 1
            continue
        x1, y1, x2, y2 = cx - w / 2, cy - h / 2, cx + w / 2, cy + h / 2
        if min(x1, y1) < -COORD_TOL or max(x2, y2) > 1 + COORD_TOL or w <= 0 or h <= 0:
            stats["boxes_out_of_range"] += 1
            continue
        x1, y1, x2, y2 = max(x1, 0), max(y1, 0), min(x2, 1), min(y2, 1)
        w, h = x2 - x1, y2 - y1
        if w < MIN_SIDE or h < MIN_SIDE or w * h < MIN_AREA:
            stats["boxes_near_zero_area"] += 1
            continue
        boxes.append((CID[dst], (x1 + x2) / 2, (y1 + y2) / 2, w, h))
    # duplicate boxes: same class, near-identical extent
    kept = []
    for b in boxes:
        if any(k[0] == b[0] and iou(k[1:], b[1:]) > DUP_BOX_IOU for k in kept):
            stats["boxes_duplicate"] += 1
        else:
            kept.append(b)
    for i, a in enumerate(kept):  # diagnostics only: different class on the same object
        for b in kept[i + 1:]:
            if a[0] != b[0] and iou(a[1:], b[1:]) > DUP_BOX_IOU:
                stats["conflicting_class_overlaps"] += 1
    return kept


def main():
    random.seed(SEED)
    assert OUT.resolve().parent == (ROOT / "data").resolve()

    # --- reset outputs (only what this script writes) ---
    for sp in OUT_SPLITS:
        shutil.rmtree(OUT / sp, ignore_errors=True)
    for f in ("data.yaml", "cleaning_report.md"):
        (OUT / f).unlink(missing_ok=True)
    OUT.mkdir(parents=True, exist_ok=True)

    stats = Counter()
    records = []  # dict per surviving image
    for ds in sorted(p for p in RAW.iterdir() if p.is_dir()):
        if ds.name not in CLASS_MAP:
            raise SystemExit(f"{ds.name} missing from class_map.CLASS_MAP")
        names = yaml.safe_load((ds / "data.yaml").read_text())["names"]
        if isinstance(names, dict):
            names = [names[k] for k in sorted(names)]
        mapping = CLASS_MAP[ds.name]
        missing = [n for n in names if n not in mapping]
        if missing:
            raise SystemExit(f"{ds.name}: unmapped classes {missing}")
        prefix = slug(ds.name)
        override = json.loads((ROOT / OTHERS_BOXMAP_FILE).read_text()) if ds.name == OTHERS_DATASET else None
        for sp in SRC_SPLITS:
            idir, ldir = ds / sp / "images", ds / sp / "labels"
            if not idir.exists():
                continue
            for img in sorted(idir.iterdir()):
                if img.suffix.lower() not in IMG_EXT:
                    continue
                stats["images_raw"] += 1
                try:
                    with Image.open(img) as im:
                        im.verify()
                    with Image.open(img) as im:
                        im = im.convert("RGB")
                        ph = imagehash.phash(im)
                        phf = imagehash.phash(im.transpose(Image.FLIP_LEFT_RIGHT))
                except Exception:
                    stats["images_corrupt"] += 1
                    continue
                boxes = parse_label(ldir / (img.stem + ".txt"), names, mapping, stats, override, sp)
                if not boxes:
                    stats["images_empty_after_remap"] += 1
                    continue
                new_stem = re.sub(r"[^A-Za-z0-9_-]+", "_", f"{prefix}__{img.stem}")
                records.append(dict(
                    ds=prefix, src=img, name=new_stem + img.suffix.lower(), stem=new_stem,
                    boxes=boxes, md5=hashlib.md5(img.read_bytes()).hexdigest(),
                    ph=np.array(ph.hash, dtype=bool).ravel(),
                    phf=np.array(phf.hash, dtype=bool).ravel()))

    # --- dedup (exact + perceptual incl. horizontal flip) across the whole pool ---
    n = len(records)
    parent = list(range(n))

    def find(x):
        while parent[x] != x:
            parent[x] = parent[parent[x]]
            x = parent[x]
        return x

    H = np.stack([r["ph"] for r in records])
    Hf = np.stack([r["phf"] for r in records])
    md5s = [r["md5"] for r in records]
    sigs = [tuple(sorted(b[0] for b in r["boxes"])) for r in records]
    pair_kind = {}
    for i in range(n):
        d = np.minimum((H[i + 1:] != H[i]).sum(1), (Hf[i + 1:] != H[i]).sum(1))
        for off in np.nonzero(d <= PHASH_MAX_DIST)[0]:
            j = i + 1 + off
            if md5s[i] != md5s[j] and sigs[i] != sigs[j]:
                continue  # same backdrop, different contents: not a duplicate
            pair_kind[(i, j)] = "exact" if md5s[i] == md5s[j] else "near"
            parent[find(j)] = find(i)
    clusters = defaultdict(list)
    for i in range(n):
        clusters[find(i)].append(i)
    drop = set()
    dup_cross = dup_within = 0
    for members in clusters.values():
        if len(members) == 1:
            continue
        keep = max(members, key=lambda i: (len(records[i]["boxes"]), records[i]["name"]))
        for i in members:
            if i == keep:
                continue
            drop.add(i)
            kinds = [pair_kind.get((min(i, keep), max(i, keep)))]
            stats["images_dup_exact" if md5s[i] == md5s[keep] else "images_dup_near"] += 1
            if records[i]["ds"] == records[keep]["ds"]:
                dup_within += 1
            else:
                dup_cross += 1
    stats["dup_within_dataset"], stats["dup_across_datasets"] = dup_within, dup_cross
    stats["dup_cluster_max_size"] = max(len(m) for m in clusters.values())
    pool = [r for i, r in enumerate(records) if i not in drop]
    stats["pool_boxes"] = sum(len(r["boxes"]) for r in pool)
    pool.sort(key=lambda r: r["name"])

    # --- clusters for splitting: complete-linkage, every pair phash <= PHASH_MAX_DIST incl. h-flip ---
    clusters_of, cl_stats = build_clusters(pool)
    stats.update(cl_stats)
    scene_groups, sg_stats = build_scene_groups(pool)  # single-linkage, report only
    stats.update(sg_stats)

    # --- cluster-aware stratified split ---
    split_of = stratified_split(pool, clusters_of, random.Random(SEED))
    bounds = {sp: [] for sp in OUT_SPLITS}
    for ci, members in enumerate(clusters_of):
        bounds[OUT_SPLITS[split_of[ci]]].extend(pool[i] for i in members)
    for sp in OUT_SPLITS:
        bounds[sp].sort(key=lambda r: r["name"])

    # drop valid/test images with a very close train neighbour (same scene across clusters)
    PHt = np.stack([r["ph"] for r in bounds["train"]])
    PHtf = np.stack([r["phf"] for r in bounds["train"]])
    leak_dropped = Counter()
    for sp in ("valid", "test"):
        keep = []
        for r in bounds[sp]:
            d = min(int((PHt != r["ph"]).sum(1).min()), int((PHtf != r["ph"]).sum(1).min()))
            if d <= LEAK_DROP_DIST:
                stats["leak_dropped"] += 1
                stats[f"leak_dropped:{sp}"] += 1
                for b in r["boxes"]:
                    leak_dropped[(sp, FINAL_CLASSES[b[0]])] += 1
            else:
                keep.append(r)
        bounds[sp] = keep

    inst = {sp: Counter() for sp in OUT_SPLITS}
    imgs = {}
    for sp, rs in bounds.items():
        (OUT / sp / "images").mkdir(parents=True)
        (OUT / sp / "labels").mkdir(parents=True)
        imgs[sp] = len(rs)
        for r in rs:
            shutil.copy2(r["src"], OUT / sp / "images" / r["name"])
            lines = []
            for c, cx, cy, w, h in r["boxes"]:
                lines.append(f"{c} {cx:.6f} {cy:.6f} {w:.6f} {h:.6f}")
                inst[sp][FINAL_CLASSES[c]] += 1
            (OUT / sp / "labels" / (r["stem"] + ".txt")).write_text("\n".join(lines) + "\n")

    (OUT / "data.yaml").write_text(yaml.safe_dump({
        "path": str(OUT),
        "train": str(OUT / "train" / "images"),
        "val": str(OUT / "valid" / "images"),
        "test": str(OUT / "test" / "images"),
        "nc": len(FINAL_CLASSES),
        "names": FINAL_CLASSES,
    }, sort_keys=False))

    leak = check_leakage(pool, clusters_of, split_of)
    img_split = {r["name"]: sp for sp in OUT_SPLITS for r in bounds[sp]}
    big = max(scene_groups, key=len)
    leak["scene_split"] = Counter(img_split.get(pool[i]["name"], "dropped") for i in big)
    leak["scene_ds"] = Counter(pool[i]["ds"] for i in big)
    cls_clusters = defaultdict(set)
    for ci, members in enumerate(clusters_of):
        for i in members:
            for b in pool[i]["boxes"]:
                cls_clusters[FINAL_CLASSES[b[0]]].add(ci)

    leak["dropped_boxes"] = leak_dropped
    write_report(stats, imgs, inst, sum(imgs.values()), cls_clusters, leak)
    print(f"Done. {sum(imgs.values())} images -> {OUT}  (train/val/test = {imgs['train']}/{imgs['valid']}/{imgs['test']})")
    print(f"Report: {OUT / 'cleaning_report.md'}")


def build_scene_groups(pool):
    """Single-linkage groups (chained). Report-only: same-scene exposure. Not used for splitting."""
    m = len(pool)
    parent = list(range(m))

    def find(x):
        while parent[x] != x:
            parent[x] = parent[parent[x]]
            x = parent[x]
        return x

    PH = np.stack([r["ph"] for r in pool])
    PHf = np.stack([r["phf"] for r in pool])
    for i in range(m):
        d = np.minimum((PH[i + 1:] != PH[i]).sum(1), (PHf[i + 1:] != PH[i]).sum(1))
        for off in np.nonzero(d <= PHASH_MAX_DIST)[0]:
            parent[find(i + 1 + off)] = find(i)
    groups = defaultdict(list)
    for i in range(m):
        groups[find(i)].append(i)
    clusters = sorted(groups.values(), key=lambda g: g[0])  # deterministic: pool is sorted by name
    st = Counter()
    st["scene_groups_n"] = len(clusters)
    st["scene_group_max"] = max(len(c) for c in clusters)
    return clusters, st


def build_clusters(pool):
    """Greedy complete-linkage: an image joins a cluster only if it is within PHASH_MAX_DIST
    (incl. h-flip) of EVERY current member. Seeded processing order. Returns (clusters, stats)."""
    m = len(pool)
    PH = np.stack([r["ph"] for r in pool])
    PHf = np.stack([r["phf"] for r in pool])
    D = np.empty((m, m), dtype=np.int16)
    for i in range(m):
        D[i] = np.minimum((PH != PH[i]).sum(1), (PHf != PH[i]).sum(1))
    A = D <= PHASH_MAX_DIST
    order = list(range(m))
    random.Random(SEED).shuffle(order)
    cid = np.full(m, -1)
    members = []
    for i in order:
        best, best_key = None, None
        for c in {int(cid[j]) for j in np.nonzero(A[i])[0] if cid[j] >= 0}:
            mem = members[c]
            if A[i, mem].all():
                key = (int(D[i, mem].max()), -len(mem), c)
                if best_key is None or key < best_key:
                    best, best_key = c, key
        if best is None:
            best = len(members)
            members.append([])
        members[best].append(i)
        cid[i] = best
    clusters = sorted((sorted(c) for c in members), key=lambda g: g[0])
    for c in clusters:  # invariant check
        sub = D[np.ix_(c, c)]
        assert sub.max() <= PHASH_MAX_DIST
    st = Counter()
    st["clusters_n"] = len(clusters)
    st["clusters_max"] = max(len(c) for c in clusters)
    st["clusters_multi_image"] = sum(1 for c in clusters if len(c) > 1)
    st["clusters_multi_dataset"] = sum(1 for c in clusters if len({pool[i]["ds"] for i in c}) > 1)
    for c in clusters:
        n_ = len(c)
        st["hist:" + (str(n_) if n_ <= 5 else "6-10" if n_ <= 10 else "11+")] += 1
    return clusters, st


def stratified_split(pool, clusters, rng):
    """Greedy, rarest-class-first assignment of whole clusters to train/valid/test."""
    info = []
    for ci, members in enumerate(clusters):
        cc = Counter()
        for i in members:
            for b in pool[i]["boxes"]:
                cc[b[0]] += 1
        info.append((ci, len(members), cc))
    T = Counter()
    for _, _, cc in info:
        T.update(cc)
    N = sum(n for _, n, _ in info)
    target = {}
    for c, t in T.items():
        v = SPLIT_FRAC[1] * t
        te = SPLIT_FRAC[2] * t
        if t >= MIN_EVAL_BOXES * 3 + 5:  # enough boxes to guarantee a floor in valid and test
            v, te = max(v, MIN_EVAL_BOXES), max(te, MIN_EVAL_BOXES)
        target[(0, c)], target[(1, c)], target[(2, c)] = t - v - te, v, te
    img_target = [f * N for f in SPLIT_FRAC]
    cur = defaultdict(float)
    cur_img = [0, 0, 0]
    order = list(info)
    rng.shuffle(order)
    order.sort(key=lambda x: min(T[c] for c in x[2]))  # stable: rarest class first, ties random
    split_of = {}
    for ci, n, cc in order:
        best, best_s = None, None
        for s in range(3):
            score = (n / N) * (img_target[s] - cur_img[s]) / N
            for c, k in cc.items():
                score += (k / T[c]) * (target[(s, c)] - cur[(s, c)]) / T[c]
            score += rng.random() * 1e-9
            if best_s is None or score > best_s:
                best, best_s = s, score
        split_of[ci] = best
        cur_img[best] += n
        for c, k in cc.items():
            cur[(best, c)] += k

    # repair: classes still under the floor in valid/test pull in train clusters that contain them,
    # as long as no other class loses too much train data and the eval split stays near its image target
    for c in sorted(T, key=lambda c: T[c]):
        if T[c] < MIN_EVAL_BOXES * 3 + 5:
            continue
        for s in (1, 2):
            while cur[(s, c)] < MIN_EVAL_BOXES:
                ok = [(ci, n, cc) for ci, n, cc in info
                      if split_of[ci] == 0 and c in cc and cur_img[s] + n <= img_target[s] * 1.3
                      and all(cur[(0, d)] - k >= 0.6 * target[(0, d)] for d, k in cc.items())]
                if not ok:
                    break
                ci, n, cc = max(ok, key=lambda x: (x[2][c] / sum(x[2].values()), -x[1]))
                split_of[ci] = s
                cur_img[0] -= n
                cur_img[s] += n
                for d, k in cc.items():
                    cur[(0, d)] -= k
                    cur[(s, d)] += k
    return split_of


def check_leakage(pool, clusters, split_of):
    """Assert no cluster spans splits, then re-hash the written files and compare valid/test vs train."""
    for ci, members in enumerate(clusters):
        assert len({split_of[ci]}) == 1  # by construction; the file-level check below is the real test
    where = {}
    for sp in OUT_SPLITS:
        for p in (OUT / sp / "images").iterdir():
            where[p.name] = sp
    for ci, members in enumerate(clusters):
        sps = {where[pool[i]["name"]] for i in members if pool[i]["name"] in where}
        assert len(sps) <= 1, f"cluster {ci} straddles splits {sps}"
    res = {"cluster_check": "PASS"}
    H, Hf, S = [], [], []
    for sp in OUT_SPLITS:
        for p in sorted((OUT / sp / "images").iterdir()):
            with Image.open(p) as im:
                im = im.convert("RGB")
                H.append(np.array(imagehash.phash(im).hash, dtype=bool).ravel())
                Hf.append(np.array(imagehash.phash(im.transpose(Image.FLIP_LEFT_RIGHT)).hash, dtype=bool).ravel())
            S.append(sp)
    H, Hf, S = np.stack(H), np.stack(Hf), np.array(S)
    tr = S == "train"
    mind, near = 99, 0
    for i in np.nonzero(~tr)[0]:
        d = int(np.minimum((H[tr] != H[i]).sum(1), (Hf[tr] != H[i]).sum(1)).min())
        mind = min(mind, d)
        near += d <= PHASH_MAX_DIST
    res.update(min_dist=mind, near_train=int(near), n_eval=int((~tr).sum()))
    print(f"Leakage check: clusters straddling splits = 0 (PASS); min phash distance valid/test->train = {mind}; "
          f"valid/test images with a train neighbour <= {PHASH_MAX_DIST}: {near}/{res['n_eval']}")
    return res


def parse_old_report(path):
    """Per-split image counts and per-class split counts from a previous cleaning_report.md."""
    if not path.exists():
        return None
    txt = path.read_text()
    m = re.search(r"Images: train (\d+), valid (\d+), test (\d+)", txt)
    rows = {}
    for r in re.finditer(r"^\| \d+ \| (\w+) \| (\d+) \| (\d+) \| (\d+) \| (\d+) \|", txt, re.M):
        rows[r.group(1)] = tuple(int(r.group(i)) for i in (2, 3, 4))
    if not m or not rows:
        return None
    return dict(imgs=dict(zip(OUT_SPLITS, map(int, m.groups()))), rows=rows)


def write_report(stats, imgs, inst, n_final, cls_clusters, leak):
    L = ["# Cleaning report", "", f"Seed {SEED}. Cluster-aware stratified split, target 70/15/15 by images.", "",
         "## Images", "", "| Reason | Count |", "|---|---|",
         f"| Raw images | {stats['images_raw']} |",
         f"| Dropped: corrupt/unreadable | {stats['images_corrupt']} |",
         f"| Dropped: no boxes left after remap/cleaning | {stats['images_empty_after_remap']} |",
         f"| Dropped: exact duplicate (identical bytes) | {stats['images_dup_exact']} |",
         f"| Dropped: near-duplicate (phash dist <= {PHASH_MAX_DIST} incl. h-flip, AND same class multiset) | {stats['images_dup_near']} |",
         f"| &nbsp;&nbsp;of the duplicates: within the same dataset | {stats['dup_within_dataset']} |",
         f"| &nbsp;&nbsp;of the duplicates: across datasets | {stats['dup_across_datasets']} |",
         f"| Dropped: valid/test image within phash {LEAK_DROP_DIST} of a train image (valid {stats['leak_dropped:valid']}, test {stats['leak_dropped:test']}) | {stats['leak_dropped']} |",
         f"| **Final images** | **{n_final}** |", "",
         f"Largest drop-duplicate group: {stats['dup_cluster_max_size']} images.", "",
         "## Boxes dropped (before image-level dedup)", "", "| Reason | Count |", "|---|---|",
         f"| Class mapped to None (non-food / excluded) | {stats['boxes_dropped_class']} |"]
    for k in sorted(k for k in stats if k.startswith("boxes_dropped_class:")):
        L.append(f"| &nbsp;&nbsp;{k.split(':', 1)[1]} | {stats[k]} |")
    for k in sorted(k for k in stats if k.startswith("boxes_relabelled:")):
        L.append(f"| Relabelled from 'others' -> {k.split(':', 1)[1]} (kept, before other box filters) | {stats[k]} |")
    L += [f"| Coordinates outside 0-1 | {stats['boxes_out_of_range']} |",
          f"| Near-zero area (side < {MIN_SIDE} or area < {MIN_AREA}) | {stats['boxes_near_zero_area']} |",
          f"| Duplicate box (same class, IoU > {DUP_BOX_IOU}) | {stats['boxes_duplicate']} |",
          f"| Malformed line | {stats['boxes_malformed']} |", "",
          f"Polygon labels converted to boxes: {stats['polygons_converted']}. "
          f"Different-class box pairs overlapping at IoU > {DUP_BOX_IOU} (kept, suspicious): {stats['conflicting_class_overlaps']}.", "",
          "## Near-duplicate clusters (used for splitting)", "",
          f"Greedy complete-linkage: every pair inside a cluster is within phash distance <= {PHASH_MAX_DIST} "
          f"incl. h-flip, without requiring matching labels. Whole clusters are assigned to one split.", "",
          f"- Clusters: {stats['clusters_n']} ({stats['clusters_multi_image']} with more than one image)",
          f"- Largest cluster: {stats['clusters_max']} images",
          f"- Clusters containing images from more than one dataset: {stats['clusters_multi_dataset']}",
          "- Size histogram: " + ", ".join(f"{k}: {stats['hist:' + k]}" for k in ("1", "2", "3", "4", "5", "6-10", "11+")), "",
          "## Same-scene exposure (single-linkage group, report only)", "",
          f"Single-linkage chaining (links at distance <= {PHASH_MAX_DIST}) gives {stats['scene_groups_n']} groups; the largest has "
          f"{stats['scene_group_max']} images from {dict(leak['scene_ds'])}. Where those images ended up: "
          f"train {leak['scene_split']['train']}, valid {leak['scene_split']['valid']}, test {leak['scene_split']['test']}, dropped as close to train {leak['scene_split']['dropped']}.", "",
          "## Leakage check", "",
          f"Valid/test images within phash distance {LEAK_DROP_DIST} of a train image were dropped after the split "
          f"({stats['leak_dropped']} images; boxes lost: "
          + ", ".join(f"{c} {n}" for c, n in sorted(Counter({c: n for (_, c), n in leak['dropped_boxes'].items()}).items())) + ").",
          "Complete-linkage clusters cannot guarantee zero cross-split neighbours: chain links between clusters can cross splits.", "",
          f"- No cluster straddles train/valid/test: **{leak['cluster_check']}**",
          f"- Min phash distance (incl. h-flip) between valid/test and train images, recomputed from the written files: **{leak['min_dist']}**",
          f"- Valid/test images with a train neighbour at distance <= {PHASH_MAX_DIST}: **{leak['near_train']}** of {leak['n_eval']}", "",
          "## Final classes and instances per split", "",
          f"Images: train {imgs['train']}, valid {imgs['valid']}, test {imgs['test']}", "",
          "| id | class | train | valid | test | total | clusters | size flag | split flag |",
          "|---|---|---|---|---|---|---|---|---|"]
    flagged = []
    for i, c in enumerate(FINAL_CLASSES):
        t = [inst[sp][c] for sp in OUT_SPLITS]
        tot = sum(t)
        size = "VERY WEAK" if tot < 50 else "WEAK" if tot < 100 else ""
        thin = "THIN-SPLIT" if min(t) < MIN_EVAL_BOXES else ""
        nc = len(cls_clusters[c])
        L.append(f"| {i} | {c} | {t[0]} | {t[1]} | {t[2]} | {tot} | {nc} | {size} | {thin} |")
        why = []
        if size:
            why.append(f"{tot} boxes total (<{50 if size == 'VERY WEAK' else 100})")
        if thin:
            why.append("fewer than %d boxes in " % MIN_EVAL_BOXES + ", ".join(
                f"{sp} ({n})" for sp, n in zip(OUT_SPLITS, t) if n < MIN_EVAL_BOXES))
        if why:
            flagged.append((c, [f for f in (size, thin) if f], why, nc))
    L += ["", "## Flagged classes", "",
          f"WEAK: total < 100 boxes. VERY WEAK: total < 50. THIN-SPLIT: any split has < {MIN_EVAL_BOXES} boxes.", ""]
    if flagged:
        L += ["| class | flags | reason | unique clusters |", "|---|---|---|---|"]
        L += [f"| {c} | {', '.join(f)} | {'; '.join(w)} | {nc} |" for c, f, w, nc in flagged]
    else:
        L.append("None.")
    few = [(c, len(s)) for c, s in sorted(cls_clusters.items(), key=lambda x: len(x[1])) if len(s) < 30]
    L += ["", "Classes drawn from fewer than 30 clusters (many boxes from few clusters is weaker than it looks): "
          + (", ".join(f"{c} ({n})" for c, n in few) if few else "none") + ".", ""]

    old = parse_old_report(OUT / "cleaning_report_v3_old.md")
    L += ["## Comparison with previous split (cleaning_report_v3_old.md)", ""]
    if old is None:
        L.append("No previous report found.")
    else:
        old_boxes = {sp: sum(r[k] for r in old["rows"].values()) for k, sp in enumerate(OUT_SPLITS)}
        new_boxes = {sp: sum(inst[sp].values()) for sp in OUT_SPLITS}
        L += ["| split | images old | images new | boxes old | boxes new |", "|---|---|---|---|---|"]
        for sp in OUT_SPLITS:
            L.append(f"| {sp} | {old['imgs'][sp]} | {imgs[sp]} | {old_boxes[sp]} | {new_boxes[sp]} |")
        L += ["", "Per-class valid/test counts that changed by more than 5 boxes:", "",
              "| class | valid old -> new | test old -> new |", "|---|---|---|"]
        n_ch = 0
        for c in FINAL_CLASSES:
            if c not in old["rows"]:
                continue
            ov, ot = old["rows"][c][1], old["rows"][c][2]
            nv, nt = inst["valid"][c], inst["test"][c]
            if abs(nv - ov) > 5 or abs(nt - ot) > 5:
                n_ch += 1
                L.append(f"| {c} | {ov} -> {nv} | {ot} -> {nt} |")
        if not n_ch:
            L.append("| (none) | | |")
    L.append("")
    (OUT / "cleaning_report.md").write_text("\n".join(L))


if __name__ == "__main__":
    main()
