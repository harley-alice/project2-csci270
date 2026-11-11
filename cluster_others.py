"""Group the raw Hien 'others' boxes into visual clusters for human labelling.

Read-only on data/raw. Writes data/cleaned/others_clusters/{clusters.json,sheet_NN.jpg}.
"""
import json
import random
from pathlib import Path

import numpy as np
import yaml
from PIL import Image, ImageDraw, ImageFont

ROOT = Path(__file__).resolve().parent
DS = ROOT / "data" / "raw" / "Hien_Fridge.v12i.yolov8"
OUT = ROOT / "data" / "cleaned" / "others_clusters"
SPLITS = ["train", "valid", "test"]
PAD, MIN_PX, THRESH = 0.10, 24, 0.55
CELL, COLS, ROWS = 160, 8, 5


def feat(crop):
    a = np.asarray(crop.convert("RGB").resize((12, 12)), dtype=np.float32).ravel() / 255
    a = a - a.mean()
    return a / (np.linalg.norm(a) + 1e-6)


def main():
    names = yaml.safe_load((DS / "data.yaml").read_text())["names"]
    cid = names.index("others")
    boxes = []  # dict(split, stem, line, path, cx..)
    for sp in SPLITS:
        imgs = {p.stem: p for p in (DS / sp / "images").iterdir()}
        for lf in sorted((DS / sp / "labels").glob("*.txt")):
            for i, line in enumerate(lf.read_text().splitlines()):
                p = line.split()
                if len(p) == 5 and int(float(p[0])) == cid:
                    boxes.append(dict(split=sp, stem=lf.stem, line=i, path=imgs[lf.stem], b=list(map(float, p[1:]))))
    feats, thumbs = [], []
    for bx in boxes:
        im = Image.open(bx["path"]).convert("RGB")
        W, H = im.size
        cx, cy, w, h = bx["b"]
        bw, bh = w * W, h * H
        c = im.crop((max(0, int(cx * W - bw * (.5 + PAD))), max(0, int(cy * H - bh * (.5 + PAD))),
                     min(W, int(cx * W + bw * (.5 + PAD))), min(H, int(cy * H + bh * (.5 + PAD)))))
        bx["px"] = (int(bw), int(bh))
        feats.append(feat(c))
        t = c.copy(); t.thumbnail((CELL, CELL - 14)); thumbs.append(t)
    F = np.stack(feats)
    # leader clustering: assign to nearest leader within THRESH else start a new cluster
    leaders, assign = [], []
    for f in F:
        if leaders:
            d = np.linalg.norm(np.stack(leaders) - f, axis=1)
            j = int(d.argmin())
            if d[j] < THRESH:
                assign.append(j); continue
        leaders.append(f); assign.append(len(leaders) - 1)
    clusters = {}
    for k, a in enumerate(assign):
        clusters.setdefault(a, []).append(k)
    order = sorted(clusters, key=lambda c: -len(clusters[c]))
    OUT.mkdir(parents=True, exist_ok=True)
    meta = {}
    f = ImageFont.load_default(size=11)
    rng = random.Random(0)
    cells = []
    for n, c in enumerate(order):
        mem = clusters[c]
        rep = max(mem, key=lambda k: boxes[k]["px"][0] * boxes[k]["px"][1])  # largest = clearest
        meta[n] = [dict(split=boxes[k]["split"], stem=boxes[k]["stem"], line=boxes[k]["line"]) for k in mem]
        cells.append((n, len(mem), thumbs[rep], Path(boxes[rep]["path"]).stem.split(".rf.")[0]))
    per = COLS * ROWS
    for s in range(0, len(cells), per):
        S = Image.new("RGB", (COLS * CELL, ROWS * CELL), (60, 60, 60))
        for i, (n, cnt, t, name) in enumerate(cells[s:s + per]):
            x, y = (i % COLS) * CELL, (i // COLS) * CELL
            S.paste(t, (x + (CELL - t.width) // 2, y))
            d = ImageDraw.Draw(S)
            d.rectangle([x, y + CELL - 14, x + CELL, y + CELL], fill=(0, 0, 0))
            d.text((x + 2, y + CELL - 14), f"#{n} n={cnt} {name[:12]}", fill=(255, 255, 0), font=f)
        S.save(OUT / f"sheet_{s // per + 1:02d}.jpg", quality=88)
    (OUT / "clusters.json").write_text(json.dumps(meta))
    print(f"{len(boxes)} boxes -> {len(clusters)} clusters; sizes top10:", [len(clusters[c]) for c in order[:10]])
    print("sheets:", (len(cells) + per - 1) // per, "in", OUT)


if __name__ == "__main__":
    main()
