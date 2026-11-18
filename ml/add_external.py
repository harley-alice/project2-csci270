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
                            load_dataset, phashes)

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
    ap.add_argument("--overwrite", action="store_true", help="rebuild data/cleaned_v2 if it exists")
    a = ap.parse_args()

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


if __name__ == "__main__":
    main()
