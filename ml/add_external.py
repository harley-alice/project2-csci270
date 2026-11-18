"""Build data/cleaned_v2/: the frozen data/cleaned splits plus approved external training images.

- valid and test: byte-identical copies of data/cleaned (verified by checksum).
- train: all of data/cleaned train plus selected external images, labels remapped to the 38 class ids with the
  approved mapping (MAPPING in ml/audit_external.py), files prefixed ext_<dataset>_.
- Excluded: external images within phash distance 4 (incl. h-flip) of ANY image in data/cleaned train/valid/test,
  and Roboflow augmentation copies (one file kept per base name).
- Policy: keep an image only if at least --min-mapped fraction of its boxes map to my classes (default 1.0 = every box),
  so no mapped-away object is left unlabeled. At most --cap images per source (default 150), chosen by a documented,
  seeded ranking, at most one image per scene cluster.
- data/cleaned is only read. Real-fridge QA photos are never used.

Usage:  python ml/add_external.py            # builds data/cleaned_v2 (refuses to overwrite)
        python ml/add_external.py --overwrite --cap 150
"""
import argparse
import hashlib
import json
import random
import re
import shutil
import sys
from collections import Counter, defaultdict
from pathlib import Path

import numpy as np
import yaml

sys.path.insert(0, str(Path(__file__).resolve().parent))
from audit_external import (IMG_EXT, MAPPING, SOURCES, SPLITS, clusters_complete_linkage, dist_matrix,  # noqa: E402
                            load_dataset, parse_label, phashes)
from class_map import EXTERNAL_V3_KEEP_ONLY, EXTERNAL_V3_MAP  # noqa: E402

REPO = Path(__file__).resolve().parents[1]
DATA = REPO / "data"
CLEANED = DATA / "cleaned"
V2 = DATA / "cleaned_v2"
SUMMARY = REPO / "ml" / "runs" / "external_audit" / "merge_summary.json"
SEED = 0
PHASH_MAX_DIST = 4
COORD_TOL = 1e-3
MIN_SIDE = 0.005
PRIORITY = {"refrigerator_contents": ["bread", "banana", "potato", "spinach"]}
URLS = {
    "refrigerator_contents": "https://universe.roboflow.com/new-workspace-32uyj/refridgerator-contents-detection",
    "objects_inside_a_fridge": "https://universe.roboflow.com/shounak-mishra/objects-inside-a-fridge",
}


def md5(path):
    return hashlib.md5(Path(path).read_bytes()).hexdigest()


def manifest(root):
    return {str(p.relative_to(root)): (p.stat().st_size, p.stat().st_mtime_ns) for p in sorted(root.rglob("*")) if p.is_file()}


def copy_split(split):
    for kind in ("images", "labels"):
        dst = V2 / split / kind
        dst.mkdir(parents=True, exist_ok=True)
        for f in sorted((CLEANED / split / kind).iterdir()):
            if f.is_file():
                shutil.copy2(f, dst / f.name)


