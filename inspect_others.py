"""Read-only inspection of the dropped "others" class. Output: data/cleaned/others_preview/."""
import random
import re
import statistics
from collections import Counter, defaultdict
from pathlib import Path

import yaml
from PIL import Image, ImageDraw, ImageFont

from class_map import CLASS_MAP

ROOT = Path(__file__).resolve().parent
RAW = ROOT / "data" / "raw"
OUT = ROOT / "data" / "cleaned" / "others_preview"
SPLITS = ["train", "valid", "test"]
IMG_EXT = {".jpg", ".jpeg", ".png", ".bmp", ".webp"}
CATCHALL = re.compile(r"^(others?|misc\w*|unknown|food)$", re.I)
CELL, COLS, ROWS, PAD, MIN_PX, N_IMAGES = 200, 5, 4, 0.10, 24, 60


def font(size):
    try:
        return ImageFont.load_default(size=size)
    except TypeError:
        return ImageFont.load_default()


def load_names(ds):
    names = yaml.safe_load((ds / "data.yaml").read_text())["names"]
    return [names[k] for k in sorted(names)] if isinstance(names, dict) else names


def find_boxes(ds, cid):
    """All (image_path, cx, cy, w, h) normalized boxes of class id cid in a dataset."""
    out = []
    for sp in SPLITS:
        idir, ldir = ds / sp / "images", ds / sp / "labels"
        if not ldir.exists():
            continue
        imgs = {p.stem: p for p in idir.iterdir() if p.suffix.lower() in IMG_EXT}
        for lf in sorted(ldir.glob("*.txt")):
            for line in lf.read_text().splitlines():
                p = line.split()
                if len(p) == 5 and int(float(p[0])) == cid and lf.stem in imgs:
                    out.append((imgs[lf.stem], *map(float, p[1:])))
    return out


def crop_box(img, cx, cy, w, h):
    W, H = img.size
    bw, bh = w * W, h * H
    x1, y1 = cx * W - bw / 2 - bw * PAD, cy * H - bh / 2 - bh * PAD
    x2, y2 = cx * W + bw / 2 + bw * PAD, cy * H + bh / 2 + bh * PAD
    return img.crop((max(0, int(x1)), max(0, int(y1)), min(W, int(x2)), min(H, int(y2)))), int(bw), int(bh)


