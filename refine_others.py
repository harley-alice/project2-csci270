"""Re-cluster the proposed fruit clusters with a stricter colour (hue) feature, for relabelling review.

Read-only on data/raw. Writes data/cleaned/others_clusters/refined.json and refined_<prior>_NN.jpg.
"""
import colorsys, json, random
from pathlib import Path
import numpy as np
from PIL import Image, ImageDraw, ImageFont
from others_relabel import CLUSTER_LABELS

ROOT = Path(__file__).resolve().parent
DS = ROOT / "data" / "raw" / "Hien_Fridge.v12i.yolov8"
OUT = ROOT / "data" / "cleaned" / "others_clusters"
THRESH, T, COLS, ROWS = 0.35, 80, 4, 6
meta = json.load(open(OUT / "clusters.json"))
font = ImageFont.load_default(size=11)
rng = random.Random(0)


def crop(m):
    ip = next((DS / m["split"] / "images").glob(m["stem"] + ".*"))
    im = Image.open(ip).convert("RGB"); W, H = im.size
    cx, cy, w, h = map(float, (DS / m["split"] / "labels" / (m["stem"] + ".txt")).read_text().splitlines()[m["line"]].split()[1:])
    return im.crop((max(0, int(cx*W-w*W*.55)), max(0, int(cy*H-h*H*.55)), min(W, int(cx*W+w*W*.55)), min(H, int(cy*H+h*H*.55))))


def feat(c):
    hsv = np.asarray(c.resize((16, 16)).convert("HSV"), dtype=np.float32) / 255
    h, s, v = hsv[..., 0].ravel(), hsv[..., 1].ravel(), hsv[..., 2].ravel()
    hist = np.histogram(h, bins=18, range=(0, 1), weights=s * v)[0]
    hist = hist / (hist.sum() + 1e-6)
    rgb = np.asarray(c.resize((6, 6)), dtype=np.float32).ravel() / 255
    return np.concatenate([hist * 2.0, (rgb - rgb.mean()) / 6])


refined = {}
for prior, ids in CLUSTER_LABELS.items():
    if prior == "jar":
        continue
    mem = [dict(m, prior=prior) for i in ids for m in meta[str(i)]]
    crops = [crop(m) for m in mem]
    F = np.stack([feat(c) for c in crops])
    leaders, assign = [], []
    for f in F:
        if leaders:
            d = np.linalg.norm(np.stack(leaders) - f, axis=1); j = int(d.argmin())
            if d[j] < THRESH:
                assign.append(j); continue
        leaders.append(f); assign.append(len(leaders) - 1)
    groups = {}
    for k, a in enumerate(assign):
        groups.setdefault(a, []).append(k)
    order = sorted(groups, key=lambda g: -len(groups[g]))
    cells = []
    for n, g in enumerate(order):
        ks = groups[g]
        refined[f"{prior}:{n}"] = [mem[k] for k in ks]
        pick = rng.sample(ks, min(3, len(ks)))
        cells.append((f"{prior}:{n}", len(ks), [crops[k] for k in pick]))
    per = COLS * ROWS
    for s in range(0, len(cells), per):
        S = Image.new("RGB", (COLS * 3 * T, ROWS * (T + 14)), (60, 60, 60)); d = ImageDraw.Draw(S)
        for i, (name, cnt, cs) in enumerate(cells[s:s + per]):
            x, y = (i % COLS) * 3 * T, (i // COLS) * (T + 14)
            for j, c in enumerate(cs):
                c = c.copy(); c.thumbnail((T, T)); S.paste(c, (x + j * T, y))
            d.text((x + 2, y + T), f"{name} n={cnt}", fill=(255, 255, 0), font=font)
        S.save(OUT / f"refined_{prior}_{s // per + 1:02d}.jpg", quality=88)
    print(prior, len(mem), "boxes ->", len(groups), "subclusters")
json.dump(refined, open(OUT / "refined.json", "w"))