def class_counts(split_dir):
    names = yaml.safe_load((CLEANED / "data.yaml").read_text())["names"]
    c = Counter()
    for f in (split_dir / "labels").glob("*.txt"):
        for line in f.read_text().splitlines():
            if line.strip():
                c[names[int(line.split()[0])]] += 1
    return c


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--cap", type=int, default=150, help="max images added per source")
    ap.add_argument("--min-mapped", type=float, default=1.0, help="minimum share of an image's boxes that must map")
    ap.add_argument("--overwrite", action="store_true", help="rebuild data/cleaned_v2 (or v3 with --v3) if it exists")
    ap.add_argument("--v3", action="store_true", help="build data/cleaned_v3 from data/cleaned_v2 plus two more sources")
    ap.add_argument("--class-cap", action="append", default=[], metavar="CLASS=N",
                    help="override the per-class cap of included external boxes in --v3 (repeatable), e.g. --class-cap egg=100")
    ap.add_argument("--validate-v3", action="store_true", help="validate an existing data/cleaned_v3 and exit (builds nothing)")
    ap.add_argument("--real-fridge", default="data/real_fridge/upright/images",
                    help="held-out real-fridge photos, checked so no external image duplicates them (relative to the repo root)")
    a = ap.parse_args()
    if a.validate_v3:
        return validate_existing_v3()
    if a.v3:
        return build_v3(a)

    my_names = yaml.safe_load((CLEANED / "data.yaml").read_text())["names"]
    cid = {n: i for i, n in enumerate(my_names)}
    before = manifest(CLEANED)

    if V2.exists():
        if not a.overwrite:
            raise SystemExit(f"{V2.relative_to(REPO)} exists; pass --overwrite to rebuild it")
        assert V2.name == "cleaned_v2" and V2.parent == DATA
        shutil.rmtree(V2)

    print("copying data/cleaned splits ...", flush=True)
    for sp in SPLITS:
        copy_split(sp)
    train_before = class_counts(CLEANED / "train")

    print("hashing data/cleaned ...", flush=True)
    my = {}
    for sp in SPLITS:
        ph, phf = [], []
        for p in sorted((CLEANED / sp / "images").iterdir()):
            if p.suffix.lower() in IMG_EXT:
                x, y = phashes(p)
                ph.append(x)
                phf.append(y)
        my[sp] = (np.stack(ph), np.stack(phf))
    cleaned_md5 = {sp: {md5(p) for p in (CLEANED / sp / "images").iterdir() if p.is_file()} for sp in SPLITS}

    report = {}
    added_rows = []
    taken_names = {p.name for p in (V2 / "train" / "images").iterdir()}
    for name in SOURCES:
        print("source", name, flush=True)
        cfg, names, recs, _ = load_dataset(name)
        mp = {k: v[0] for k, v in MAPPING[name].items()}
        info = {"images_total": len(recs), "excluded": Counter()}

        PH, PHf = np.stack([r["ph"] for r in recs]), np.stack([r["phf"] for r in recs])
        near = np.zeros(len(recs), dtype=bool)
        for sp in SPLITS:
            near |= dist_matrix(PH, PHf, my[sp][0]).min(1) <= PHASH_MAX_DIST
        info["excluded"]["near_duplicate_of_data_cleaned"] = int(near.sum())

        # one file per Roboflow base name (deterministic: split order, then name)
        order = {sp: i for i, sp in enumerate(SPLITS)}
        by_base = defaultdict(list)
        for i, r in enumerate(recs):
            by_base[r["base"]].append(i)
        keep = []
        for b, ix in by_base.items():
            ok = sorted((i for i in ix if not near[i]), key=lambda i: (order[recs[i]["split"]], recs[i]["stem"]))
            info["excluded"]["augmentation_copy"] += len(ix) - 1
            if ok:
                keep.append(ok[0])

        cand = []
        for i in keep:
            r = recs[i]
            if not r["boxes"]:
                info["excluded"]["no_boxes"] += 1
                continue
            mapped = [mp[names[c]] for c, *_ in r["boxes"]]
            share = sum(m is not None for m in mapped) / len(mapped)
            if share < a.min_mapped or share == 0:
                info["excluded"]["too_many_unmapped_boxes"] += 1
                continue
            lines, bad = [], False
            for (c, xc, yc, w, h), m in zip(r["boxes"], mapped):
                if m is None:
                    continue
                x1, y1, x2, y2 = xc - w / 2, yc - h / 2, xc + w / 2, yc + h / 2
                if min(x1, y1) < -COORD_TOL or max(x2, y2) > 1 + COORD_TOL:
                    bad = True
                    break
                x1, y1, x2, y2 = max(0, x1), max(0, y1), min(1, x2), min(1, y2)
                if x2 - x1 < MIN_SIDE or y2 - y1 < MIN_SIDE:
                    bad = True
                    break
                lines.append((cid[m], (x1 + x2) / 2, (y1 + y2) / 2, x2 - x1, y2 - y1))
            if bad:
                info["excluded"]["invalid_or_degenerate_box"] += 1
                continue
            cand.append({"i": i, "lines": lines, "classes": {my_names[l[0]] for l in lines}})
        info["eligible"] = len(cand)

        # ranking: priority classes first, then 2+ boxes, then class variety, seeded tie-break; one per scene cluster
        rnd = random.Random(SEED)
        pri = set(PRIORITY.get(name, []))
        for c in cand:
            c["key"] = (-int(bool(c["classes"] & pri)) if pri else 0, -int(len(c["lines"]) >= 2), -min(len(c["classes"]), 3), rnd.random())
        cand.sort(key=lambda c: c["key"])
        cl, _ = clusters_complete_linkage(PH, PHf)
        cluster_of = {m: ci for ci, mem in enumerate(cl) for m in mem}
        chosen, used = [], set()
        for c in cand:
            if len(chosen) >= a.cap:
                break
            if cluster_of[c["i"]] in used:
                info["excluded"]["same_scene_cluster_as_selected"] += 1
                continue
            used.add(cluster_of[c["i"]])
            chosen.append(c)
        info["selected"] = len(chosen)
        info["selected_with_priority_class_and_2plus_boxes"] = sum(1 for c in chosen if (c["classes"] & pri) and len(c["lines"]) >= 2) if pri else None

        added = Counter()
        for c in chosen:
            r = recs[c["i"]]
            stem = re.sub(r"[^A-Za-z0-9_-]+", "_", f"ext_{name}_{r['stem']}")
            fname = stem + r["path"].suffix.lower()
            assert fname not in taken_names, f"filename collision: {fname}"
            taken_names.add(fname)
            shutil.copy2(r["path"], V2 / "train" / "images" / fname)
            (V2 / "train" / "labels" / f"{stem}.txt").write_text(
                "".join(f"{k} {xc:.6f} {yc:.6f} {w:.6f} {h:.6f}\n" for k, xc, yc, w, h in c["lines"]))
            for k, *_ in c["lines"]:
                added[my_names[k]] += 1
            added_rows.append(fname)
        info["boxes_added"] = dict(added)
        info["excluded"] = dict(info["excluded"])
        report[name] = info

    # ---------------------------------------------------------------- data.yaml and ADDED_FROM.md
    (V2 / "data.yaml").write_text(yaml.safe_dump(
        {"train": "train/images", "val": "valid/images", "test": "test/images", "nc": len(my_names), "names": my_names}, sort_keys=False))
    train_after = class_counts(V2 / "train")
    write_added_from(report, my_names, train_before, train_after)

    # ---------------------------------------------------------------- validation
    problems = []
    for sp in SPLITS:
        for kind in ("images", "labels"):
            for f in sorted((CLEANED / sp / kind).iterdir()):
                if f.is_file() and md5(f) != md5(V2 / sp / kind / f.name):
                    problems.append(f"{sp}/{kind}/{f.name} differs from data/cleaned")
    for sp in ("valid", "test"):
        if {p.name for p in (V2 / sp / "images").iterdir()} != {p.name for p in (CLEANED / sp / "images").iterdir()}:
            problems.append(f"{sp} file list differs")
    n_img = {sp: len([p for p in (V2 / sp / "images").iterdir() if p.is_file()]) for sp in SPLITS}
    ext_files = [p for p in (V2 / "train" / "images").iterdir() if p.name.startswith("ext_")]
    leak = [p.name for p in ext_files if md5(p) in cleaned_md5["valid"] | cleaned_md5["test"] | cleaned_md5["train"]]
    if leak:
        problems.append(f"added images identical to data/cleaned images: {leak[:3]}")
    bad_labels = empty = 0
    for f in (V2 / "train" / "labels").glob("ext_*.txt"):
        lines = [l.split() for l in f.read_text().splitlines() if l.strip()]
        if not lines:
            empty += 1
        for v in lines:
            if len(v) != 5 or not 0 <= int(v[0]) < len(my_names) or not all(0 <= float(x) <= 1 for x in v[1:]):
                bad_labels += 1
    if bad_labels:
        problems.append(f"{bad_labels} invalid label lines among added files")
    if empty:
        problems.append(f"{empty} empty added label files")
    names_all = [p.name for p in (V2 / "train" / "images").iterdir()]
    if len(names_all) != len(set(names_all)):
        problems.append("duplicate file names in train/images")
    after = manifest(CLEANED)
    if before != after:
        problems.append("data/cleaned changed during the build")
    yml = yaml.safe_load((V2 / "data.yaml").read_text())
    if yml["names"] != my_names or any(str(v).startswith("/") for v in (yml["train"], yml["val"], yml["test"])):
        problems.append("data.yaml names/paths wrong")

    summary = {"sources": report, "images": {"train_before": len(list((CLEANED / "train" / "images").iterdir())), **{f"{k}_v2": v for k, v in n_img.items()}},
               "ext_files": len(ext_files), "train_boxes_before": dict(train_before), "train_boxes_after": dict(train_after),
               "problems": problems, "checksum_matches_added_vs_cleaned": len(leak), "empty_added_labels": empty}
    SUMMARY.write_text(json.dumps(summary, indent=2, default=int))
    print(json.dumps({k: v for k, v in summary.items() if k != "train_boxes_before" and k != "train_boxes_after"}, indent=2, default=int))
    print("PROBLEMS:", problems or "none")