def cell(crop, label, f):
    c = Image.new("RGB", (CELL, CELL), (128, 128, 128))
    crop = crop.copy()
    crop.thumbnail((CELL, CELL - 28))
    c.paste(crop, ((CELL - crop.width) // 2, (CELL - 28 - crop.height) // 2))
    d = ImageDraw.Draw(c)
    d.rectangle([0, CELL - 28, CELL, CELL], fill=(0, 0, 0))
    d.text((3, CELL - 27), label[0], fill=(255, 255, 255), font=f)
    d.text((3, CELL - 14), label[1], fill=(255, 255, 0), font=f)
    return c


def sheet(items, path, f):
    S = Image.new("RGB", (COLS * CELL, ROWS * CELL), (60, 60, 60))
    for i, (crop, lab) in enumerate(items):
        S.paste(cell(crop, lab, f), ((i % COLS) * CELL, (i // COLS) * CELL))
    S.save(path, quality=90)


def short(p, n=26):
    s = p.stem.split(".rf.")[0]
    return s if len(s) <= n else s[:n - 1] + "…"


def main():
    # ---- step 1: find catch-all classes and everything dropped ----
    found = {}  # (ds, cid) -> (name, boxes list)
    print("== Catch-all classes ==")
    for ds in sorted(p for p in RAW.iterdir() if p.is_dir()):
        for cid, n in enumerate(load_names(ds)):
            if CATCHALL.match(n):
                bx = find_boxes(ds, cid)
                found[(ds, cid)] = (n, bx)
                print(f"{ds.name}: id {cid} '{n}' boxes={len(bx)} images={len({b[0] for b in bx})}")
    if not found:
        print("none found")
    print("\n== class_map entries mapped to None, with raw box counts ==")
    for dname, m in CLASS_MAP.items():
        names = load_names(RAW / dname)
        for src, dst in m.items():
            if dst is None:
                bx = find_boxes(RAW / dname, names.index(src))
                print(f"{dname}: '{src}' -> None  boxes={len(bx)} images={len({b[0] for b in bx})}")

    # ---- step 2: sample ----
    others = {k: v for k, v in found.items() if v[0].lower() == "others"}
    per_ds = {k[0].name: v[1] for k, v in others.items()}
    rng = random.Random(0)
    imgs = []  # (ds_name, image path, [boxes])
    for dn, bx in per_ds.items():
        by = defaultdict(list)
        for b in bx:
            by[b[0]].append(b)
        imgs += [(dn, p, v) for p, v in sorted(by.items())]
    rng.shuffle(imgs)
    # spread across datasets: round-robin over per-dataset shuffled lists
    groups = defaultdict(list)
    for t in imgs:
        groups[t[0]].append(t)
    order = []
    while any(groups.values()):
        for g in groups.values():
            if g:
                order.append(g.pop())
    f = font(11)
    crops, sizes = [], []
    for dn, p, boxes in order:
        if len(crops) >= N_IMAGES:
            break
        im = Image.open(p).convert("RGB")
        ok = []
        for b in boxes:
            c, bw, bh = crop_box(im, *b[1:])
            if bw >= MIN_PX and bh >= MIN_PX:
                ok.append((c, bw, bh))
        if ok:
            c, bw, bh = rng.choice(ok)
            crops.append((c, (f"{short(p)}", f"{bw}x{bh}px  ({len(boxes)} 'others' in img)")))
    OUT.mkdir(parents=True, exist_ok=True)
    for i in range(3):
        sheet(crops[i * 20:(i + 1) * 20], OUT / f"sheet_{i + 1}.jpg", f)

    # ---- step 3: largest by pixel area ----
    allb = []
    for dn, bx in per_ds.items():
        for p, cx, cy, w, h in bx:
            with Image.open(p) as im:
                W, H = im.size
            allb.append((w * W * h * H, p, cx, cy, w, h))
    allb.sort(key=lambda t: -t[0])
    big = []
    for area, p, cx, cy, w, h in allb[:20]:
        c, bw, bh = crop_box(Image.open(p).convert("RGB"), cx, cy, w, h)
        big.append((c, (short(p), f"{bw}x{bh}px")))
    sheet(big, OUT / "sheet_largest.jpg", f)

    # ---- step 5: stats ----
    print("\n== Summary ==")
    for (ds, cid), (n, bx) in others.items():
        ws, hs, per_img = [], [], Counter()
        for p, cx, cy, w, h in bx:
            with Image.open(p) as im:
                W, H = im.size
            ws.append(w * W); hs.append(h * H); per_img[p] += 1
        top = per_img.most_common(5)
        top_share = sum(c for _, c in top) / len(bx)
        small = sum(1 for a, b in zip(ws, hs) if a < MIN_PX or b < MIN_PX)
        print(f"{ds.name}: boxes={len(bx)} images={len(per_img)} "
              f"median box={statistics.median(ws):.0f}x{statistics.median(hs):.0f}px "
              f"boxes/img median={statistics.median(per_img.values())} max={top[0][1]} "
              f"top-5 images hold {top_share:.1%}; boxes <{MIN_PX}px side: {small}")
        by_split = Counter(p.parent.parent.name for p, *_ in bx)
        print("  boxes by split:", dict(by_split))
        both = sum(1 for p in per_img if any(
            int(float(l.split()[0])) != cid for l in (p.parent.parent / "labels" / (p.stem + ".txt")).read_text().splitlines() if l.strip()))
        print(f"  images that also have other classes (so would survive): {both} of {len(per_img)}")
    print(f"\n{len(crops)} crops on sheets 1-3; 20 largest on sheet_largest.jpg")
    print(f"Output folder: {OUT}")


if __name__ == "__main__":
    main()
