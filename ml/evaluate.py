"""Evaluate a trained YOLO model on the validation split and write a report.

Produces, in --out (default ml/runs/eval_baseline_v8n):
  metrics_summary.json, per_class_metrics.csv, confusion_matrix.png,
  confusion_matrix_normalized.png, confusion_matrix_large.png,
  confusion_matrix_counts.csv, weak_class_analysis.csv,
  safety_class_analysis.json, evaluation_report.md

Note: --split "val" means the `val:` entry of data.yaml (the valid/ folder).
The test split is never used.

Usage:  python ml/evaluate.py
"""
import argparse
import csv
import json
import re
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import yaml
from ultralytics import YOLO

REPO = Path(__file__).resolve().parent.parent
WEAK = ["chocolate", "goat_cheese", "ham", "mango", "pomegranate"]
SAFETY = ["chicken", "beef", "shrimp"]
MEAT = ["bacon", "ham", "beef", "chicken", "shrimp"]
LOW_SUPPORT = 20


def rel(p):
    p = Path(p)
    return p if p.is_absolute() else REPO / p


def parse_args():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--weights", default="ml/runs/baseline_v8n/weights/best.pt")
    ap.add_argument("--data", default="data/cleaned/data.yaml")
    ap.add_argument("--split", default="val", help='"val" = the valid/ folder. Do not use "test".')
    ap.add_argument("--imgsz", type=int, default=640)
    ap.add_argument("--conf", type=float, default=0.001)
    ap.add_argument("--iou", type=float, default=0.6)
    ap.add_argument("--cm-conf", type=float, default=0.25,
                    help="confidence threshold for the confusion matrix (a deployable operating point)")
    ap.add_argument("--device", default="mps")
    ap.add_argument("--out", default="ml/runs/eval_baseline_v8n")
    a = ap.parse_args()
    if a.split == "test":
        ap.error("this script is for the valid split only; test is held out")
    return a


def label_stats(data_cfg, split_key, names):
    """Per-class image and instance counts from the label files of the split."""
    img_dir = Path(data_cfg[split_key])
    lbl_dir = img_dir.parent / "labels"
    inst, imgs = {}, {}
    for f in lbl_dir.glob("*.txt"):
        seen = set()
        for line in f.read_text().splitlines():
            if line.strip():
                c = int(float(line.split()[0]))
                inst[c] = inst.get(c, 0) + 1
                seen.add(c)
        for c in seen:
            imgs[c] = imgs.get(c, 0) + 1
    return inst, imgs


def train_counts(report_path, names):
    """class -> train instance count, parsed from the cleaning report table."""
    out = {}
    if not report_path.exists():
        return out
    for line in report_path.read_text().splitlines():
        m = re.match(r"\|\s*\d+\s*\|\s*(\w+)\s*\|\s*(\d+)\s*\|\s*(\d+)\s*\|\s*(\d+)\s*\|\s*(\d+)\s*\|", line)
        if m and m.group(1) in names:
            out[m.group(1)] = int(m.group(2))
    return out


def pct(n, d):
    return f"{n} ({100 * n / d:.1f}%)" if d else "0 (n/a)"