def write_added_from(report, my_names, before, after):
    L = []
    a = L.append
    a("# data/cleaned_v2: what was added and from where\n")
    a("`valid/` and `test/` are byte-identical copies of `data/cleaned`. `train/` is all of `data/cleaned` train plus the external images below. "
      "Real-fridge QA photos are not used anywhere in this dataset. Rebuild with `python ml/add_external.py --overwrite`.\n")
    a("## Sources and licenses\n")
    for name, info in report.items():
        s = SOURCES[name]
        a(f"### {name}\n")
        a(f"- URL: {URLS[name]}")
        a(f"- Roboflow workspace/project: `{s['workspace']}/{s['project']}`, version 1, license **CC BY 4.0** (https://creativecommons.org/licenses/by/4.0/).")
        a(f"- Attribution: \"{s['project']}\" (Roboflow Universe, workspace {s['workspace']}), provided by a Roboflow user, licensed under CC BY 4.0. "
          "Changes made: the class labels were remapped to this project's 38 classes, a subset of images was selected, and no pixel changes were applied by this project "
          "(Roboflow had already resized the images to 640x640 with stretch).")
        a(f"- Images in the source: {info['images_total']}. Added to train: **{info['selected']}**. Eligible before the cap: {info['eligible']}. "
          f"Exclusions: {info['excluded']}.\n")
    a("## Approved class mapping (external class -> my class, None = box dropped)\n")
    for name in report:
        a(f"### {name}\n")
        a("| External class | Maps to |\n|---|---|")
        for k, v in MAPPING[name].items():
            a(f"| {k} | {v[0]} |")
        a("")
    a("Policy: an image is kept only if every one of its boxes maps to one of my classes, so no object is left unlabeled by a dropped box. "
      "Per source, at most 150 images (the default cap); ranking prefers images that contain a priority class (for refrigerator_contents: bread, banana, "
      "potato, spinach), then images with two or more boxes, then class variety, with a seeded tie-break and at most one image per near-duplicate scene cluster.\n")
    a("## Boxes added per class\n")
    names_added = sorted({c for i in report.values() for c in i["boxes_added"]})
    a("| Class | Train boxes before | " + " | ".join(report) + " | Train boxes after |\n|---|---|" + "---|" * (len(report) + 1))
    for c in names_added:
        a(f"| {c} | {before.get(c, 0)} | " + " | ".join(str(report[n]["boxes_added"].get(c, 0)) for n in report) + f" | {after.get(c, 0)} |")
    a("")
    (V2 / "ADDED_FROM.md").write_text("\n".join(L) + "\n")


# =============================================================================== v3: two more external sources
V3 = DATA / "cleaned_v3"
V2_DIR = DATA / "cleaned_v2"
REPORT_V3 = REPO / "ml" / "runs" / "external_audit" / "report_v3.md"
SUMMARY_V3 = REPO / "ml" / "runs" / "external_audit" / "merge_summary_v3.json"
V3_SEED = 270
CAP_OVERRIDES = {}                          # filled from --class-cap
V3_SOURCES = {
    "fridge_food_images_v14": {"tag": "ffi14", "dir": DATA / "external" / "fridge_food_images_v14"},
    "fridge_v1i": {"tag": "fv1i", "dir": DATA / "external" / "fridge_v1i"},
}
CAP_DEFAULT, CAP_FRUIT = 300, 150          # included boxes per class: A classes / mango and pomegranate
FRUIT_CAPPED = {"mango", "pomegranate"}
MIN_SIDE_V3 = 0.005                         # box width or height under 0.5% of the image is dropped
LARGE_FRAC = 0.05                           # a dropped box this large (share of image area) is a visible unlabeled object
OVERLAP_IOA = 0.10                          # a dropped box overlapping a kept box by this much of the smaller area, too
MAX_SINGLE_BOX = 0.60                       # drop images whose only kept box covers more than this (close-up stock shots)
SMALL_BOX = 0.15                            # preferred box size when a class is over its cap
SAMPLE_N = 12


def v3_load(src):
    d = V3_SOURCES[src]["dir"]
    cfg = yaml.safe_load((d / "data.yaml").read_text())
    names = cfg["names"]
    recs, counts, poly = [], defaultdict(Counter), 0
    for sp in SPLITS:
        for p in sorted((d / sp / "images").iterdir()):
            if p.suffix.lower() not in IMG_EXT:
                continue
            boxes, pl = parse_label(d / sp / "labels" / f"{p.stem}.txt")
            poly += pl
            for c, *_ in boxes:
                counts[names[c]][sp] += 1
            base, _, h = p.stem.partition(".rf.")
            recs.append({"src": src, "path": p, "split": sp, "stem": p.stem, "base": base, "hash": h, "raw": boxes})
    return cfg, names, recs, counts, poly


