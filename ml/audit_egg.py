"""Audit `egg` labels: external images (ext3_ files in data/cleaned_v3 train) versus data/cleaned_v2 train.

Flags every egg box with simple heuristics, draws 30 random egg boxes per source in context, and writes
ml/runs/external_audit/egg_audit.md plus two contact sheets (photo crops, not committed):
    ml/runs/external_audit/egg_audit_ext.png    ml/runs/external_audit/egg_audit_v2.png

Heuristic flags (box geometry in pixels):
    very_large   box covers more than 25% of the image
    tiny         box covers less than 0.05% of the image
    odd_aspect   long side more than 3x the short side
    duplicate    another egg box in the same image with IoU > 0.7
    overlaps_other_class   IoU > 0.3 with a box of a different class in the same image

Usage:  python ml/audit_egg.py [--eye-ext N --eye-v2 N --notes "text"]
        (the --eye-* numbers are counts from looking at the sheets; they are written into the report)
"""
import argparse
import random
from pathlib import Path

import yaml
from PIL import Image, ImageDraw

REPO = Path(__file__).resolve().parents[1]
V3 = REPO / "data" / "cleaned_v3"
V2 = REPO / "data" / "cleaned_v2"
OUT = REPO / "ml" / "runs" / "external_audit"
SEED = 270
N = 30
IMG_EXT = {".jpg", ".jpeg", ".png", ".bmp", ".webp"}


def iou(a, b):
    ix = max(0.0, min(a[2], b[2]) - max(a[0], b[0]))
    iy = max(0.0, min(a[3], b[3]) - max(a[1], b[1]))
    i = ix * iy
    u = (a[2] - a[0]) * (a[3] - a[1]) + (b[2] - b[0]) * (b[3] - b[1]) - i
    return i / u if u > 0 else 0.0


def collect(train_dir, prefix, names, egg):
    """All egg boxes in a train folder (files starting with prefix, or all if prefix is None)."""
    out = []
    for lf in sorted((train_dir / "labels").glob("*.txt")):
        if prefix and not lf.name.startswith(prefix):
            continue
        ip = next((p for p in (train_dir / "images").glob(lf.stem + ".*") if p.suffix.lower() in IMG_EXT), None)
        if ip is None:
            continue
        with Image.open(ip) as im:
            W, H = im.size
        boxes = []
        for line in lf.read_text().splitlines():
            v = line.split()
            if len(v) == 5:
                c, xc, yc, w, h = int(v[0]), *map(float, v[1:])
                boxes.append((c, (xc - w / 2) * W, (yc - h / 2) * H, (xc + w / 2) * W, (yc + h / 2) * H))
        for i, b in enumerate(boxes):
            if b[0] != egg:
                continue
            box = b[1:]
            w, h = box[2] - box[0], box[3] - box[1]
            share = w * h / (W * H)
            flags = set()
            if share > 0.25:
                flags.add("very_large")
            if share < 0.0005:
                flags.add("tiny")
            if max(w, h) > 3 * max(min(w, h), 1e-9):
                flags.add("odd_aspect")
            if any(j != i and o[0] == egg and iou(box, o[1:]) > 0.7 for j, o in enumerate(boxes)):
                flags.add("duplicate")
            if any(o[0] != egg and iou(box, o[1:]) > 0.3 for o in boxes):
                flags.add("overlaps_other_class")
            out.append({"img": ip, "W": W, "H": H, "box": box, "boxes": boxes, "idx": i, "share": share, "flags": flags})
    return out


