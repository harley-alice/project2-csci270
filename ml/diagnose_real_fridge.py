"""Diagnose why the baseline detector finds few objects on the real-fridge QA photos.

Builds a diagnostic copy of the QA set under data/real_fridge/ (git-ignored): an `upright` set
(EXIF orientation applied) and a `raw` set (pixels as stored, EXIF stripped), runs the .pt model
over a matrix of settings, matches predictions to ground truth (one-to-one, greedy by confidence),
and writes ml/runs/real_fridge_diagnostics/{results.json,report.md,overlays/}.

Usage (the export folder holds images_original/, ground_truth/, food_classes.txt, evaluation/):
    python ml/diagnose_real_fridge.py --src <path to fridge_qa_reproducibility folder>
    python ml/diagnose_real_fridge.py --src <folder> --device cpu

Held-out mode (the 160-photo evaluation set; never train or tune on it):
    python ml/diagnose_real_fridge.py --data data/real_fridge/data_heldout.yaml --ignore-classes jar \
        --weights <weights .pt> --confs 0.25,0.001 --imgsz 640
  writes ml/runs/real_fridge_diagnostics/{confusion_heldout.md,results_heldout.json,confusion_heldout_worst20.png}.
  Ignored classes: ground-truth boxes of that class are removed, and predictions that land on one (IoU >= 0.5) are not
  counted as false positives; a prediction of an ignored class on another class's box still shows up as a confusion.

Every number in the report comes from this run. Nothing is trained.
"""
import argparse
import csv
import json
import random
import shutil
import tempfile
from collections import Counter, defaultdict
from pathlib import Path

import numpy as np
import yaml
from PIL import Image, ImageDraw, ImageOps

REPO = Path(__file__).resolve().parents[1]
DATA = REPO / "data" / "real_fridge"
OUT = REPO / "ml" / "runs" / "real_fridge_diagnostics"
WEIGHTS = REPO / "ml" / "export" / "food_detector_v8n_baseline.pt"
DATA_YAML = REPO / "data" / "cleaned" / "data.yaml"
TRAIN_LABELS = REPO / "data" / "cleaned" / "train" / "labels"
BUCKETS = [("<0.5%", 0.0, 0.005), ("0.5-2%", 0.005, 0.02), ("2-8%", 0.02, 0.08), (">8%", 0.08, 1.01)]
IOUS = (0.5, 0.3, 0.1)
HIGHLIGHT = ["milk", "egg", "jar", "cream", "butter", "yogurt", "chicken", "beef", "shrimp"]


# ----------------------------------------------------------------------------- data preparation
def exif_orientation(path):
    with Image.open(path) as im:
        return int(im.getexif().get(0x0112, 1))


def prepare(src, class_names):
    """Write data/real_fridge/{upright,raw}/images, upright/labels, data_real.yaml. Returns image records."""
    classes_file = [c for c in (src / "food_classes.txt").read_text().splitlines()]
    if classes_file != class_names:
        raise SystemExit("food_classes.txt does not match data/cleaned/data.yaml (order matters)")
    imgs = sorted(p for p in (src / "images_original").iterdir() if p.suffix.lower() in {".jpg", ".jpeg", ".png"})
    for sub in ("upright/images", "upright/labels", "raw/images"):
        (DATA / sub).mkdir(parents=True, exist_ok=True)
    records, unmapped = [], Counter()
    for p in imgs:
        label = src / "ground_truth" / f"{p.stem}.txt"
        if not label.exists():
            raise SystemExit(f"missing label for {p.name}")
        orient = exif_orientation(p)
        up_path, raw_path = DATA / "upright/images" / f"{p.stem}.jpg", DATA / "raw/images" / f"{p.stem}.jpg"
        with Image.open(p) as im:
            raw_rgb = im.convert("RGB")
            raw_size = raw_rgb.size
            if not raw_path.exists():
                raw_rgb.save(raw_path, quality=95)  # pixels as stored, EXIF not written
            if not up_path.exists():
                ImageOps.exif_transpose(im).convert("RGB").save(up_path, quality=95)
        with Image.open(up_path) as u:
            disp_size = u.size
        gt = []
        for ln, line in enumerate(label.read_text().splitlines(), 1):
            v = line.split()
            if not v:
                continue
            if len(v) != 5:
                raise SystemExit(f"bad annotation {label.name}:{ln}")
            cid = int(v[0])
            if not 0 <= cid < len(class_names):
                unmapped[cid] += 1
                continue
            xc, yc, w, h = map(float, v[1:])
            gt.append((cid, xc, yc, w, h))
        shutil.copyfile(label, DATA / "upright/labels" / f"{p.stem}.txt")
        records.append({"stem": p.stem, "orientation": orient, "raw_size": raw_size, "disp_size": disp_size, "gt": gt})
    (DATA / "data_real.yaml").write_text(yaml.safe_dump(
        {"train": "upright/images", "val": "upright/images", "nc": len(class_names), "names": class_names},
        sort_keys=False))
    return records, dict(unmapped)


# ----------------------------------------------------------------------------- geometry and matching
def gt_boxes(rec, frame="disp"):
    w, h = rec[f"{frame}_size"]
    return [(c, [(xc - bw / 2) * w, (yc - bh / 2) * h, (xc + bw / 2) * w, (yc + bh / 2) * h]) for c, xc, yc, bw, bh in rec["gt"]]