def clamp_box(xc, yc, w, h):
    x1, y1, x2, y2 = max(0.0, xc - w / 2), max(0.0, yc - h / 2), min(1.0, xc + w / 2), min(1.0, yc + h / 2)
    return x1, y1, x2, y2


def ioa(a, b):
    ix = max(0.0, min(a[2], b[2]) - max(a[0], b[0]))
    iy = max(0.0, min(a[3], b[3]) - max(a[1], b[1]))
    small = min((a[2] - a[0]) * (a[3] - a[1]), (b[2] - b[0]) * (b[3] - b[1]))
    return ix * iy / small if small > 0 else 0.0


def v3_filter(rec, names, mp, keep_only, stats):
    """Convert, clamp and map the boxes of one image; return a reason string if the image must be dropped."""
    kept, dropped = [], []
    for c, xc, yc, w, h in rec["raw"]:
        sname = names[c]
        x1, y1, x2, y2 = clamp_box(xc, yc, w, h)
        if x2 - x1 < MIN_SIDE_V3 or y2 - y1 < MIN_SIDE_V3:
            stats["tiny_boxes_dropped"] += 1
            continue
        tgt = mp.get(sname)
        if tgt is not None:
            kept.append((tgt, x1, y1, x2, y2))
        else:
            if sname not in mp and not keep_only:
                stats["unmapped_source_class"][sname] += 1
            dropped.append((sname, x1, y1, x2, y2))
    rec["kept"], rec["dropped"] = kept, dropped
    if not kept:
        return "no_kept_boxes"
    area = lambda b: (b[3] - b[1]) * (b[4] - b[2])
    if any(area(d) >= LARGE_FRAC for d in dropped):
        return "large_unlabeled_object"
    if any(ioa(d[1:], k[1:]) >= OVERLAP_IOA for d in dropped for k in kept):
        return "unlabeled_object_overlaps_kept_box"
    if len(kept) == 1 and area(kept[0]) > MAX_SINGLE_BOX:
        return "single_box_over_60pct"
    return None


def hash_dir(paths):
    ph, phf = [], []
    for p in paths:
        x, y = phashes(p)
        ph.append(x)
        phf.append(y)
    return np.stack(ph), np.stack(phf)


def list_images(d):
    return sorted(p for p in Path(d).iterdir() if p.suffix.lower() in IMG_EXT)


