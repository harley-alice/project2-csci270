"""Audit the two external Roboflow datasets before any of them is used for training (read-only).

Reads data/external/{refrigerator_contents,objects_inside_a_fridge} and the frozen data/cleaned splits, and writes
ml/runs/external_audit/{report.md,results.json} plus an untracked contact sheet per dataset
(data/external/<name>/_contact.jpg). Nothing under data/cleaned is modified.

Conventions reused from ml/clean_and_merge.py: 64-bit phash, Hamming distance <= 4 counted as a near-duplicate
(minimum over the image and its horizontal flip), complete-linkage scene clusters with seed 0.

Usage:  python ml/audit_external.py
"""
import json
import random
import re
from collections import Counter, defaultdict
from pathlib import Path

import imagehash
import numpy as np
import yaml
from PIL import Image, ImageDraw

REPO = Path(__file__).resolve().parents[1]
DATA = REPO / "data"
EXT = DATA / "external"
CLEANED = DATA / "cleaned"
OUT = REPO / "ml" / "runs" / "external_audit"
SEED = 0
PHASH_MAX_DIST = 4
SPLITS = ["train", "valid", "test"]
IMG_EXT = {".jpg", ".jpeg", ".png", ".bmp", ".webp"}
BUCKETS = [("<0.5%", 0.0, 0.005), ("0.5-2%", 0.005, 0.02), ("2-8%", 0.02, 0.08), (">8%", 0.08, 1.01)]
WEAK = ["chocolate", "goat_cheese", "ham", "mango", "pomegranate"]
WATCH = ["bread", "cheese", "egg", "milk", "butter", "yogurt"]
SOURCES = {
    "refrigerator_contents": {"folder": "Fridgecontents", "workspace": "new-workspace-32uyj",
                              "project": "refridgerator-contents-detection"},
    "objects_inside_a_fridge": {"folder": "Objinsidefridge", "workspace": "shounak-mishra",
                                "project": "objects-inside-a-fridge"},
}

# Proposed mapping: external class -> (my class or None, status, reason). Status "ASK" = NEEDS MY APPROVAL.
MAPPING = {
    "refrigerator_contents": {
        "banana": ("banana", "ok", "same food"),
        "bread": ("bread", "ok", "same food"),
        "eggs": ("egg", "ASK", "per-egg boxes like mine (checked on 12 of my egg images and the contact sheet), but close-up scale: median box 5.56% vs my 1.56%"),
        "milk": ("milk", "ok", "same food"),
        "potato": ("potato", "ok", "same food"),
        "spinach": ("spinach", "ok", "same food"),
        "tomato": ("tomato", "ok", "same food"),
    },
    "objects_inside_a_fridge": {
        "bottle": (None, "ok", "generic bottle (2 boxes); no matching class"),
        "bread": ("bread", "ok", "same food (1 box)"),
        "chesse": ("cheese", "ok", "typo of cheese"),
        "chocolate": ("chocolate", "ok", "same food (weak class)"),
        "cold drinks": (None, "ok", "drinks are not in the 38 classes (my map also drops soda_can)"),
        "egg tray": (None, "ASK", "one box covers a whole tray (my egg boxes are per egg), so mapping it to egg would teach a different box shape; proposed None"),
        "energy drinks": (None, "ok", "drinks are not in the 38 classes"),
        "honey": ("jar", "ASK", "honey container; my jar class was relabelled from catch-all 'others' boxes"),
        "jam": ("jar", "ASK", "jam container; same question as honey"),
        "ketchup": ("jar", "ASK", "ketchup bottle/jar; same question as honey"),
        "nan": (None, "ASK", "unnamed class: check the contact sheet before deciding"),
        "softdrinks": (None, "ok", "drinks are not in the 38 classes"),
        "spices": (None, "ASK", "spice jars at 0.43% median area (tiny, below my jar median of 3.93%); proposed None"),
        "utensil": (None, "ok", "not a food"),
    },
}