def sheet(sample, names, path, cols=6, tile=256):
    rows = (len(sample) + cols - 1) // cols
    canvas = Image.new("RGB", (cols * tile, rows * tile), (30, 30, 30))
    for k, s in enumerate(sample):
        x1, y1, x2, y2 = s["box"]
        bw, bh = x2 - x1, y2 - y1
        cx1, cy1 = max(0, x1 - 0.5 * bw), max(0, y1 - 0.5 * bh)
        cx2, cy2 = min(s["W"], x2 + 0.5 * bw), min(s["H"], y2 + 0.5 * bh)
        with Image.open(s["img"]) as im:
            crop = im.convert("RGB").crop((int(cx1), int(cy1), int(cx2), int(cy2)))
        sc = tile / max(crop.size)
        crop = crop.resize((max(1, round(crop.size[0] * sc)), max(1, round(crop.size[1] * sc))))
        d = ImageDraw.Draw(crop)
        for j, b in enumerate(s["boxes"]):
            bb = [(b[1] - cx1) * sc, (b[2] - cy1) * sc, (b[3] - cx1) * sc, (b[4] - cy1) * sc]
            if j == s["idx"]:
                d.rectangle(bb, outline=(255, 40, 40), width=3)
            elif b[0] == s["boxes"][s["idx"]][0]:
                d.rectangle(bb, outline=(255, 170, 0), width=1)
            else:
                d.rectangle(bb, outline=(60, 140, 255), width=1)
                d.text((bb[0] + 2, bb[1] + 1), names[b[0]], fill=(120, 190, 255))
        d.text((3, 3), str(k + 1), fill=(255, 255, 0))
        canvas.paste(crop, ((k % cols) * tile, (k // cols) * tile))
    canvas.save(path)


def rates(boxes):
    n = len(boxes)
    c = {f: sum(1 for b in boxes if f in b["flags"]) for f in ("very_large", "tiny", "odd_aspect", "duplicate", "overlaps_other_class")}
    c["any_flag"] = sum(1 for b in boxes if b["flags"])
    return n, c


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--eye-ext", type=int, default=None, help="of the 30 external sample boxes, how many look wrong by eye")
    ap.add_argument("--eye-v2", type=int, default=None, help="of the 30 v2 sample boxes, how many look wrong by eye")
    ap.add_argument("--notes", default="", help="free text about what looked wrong")
    ap.add_argument("--decision-text", default="", help="replaces the automatic cap decision paragraph (use when the report is regenerated after the cap)")
    ap.add_argument("--eye-ashton", default=None, help="of the 15 sampled held-out egg boxes: 'carton,eggs,unclear' counts from looking at the sheet")
    ap.add_argument("--ashton-notes", default="", help="free text about how the held-out labels box eggs")
    a = ap.parse_args()
    names = yaml.safe_load((V3 / "data.yaml").read_text())["names"]
    egg = names.index("egg")
    ext = collect(V3 / "train", "ext3_", names, egg)
    v2 = collect(V2 / "train", None, names, egg)
    rnd = random.Random(SEED)
    s_ext, s_v2 = rnd.sample(ext, min(N, len(ext))), rnd.sample(v2, min(N, len(v2)))
    OUT.mkdir(parents=True, exist_ok=True)
    sheet(s_ext, names, OUT / "egg_audit_ext.png")
    sheet(s_v2, names, OUT / "egg_audit_v2.png")

    ash = collect(REPO / "data" / "real_fridge" / "upright", None, names, egg)
    s_ash = random.Random(SEED).sample(ash, min(15, len(ash)))
    sheet(s_ash, names, OUT / "egg_audit_ashton.png", cols=5)
    ne, ce = rates(ext)
    nv, cv = rates(v2)
    se, sv = rates(s_ext), rates(s_v2)
    pct = lambda x, n: f"{x} ({100 * x / n:.1f}%)" if n else "0"
    L = []
    w = L.append
    w("# Egg label audit\n")
    w("Produced by `ml/audit_egg.py`. External = egg boxes in the `ext3_` files of `data/cleaned_v3` train; v2 = all egg boxes in `data/cleaned_v2` train "
      "(which includes the 150 earlier `ext_` images). Heuristics are described in the script docstring. The two contact sheets "
      "(`egg_audit_ext.png`, `egg_audit_v2.png`) show 30 seeded random egg boxes each, in context: red = the audited box, orange = other egg boxes, blue = other classes. "
      "The sheets contain photo crops and are not committed.\n")
    w("## Heuristic flags over every egg box\n")
    w("| Flag | External | v2 train |\n|---|---|---|")
    w(f"| egg boxes | {ne} | {nv} |")
    for f in ("very_large", "tiny", "odd_aspect", "duplicate", "overlaps_other_class", "any_flag"):
        w(f"| {f} | {pct(ce[f], ne)} | {pct(cv[f], nv)} |")
    import numpy as np
    w(f"| median box area | {100 * float(np.median([b['share'] for b in ext])):.2f}% of the image | {100 * float(np.median([b['share'] for b in v2])):.2f}% |")
    w("")
    w("## The 30 sampled boxes per source\n")
    w(f"Heuristic flags among the 30 sampled boxes: external {se[1]['any_flag']} of {se[0]}, v2 {sv[1]['any_flag']} of {sv[0]}.")
    if a.eye_ext is not None and a.eye_v2 is not None:
        w(f"\n**Looked wrong by eye (box does not fit one egg or one tight group, wrong object, or box around other items):** external {a.eye_ext} of {se[0]}, v2 {a.eye_v2} of {sv[0]}.")
        if a.notes:
            w(f"\nNotes: {a.notes}")
    w("")
    ext_rate, v2_rate = ce["any_flag"] / ne, cv["any_flag"] / nv
    clean = ext_rate <= v2_rate + 0.05 and (a.eye_ext is not None and a.eye_ext <= 3)
    if a.decision_text:
        w("## Decision for the external egg cap\n")
        w(a.decision_text + "\n")
    else:
      w("## Decision rule for the external egg cap\n")
      w("External egg labels count as clean if the share of flagged boxes is at most the v2 share plus 5 percentage points "
        f"({100 * ext_rate:.1f}% versus {100 * v2_rate:.1f}%) and at most 3 of the 30 sampled external boxes look wrong by eye "
        + (f"({a.eye_ext} of 30)." if a.eye_ext is not None else "(not yet recorded)."))
      w(f"\nResult: **{'clean, keep the cap of 300' if clean else 'not clearly clean, lower the external egg cap to 100'}**.\n")
    import numpy as np  # noqa: F811
    w("## How Ashton boxes eggs (held-out photos, `data/real_fridge`)\n")
    w(f"{len(ash)} egg boxes in her 160 labels; median box area {100 * float(np.median([b['share'] for b in ash])):.2f}% of the image "
      f"(my v2 train {100 * float(np.median([b['share'] for b in v2])):.2f}%, external {100 * float(np.median([b['share'] for b in ext])):.2f}%); "
      f"{sum(1 for b in ash if b['share'] > 0.25)} boxes cover more than 25% of the image; "
      f"{len({b['img'].name for b in ash})} photos contain at least one egg box (median {float(np.median(list(__import__('collections').Counter(b['img'].name for b in ash).values()))):.0f} egg boxes per photo). "
      "Sheet of 15 seeded random boxes: `egg_audit_ashton.png` (photo crops, not committed).\n")
    if a.eye_ashton:
        cart, eggs_n, unc = (int(x) for x in a.eye_ashton.split(","))
        w(f"**Looked at by eye ({len(s_ash)} boxes): whole carton or tray {cart}, individual eggs or a small group of visible eggs {eggs_n}, unclear {unc}.**")
        if a.ashton_notes:
            w(f"\n{a.ashton_notes}")
        w("")
    (OUT / "egg_audit.md").write_text("\n".join(L) + "\n")
    print("external egg boxes", ne, ce, "\nv2 egg boxes", nv, cv, "\nsample flags", se[1]["any_flag"], sv[1]["any_flag"], "| decision:", "keep 300" if clean else "lower to 100")


if __name__ == "__main__":
    main()