def build_v3(a):
    real_fridge = (REPO / a.real_fridge).resolve()
    for need in (CLEANED, V2_DIR):
        if not need.exists():
            raise SystemExit(f"missing input: {need.relative_to(REPO)}")
    if not real_fridge.exists():
        print(f"WARNING: held-out photos not found at {a.real_fridge}; the real-fridge duplicate check is SKIPPED")
    for s in V3_SOURCES.values():
        if not s["dir"].exists():
            raise SystemExit(f"missing source folder: {s['dir'].relative_to(REPO)}")
    my_names = yaml.safe_load((CLEANED / "data.yaml").read_text())["names"]
    v2_names = yaml.safe_load((V2_DIR / "data.yaml").read_text())["names"]
    assert my_names == v2_names
    cid = {n: i for i, n in enumerate(my_names)}
    before_cleaned, before_v2 = manifest(CLEANED), manifest(V2_DIR)
    if V3.exists():
        if not a.overwrite:
            raise SystemExit(f"{V3.relative_to(REPO)} exists; pass --overwrite to rebuild it")
        assert V3.name == "cleaned_v3" and V3.parent == DATA
        shutil.rmtree(V3)

    # ------------------------------------------------ steps 1-3: load, list, map, filter
    srcs, funnel = {}, {}
    for src, meta in V3_SOURCES.items():
        mp, keep_only = EXTERNAL_V3_MAP[src], src in EXTERNAL_V3_KEEP_ONLY
        cfg, names, recs, counts, poly = v3_load(src)
        print(f"\n=== {src}: {len(recs)} images, {cfg['nc']} classes, polygon lines converted: {poly}")
        print(f"{'class':<16}{'train':>7}{'valid':>7}{'test':>7}  maps to")
        for cname in names:
            c = counts[cname]
            tgt = mp.get(cname, "(dropped: keep-only source)" if keep_only else "(NOT IN MAP)")
            print(f"{cname:<16}{c['train']:>7}{c['valid']:>7}{c['test']:>7}  {tgt}")
        stats = {"tiny_boxes_dropped": 0, "unmapped_source_class": Counter()}
        reasons = Counter()
        survivors = []
        for r in recs:
            why = v3_filter(r, names, mp, keep_only, stats)
            if why:
                reasons[why] += 1
            else:
                survivors.append(r)
        # step 4: one copy per source image (prefer most kept boxes, ties by lowest hash)
        groups = defaultdict(list)
        for r in survivors:
            groups[r["base"]].append(r)
        all_bases = len({r["base"] for r in recs})
        picked = [sorted(g, key=lambda r: (-len(r["kept"]), r["hash"]))[0] for g in groups.values()]
        picked.sort(key=lambda r: r["stem"])
        skipped_raw = Counter({n: sum(counts[n].values()) for n in names if mp.get(n, 1) is None})
        print(f"files {len(recs)} -> source images {all_bases}; after image filters {len(survivors)} files in {len(groups)} source images; "
              f"kept one per source: {len(picked)}")
        print("image drops:", dict(reasons), "| tiny boxes dropped:", stats["tiny_boxes_dropped"],
              "| source classes not in map:", dict(stats["unmapped_source_class"]) or "none")
        if skipped_raw:
            print("boxes in skipped classes (all files):", dict(skipped_raw))
        funnel[src] = {"files": len(recs), "source_images": all_bases, "polygon_lines": poly, "reasons": dict(reasons),
                       "after_filters_files": len(survivors), "after_filters_sources": len(groups), "one_per_source": len(picked),
                       "tiny_boxes_dropped": stats["tiny_boxes_dropped"], "unmapped_source_classes": dict(stats["unmapped_source_class"]),
                       "skipped_class_boxes_all_files": dict(skipped_raw),
                       "class_box_counts": {n: dict(counts[n]) for n in names}}
        srcs[src] = {"names": names, "picked": picked, "cfg": cfg}

    # ------------------------------------------------ step 5: perceptual dedupe and leakage
    print("\nhashing reference images ...", flush=True)
    refs = {
        "data/cleaned": hash_dir([p for sp in SPLITS for p in list_images(CLEANED / sp / "images")]),
        "data/cleaned_v2": hash_dir([p for sp in SPLITS for p in list_images(V2_DIR / sp / "images")]),
    }
    refs["data/real_fridge (held-out QA photos)"] = hash_dir(list_images(real_fridge)) if real_fridge.exists() else (
        np.zeros((0, 64), dtype=bool), np.zeros((0, 64), dtype=bool))
    cand = [r for src in V3_SOURCES for r in srcs[src]["picked"]]
    print(f"hashing {len(cand)} candidate images ...", flush=True)
    PH, PHf = hash_dir([r["path"] for r in cand])
    drop_ref = {k: np.zeros(len(cand), dtype=bool) for k in refs}
    for k, (rph, _) in refs.items():
        if len(rph):
            drop_ref[k] = dist_matrix(PH, PHf, rph).min(1) <= PHASH_MAX_DIST
    D = dist_matrix(PH, PHf, PH)
    removed_ref = np.zeros(len(cand), dtype=bool)
    for k in refs:
        removed_ref |= drop_ref[k]
    keep_idx, within = [], np.zeros(len(cand), dtype=bool)
    for i in range(len(cand)):
        if removed_ref[i]:
            continue
        if keep_idx and (D[i, keep_idx] <= PHASH_MAX_DIST).any():
            within[i] = True
            continue
        keep_idx.append(i)
    for src in V3_SOURCES:
        ix = [i for i, r in enumerate(cand) if r["src"] == src]
        funnel[src]["dedupe"] = {**{k: int(drop_ref[k][ix].sum()) for k in refs}, "any_reference": int(removed_ref[ix].sum()),
                                 "within_external": int(within[ix].sum()), "remaining": sum(1 for i in keep_idx if cand[i]["src"] == src)}
        print(src, "dedupe:", funnel[src]["dedupe"])
    pool = [cand[i] for i in keep_idx]

    # ------------------------------------------------ step 6: caps (seed 270, all-or-nothing per image)
    rng = random.Random(V3_SEED)
    pool.sort(key=lambda r: (r["src"], r["stem"]))
    for r in pool:
        area = lambda b: (b[3] - b[1]) * (b[4] - b[2])
        small = sum(1 for k in r["kept"] if area(k) < SMALL_BOX) / len(r["kept"])
        r["prio"] = (-int(len(r["kept"]) >= 2), -small, rng.random())
    pool.sort(key=lambda r: r["prio"])
    CAP_OVERRIDES.clear()
    for item in a.class_cap:
        k, _, v = item.partition("=")
        assert k in my_names and v.isdigit(), f"bad --class-cap {item}"
        CAP_OVERRIDES[k] = int(v)
    caps = lambda c: CAP_OVERRIDES.get(c, CAP_FRUIT if c in FRUIT_CAPPED else CAP_DEFAULT)
    used, chosen, cap_skipped = Counter(), [], Counter()
    for r in pool:
        need = Counter(k[0] for k in r["kept"])
        if all(used[c] + n <= caps(c) for c, n in need.items()):
            chosen.append(r)
            used.update(need)
        else:
            cap_skipped[r["src"]] += 1
    for src in V3_SOURCES:
        funnel[src]["cap_skipped"] = cap_skipped[src]
        funnel[src]["added_images"] = sum(1 for r in chosen if r["src"] == src)
        print(src, "after caps:", funnel[src]["added_images"], "images (skipped for caps:", cap_skipped[src], ")")

    # ------------------------------------------------ step 7: build data/cleaned_v3
    print("\ncopying data/cleaned_v2 -> data/cleaned_v3 ...", flush=True)
    shutil.copytree(V2_DIR, V3)
    train_before = class_counts(V2_DIR / "train")
    taken = {p.name for p in (V3 / "train" / "images").iterdir()}
    added = defaultdict(Counter)
    for r in sorted(chosen, key=lambda r: (r["src"], r["stem"])):
        tag = V3_SOURCES[r["src"]]["tag"]
        stem = re.sub(r"[^A-Za-z0-9_-]+", "_", f"ext3_{tag}_{r['stem']}")
        fname = stem + r["path"].suffix.lower()
        assert fname not in taken, f"filename collision: {fname}"
        taken.add(fname)
        r["out_name"] = fname
        shutil.copy2(r["path"], V3 / "train" / "images" / fname)
        (V3 / "train" / "labels" / f"{stem}.txt").write_text("".join(
            f"{cid[c]} {(x1 + x2) / 2:.6f} {(y1 + y2) / 2:.6f} {x2 - x1:.6f} {y2 - y1:.6f}\n" for c, x1, y1, x2, y2 in r["kept"]))
        for c, *_ in r["kept"]:
            added[r["src"]][c] += 1
    train_after = class_counts(V3 / "train")

    # ------------------------------------------------ validation (PASS/FAIL table)
    rows = []
    def check(name, ok, detail=""):
        rows.append((name, "PASS" if ok else "FAIL", detail))
    img_sets = {sp: {p.name: p for p in list_images(V3 / sp / "images")} for sp in SPLITS}
    missing_lbl = [n for sp in SPLITS for n, p in img_sets[sp].items() if not (V3 / sp / "labels" / f"{p.stem}.txt").exists()]
    check("every image has a label file", not missing_lbl, f"{len(missing_lbl)} missing")
    bad5 = oor = outside = 0
    for sp in SPLITS:
        for f in (V3 / sp / "labels").glob("*.txt"):
            for line in f.read_text().splitlines():
                if not line.strip():
                    continue
                v = line.split()
                if len(v) != 5:
                    bad5 += 1
                    continue
                if not 0 <= int(v[0]) < len(my_names):
                    oor += 1
                xc, yc, w, h = map(float, v[1:])
                if min(xc, yc, w, h) < 0 or xc + w / 2 > 1 + 1e-6 or yc + h / 2 > 1 + 1e-6 or xc - w / 2 < -1e-6 or yc - h / 2 < -1e-6:
                    outside += 1
    check("every label line has 5 values", bad5 == 0, f"{bad5} bad")
    check(f"class ids within 0-{len(my_names) - 1}", oor == 0, f"{oor} out of range")
    check("boxes within [0,1]", outside == 0, f"{outside} outside")
    names_train = [p.name for p in list_images(V3 / "train" / "images")]
    check("no duplicate filenames in train", len(names_train) == len(set(names_train)))
    md5s = {sp: {md5(p) for p in img_sets[sp].values()} for sp in SPLITS}
    check("no image in both train and valid/test (checksum)", not (md5s["train"] & (md5s["valid"] | md5s["test"])))
    ext_files = [p for p in img_sets["train"].values() if p.name.startswith("ext3_")]
    eph, ephf = hash_dir(ext_files)
    vt = hash_dir([p for sp in ("valid", "test") for p in img_sets[sp].values()])[0]
    check("added images vs valid/test: phash distance > 4", int((dist_matrix(eph, ephf, vt).min(1) <= PHASH_MAX_DIST).sum()) == 0)
    same = all(md5(p) == md5(V3 / sp / k / p.name) for sp in ("valid", "test") for k in ("images", "labels") for p in (CLEANED / sp / k).iterdir() if p.is_file())
    check("valid/test identical to data/cleaned (checksum)", same)
    check("data/cleaned and data/cleaned_v2 unchanged", manifest(CLEANED) == before_cleaned and manifest(V2_DIR) == before_v2)
    y3 = yaml.safe_load((V3 / "data.yaml").read_text())
    check("data.yaml: relative paths, same class order", y3["names"] == my_names and not any(str(y3[k]).startswith("/") for k in ("train", "val", "test")))
    check("added files carry the ext3_ prefix", len(ext_files) == len(chosen) and all(p.name.startswith("ext3_") for p in ext_files), f"{len(ext_files)} files")
    check("no added file from data/real_fridge", all(not drop_ref["data/real_fridge (held-out QA photos)"][cand.index(r)] for r in chosen))
    print("\nVALIDATION")
    for n, s, d in rows:
        print(f"  [{s}] {n} {d}")
    failed = [n for n, s, _ in rows if s == "FAIL"]

    # ------------------------------------------------ contact sheets (untracked) and report
    sheets = write_contact_sheets(chosen)
    samples = {}
    for cname in sorted(FRUIT_CAPPED):
        rs = sorted([r for r in chosen if r["src"] == "fridge_v1i" and any(k[0] == cname for k in r["kept"])], key=lambda r: r["out_name"])
        samples[cname] = [r["out_name"] for r in random.Random(V3_SEED).sample(rs, min(SAMPLE_N, len(rs)))]
    write_added_from_v3(funnel, added, train_before, train_after, my_names)
    write_report_v3(funnel, added, train_before, train_after, rows, samples, sheets, srcs, len(chosen))
    SUMMARY_V3.write_text(json.dumps({"funnel": funnel, "boxes_added": {s: dict(c) for s, c in added.items()}, "validation": rows,
                                      "train_before": dict(train_before), "train_after": dict(train_after),
                                      "images": {sp: len(img_sets[sp]) for sp in SPLITS}, "failed": failed}, indent=2, default=int))
    print(f"\ntrain images: {len(list_images(V2_DIR / 'train' / 'images'))} -> {len(img_sets['train'])}; added {len(chosen)}")
    print("FAILED CHECKS:", failed or "none")