# ----------------------------------------------------------------------------- loading
def parse_label(path):
    """Return (boxes [(cls, xc, yc, w, h)], n_polygon_lines). Polygon lines are converted to their bounding box."""
    boxes, poly = [], 0
    if not path.exists():
        return boxes, poly
    for line in path.read_text().splitlines():
        v = line.split()
        if not v:
            continue
        if len(v) == 5:
            c, xc, yc, w, h = int(v[0]), *map(float, v[1:])
        elif len(v) >= 7 and (len(v) - 1) % 2 == 0:
            xs, ys = list(map(float, v[1::2])), list(map(float, v[2::2]))
            x1, x2, y1, y2 = min(xs), max(xs), min(ys), max(ys)
            c, xc, yc, w, h = int(v[0]), (x1 + x2) / 2, (y1 + y2) / 2, x2 - x1, y2 - y1
            poly += 1
        else:
            continue
        boxes.append((c, xc, yc, w, h))
    return boxes, poly


def phashes(path):
    with Image.open(path) as im:
        im = im.convert("RGB")
        return (np.array(imagehash.phash(im).hash, dtype=bool).ravel(),
                np.array(imagehash.phash(im.transpose(Image.FLIP_LEFT_RIGHT)).hash, dtype=bool).ravel())


def load_dataset(name):
    d = EXT / name
    cfg = yaml.safe_load((d / "data.yaml").read_text())
    names = cfg["names"]
    recs, poly = [], 0
    for sp in SPLITS:
        for p in sorted((d / sp / "images").iterdir()):
            if p.suffix.lower() not in IMG_EXT:
                continue
            boxes, pl = parse_label(d / sp / "labels" / f"{p.stem}.txt")
            poly += pl
            with Image.open(p) as im:
                size = im.size
            ph, phf = phashes(p)
            base = re.sub(r"_(jpg|jpeg|png)\.rf\.[0-9a-f]+$", "", p.stem)
            recs.append({"path": p, "split": sp, "stem": p.stem, "base": base, "size": size, "boxes": boxes, "ph": ph, "phf": phf})
    return cfg, names, recs, poly


def dist_matrix(a, af, b):
    """Min Hamming distance (incl. horizontal flip of a) between every row of a and every row of b."""
    out = np.empty((len(a), len(b)), dtype=np.int16)
    for i in range(len(a)):
        out[i] = np.minimum((b != a[i]).sum(1), (b != af[i]).sum(1))
    return out


def clusters_complete_linkage(PH, PHf):
    """Greedy complete-linkage (same logic as ml/clean_and_merge.build_clusters), seeded order."""
    m = len(PH)
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
    return [sorted(c) for c in members if c], D


# ----------------------------------------------------------------------------- helpers
def bucket_shares(areas):
    a = np.asarray(areas)
    return {b[0]: float(((a >= b[1]) & (a < b[2])).mean()) for b in BUCKETS}