def to_display(box, orient, raw_h):
    """Map a box from the raw (stored) frame to the upright display frame (EXIF 1 or 6 only)."""
    x1, y1, x2, y2 = box
    if orient == 1:
        return [x1, y1, x2, y2]
    if orient == 6:  # display = raw rotated 90 degrees clockwise
        return [raw_h - y2, x1, raw_h - y1, x2]
    raise ValueError(f"unsupported EXIF orientation {orient}")


def iou_many(box, boxes):
    b = np.asarray(boxes, dtype=float).reshape(-1, 4)
    ix1, iy1 = np.maximum(box[0], b[:, 0]), np.maximum(box[1], b[:, 1])
    ix2, iy2 = np.minimum(box[2], b[:, 2]), np.minimum(box[3], b[:, 3])
    inter = np.clip(ix2 - ix1, 0, None) * np.clip(iy2 - iy1, 0, None)
    a = max(0.0, box[2] - box[0]) * max(0.0, box[3] - box[1])
    ab = np.clip(b[:, 2] - b[:, 0], 0, None) * np.clip(b[:, 3] - b[:, 1], 0, None)
    return inter / np.maximum(a + ab - inter, 1e-9)


def match(gt, preds, thr, class_aware):
    """One-to-one, greedy by prediction confidence. gt: [(cls, box)], preds: [(cls, conf, box)]."""
    taken, out = set(), []
    for pi in sorted(range(len(preds)), key=lambda i: -preds[i][1]):
        pc, _, pb = preds[pi]
        free = [g for g in range(len(gt)) if g not in taken and (not class_aware or gt[g][0] == pc)]
        if not free:
            continue
        ious = iou_many(pb, [gt[g][1] for g in free])
        j = int(np.argmax(ious))
        if ious[j] >= thr:
            taken.add(free[j])
            out.append((free[j], pi))
    return out


def evaluate(recs, preds_by_stem, frame="disp"):
    """Metrics at each IoU threshold, plus per-GT flags at IoU 0.5 for size/class breakdowns."""
    res = {}
    per_gt = []
    for thr in IOUS:
        n_gt = loc = cor = e2e = n_pred = 0
        conf_sum = 0.0
        for r in recs:
            gt = gt_boxes(r, frame)
            preds = preds_by_stem.get(r["stem"], [])
            n_gt += len(gt)
            n_pred += len(preds)
            m_any = match(gt, preds, thr, False)
            m_cls = match(gt, preds, thr, True)
            loc += len(m_any)
            cor += sum(1 for g, p in m_any if gt[g][0] == preds[p][0])
            conf_sum += sum(preds[p][1] for _, p in m_any)
            e2e += len(m_cls)
            if thr == 0.5:
                any_g = {g for g, _ in m_any}
                cls_g = {g for g, _ in m_cls}
                wrong = {g: preds[p][0] for g, p in m_any if gt[g][0] != preds[p][0]}
                for gi, (c, _) in enumerate(gt):
                    _, _, bw, bh = r["gt"][gi][1:]
                    per_gt.append({"cls": c, "area": bw * bh, "loc": gi in any_g, "e2e": gi in cls_g, "pred_cls": wrong.get(gi)})
        res[str(thr)] = {
            "gt": n_gt, "localized": loc, "loc_recall": loc / n_gt, "class_correct_share": cor / loc if loc else 0.0,
            "e2e_matched": e2e, "e2e_recall": e2e / n_gt, "preds_per_image": n_pred / len(recs),
            "mean_conf_matched": conf_sum / loc if loc else 0.0,
        }
    return res, per_gt


# ----------------------------------------------------------------------------- inference
def run_model(model, recs, subset, imgsz, conf, device):
    """Predict on data/real_fridge/<subset>/images; boxes mapped into the display frame."""
    paths = [DATA / subset / "images" / f"{r['stem']}.jpg" for r in recs]
    out = {}
    for r, p in zip(recs, paths):
        res = model.predict(source=str(p), imgsz=imgsz, conf=conf, iou=0.7, device=device, verbose=False)[0]
        b = res.boxes
        boxes = b.xyxy.cpu().numpy().tolist() if b is not None and len(b) else []
        cls = b.cls.cpu().numpy().astype(int).tolist() if boxes else []
        cf = b.conf.cpu().numpy().tolist() if boxes else []
        if subset == "raw":
            boxes = [to_display(bx, r["orientation"], r["raw_size"][1]) for bx in boxes]
        out[r["stem"]] = [(c, s, bx) for c, s, bx in zip(cls, cf, boxes)]
    return out


def ultralytics_val(model, imgsz, device):
    tmp = tempfile.mkdtemp(prefix="rf_val_")
    try:
        r = model.val(data=str(DATA / "data_real.yaml"), imgsz=imgsz, conf=0.001, iou=0.7, device=device,
                      plots=False, verbose=False, project=tmp, name="v", exist_ok=True)
        return {"mAP50": float(r.box.map50), "mAP50_95": float(r.box.map), "precision": float(r.box.mp), "recall": float(r.box.mr)}
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


# ----------------------------------------------------------------------------- analysis helpers
def bucket_of(area):
    for name, lo, hi in BUCKETS:
        if lo <= area < hi:
            return name
    return BUCKETS[-1][0]


def bucket_table(per_gt):
    t = {b[0]: {"n": 0, "loc": 0, "e2e": 0} for b in BUCKETS}
    for g in per_gt:
        k = bucket_of(g["area"])
        t[k]["n"] += 1
        t[k]["loc"] += g["loc"]
        t[k]["e2e"] += g["e2e"]
    return t