def validate_existing_v3():
    """Independent PASS/FAIL checks on an existing data/cleaned_v3 (builds nothing)."""
    my_names = yaml.safe_load((CLEANED / "data.yaml").read_text())["names"]
    rows = []

    def check(name, ok, detail=""):
        rows.append((name, "PASS" if ok else "FAIL", detail))

    sets = {sp: {p.name: p for p in list_images(V3 / sp / "images")} for sp in SPLITS}
    missing = [n for sp in SPLITS for n, p in sets[sp].items() if not (V3 / sp / "labels" / f"{p.stem}.txt").exists()]
    orphan = [f.name for sp in SPLITS for f in (V3 / sp / "labels").glob("*.txt") if f.stem not in {p.stem for p in sets[sp].values()}]
    check("every image has a label file", not missing, f"{len(missing)} missing, {len(orphan)} labels without an image")
    bad5 = oor = outside = empty = 0
    for sp in SPLITS:
        for f in (V3 / sp / "labels").glob("*.txt"):
            lines = [l.split() for l in f.read_text().splitlines() if l.strip()]
            if not lines and f.name.startswith("ext3_"):
                empty += 1
            for v in lines:
                if len(v) != 5:
                    bad5 += 1
                    continue
                if not 0 <= int(v[0]) < len(my_names):
                    oor += 1
                xc, yc, w, h = map(float, v[1:])
                if min(xc, yc, w, h) < 0 or xc + w / 2 > 1 + 1e-6 or yc + h / 2 > 1 + 1e-6 or xc - w / 2 < -1e-6 or yc - h / 2 < -1e-6:
                    outside += 1
    check("every label line has 5 values", bad5 == 0, f"{bad5} bad")
    check(f"class ids within 0-{len(my_names) - 1}", oor == 0, f"{oor} out of range")
    check("boxes within [0,1]", outside == 0, f"{outside} outside")
    check("no empty label files among added images", empty == 0, f"{empty} empty")
    names_tr = [p.name for p in list_images(V3 / "train" / "images")]
    check("no duplicate filenames in train", len(names_tr) == len(set(names_tr)))
    md5s = {sp: {md5(p) for p in sets[sp].values()} for sp in SPLITS}
    check("no image in both train and valid/test (checksum)", not (md5s["train"] & (md5s["valid"] | md5s["test"])))
    ext = [p for p in sets["train"].values() if p.name.startswith("ext3_")]
    eph, ephf = hash_dir(ext)
    vt = hash_dir([p for sp in ("valid", "test") for p in sets[sp].values()])[0]
    check("added images vs valid/test: phash distance > 4", int((dist_matrix(eph, ephf, vt).min(1) <= PHASH_MAX_DIST).sum()) == 0, f"{len(ext)} added images checked")
    same = all(md5(p) == md5(V3 / sp / k / p.name) for sp in ("valid", "test") for k in ("images", "labels") for p in (CLEANED / sp / k).iterdir() if p.is_file())
    check("valid/test identical to data/cleaned (checksum)", same)
    v2_train = {p.name for p in list_images(V2_DIR / "train" / "images")}
    others = [n for n in names_tr if n not in v2_train and not n.startswith("ext3_")]
    check("train = cleaned_v2 train + ext3_ files only", v2_train <= set(names_tr) and not others, f"{len(others)} unexpected")
    y3 = yaml.safe_load((V3 / "data.yaml").read_text())
    y2 = yaml.safe_load((V2_DIR / "data.yaml").read_text())
    check("data.yaml: relative paths, same class order as cleaned_v2",
          y3["names"] == y2["names"] == my_names and not any(str(y3[k]).startswith("/") for k in ("train", "val", "test")))
    print("VALIDATION of data/cleaned_v3")
    for n, st, d in rows:
        print(f"  [{st}] {n} {d}")
    print("images:", {sp: len(sets[sp]) for sp in SPLITS}, "| added ext3_:", len(ext))
    fails = [n for n, st, _ in rows if st == "FAIL"]
    print("FAILED CHECKS:", fails or "none")
    return 1 if fails else 0


