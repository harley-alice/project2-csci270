"""Read-only: summarize the largest near-duplicate clusters of the written cleaned dataset."""
import random
from collections import Counter, defaultdict
from pathlib import Path

import imagehash
import numpy as np
import yaml
from PIL import Image, ImageDraw, ImageFont

OUT = Path(__file__).resolve().parent / "data" / "cleaned"
SPLITS = ["train", "valid", "test"]
MAXD = 4
names = yaml.safe_load((OUT / "data.yaml").read_text())["names"]

files, H, Hf = [], [], []
for sp in SPLITS:
    for p in sorted((OUT / sp / "images").iterdir()):
        with Image.open(p) as im:
            im = im.convert("RGB")
            H.append(np.array(imagehash.phash(im).hash, dtype=bool).ravel())
            Hf.append(np.array(imagehash.phash(im.transpose(Image.FLIP_LEFT_RIGHT)).hash, dtype=bool).ravel())
        files.append((sp, p))
H, Hf = np.stack(H), np.stack(Hf)
n = len(files)
parent = list(range(n))


def find(x):
    while parent[x] != x:
        parent[x] = parent[parent[x]]
        x = parent[x]
    return x


for i in range(n):
    d = np.minimum((H[i + 1:] != H[i]).sum(1), (Hf[i + 1:] != H[i]).sum(1))
    for o in np.nonzero(d <= MAXD)[0]:
        parent[find(i + 1 + o)] = find(i)
groups = defaultdict(list)
for i in range(n):
    groups[find(i)].append(i)
clusters = sorted(groups.values(), key=len, reverse=True)
print(f"{len(clusters)} clusters; sizes of top 6: {[len(c) for c in clusters[:6]]}")


def summarize(k, mem):
    m = len(mem)
    D = np.minimum((H[mem][:, None, :] != H[mem][None, :, :]).sum(2),
                   (Hf[mem][:, None, :] != H[mem][None, :, :]).sum(2))
    iu = np.triu_indices(m, 1)
    pd = D[iu]
    deg = ((D <= MAXD).sum(1) - 1)  # direct neighbours within the cluster
    ds = Counter(files[i][1].name.split("__")[0] for i in mem)
    sp = Counter(files[i][0] for i in mem)
    cls = Counter()
    for i in mem:
        for l in (files[i][1].parent.parent / "labels" / (files[i][1].stem + ".txt")).read_text().split("\n"):
            if l.strip():
                cls[names[int(l.split()[0])]] += 1
    print(f"\n=== cluster #{k}: {m} images ===")
    print("datasets:", dict(ds), " splits:", dict(sp))
    print(f"pairwise phash dist: min {pd.min()}  median {np.median(pd):.0f}  max {pd.max()}  "
          f"(share of pairs <= {MAXD}: {(pd <= MAXD).mean():.1%})")
    print(f"direct neighbours (<= {MAXD}) per member: min {deg.min()}  median {np.median(deg):.0f}  max {deg.max()}; "
          f"members with < 5% of the cluster as direct neighbours: {(deg < 0.05 * (m - 1)).sum()} of {m}; "
          f"members with <= 2 direct neighbours: {(deg <= 2).sum()}")
    print("boxes per class:", dict(cls.most_common()), " total", sum(cls.values()))
    return cls


tot = Counter()
for sp in SPLITS:
    for p in (OUT / sp / "labels").glob("*.txt"):
        for l in p.read_text().split("\n"):
            if l.strip():
                tot[names[int(l.split()[0])]] += 1
big = summarize(1, clusters[0])
for k, c in enumerate(clusters[1:6], 2):
    summarize(k, c)
print("\nShare of each class's boxes that sit in the biggest cluster:")
for c in ("goat_cheese", "ham"):
    print(f"  {c}: {big[c]} of {tot[c]} ({big[c] / tot[c]:.0%})")
print("  top classes by share:", [(c, f"{big[c] / tot[c]:.0%}") for c, _ in sorted(big.items(), key=lambda x: -x[1] / tot[x[0]])[:8]])

# contact sheet
(OUT / "cluster_preview").mkdir(exist_ok=True)
mem = random.Random(0).sample(clusters[0], 40)
C, f = 200, ImageFont.load_default(size=10)
S = Image.new("RGB", (8 * C, 5 * (C + 12)), (50, 50, 50))
d = ImageDraw.Draw(S)
for k, i in enumerate(mem):
    sp, p = files[i]
    im = Image.open(p).convert("RGB"); im.thumbnail((C, C))
    x, y = (k % 8) * C, (k // 8) * (C + 12)
    S.paste(im, (x, y))
    d.text((x + 2, y + C), p.name.split("__", 1)[1][:34], fill=(255, 255, 0), font=f)
S.save(OUT / "cluster_preview" / "big_cluster.jpg", quality=88)
print("sheet:", OUT / "cluster_preview" / "big_cluster.jpg")