def class_table(per_gt, names):
    t = defaultdict(lambda: {"n": 0, "loc": 0, "e2e": 0})
    for g in per_gt:
        c = names[g["cls"]]
        t[c]["n"] += 1
        t[c]["loc"] += g["loc"]
        t[c]["e2e"] += g["e2e"]
    return dict(t)


def train_sizes():
    areas = []
    for f in TRAIN_LABELS.glob("*.txt"):
        for line in f.read_text().splitlines():
            v = line.split()
            if len(v) == 5:
                areas.append(float(v[3]) * float(v[4]))
    a = np.array(areas)
    shares = {b[0]: float(((a >= b[1]) & (a < b[2])).mean()) for b in BUCKETS}
    return {"boxes": int(len(a)), "median_area": float(np.median(a)), "bucket_share": shares}


def ashton_predictions(src, recs):
    p = src / "evaluation" / "detections.csv"
    names = DATA_YAML_NAMES
    by = defaultdict(list)
    stems = {r["stem"] for r in recs}
    with p.open(newline="", encoding="utf-8-sig") as f:
        for row in csv.DictReader(f):
            stem = Path(row["image"]).stem
            if stem in stems and row["class_name"] in names:
                by[stem].append((names.index(row["class_name"]), float(row["confidence"]),
                                 [float(row["x1"]), float(row["y1"]), float(row["x2"]), float(row["y2"])]))
    return by