def write_contact_sheets(chosen, cols=6, width=1600):
    from PIL import Image, ImageDraw
    out = {}
    groups = {"A_fridge_food_images_v14": [r for r in chosen if r["src"] == "fridge_food_images_v14"],
              "B_mango": [r for r in chosen if r["src"] == "fridge_v1i" and any(k[0] == "mango" for k in r["kept"])],
              "B_pomegranate": [r for r in chosen if r["src"] == "fridge_v1i" and any(k[0] == "pomegranate" for k in r["kept"])]}
    for name, rs in groups.items():
        rs = sorted(rs, key=lambda r: r["out_name"])
        pick = random.Random(V3_SEED).sample(rs, min(24, len(rs)))
        if not pick:
            continue
        tile = width // cols
        rows_n = (len(pick) + cols - 1) // cols
        sheet = Image.new("RGB", (tile * cols, tile * rows_n), (30, 30, 30))
        for i, r in enumerate(pick):
            with Image.open(r["path"]) as im:
                im = im.convert("RGB").resize((tile, tile))
            dr = ImageDraw.Draw(im)
            for c, x1, y1, x2, y2 in r["kept"]:
                dr.rectangle([x1 * tile, y1 * tile, x2 * tile, y2 * tile], outline=(255, 50, 50), width=2)
                dr.text((x1 * tile + 2, y1 * tile + 1), c, fill=(255, 255, 0))
            sheet.paste(im, ((i % cols) * tile, (i // cols) * tile))
        fn = V3 / f"_contact_{name}.jpg"
        sheet.save(fn, quality=88)
        out[name] = str(fn.relative_to(REPO))
    return out


def write_added_from_v3(funnel, added, before, after, my_names):
    L = []
    a = L.append
    a("# data/cleaned_v3: what was added and from where\n")
    a("v3 starts from `data/cleaned_v2` (copied: train, valid, test, data.yaml) and adds external images to **train only**, prefixed `ext3_`. "
      "`valid/` and `test/` are identical to `data/cleaned`. Real-fridge QA photos are not used. Rebuild with `python ml/add_external.py --v3 --overwrite`.\n")
    if CAP_OVERRIDES:
        a(f"Per-class cap overrides on included external boxes: {CAP_OVERRIDES} (default {CAP_DEFAULT}; mango and pomegranate {CAP_FRUIT}).\n")
    a("## New sources (v3)\n")
    for src, meta in V3_SOURCES.items():
        cfg = yaml.safe_load((meta["dir"] / "data.yaml").read_text())
        rf = cfg.get("roboflow", {})
        a(f"### {src}\n")
        a(f"- URL: {rf.get('url', 'not given in the source data.yaml')}")
        a(f"- Roboflow workspace/project: `{rf.get('workspace')}/{rf.get('project')}`, version {rf.get('version')}.")
        a(f"- License: **{rf.get('license')}** per Roboflow (https://creativecommons.org/licenses/by/4.0/); **check original** for the underlying photos. "
          "Attribution: provided by a Roboflow user; changes made: boxes converted to this project's classes and a subset selected.")
        f = funnel[src]
        a(f"- Source files {f['files']} ({f['source_images']} source images); added to train: **{f['added_images']}** images.\n")
    a("## Mapping used (source class -> my class; None = skipped, box dropped)\n")
    for src in V3_SOURCES:
        a(f"### {src}\n")
        a("| Source class | Maps to |\n|---|---|")
        for k, v in EXTERNAL_V3_MAP[src].items():
            a(f"| {k} | {v} |")
        if src in EXTERNAL_V3_KEEP_ONLY:
            a("| every other class | dropped (keep-only source) |")
        a("")
    a("## Boxes added per class (train)\n")
    srcs = list(V3_SOURCES)
    cls = sorted({c for s in added.values() for c in s})
    a("| Class | v2 train boxes | " + " | ".join(srcs) + " | v3 train boxes |\n|---|---|" + "---|" * (len(srcs) + 1))
    for c in cls:
        a(f"| {c} | {before.get(c, 0)} | " + " | ".join(str(added[s].get(c, 0)) for s in srcs) + f" | {after.get(c, 0)} |")
    a("")
    prev = (V2_DIR / "ADDED_FROM.md").read_text()
    a("---\n\n## Earlier additions (carried over from data/cleaned_v2)\n")
    a(prev.split("\n", 1)[1] if prev.startswith("#") else prev)
    (V3 / "ADDED_FROM.md").write_text("\n".join(L) + "\n")


def write_report_v3(funnel, added, before, after, rows, samples, sheets, srcs, n_added):
    L = []
    a = L.append
    a("# External sources audit, v3 (fridge food images v14 + fridge v1i)\n")
    a("Produced by `ml/add_external.py --v3`. `data/cleaned` and `data/cleaned_v2` were only read; the build is `data/cleaned_v3` (train only, prefix `ext3_`). "
      "No photos are in this report; contact sheets are untracked files in `data/cleaned_v3/`.\n")
    a("## Parameters\n")
    a(f"seed {V3_SEED}; per-class cap of included boxes {CAP_DEFAULT} (mango and pomegranate {CAP_FRUIT}"
      + (f"; overrides {CAP_OVERRIDES}" if CAP_OVERRIDES else "") + f"); boxes under {100 * MIN_SIDE_V3:.1f}% width or height dropped; "
      f"an image is dropped if a skipped-class box covers at least {100 * LARGE_FRAC:.0f}% of the image or overlaps a kept box (intersection over the smaller box >= {OVERLAP_IOA}); "
      f"images whose only kept box covers more than {100 * MAX_SINGLE_BOX:.0f}% are dropped; over the cap, images with boxes under {100 * SMALL_BOX:.0f}% of the image are preferred, then random; "
      "phash Hamming distance <= 4 incl. horizontal flip.\n")
    for src in V3_SOURCES:
        f = funnel[src]
        a(f"## {src}\n")
        a(f"Roboflow preprocessing/augmentation per its README: " + ("auto-orient, resize 640x640 stretch, **augmentation: 3 versions per source image, rotation -15 to +15 degrees**." if src == "fridge_food_images_v14" else "no augmentation listed; filenames still show several files per source image.") + "\n")
        a("| Class | train | valid | test | Maps to |\n|---|---|---|---|---|")
        for cname, c in f["class_box_counts"].items():
            tgt = EXTERNAL_V3_MAP[src].get(cname, "dropped (keep-only)" if src in EXTERNAL_V3_KEEP_ONLY else "NOT IN MAP")
            a(f"| {cname} | {c.get('train', 0)} | {c.get('valid', 0)} | {c.get('test', 0)} | {tgt} |")
        if f["skipped_class_boxes_all_files"]:
            a("\nBoxes in skipped classes (all files): " + ", ".join(f"{k} {v}" for k, v in f["skipped_class_boxes_all_files"].items()) + ". `meat` and `green leaves` need Ashton's approval.")
        a(f"\nPolygon label lines converted to boxes: {f['polygon_lines']}. Tiny boxes dropped: {f['tiny_boxes_dropped']}. Source classes not in the map: {f['unmapped_source_classes'] or 'none'}.\n")
        a("| Step | Images |\n|---|---|")
        a(f"| files in the source | {f['files']} |")
        a(f"| distinct source images (base name before `.rf.`) | {f['source_images']} |")
        for k, v in f["reasons"].items():
            a(f"| dropped: {k} | {v} |")
        a(f"| files surviving the label filters | {f['after_filters_files']} (in {f['after_filters_sources']} source images) |")
        a(f"| one copy per source image | {f['one_per_source']} |")
        d = f["dedupe"]
        a(f"| dropped: phash match with data/cleaned / data/cleaned_v2 / data/real_fridge | {d['data/cleaned']} / {d['data/cleaned_v2']} / {d['data/real_fridge (held-out QA photos)']} (any: {d['any_reference']}) |")
        a(f"| dropped: near-duplicate of another external image | {d['within_external']} |")
        a(f"| remaining before caps | {d['remaining']} |")
        a(f"| skipped for the per-class caps | {f['cap_skipped']} |")
        a(f"| **added to train** | **{f['added_images']}** |\n")
    a("## Train boxes per class: v2 vs v3\n")
    allc = sorted(set(before) | set(after))
    a("| Class | v2 train | " + " | ".join(f"+{s}" for s in V3_SOURCES) + " | v3 train |\n|---|---|" + "---|" * (len(V3_SOURCES) + 1))
    for c in allc:
        a(f"| {c}{' (weak)' if c in ('chocolate', 'goat_cheese', 'ham', 'mango', 'pomegranate') else ''} | {before.get(c, 0)} | "
          + " | ".join(str(added[s].get(c, 0)) for s in V3_SOURCES) + f" | {after.get(c, 0)} |")
    tot_b, tot_a = sum(before.values()), sum(after.values())
    n_v2 = len(list_images(V2_DIR / "train" / "images"))
    a(f"\nTotal train boxes {tot_b} -> {tot_a}; train images {n_v2} -> {n_v2 + n_added} (valid and test unchanged).\n")
    a("## Mango and pomegranate sample files (for checking by eye)\n")
    for cname, fs in samples.items():
        a(f"**{cname}** ({len(fs)} files):\n")
        for x in fs:
            a(f"- `{x}`")
        a("")
    if sheets:
        a("Untracked contact sheets of the selected images: " + ", ".join(f"`{v}`" for v in sheets.values()) + ".\n")
    a("## Validation\n")
    a("| Check | Result | Detail |\n|---|---|---|")
    for n, s, dtl in rows:
        a(f"| {n} | {s} | {dtl} |")
    REPORT_V3.write_text("\n".join(L) + "\n")


if __name__ == "__main__":
    main()