def contact_sheet(name, recs, names, n=24, cols=6, width=1600):
    rnd = random.Random(SEED)
    pick = rnd.sample(recs, min(n, len(recs)))
    tile = width // cols
    rows = (len(pick) + cols - 1) // cols
    sheet = Image.new("RGB", (tile * cols, tile * rows), (30, 30, 30))
    for i, r in enumerate(pick):
        with Image.open(r["path"]) as im:
            im = im.convert("RGB").resize((tile, tile))
        dr = ImageDraw.Draw(im)
        for c, xc, yc, w, h in r["boxes"]:
            box = [(xc - w / 2) * tile, (yc - h / 2) * tile, (xc + w / 2) * tile, (yc + h / 2) * tile]
            dr.rectangle(box, outline=(255, 50, 50), width=2)
            dr.text((box[0] + 2, box[1] + 1), names[c], fill=(255, 255, 0))
        sheet.paste(im, ((i % cols) * tile, (i // cols) * tile))
    sheet.save(EXT / name / "_contact.jpg", quality=88)
    return [r["stem"][:40] for r in pick]


def pct(x):
    return f"{100 * x:.1f}%"


# ----------------------------------------------------------------------------- main
def main():
    OUT.mkdir(parents=True, exist_ok=True)
    my_names = yaml.safe_load((CLEANED / "data.yaml").read_text())["names"]
    cid = {n: i for i, n in enumerate(my_names)}

    # frozen data/cleaned: hashes, box counts and size shares (read-only)
    print("hashing data/cleaned ...", flush=True)
    my = {sp: {"ph": [], "phf": [], "names": []} for sp in SPLITS}
    my_boxes = {sp: Counter() for sp in SPLITS}
    my_train_areas = []
    for sp in SPLITS:
        for p in sorted((CLEANED / sp / "images").iterdir()):
            if p.suffix.lower() not in IMG_EXT:
                continue
            ph, phf = phashes(p)
            my[sp]["ph"].append(ph)
            my[sp]["phf"].append(phf)
            my[sp]["names"].append(p.name)
            for line in (CLEANED / sp / "labels" / f"{p.stem}.txt").read_text().splitlines():
                v = line.split()
                if len(v) == 5:
                    my_boxes[sp][my_names[int(v[0])]] += 1
                    if sp == "train":
                        my_train_areas.append(float(v[3]) * float(v[4]))
        my[sp]["ph"], my[sp]["phf"] = np.stack(my[sp]["ph"]), np.stack(my[sp]["phf"])
    egg_areas = []
    for p in (CLEANED / "train" / "labels").glob("*.txt"):
        for line in p.read_text().splitlines():
            v = line.split()
            if len(v) == 5 and my_names[int(v[0])] == "egg":
                egg_areas.append(float(v[3]) * float(v[4]))
    my_egg_med = float(np.median(egg_areas))
    jar_areas = []
    for p in (CLEANED / "train" / "labels").glob("*.txt"):
        for line in p.read_text().splitlines():
            v = line.split()
            if len(v) == 5 and my_names[int(v[0])] == "jar":
                jar_areas.append(float(v[3]) * float(v[4]))

    R = {"datasets": {}, "my_train": {"images": len(my["train"]["names"]), "boxes": dict(my_boxes["train"]),
                                      "bucket_share": bucket_shares(my_train_areas), "median_area": float(np.median(my_train_areas)),
                                      "egg_median_area": my_egg_med, "jar_median_area": float(np.median(jar_areas))},
         "my_images": {sp: len(my[sp]["names"]) for sp in SPLITS}}

    for name in SOURCES:
        print("auditing", name, flush=True)
        cfg, names, recs, poly = load_dataset(name)
        info = {"source": SOURCES[name], "license": cfg.get("roboflow", {}).get("license"), "version": cfg.get("roboflow", {}).get("version"),
                "class_names": names, "polygon_lines": poly}
        info["images_per_split"] = dict(Counter(r["split"] for r in recs))
        info["image_sizes"] = {f"{w}x{h}": n for (w, h), n in Counter(r["size"] for r in recs).items()}
        cls_counts, cls_by_split, cls_area = Counter(), defaultdict(Counter), defaultdict(list)
        all_areas = []
        for r in recs:
            for c, xc, yc, w, h in r["boxes"]:
                cls_counts[names[c]] += 1
                cls_by_split[names[c]][r["split"]] += 1
                cls_area[names[c]].append(w * h)
                all_areas.append(w * h)
        info["boxes_per_class"] = {k: {"total": v, "by_split": dict(cls_by_split[k]), "median_area": float(np.median(cls_area[k]))} for k, v in cls_counts.most_common()}
        info["total_boxes"] = sum(cls_counts.values())
        info["bucket_share"] = bucket_shares(all_areas)
        info["median_area"] = float(np.median(all_areas))
        info["images_without_boxes"] = sum(1 for r in recs if not r["boxes"])

        # Roboflow augmentation copies: files sharing a base name
        groups = defaultdict(list)
        for i, r in enumerate(recs):
            groups[r["base"]].append(i)
        multi = {b: ix for b, ix in groups.items() if len(ix) > 1}
        info["augmentation_groups"] = {"base_names": len(groups), "groups_with_multiple_files": len(multi),
                                       "extra_copies": sum(len(ix) - 1 for ix in multi.values()),
                                       "groups_spanning_splits": sum(1 for ix in multi.values() if len({recs[i]["split"] for i in ix}) > 1)}

        # duplicates and scenes
        PH, PHf = np.stack([r["ph"] for r in recs]), np.stack([r["phf"] for r in recs])
        cl, D = clusters_complete_linkage(PH, PHf)
        np.fill_diagonal(D, 99)
        info["within_dataset"] = {"images_with_near_duplicate": int((D.min(1) <= PHASH_MAX_DIST).sum()), "scene_clusters": len(cl),
                                  "multi_image_clusters": sum(1 for c in cl if len(c) > 1), "largest_cluster": max(len(c) for c in cl)}
        vs, min_to = {}, {}
        for sp in SPLITS:
            Dm = dist_matrix(PH, PHf, my[sp]["ph"])
            min_to[sp] = Dm.min(1)
            vs[sp] = {"images_within_4": int((min_to[sp] <= PHASH_MAX_DIST).sum()), "images_within_2": int((min_to[sp] <= 2).sum()),
                      "min_distance_hist": {"0": int((min_to[sp] == 0).sum()), "1-2": int(((min_to[sp] >= 1) & (min_to[sp] <= 2)).sum()),
                                            "3-4": int(((min_to[sp] >= 3) & (min_to[sp] <= 4)).sum()), "5-8": int(((min_to[sp] >= 5) & (min_to[sp] <= 8)).sum()),
                                            ">8": int((min_to[sp] > 8).sum())}}
        info["vs_cleaned"] = vs
        near_any = np.minimum.reduce([min_to[sp] for sp in SPLITS]) <= PHASH_MAX_DIST
        near_vt = np.minimum(min_to["valid"], min_to["test"]) <= PHASH_MAX_DIST
        info["vs_cleaned"]["any_split_within_4"] = int(near_any.sum())
        info["vs_cleaned"]["valid_or_test_within_4"] = int(near_vt.sum())

        # keepers after build-time exclusions: one file per augmentation base name, none near-duplicate of data/cleaned
        keep_idx = []
        for b, ix in groups.items():
            ok = [i for i in ix if not near_any[i]]
            if ok:
                keep_idx.append(sorted(ok)[0])
        info["eligible_images_after_exclusions"] = len(keep_idx)
        elig = Counter(names[c] for i in keep_idx for c, *_ in recs[i]["boxes"])
        for k in info["boxes_per_class"]:
            info["boxes_per_class"][k]["eligible_unique_boxes"] = elig.get(k, 0)
        info["augmentation_groups"]["files_per_base"] = sorted(len(ix) for ix in groups.values())

        # mapping scenarios and policies
        mp = MAPPING[name]
        missing = [n for n in names if n not in mp]
        assert not missing, f"unmapped external classes: {missing}"
        info["mapping"] = {k: {"to": v[0], "status": v[1], "reason": v[2]} for k, v in mp.items()}
        scen = {"proposed": lambda c: mp[names[c]][0],
                "conservative": lambda c: mp[names[c]][0] if mp[names[c]][1] == "ok" else None}
        pol = {}
        for sc_name, f in scen.items():
            for pol_name, rule in (("a_all_boxes_map", lambda fr: fr == 1.0), ("b_90pct_map", lambda fr: fr >= 0.9)):
                added, kept, dropped_boxes = Counter(), 0, 0
                for i in keep_idx:
                    bx = recs[i]["boxes"]
                    if not bx:
                        continue
                    mapped = [f(c) for c, *_ in bx]
                    fr = sum(m is not None for m in mapped) / len(bx)
                    if fr > 0 and rule(fr):
                        kept += 1
                        for m in mapped:
                            if m is None:
                                dropped_boxes += 1
                            else:
                                added[m] += 1
                pol[f"{sc_name}/{pol_name}"] = {"images_kept": kept, "boxes_added": dict(added), "unlabeled_boxes_left_in_kept_images": dropped_boxes}
        info["policies"] = pol
        R["datasets"][name] = info
        R["datasets"][name]["contact_sheet_images"] = contact_sheet(name, recs, names)

    (OUT / "results.json").write_text(json.dumps(R, indent=2, default=float))
    write_report(R, my_names)
    print("wrote", (OUT / "report.md").relative_to(REPO))


def recommendations(R):
    rc, oi, mt = R["datasets"]["refrigerator_contents"], R["datasets"]["objects_inside_a_fridge"], R["my_train"]
    pa = rc["policies"]["proposed/a_all_boxes_map"]
    pc = rc["policies"]["conservative/a_all_boxes_map"]
    doubled = [c for c in ("bread", "banana", "potato", "spinach") if pa["boxes_added"].get(c, 0) >= mt["boxes"].get(c, 0)]
    covered = [c for c in ("egg", "milk", "tomato")]
    zero = [c for c in WEAK + ["cheese", "butter", "yogurt", "jar"] if pa["boxes_added"].get(c, 0) == 0]
    ag, oiag = rc["augmentation_groups"], oi["augmentation_groups"]
    po = oi["policies"]["proposed/b_90pct_map"]
    out = []
    out.append(f"**refrigerator_contents: use a subset.** {rc['eligible_images_after_exclusions']} eligible images, no augmentation copies "
               f"({ag['extra_copies']}), no near-duplicate of my valid or test ({rc['vs_cleaned']['valid']['images_within_4']} and {rc['vs_cleaned']['test']['images_within_4']}), "
               f"CC BY 4.0 (attribution required). All 7 classes map to my classes; the only ASK row is `eggs` (per-egg boxes, so compatible). "
               f"It more than doubles my train boxes for {', '.join(doubled)} (policy a adds "
               + ", ".join(f"{c} +{pa['boxes_added'].get(c, 0)} on {mt['boxes'].get(c, 0)}" for c in doubled)
               + f"), while {', '.join(covered)} already have "
               + ", ".join(str(mt['boxes'].get(c, 0)) for c in covered) + " train boxes. "
               f"Against that: {pct(rc['bucket_share']['>8%'])} of its boxes cover more than 8% of the image (my train {pct(mt['bucket_share']['>8%'])}) and only "
               f"{pct(rc['bucket_share']['<0.5%'])} are under 0.5% (my train {pct(mt['bucket_share']['<0.5%'])}), and the images are stock photos, "
               f"so it pushes the box-size distribution away from cluttered real fridge photos. It adds 0 boxes to {', '.join(zero)}. "
               f"Suggested cap: the default 150 images, taken from images that contain bread, banana, potato or spinach and have two or more boxes. "
               f"Dropping the ASK class (`eggs`) costs {rc['policies']['proposed/a_all_boxes_map']['images_kept'] - pc['images_kept']} of {pa['images_kept']} images under policy (a).")
    out.append(f"**objects_inside_a_fridge: skip.** It has {oiag['base_names']} unique photos behind {oi['images_per_split']['train'] + oi['images_per_split']['valid'] + oi['images_per_split']['test']} files "
               f"({oiag['extra_copies']} extra copies; {oiag['groups_spanning_splits']} of {oiag['groups_with_multiple_files']} multi-file groups span splits), all from one fridge. "
               f"{'No image passes' if po['images_kept'] == 0 else str(po['images_kept']) + ' image(s) pass'} policy (b) with the proposed mapping, and it adds nothing to the weak classes: "
               f"`chocolate` has {oi['boxes_per_class']['chocolate']['total']} boxes in the files but {oi['boxes_per_class']['chocolate']['eligible_unique_boxes']} in the unique photos, "
               f"and those photos' drinks, spices and utensils would be left unlabeled. It matches the real-fridge box size better "
               f"({pct(oi['bucket_share']['<0.5%'])} of boxes under 0.5%), but one fridge and 10 scenes would mainly teach that fridge.")
    jar_added = sum(d["policies"]["proposed/b_90pct_map"]["boxes_added"].get("jar", 0) for d in R["datasets"].values())
    out.append(f"Neither dataset adds `butter`, `cream` or `yogurt`, and together they add {jar_added} `jar` boxes under policy (b), the classes that the "
               "real-fridge diagnostics (branch `ml/real-fridge-diagnostics`) found weakest. Additional real fridge photos, split by fridge, are likely worth more than either source.")
    return "\n\n".join(out) + "\n"


def write_report(R, my_names):
    L = []
    a = L.append
    mt = R["my_train"]
    a("# External dataset audit (Phase 1, read-only)\n")
    a("Produced by `ml/audit_external.py`. `data/cleaned/` was only read. Numbers are also written to `results.json` (kept locally, not committed). "
      "No photos are included here; each dataset has an untracked `_contact.jpg` under `data/external/<name>/`.\n")
    for name, d in R["datasets"].items():
        s = d["source"]
        a(f"## {name}\n")
        a(f"Roboflow `{s['workspace']}/{s['project']}`, version {d['version']}, license **{d['license']}**. "
          f"Images per split: {d['images_per_split']}. Image sizes: {d['image_sizes']}. Boxes: {d['total_boxes']}; "
          f"images without boxes: {d['images_without_boxes']}; polygon label lines converted to boxes: {d['polygon_lines']}.\n")
        a("| Class | Boxes | train/valid/test | Median box area | Boxes in eligible unique images |\n|---|---|---|---|---|")
        for k, v in d["boxes_per_class"].items():
            bs = v["by_split"]
            a(f"| {k} | {v['total']} | {bs.get('train', 0)}/{bs.get('valid', 0)}/{bs.get('test', 0)} | {100 * v['median_area']:.2f}% | {v['eligible_unique_boxes']} |")
        ag = d["augmentation_groups"]
        a(f"\n**Augmentation copies:** {ag['base_names']} base names; {ag['groups_with_multiple_files']} groups have more than one file "
          f"({ag['extra_copies']} extra copies); {ag['groups_spanning_splits']} groups span more than one split. Files per base name: {ag['files_per_base'] if ag['groups_with_multiple_files'] else 'all 1'}.\n")
        w, vc = d["within_dataset"], d["vs_cleaned"]
        a(f"**Duplicates and scenes:** within the dataset, {w['images_with_near_duplicate']} images have a near-duplicate (phash <= 4 incl. flip); "
          f"complete-linkage scene clusters: {w['scene_clusters']} ({w['multi_image_clusters']} with more than one image, largest {w['largest_cluster']}).")
        a(f"Against `data/cleaned`: within distance 4 of train {vc['train']['images_within_4']}, **valid {vc['valid']['images_within_4']}, "
          f"test {vc['test']['images_within_4']}** (these must be excluded); any split {vc['any_split_within_4']}. "
          f"Eligible after exclusions (one file per base name, none near-duplicate of `data/cleaned`): **{d['eligible_images_after_exclusions']}** images.\n")
        a("Minimum distance to `data/cleaned` (images per bucket):\n")
        a("| Split | 0 | 1-2 | 3-4 | 5-8 | >8 |\n|---|---|---|---|---|---|")
        for sp in ("train", "valid", "test"):
            h = vc[sp]["min_distance_hist"]
            a(f"| {sp} | {h['0']} | {h['1-2']} | {h['3-4']} | {h['5-8']} | {h['>8']} |")
        a("")
    a("## Box-size distribution (share of boxes by area as a share of the image)\n")
    a("| Bucket | " + " | ".join(R["datasets"]) + " | my data/cleaned train |\n|---|" + "---|" * (len(R["datasets"]) + 1))
    for b in [x[0] for x in BUCKETS]:
        a(f"| {b} | " + " | ".join(pct(d["bucket_share"][b]) for d in R["datasets"].values()) + f" | {pct(mt['bucket_share'][b])} |")
    a("\nMedian box area: " + ", ".join(f"{n} {100 * d['median_area']:.2f}%" for n, d in R["datasets"].items())
      + f", my train {100 * mt['median_area']:.2f}%. My `egg` boxes: median {100 * mt['egg_median_area']:.2f}%; my `jar` boxes: median {100 * mt['jar_median_area']:.2f}%.\n")
    a("## What the contact sheets show (reviewed by eye, 24 random images each)\n")
    a("- **refrigerator_contents:** stock product photography, not fridge interiors: one to a handful of items on plain, white or coloured "
      "backgrounds, with stock-photo watermarks, close-ups and very large boxes. Only a few images show items in a fridge. Eggs are boxed one by one, "
      "like my egg boxes. Images were stretched to 640x640, so shapes are distorted.")
    a("- **objects_inside_a_fridge:** one fridge seen through a wide-angle camera, repeated in all 51 images. Many frames are visibly rotated, "
      "sheared or re-lit copies of the same few shots, despite the README saying no augmentation. Dense scenes with 10 to 15 small boxes "
      "(drinks, spices, jars, chocolate). The `egg tray` box covers a whole transparent tray, and `nan` marks small unnamed items.\n")
    a("My own `egg` boxes (12 train images checked by eye) are drawn per egg or per small group. One of the 12 shows a large `egg` box around a tomato and "
      "packaged goods, which looks like a label error in `data/cleaned` worth a separate check.\n")
    a("## Proposed class mapping\n")
    a("Status `ASK` = **NEEDS MY APPROVAL**. `None` means the box is dropped.\n")
    for name, d in R["datasets"].items():
        a(f"### {name}\n")
        a("| External class | Boxes | Maps to | Status | Reason |\n|---|---|---|---|---|")
        for k, v in d["mapping"].items():
            st = "NEEDS MY APPROVAL" if v["status"] == "ASK" else "ok"
            a(f"| {k} | {d['boxes_per_class'].get(k, {}).get('total', 0)} | {v['to']} | {st} | {v['reason']} |")
        a("")
    a("## Policies: images kept and boxes added\n")
    a("Policy (a): keep images where every box maps. Policy (b): keep images where at least 90% of boxes map. "
      "'proposed' applies the mapping above (each ASK row goes to its proposed target); 'conservative' treats every ASK row as None. "
      "Counts are after the exclusions (one file per augmentation base name, no near-duplicate of `data/cleaned`).\n")
    show = WEAK + WATCH
    for name, d in R["datasets"].items():
        a(f"### {name}\n")
        pols = d["policies"]
        touched = sorted({c for p in pols.values() for c in p["boxes_added"]}, key=lambda c: (c not in show, c))
        keys = list(pols)
        a("| Class | My train boxes | " + " | ".join(k.replace("/", " ") for k in keys) + " |\n|---|---|" + "---|" * len(keys))
        a("| **images kept** | " + f"{mt['images']} images | " + " | ".join(str(pols[k]["images_kept"]) for k in keys) + " |")
        for c in show:
            a(f"| {c}{' (weak)' if c in WEAK else ''} | {mt['boxes'].get(c, 0)} | " + " | ".join(str(pols[k]["boxes_added"].get(c, 0)) for k in keys) + " |")
        for c in touched:
            if c not in show:
                a(f"| {c} | {mt['boxes'].get(c, 0)} | " + " | ".join(str(pols[k]["boxes_added"].get(c, 0)) for k in keys) + " |")
        a("| unlabeled boxes left in kept images | | " + " | ".join(str(pols[k]["unlabeled_boxes_left_in_kept_images"]) for k in keys) + " |")
        a("")
    a("Risk: dropping an unmapped box (None) leaves that object unlabeled in a kept image, which teaches the model to treat it as background. "
      "The last row of each table counts those boxes.\n")
    a("## Recommendations\n")
    a(recommendations(R))
    (OUT / "report.md").write_text("\n".join(L) + "\n")


if __name__ == "__main__":
    main()