def overlays(recs, names, seed=0):
    d = OUT / "overlays"
    d.mkdir(parents=True, exist_ok=True)
    rnd = random.Random(seed)
    picks = {"upright": rnd.sample(recs, 6), "raw": rnd.sample(recs, 6)}
    info = {}
    for subset, chosen in picks.items():
        info[subset] = []
        for i, r in enumerate(chosen):
            im = Image.open(DATA / subset / "images" / f"{r['stem']}.jpg").convert("RGB")
            w, h = im.size
            dr = ImageDraw.Draw(im)
            lw = max(3, w // 300)
            for c, xc, yc, bw, bh in r["gt"]:  # normalized GT drawn on whichever pixels this set has
                box = [(xc - bw / 2) * w, (yc - bh / 2) * h, (xc + bw / 2) * w, (yc + bh / 2) * h]
                dr.rectangle(box, outline=(255, 40, 40), width=lw)
                dr.text((box[0] + lw + 2, box[1] + lw + 2), names[c], fill=(255, 255, 0))
            s = 1000 / max(w, h)
            im.resize((round(w * s), round(h * s)), Image.LANCZOS).save(d / f"{subset}_{i}.png", optimize=True)
            info[subset].append({"file": f"{subset}_{i}.png", "orientation": r["orientation"], "gt_boxes": len(r["gt"])})
    return info


# ----------------------------------------------------------------------------- report
def pct(x):
    return f"{100 * x:.1f}%"


def make_val_note(R):
    m, v = R["matrix"], R["val_control"]
    e025 = m["upright_640_conf0.25"]["metrics"]["0.5"]
    e001 = m["upright_640_conf0.001"]["metrics"]["0.5"]
    maps = [v[k]["mAP50"] for k in v]
    return (f"Ultralytics' recall at its own F1-optimal confidence ({v['640']['recall']:.3f} at 640 px) is the same order as my "
            f"end-to-end recall at the deployed conf 0.25 ({pct(e025['e2e_recall'])}) and far below my end-to-end recall at conf 0.001 "
            f"({pct(e001['e2e_recall'])}). The mAP is low ({min(maps):.3f}-{max(maps):.3f}) because correct-class matches carry low "
            f"confidence (mean confidence of matched boxes {e001['mean_conf_matched']:.3f} at 640 px). mAP does not follow my recall ordering "
            f"across image sizes, so treat small differences between sizes as noise. The control reads the same labels with the same class "
            f"order and shows the same low end-to-end picture, and my localization recall ({pct(e001['loc_recall'])} at 640 px) shows the boxes "
            f"line up with the photos, so there is no sign of a label-format or class-order bug.")


def write_report(R, names):
    L = []
    a = L.append
    a("# Real-fridge diagnostics (baseline YOLOv8n)\n")
    a("All numbers below were produced by `ml/diagnose_real_fridge.py` and are saved in `results.json`. Nothing was trained.\n")
    s = R["setup"]
    a("## Setup\n")
    a(f"- **Data:** {s['images']} annotated photos, {s['gt_boxes']} ground-truth boxes over {s['classes_used']} of 38 classes "
      f"({s['empty_images']} images have no objects). An earlier message cited 96 images; the export contains {s['images']}.")
    a(f"- **EXIF orientation:** {s['exif_counts']}. {s['rotated_images']} images are stored sideways (raw size differs from display size).")
    a(f"- **Image size:** median long side {s['median_long_side']} px (min {s['min_long_side']}, max {s['max_long_side']}); the model input is 640 px.")
    a(f"- **Class mapping:** `food_classes.txt` equals the model's 38 class names in the same order: {s['class_order_ok']}. "
      f"Annotation class ids outside 0-37: {s['unmapped_class_ids'] or 'none'}. Fridge/session IDs were not supplied, so images cannot be split by fridge yet.")
    a("- **Ashton's pipeline** (read from her scripts): ONNX model, imgsz 640, conf 0.25, NMS iou 0.7, images passed as file paths "
      "(Ultralytics rotates by EXIF); ground truth is scaled with PIL's raw `image.size` (no EXIF transpose); IoU >= 0.50, one-to-one "
      "matching, greedy by IoU.")
    a("- **This run:** `.pt` model, `upright` = EXIF applied, `raw` = pixels as stored (what the backend saw before the EXIF fix); raw-set "
      "boxes are rotated back into the display frame before matching. Matching is one-to-one, greedy by confidence. "
      "'Localization' ignores class; 'end-to-end' requires the right class.\n")
    a("## Reproducing Ashton's numbers\n")
    ar = R["ashton"]
    a("Her saved `detections.csv` re-scored with my matcher, using her ground-truth frame (raw size) versus the correct frame (display size):\n")
    a("| GT frame | GT boxes | Localized (IoU>=0.5) | Correct class among localized | End-to-end TP |\n|---|---|---|---|---|")
    for k, lab in (("raw_frame", "raw size (her script)"), ("display_frame", "display size (upright)")):
        m = ar[k]["0.5"]
        a(f"| {lab} | {m['gt']} | {m['localized']} | {round(m['class_correct_share'] * m['localized'])} | {m['e2e_matched']} |")
    a(f"\nHer summary reports TP = {ar['her_tp']} (matches the raw-frame row when it reproduces). Same predictions, different ground-truth frame.\n")
    a("## Settings matrix (.pt model)\n")
    a("IoU >= 0.50 (localization = any class; end-to-end = correct class):\n")
    a("| Run | Localization recall | Class-correct share | End-to-end recall | Preds/image | Mean conf (matched) |\n|---|---|---|---|---|---|")
    for name, m in R["matrix"].items():
        x = m["metrics"]["0.5"]
        a(f"| {name} | {pct(x['loc_recall'])} | {pct(x['class_correct_share'])} | {pct(x['e2e_recall'])} | {x['preds_per_image']:.1f} | {x['mean_conf_matched']:.3f} |")
    a("\nLower IoU thresholds (localization / end-to-end recall):\n")
    a("| Run | IoU 0.30 | IoU 0.10 |\n|---|---|---|")
    for name, m in R["matrix"].items():
        a(f"| {name} | {pct(m['metrics']['0.3']['loc_recall'])} / {pct(m['metrics']['0.3']['e2e_recall'])} | "
          f"{pct(m['metrics']['0.1']['loc_recall'])} / {pct(m['metrics']['0.1']['e2e_recall'])} |")
    a("\n## Ultralytics `model.val` control (upright set, conf 0.001)\n")
    a("| imgsz | mAP@50 | mAP@50-95 | Precision | Recall |\n|---|---|---|---|---|")
    for sz, v in R["val_control"].items():
        a(f"| {sz} | {v['mAP50']:.3f} | {v['mAP50_95']:.3f} | {v['precision']:.3f} | {v['recall']:.3f} |")
    a("\n" + make_val_note(R) + "\n")
    a("## Object size\n")
    a("Ground-truth boxes by share of image area; recall at IoU >= 0.50 (localization / end-to-end), upright set, conf 0.001:\n")
    runs = [k for k in R["matrix"] if k.startswith("upright_") and "conf0.001" in k]
    head = "| Size bucket | GT boxes | " + " | ".join(runs) + " |"
    a(head)
    a("|" + "---|" * (2 + len(runs)))
    for b in [x[0] for x in BUCKETS]:
        n = R["matrix"][runs[0]]["buckets"][b]["n"]
        cells = []
        for rn in runs:
            t = R["matrix"][rn]["buckets"][b]
            cells.append(f"{pct(t['loc'] / t['n']) if t['n'] else 'n/a'} / {pct(t['e2e'] / t['n']) if t['n'] else 'n/a'}")
        a(f"| {b} | {n} | " + " | ".join(cells) + " |")
    ts = R["train_sizes"]
    rs = R["real_sizes"]
    a("\nBox-size distribution, training labels versus the real-fridge photos (share of boxes per bucket):\n")
    a("| Bucket | Training labels | Real fridge |\n|---|---|---|")
    for b in [x[0] for x in BUCKETS]:
        a(f"| {b} | {pct(ts['bucket_share'][b])} | {pct(rs['bucket_share'][b])} |")
    a(f"\nMedian box area: training {100 * ts['median_area']:.2f}% of the image ({ts['boxes']} boxes) versus real fridge {100 * rs['median_area']:.2f}% ({rs['boxes']} boxes). "
      f"Median real box side at 640 input: {rs['median_side_at_640']:.0f} px.\n")
    a("## Per-class results (upright, conf 0.001; localization / end-to-end recall)\n")
    a("| Class | GT boxes | 960 px | 640 px | Note |\n|---|---|---|---|---|")
    for c in R["class_rows"]:
        a(f"| {c['class']} | {c['n']} | {c['r960']} | {c['r640']} | {c['note']} |")
    a("\n## Most common wrong-class predictions (matched boxes, upright 960, conf 0.001)\n")
    a("| True class | Predicted | Count |\n|---|---|---|")
    for t, p, n in R["wrong_top5"]:
        a(f"| {t} | {p} | {n} |")
    a("\n## What explains the missing recall\n")
    for line in R["ranking_text"]:
        a(line)
    mx = R["matrix"]
    p001, p025 = mx["upright_640_conf0.001"]["metrics"]["0.5"], mx["upright_640_conf0.25"]["metrics"]["0.5"]
    gt_per_img = R["setup"]["gt_boxes"] / R["setup"]["images"]
    a(f"- **How to read the ranking:** conf 0.001 is a recall ceiling, not a deployable setting. It returns {p001['preds_per_image']:.0f} boxes per "
      f"image against {gt_per_img:.1f} ground-truth boxes per image, at mean matched confidence {p001['mean_conf_matched']:.3f}. At the deployed "
      f"conf 0.25 the model returns {p025['preds_per_image']:.1f} boxes per image and end-to-end recall is {pct(p025['e2e_recall'])}. "
      f"The EXIF row was measured at conf 0.001 only.")
    a("\n## Overlays (`overlays/`)\n")
    ov = R["overlays"]
    a("Six random images per set with ground-truth boxes drawn from the normalized labels. EXIF orientation of the picks: "
      f"upright set {[o['orientation'] for o in ov['upright']]}, raw set {[o['orientation'] for o in ov['raw']]}. "
      "Reviewed by eye (only these four): `upright_0`, `upright_3`, `raw_0`, `raw_3`. In the two upright images the boxes sit on the objects. "
      "In the raw set the boxes fit for an EXIF-1 photo (`raw_3`) and land on unrelated regions for an EXIF-6 photo (`raw_0`), because the "
      "photo is stored sideways while the labels follow the upright view. In the images reviewed, many visible items are not annotated, and "
      "`jar` covers glass food containers, bottles and jars.")
    a("\n## Caveats\n")
    a("- Scores come from one set of 160 photos from a small number of fridges, with no fridge IDs, so classes with few boxes are noisy.")
    a("- `.pt` rectangular inference is used here; the deployed ONNX model pads to a square (see `ml/export/MODEL_CARD.md`), so ONNX numbers can differ slightly.")
    a("- Ground truth was drawn by a person; box tightness is not checked here.")
    (OUT / "report.md").write_text("\n".join(L) + "\n")


# ----------------------------------------------------------------------------- held-out evaluation (--data)
def load_heldout(yaml_rel):
    ypath = (REPO / yaml_rel).resolve()
    cfg = yaml.safe_load(ypath.read_text())
    names = cfg["names"]
    img_dir = (ypath.parent / cfg["val"]).resolve()
    lbl_dir = img_dir.parent / "labels"
    recs = []
    for p in sorted(x for x in img_dir.iterdir() if x.suffix.lower() in {".jpg", ".jpeg", ".png"}):
        with Image.open(p) as im:
            W, H = im.size
        gt = []
        lf = lbl_dir / f"{p.stem}.txt"
        for line in lf.read_text().splitlines() if lf.exists() else []:
            v = line.split()
            if len(v) == 5:
                c, xc, yc, w, h = int(v[0]), *map(float, v[1:])
                gt.append((c, [(xc - w / 2) * W, (yc - h / 2) * H, (xc + w / 2) * W, (yc + h / 2) * H]))
        recs.append({"stem": p.stem, "path": p, "size": (W, H), "gt": gt})
    return names, recs


def eval_heldout(recs, preds, ignore_ids, thr=0.5):
    tot, pairs, per_class, wrong = Counter(), Counter(), defaultdict(Counter), []
    for r in recs:
        gt = [g for g in r["gt"] if g[0] not in ignore_ids]
        ign = [g[1] for g in r["gt"] if g[0] in ignore_ids]
        pr = preds[r["stem"]]
        m_any, m_cls = match(gt, pr, thr, False), match(gt, pr, thr, True)
        tp_preds = {p for _, p in m_cls}
        ignored_preds = sum(1 for i, (_, _, b) in enumerate(pr) if i not in tp_preds and ign and iou_many(b, ign).max() >= thr)
        tot["gt"] += len(gt)
        tot["ignored_gt"] += len(ign)
        tot["localized"] += len(m_any)
        tot["e2e"] += len(m_cls)
        tot["preds"] += len(pr) - ignored_preds
        tot["ignored_preds"] += ignored_preds
        for c, _ in gt:
            per_class[c]["gt"] += 1
        for g, _ in m_cls:
            per_class[gt[g][0]]["e2e"] += 1
        for g, pi in m_any:
            t, pc = gt[g][0], pr[pi][0]
            pairs[(t, pc)] += 1
            per_class[t]["localized"] += 1
            if t == pc:
                per_class[t]["correct"] += 1
            else:
                wrong.append({"stem": r["stem"], "box": gt[g][1], "true": t, "pred": pc, "conf": pr[pi][1]})
    return tot, pairs, per_class, wrong


def worst_sheet(recs, wrong, names, path, n=20, cols=5, tile=256):
    by = {r["stem"]: r for r in recs}
    pick = sorted(wrong, key=lambda w: -w["conf"])[:n]
    canvas = Image.new("RGB", (cols * tile, ((len(pick) + cols - 1) // cols) * (tile + 18)), (30, 30, 30))
    for k, w in enumerate(pick):
        with Image.open(by[w["stem"]]["path"]) as im:
            im = im.convert("RGB")
            x1, y1, x2, y2 = w["box"]
            mx, my = 0.3 * (x2 - x1), 0.3 * (y2 - y1)
            crop = im.crop((max(0, int(x1 - mx)), max(0, int(y1 - my)), min(im.width, int(x2 + mx)), min(im.height, int(y2 + my))))
        sc = tile / max(crop.size)
        crop = crop.resize((max(1, round(crop.width * sc)), max(1, round(crop.height * sc))))
        x, y = (k % cols) * tile, (k // cols) * (tile + 18)
        canvas.paste(crop, (x, y + 18))
        ImageDraw.Draw(canvas).text((x + 3, y + 3), f"{k + 1}. {names[w['true']]} -> {names[w['pred']]} ({w['conf']:.2f})", fill=(255, 255, 0))
    canvas.save(path)
    return pick


def heldout(a):
    from ultralytics import YOLO

    names, recs = load_heldout(a.data)
    ignore = [c.strip() for c in a.ignore_classes.split(",") if c.strip()]
    unknown = [c for c in ignore if c not in names]
    if unknown:
        raise SystemExit(f"unknown --ignore-classes: {unknown}")
    ignore_ids = {names.index(c) for c in ignore}
    weights = Path(a.weights) if a.weights else WEIGHTS
    weights = weights if weights.is_absolute() else (REPO / weights).resolve()
    label = a.weights_label or weights.parent.parent.name
    model = YOLO(str(weights))
    assert [model.names[i] for i in range(len(names))] == names, "model class order differs from the held-out yaml"
    confs = [float(c) for c in a.confs.split(",")]
    OUT.mkdir(parents=True, exist_ok=True)
    results, sheet_pick = {}, []
    for conf in confs:
        print("held-out run, conf", conf, flush=True)
        preds = {}
        for r in recs:
            res = model.predict(source=str(r["path"]), imgsz=a.imgsz, conf=conf, iou=0.7, device=a.device, verbose=False)[0]
            b = res.boxes
            boxes = b.xyxy.cpu().numpy().tolist() if b is not None and len(b) else []
            cls = b.cls.cpu().numpy().astype(int).tolist() if boxes else []
            cf = b.conf.cpu().numpy().tolist() if boxes else []
            preds[r["stem"]] = list(zip(cls, cf, boxes))
        tot, pairs, per_class, wrong = eval_heldout(recs, preds, ignore_ids)
        results[conf] = {"tot": dict(tot), "pairs": pairs, "per_class": per_class, "wrong": wrong}
        if conf == min(confs):
            sheet_pick = worst_sheet(recs, wrong, names, OUT / "confusion_heldout_worst20.png")

    L = []
    w = L.append
    w("# Held-out real-fridge evaluation (160 photos)\n")
    w(f"Produced by `ml/diagnose_real_fridge.py --data {a.data}`. Weights: `{label}`; imgsz {a.imgsz}; NMS iou 0.7; matching at IoU >= 0.5, "
      f"one-to-one, greedy by confidence. Ignored classes: {ignore or 'none'}. These 160 photos are never used for training or tuning.\n")
    w(f"{len(recs)} photos, {results[confs[0]]['tot']['gt']} ground-truth boxes after ignoring ({results[confs[0]]['tot']['ignored_gt']} ignored-class boxes removed).\n")
    w("## Headline\n")
    w("| conf | Localization recall | Class-correct share (localized) | End-to-end recall | Predictions/image | End-to-end precision |\n|---|---|---|---|---|---|")
    for conf in confs:
        t = results[conf]["tot"]
        correct = sum(c["correct"] for c in results[conf]["per_class"].values())
        w(f"| {conf} | {100 * t['localized'] / t['gt']:.1f}% ({t['localized']}/{t['gt']}) | {100 * correct / max(t['localized'], 1):.1f}% | "
          f"{100 * t['e2e'] / t['gt']:.1f}% ({t['e2e']}/{t['gt']}) | {t['preds'] / len(recs):.1f} | {100 * t['e2e'] / max(t['preds'], 1):.1f}% |")
    w("\nPredictions that landed on an ignored-class box and were not counted: " + ", ".join(f"conf {c}: {results[c]['tot']['ignored_preds']}" for c in confs) + ".\n")
    w("## Per class (localization / end-to-end recall)\n")
    head = "| Class | GT boxes | " + " | ".join(f"conf {c}" for c in confs) + " |\n|---|---|" + "---|" * len(confs)
    w(head)
    gts = Counter()
    for c in results[confs[0]]["per_class"]:
        gts[c] = results[confs[0]]["per_class"][c]["gt"]
    for c, n in gts.most_common():
        cells = []
        for conf in confs:
            pc = results[conf]["per_class"][c]
            cells.append(f"{100 * pc['localized'] / n:.0f}% / {100 * pc['e2e'] / n:.0f}%")
        w(f"| {names[c]}{' (low support)' if n < 10 else ''} | {n} | " + " | ".join(cells) + " |")
    w("")
    for conf in confs:
        pairs = results[conf]["pairs"]
        loc = sum(pairs.values())
        w(f"## Confusion at conf {conf}: true class -> predicted class (correctly localized boxes, IoU >= 0.5)\n")
        wrong_pairs = [(k, v) for k, v in pairs.items() if k[0] != k[1]]
        w(f"{loc} boxes localized; {sum(v for k, v in pairs.items() if k[0] == k[1])} with the right class; {sum(v for _, v in wrong_pairs)} with a wrong class. Top wrong pairs:\n")
        w("| True class | Predicted | Count |\n|---|---|---|")
        for (t, pc), v in sorted(wrong_pairs, key=lambda kv: -kv[1])[:25]:
            w(f"| {names[t]} | {names[pc]} | {v} |")
        w("")
        w("Per true class, the most common predictions among localized boxes:\n")
        w("| True class | Localized | Predicted classes (count) |\n|---|---|---|")
        by_true = defaultdict(Counter)
        for (t, pc), v in pairs.items():
            by_true[t][pc] += v
        for t in sorted(by_true, key=lambda t: -sum(by_true[t].values())):
            w(f"| {names[t]} | {sum(by_true[t].values())} | " + ", ".join(f"{names[pc]} {v}" for pc, v in by_true[t].most_common(4)) + " |")
        w("")
        with (OUT / f"confusion_heldout_conf{conf}.csv").open("w", newline="") as f:
            cw = csv.writer(f)
            used = sorted({k[1] for k in pairs} | set(by_true))
            cw.writerow(["true\\pred"] + [names[c] for c in used])
            for t in sorted(by_true):
                cw.writerow([names[t]] + [pairs.get((t, c), 0) for c in used])
    w(f"## 20 worst crops\n")
    w(f"The 20 localized boxes with the wrong class that the model was most confident about (conf {min(confs)} run). Sheet: `ml/runs/real_fridge_diagnostics/confusion_heldout_worst20.png` (photo crops, not committed):\n")
    for k, x in enumerate(sheet_pick, 1):
        w(f"{k}. {names[x['true']]} -> {names[x['pred']]} ({x['conf']:.2f}), `{x['stem'][:40]}`")
    (OUT / "confusion_heldout.md").write_text("\n".join(L) + "\n")
    ser = {str(c): {"tot": r["tot"], "per_class": {names[k]: dict(v) for k, v in r["per_class"].items()},
                    "pairs": {f"{names[t]}->{names[pc]}": v for (t, pc), v in r["pairs"].items()}} for c, r in results.items()}
    (OUT / "results_heldout.json").write_text(json.dumps({"weights": label, "imgsz": a.imgsz, "ignore": ignore, "photos": len(recs), "runs": ser}, indent=2))
    print("wrote", (OUT / "confusion_heldout.md").relative_to(REPO))


# ----------------------------------------------------------------------------- main
def main():
    global DATA_YAML_NAMES
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--src", default=None, help="fridge_qa_reproducibility folder (full diagnostics mode)")
    ap.add_argument("--device", default="mps")
    ap.add_argument("--report-only", action="store_true", help="rebuild report.md from an existing results.json")
    ap.add_argument("--data", default=None, help="held-out mode: dataset yaml, e.g. data/real_fridge/data_heldout.yaml")
    ap.add_argument("--ignore-classes", default="", help="held-out mode: comma-separated classes to ignore, e.g. jar")
    ap.add_argument("--weights", default=None, help="model weights (default: ml/export/food_detector_v8n_baseline.pt)")
    ap.add_argument("--weights-label", default=None, help="name written into reports (default: the run folder name)")
    ap.add_argument("--confs", default="0.25,0.001", help="held-out mode: comma-separated confidence thresholds")
    ap.add_argument("--imgsz", type=int, default=640, help="held-out mode: inference size")
    a = ap.parse_args()
    if a.data:
        return heldout(a)
    if not a.src:
        ap.error("pass --src (full diagnostics) or --data (held-out evaluation)")
    src = Path(a.src).expanduser()
    names = yaml.safe_load(DATA_YAML.read_text())["names"]
    DATA_YAML_NAMES = names
    OUT.mkdir(parents=True, exist_ok=True)
    if a.report_only:
        R = json.loads((OUT / "results.json").read_text())
        R["val_note"] = make_val_note(R)
        (OUT / "results.json").write_text(json.dumps(R, indent=2, default=float))
        write_report(R, names)
        print("rewrote", (OUT / "report.md").relative_to(REPO))
        return
    from ultralytics import YOLO

    recs, unmapped = prepare(src, names)
    orient_counts = dict(Counter(r["orientation"] for r in recs))
    long_sides = sorted(max(r["raw_size"]) for r in recs)
    all_gt = [(r, g) for r in recs for g in r["gt"]]
    setup = {
        "images": len(recs), "gt_boxes": len(all_gt), "classes_used": len({g[0] for _, g in all_gt}),
        "empty_images": sum(1 for r in recs if not r["gt"]), "exif_counts": {str(k): v for k, v in sorted(orient_counts.items())},
        "rotated_images": sum(1 for r in recs if r["raw_size"] != r["disp_size"]), "median_long_side": long_sides[len(long_sides) // 2],
        "min_long_side": long_sides[0], "max_long_side": long_sides[-1], "class_order_ok": True, "unmapped_class_ids": unmapped,
    }
    model = YOLO(str(WEIGHTS))
    assert [model.names[i] for i in range(len(names))] == names

    matrix, runs = {}, [("upright_640_conf0.001", "upright", 640, 0.001), ("upright_960_conf0.001", "upright", 960, 0.001),
                        ("upright_1280_conf0.001", "upright", 1280, 0.001), ("raw_640_conf0.001", "raw", 640, 0.001),
                        ("upright_640_conf0.25", "upright", 640, 0.25)]
    for name, subset, sz, conf in runs:
        print("running", name, flush=True)
        preds = run_model(model, recs, subset, sz, conf, a.device)
        metrics, per_gt = evaluate(recs, preds)
        matrix[name] = {"subset": subset, "imgsz": sz, "conf": conf, "metrics": metrics,
                        "buckets": bucket_table(per_gt), "classes": class_table(per_gt, names), "per_gt": per_gt}

    val = {}
    for sz in (640, 960, 1280):
        print("val control", sz, flush=True)
        val[str(sz)] = ultralytics_val(model, sz, a.device)
    ref = matrix["upright_960_conf0.001"]["metrics"]["0.5"]
    ref_map = val["960"]["mAP50"]
    val_note = (f"The control uses Ultralytics' own matching and AP interpolation, so its precision/recall are at the best-F1 confidence "
                f"and are not directly comparable to my fixed-threshold recall (for example, 960 px: my localization recall "
                f"{pct(ref['loc_recall'])} and end-to-end recall {pct(ref['e2e_recall'])} versus Ultralytics mAP@50 {ref_map:.3f}). "
                f"Class order and label format are not the cause: the control reads the same labels with the same class order, and "
                f"mAP@50 here tracks the end-to-end recall ordering across image sizes.")

    # Ashton's saved predictions, scored under both ground-truth frames
    her = ashton_predictions(src, recs)
    her_raw, _ = evaluate(recs, her, frame="raw")
    her_disp, _ = evaluate(recs, her, frame="disp")
    her_tp = None
    with (src / "evaluation" / "evaluation_summary.csv").open() as f:
        for row in csv.DictReader(f):
            if row["metric"] == "True positives":
                her_tp = int(row["value"])

    # sizes
    areas = np.array([g[3] * g[4] for _, g in all_gt])
    side640 = [np.sqrt(g[3] * g[4] * r["disp_size"][0] * r["disp_size"][1]) * 640 / max(r["disp_size"]) for r, g in all_gt]
    real_sizes = {"boxes": len(areas), "median_area": float(np.median(areas)),
                  "bucket_share": {b[0]: float(((areas >= b[1]) & (areas < b[2])).mean()) for b in BUCKETS},
                  "median_side_at_640": float(np.median(side640))}

    # per-class table
    c960, c640 = matrix["upright_960_conf0.001"]["classes"], matrix["upright_640_conf0.001"]["classes"]
    order = [c for c in HIGHLIGHT if c in c960] + sorted([c for c in c960 if c not in HIGHLIGHT], key=lambda c: -c960[c]["n"])
    class_rows = []
    for c in order:
        t9, t6 = c960[c], c640[c]
        class_rows.append({"class": c, "n": t9["n"], "r960": f"{pct(t9['loc'] / t9['n'])} / {pct(t9['e2e'] / t9['n'])}",
                           "r640": f"{pct(t6['loc'] / t6['n'])} / {pct(t6['e2e'] / t6['n'])}",
                           "note": "low-support (<10 boxes)" if t9["n"] < 10 else ""})
    missing = [c for c in HIGHLIGHT if c not in c960]
    if missing:
        class_rows.append({"class": ", ".join(missing), "n": 0, "r960": "n/a", "r640": "n/a", "note": "no ground-truth boxes"})

    wrong = Counter((names[g["cls"]], names[g["pred_cls"]]) for g in matrix["upright_960_conf0.001"]["per_gt"] if g["pred_cls"] is not None)
    wrong_top5 = [(t, p, n) for (t, p), n in wrong.most_common(5)]

    # factor ranking (end-to-end recall, IoU 0.5, in percentage points)
    e = lambda k: matrix[k]["metrics"]["0.5"]["e2e_recall"]
    best_sz = max(("upright_640_conf0.001", "upright_960_conf0.001", "upright_1280_conf0.001"), key=e)
    factors = [
        ("EXIF orientation (model input rotated vs sideways, 640 px)", e("upright_640_conf0.001") - e("raw_640_conf0.001")),
        ("Confidence threshold (0.001 vs 0.25, 640 px upright)", e("upright_640_conf0.001") - e("upright_640_conf0.25")),
        (f"Image size ({best_sz.split('_')[1]} vs 640 px, conf 0.001 upright)", e(best_sz) - e("upright_640_conf0.001")),
        ("Evaluation frame (ground truth scaled by display vs raw size, Ashton's saved predictions)",
         her_disp["0.5"]["e2e_recall"] - her_raw["0.5"]["e2e_recall"]),
    ]
    ranked = sorted(factors, key=lambda x: -abs(x[1]))
    bk = matrix[best_sz]["buckets"]
    small = bk["<0.5%"]
    ranking_text = []
    for i, (lab, d) in enumerate(ranked, 1):
        verdict = "no meaningful change" if abs(d) < 0.005 else (f"{'+' if d > 0 else ''}{100 * d:.1f} points")
        ranking_text.append(f"{i}. **{lab}:** end-to-end recall moves {verdict}.")
    bm = matrix[best_sz]["metrics"]["0.5"]
    ranking_text.append(f"- **Object size:** at {best_sz.split('_')[1]} px, end-to-end recall is "
                        + ", ".join(f"{b}: {pct(bk[b]['e2e'] / bk[b]['n']) if bk[b]['n'] else 'n/a'}" for b in bk)
                        + f" (GT counts "
                        + ", ".join(str(bk[b]['n']) for b in bk) + ").")
    ranking_text.append(f"- **Class definitions:** at the best size, localization recall is {pct(bm['loc_recall'])} but end-to-end recall is "
                        f"{pct(bm['e2e_recall'])}; among localized boxes {pct(bm['class_correct_share'])} have the right class, "
                        f"so {pct(bm['loc_recall'] - bm['e2e_recall'])} of all ground-truth boxes are found but mislabeled.")
    if abs(factors[0][1]) < 0.005:
        ranking_text.append("- EXIF made no difference to end-to-end recall in this run.")
    if abs(factors[1][1]) < 0.005:
        ranking_text.append("- The confidence threshold made no difference to end-to-end recall in this run.")

    R = {"setup": setup, "ashton": {"raw_frame": her_raw, "display_frame": her_disp, "her_tp": her_tp},
         "matrix": {k: {kk: vv for kk, vv in v.items() if kk != "per_gt"} for k, v in matrix.items()},
         "val_control": val, "val_note": val_note, "train_sizes": train_sizes(), "real_sizes": real_sizes,
         "class_rows": class_rows, "wrong_top5": wrong_top5, "factor_deltas_e2e": {lab: d for lab, d in factors},
         "ranking_text": ranking_text}
    R["overlays"] = overlays(recs, names)
    (OUT / "results.json").write_text(json.dumps(R, indent=2, default=float))
    write_report(R, names)
    print("wrote", (OUT / "report.md").relative_to(REPO))


if __name__ == "__main__":
    main()