def main():
    a = parse_args()
    weights, data_path, out = rel(a.weights), rel(a.data), rel(a.out)
    out.mkdir(parents=True, exist_ok=True)
    data_cfg = yaml.safe_load(data_path.read_text())

    model = YOLO(str(weights))
    names = model.names  # {idx: name}
    nc = len(names)
    cls_idx = {n: i for i, n in names.items()}
    print(f"classes: {nc}")

    # Pass 1: confusion matrix at a deployable confidence (Ultralytics builds it at the val conf,
    # and at conf=0.001 every low-confidence box would count as a background false positive).
    cm_tmp = out / "_cm_pass"
    cm_res = model.val(data=str(data_path), split=a.split, imgsz=a.imgsz, conf=a.cm_conf, iou=a.iou,
                       device=a.device, plots=True, project=str(out), name=cm_tmp.name,
                       exist_ok=True, verbose=False)
    cm_matrix = np.array(cm_res.confusion_matrix.matrix, dtype=int)

    # Pass 2: metrics (mAP, P, R, curves) at conf 0.001 as is standard
    res = model.val(data=str(data_path), split=a.split, imgsz=a.imgsz, conf=a.conf, iou=a.iou,
                    device=a.device, plots=True, project=str(out.parent), name=out.name,
                    exist_ok=True, verbose=False)
    box = res.box

    inst_lbl, imgs_lbl = label_stats(data_cfg, a.split if a.split in data_cfg else "val", names)
    n_images = len([f for f in Path(data_cfg['val']).iterdir() if f.suffix.lower() in {'.jpg', '.jpeg', '.png', '.bmp', '.webp'}])
    n_instances = sum(inst_lbl.values())
    cm_gt = int(cm_matrix[:, :-1].sum())
    assert cm_gt == n_instances, f"label count {n_instances} != confusion-matrix ground truth {cm_gt}"

    summary = {
        "weights": str(weights.relative_to(REPO)), "split": a.split, "data": str(data_path.relative_to(REPO)),
        "imgsz": a.imgsz, "conf": a.conf, "iou": a.iou, "device": a.device,
        "mAP50": float(box.map50), "mAP50_95": float(box.map),
        "mean_precision": float(box.mp), "mean_recall": float(box.mr),
        "images_evaluated": n_images, "instances_evaluated": n_instances,
    }
    (out / "metrics_summary.json").write_text(json.dumps(summary, indent=2))
    print(json.dumps(summary, indent=2))

    # ---- per-class table, mapped by class index (not position) ----
    rows = []
    present = [int(c) for c in box.ap_class_index]
    for pos, c in enumerate(present):
        p, r, ap50, ap = box.class_result(pos)
        rows.append({
            "class": names[c], "class_id": c,
            "n_images": imgs_lbl.get(c, 0), "n_instances": inst_lbl.get(c, 0),
            "precision": float(p), "recall": float(r), "AP50": float(ap50),
            "AP50-95": float(box.maps[c]),
        })
    pc = pd.DataFrame(rows).sort_values("AP50").reset_index(drop=True)
    pc.drop(columns="class_id").to_csv(out / "per_class_metrics.csv", index=False)
    pcd = pc.set_index("class")

    # ---- confusion matrix: rows = predicted, cols = true, last = background ----
    cm = cm_matrix
    import shutil
    for f in cm_tmp.glob('confusion_matrix*.png'):
        shutil.copy(f, out / f.name)
    shutil.rmtree(cm_tmp, ignore_errors=True)
    labels = [names[i] for i in range(nc)] + ["background"]
    cm_df = pd.DataFrame(cm, index=labels, columns=labels)
    cm_df.index.name = "predicted\\true"
    cm_df.to_csv(out / "confusion_matrix_counts.csv")
    bg = nc  # index of background

    # large, readable version
    norm = cm / np.maximum(cm.sum(axis=0, keepdims=True), 1)
    fig, ax = plt.subplots(figsize=(20, 20))
    ax.imshow(norm, cmap="Blues", vmin=0, vmax=1)
    ax.set_xticks(range(nc + 1)); ax.set_yticks(range(nc + 1))
    ax.set_xticklabels(labels, rotation=90, fontsize=11); ax.set_yticklabels(labels, fontsize=11)
    for i in range(nc + 1):
        for j in range(nc + 1):
            if cm[i, j]:
                ax.text(j, i, cm[i, j], ha="center", va="center", fontsize=7,
                        color="white" if norm[i, j] > 0.5 else "black")
    ax.set_xlabel("True class"); ax.set_ylabel("Predicted class")
    ax.set_title("Confusion matrix (counts; colour = share of each true class) - valid split")
    fig.tight_layout(); fig.savefig(out / "confusion_matrix_large.png", dpi=100); plt.close(fig)

    # ---- weak-class analysis ----
    tr = train_counts(rel("data/cleaned/cleaning_report.md"), set(cls_idx))

    def top_conf(col=None, row=None, k=3):
        """top-k off-diagonal, non-background confusions for a class."""
        if col is not None:  # true=col predicted as row
            v = [(labels[i], int(cm[i, col])) for i in range(nc) if i != col and cm[i, col] > 0]
        else:                # predicted=row when true=col
            v = [(labels[j], int(cm[row, j])) for j in range(nc) if j != row and cm[row, j] > 0]
        return sorted(v, key=lambda t: -t[1])[:k]

    weak_rows, weak_md = [], []
    for w in WEAK:
        c = cls_idx[w]
        s = pcd.loc[w]
        as_true = top_conf(col=c)
        as_pred = top_conf(row=c)
        missed = int(cm[bg, c])        # true w, predicted background
        fp_bg = int(cm[c, bg])         # predicted w, true background
        support = "low-support: metric unreliable" if s.n_instances < LOW_SUPPORT else "ok"
        # one-line cause from data, not guesswork about content
        t = tr.get(w)
        parts = []
        if t is not None and t < 100:
            parts.append(f"few training instances ({t})")
        if as_true:
            parts.append(f"true {w} most often predicted as {as_true[0][0]} ({as_true[0][1]})")
        if as_pred:
            parts.append(f"predicted {w} most often actually {as_pred[0][0]} ({as_pred[0][1]})")
        if missed >= max(3, 0.1 * s.n_instances):
            parts.append(f"{missed} missed detections")
        cause = "; ".join(parts) or "no dominant pattern in the confusion matrix"
        if s.AP50 >= summary["mAP50"] and s.recall >= summary["mean_recall"]:
            cause = (f"no clear weakness on valid (AP50 {s.AP50:.3f} and recall {s.recall:.3f} are at or above the overall "
                     f"values); the few instances make this uncertain. Note: {cause}")
        weak_rows.append({
            "class": w, "n_instances": int(s.n_instances), "precision": s.precision, "recall": s.recall,
            "AP50": s.AP50, "AP50-95": s["AP50-95"], "support": support, "train_instances": t,
            "true_as_other_top3": "; ".join(f"{n}:{k}" for n, k in as_true),
            "pred_as_this_true_other_top3": "; ".join(f"{n}:{k}" for n, k in as_pred),
            "missed_to_background": missed, "false_positive_background": fp_bg, "likely_cause": cause,
        })
    pd.DataFrame(weak_rows).to_csv(out / "weak_class_analysis.csv", index=False)

    # ---- safety-class analysis ----
    meat_idx = [cls_idx[m] for m in MEAT if m in cls_idx]
    mean_recall = summary["mean_recall"]
    safety = {}
    for sname in SAFETY:
        c = cls_idx[sname]
        s = pcd.loc[sname]
        total = int(cm[:, c].sum())
        correct = int(cm[c, c])
        other_meat = int(sum(cm[i, c] for i in meat_idx if i != c))
        other_food = int(sum(cm[i, c] for i in range(nc) if i not in meat_idx))
        missed = int(cm[bg, c])
        ptotal = int(cm[c, :].sum())
        pcorrect = int(cm[c, c])
        p_meat = int(sum(cm[c, j] for j in meat_idx if j != c))
        p_food = int(sum(cm[c, j] for j in range(nc) if j not in meat_idx))
        p_bg = int(cm[c, bg])
        safety[sname] = {
            "n_instances": int(s.n_instances), "precision": s.precision, "recall": s.recall,
            "AP50": s.AP50, "AP50-95": s["AP50-95"],
            "recall_vs_mean": "above" if s.recall > mean_recall else "below",
            "true_instances_in_matrix": total,
            "true_breakdown": {"correct": correct, "other_meat": other_meat,
                               "produce_or_other_food": other_food, "missed_background": missed},
            "predicted_total": ptotal,
            "predicted_breakdown": {"correct": pcorrect, "actually_other_meat": p_meat,
                                    "actually_produce_or_other_food": p_food,
                                    "actually_background_false_positive": p_bg},
            "other_meat_detail": {labels[i]: int(cm[i, c]) for i in meat_idx if i != c and cm[i, c]},
            "produce_detail_top": sorted(((labels[i], int(cm[i, c])) for i in range(nc)
                                          if i not in meat_idx and cm[i, c] > 0), key=lambda t: -t[1])[:5],
        }
    (out / "safety_class_analysis.json").write_text(json.dumps(safety, indent=2))

    # ---- convergence from training results.csv ----
    conv = {}
    rc = rel("ml/runs/baseline_v8n/results.csv")
    seed = None
    ay = rel("ml/runs/baseline_v8n/args.yaml")
    if ay.exists():
        seed = yaml.safe_load(ay.read_text()).get("seed")
    if rc.exists():
        with open(rc, newline="") as f:
            rr = [{k.strip(): v.strip() for k, v in r.items()} for r in csv.DictReader(f)]
        last = rr[-1]
        conv["epochs"] = len(rr)
        for k in ("box", "cls", "dfl"):
            tv = [float(r[f"train/{k}_loss"]) for r in rr]
            vv = [float(r[f"val/{k}_loss"]) for r in rr]
            mid = float(np.mean(vv[25:35])); end = float(np.mean(vv[-10:]))
            conv[k] = {"train_final": tv[-1], "val_final": vv[-1],
                       "val_mean_ep26_35": mid, "val_mean_last10": end,
                       "val_change_pct": 100 * (end - mid) / mid,
                       "train_change_pct": 100 * (float(np.mean(tv[-10:])) - float(np.mean(tv[25:35]))) / float(np.mean(tv[25:35])),
                       "val_min": min(vv), "val_min_epoch": int(np.argmin(vv)) + 1}

    # ---- caveat numbers pulled from the cleaning report ----
    crep = rel("data/cleaned/cleaning_report.md")
    ctext = crep.read_text() if crep.exists() else ""
    m_leak = re.search(r"train neighbour at distance <= 4: \*\*(\d+)\*\* of (\d+)", ctext)
    m_grp = re.search(r"largest has (\d+) images from \{'aicook'", ctext)

    # ---- write the report ----
    L = []
    L.append("# Baseline YOLOv8n evaluation (valid split)\n")
    L.append("All numbers below were produced by `ml/evaluate.py` (files in this folder). "
             "The test split was not used.\n")
    L.append("## Headline metrics\n")
    L.append("| Metric | Value |\n|---|---|")
    L.append(f"| mAP@50 | {summary['mAP50']:.3f} |")
    L.append(f"| mAP@50-95 | {summary['mAP50_95']:.3f} |")
    L.append(f"| Mean precision | {summary['mean_precision']:.3f} |")
    L.append(f"| Mean recall | {summary['mean_recall']:.3f} |")
    L.append(f"| Images / instances evaluated | {n_images} / {n_instances} |\n")
    L.append("Run config: " + f"weights `{summary['weights']}`, split `{a.split}` (valid/), imgsz {a.imgsz}, "
             f"conf {a.conf}, iou {a.iou}, seed {seed} (training), device {a.device}. "
             "Precision/recall are at the confidence that maximises F1 (Ultralytics default); "
             f"the confusion matrix is built in a separate pass at conf {a.cm_conf} (a deployable threshold), so its counts are not the "
             "same operating point as the P/R above.\n")
    if conv:
        L.append("## Convergence\n")
        L.append("| Loss | train final | val final | val mean ep26-35 | val mean last 10 | val change | train change |\n|---|---|---|---|---|---|---|")
        for k in ("box", "cls", "dfl"):
            d = conv[k]
            L.append(f"| {k} | {d['train_final']:.3f} | {d['val_final']:.3f} | {d['val_mean_ep26_35']:.3f} | "
                     f"{d['val_mean_last10']:.3f} | {d['val_change_pct']:+.1f}% | {d['train_change_pct']:+.1f}% |")
        flat = all(abs(conv[k]["val_change_pct"]) < 5 for k in ("box", "cls", "dfl"))
        L.append("")
        L.append(("Validation loss is roughly flat from epoch 26 onward (all three within 5%) while training loss keeps falling, "
                  "so extra epochs would mainly widen the train/val gap." if flat else
                  "Validation loss changes by more than 5% between epochs 26-35 and the last 10 epochs for at least one loss; "
                  "see the table for which.") + "\n")
    L.append("## Weak classes\n")
    L.append("| Class | Val instances | Train instances | Precision | Recall | AP50 | AP50-95 | Support |\n|---|---|---|---|---|---|---|---|")
    for r in weak_rows:
        L.append(f"| {r['class']} | {r['n_instances']} | {r['train_instances']} | {r['precision']:.3f} | {r['recall']:.3f} | "
                 f"{r['AP50']:.3f} | {r['AP50-95']:.3f} | {r['support']} |")
    L.append("\nTop confusions (count) and likely cause:\n")
    for r in weak_rows:
        L.append(f"- **{r['class']}**: true as other: {r['true_as_other_top3'] or 'none'}; "
                 f"predicted as {r['class']} but actually: {r['pred_as_this_true_other_top3'] or 'none'}; "
                 f"missed to background: {r['missed_to_background']}; false positives on background: "
                 f"{r['false_positive_background']}. Likely cause: {r['likely_cause']}.")
    n_low = sum(1 for r in weak_rows if r["support"] != "ok")
    n_below = sum(1 for r in weak_rows if r["AP50"] < summary["mAP50"])
    L.append(f"\n{n_below} of the 5 weak classes {'has' if n_below == 1 else 'have'} AP50 below the overall mAP@50 ({summary['mAP50']:.3f}); "
             f"{n_low} have fewer than {LOW_SUPPORT} valid instances, so their per-class numbers move a lot with a few boxes.\n")
    L.append("## Safety-critical classes\n")
    L.append("| Class | Val instances | Precision | Recall | AP50 | AP50-95 | Recall vs mean recall |\n|---|---|---|---|---|---|---|")
    for k, d in safety.items():
        L.append(f"| {k} | {d['n_instances']} | {d['precision']:.3f} | {d['recall']:.3f} | {d['AP50']:.3f} | "
                 f"{d['AP50-95']:.3f} | {d['recall_vs_mean']} ({mean_recall:.3f}) |")
    L.append("\nWhere true instances go (confusion matrix, conf " + str(a.cm_conf) + "):\n")
    L.append("| Class | True n | Correct | Other meat | Produce/other food | Missed (background) |\n|---|---|---|---|---|---|")
    for k, d in safety.items():
        t = d["true_instances_in_matrix"]; b = d["true_breakdown"]
        L.append(f"| {k} | {t} | {pct(b['correct'], t)} | {pct(b['other_meat'], t)} | "
                 f"{pct(b['produce_or_other_food'], t)} | {pct(b['missed_background'], t)} |")
    L.append("\nWhat the predictions of each class actually were:\n")
    L.append("| Predicted | Predicted n | Correct | Actually other meat | Actually produce/other | Background (false positive) |\n|---|---|---|---|---|---|")
    for k, d in safety.items():
        t = d["predicted_total"]; b = d["predicted_breakdown"]
        L.append(f"| {k} | {t} | {pct(b['correct'], t)} | {pct(b['actually_other_meat'], t)} | "
                 f"{pct(b['actually_produce_or_other_food'], t)} | {pct(b['actually_background_false_positive'], t)} |")
    L.append("")
    for k, d in safety.items():
        b = d["true_breakdown"]; t = d["true_instances_in_matrix"]
        danger = b["produce_or_other_food"] + b["missed_background"]
        det = ", ".join(f"{n} {c}" for n, c in d["produce_detail_top"]) or "none"
        L.append(f"- **{k}**: recall {d['recall']:.3f} is {d['recall_vs_mean']} the mean recall ({mean_recall:.3f}). "
                 f"{danger} of {t} true instances ({100 * danger / max(t, 1):.1f}%) were the dangerous failures "
                 f"(missed or labelled as produce/other food; top produce/other labels: {det}); "
                 f"{b['other_meat']} went to another meat class.")
    L.append("")
    L.append("## Caveats\n")
    L.append(f"- The valid split is small ({n_images} images), and {int((pc.n_instances < LOW_SUPPORT).sum())} classes have fewer than {LOW_SUPPORT} valid instances.")
    if m_leak:
        L.append(f"- The cleaning report records {m_leak.group(1)} of {m_leak.group(2)} valid/test images with a train neighbour within phash distance 4"
                 + (f", and a {m_grp.group(1)}-image same-scene `aicook` group that spans all splits" if m_grp else "")
                 + ". These numbers are probably optimistic.")
    L.append("- Confirm on a separate set of real fridge photos before trusting these numbers for the app.")
    L.append(f"- The confusion matrix is at conf {a.cm_conf} while P/R use the F1-optimal threshold, so counts and rates will not match exactly.\n")
    L.append("## Files\n")
    L.append("`metrics_summary.json`, `per_class_metrics.csv`, `confusion_matrix.png`, `confusion_matrix_normalized.png`, "
             "`confusion_matrix_large.png`, `confusion_matrix_counts.csv` (rows predicted, columns true, incl. background), "
             "`weak_class_analysis.csv`, `safety_class_analysis.json`, plus Ultralytics PR/F1/P/R curve PNGs.")
    (out / "evaluation_report.md").write_text("\n".join(L) + "\n")
    print(f"wrote {out / 'evaluation_report.md'}")


if __name__ == "__main__":
    main()
