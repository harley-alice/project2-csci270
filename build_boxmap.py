"""Build others_boxmap.json from all relabel stages in others_relabel.py, plus stage-3 verify sheets.

Needs data/cleaned/others_clusters/{clusters,refined}.json from cluster_others.py / refine_others.py.
"""
import json, random
from pathlib import Path
from PIL import Image
from others_relabel import CLUSTER_LABELS, REFINED_LABELS, STAGE3_LABELS

ROOT = Path(__file__).resolve().parent
DS = ROOT / "data" / "raw" / "Hien_Fridge.v12i.yolov8"
OUT = ROOT / "data" / "cleaned" / "others_clusters"
meta, ref = json.load(open(OUT / "clusters.json")), json.load(open(OUT / "refined.json"))
boxmap, stage3 = {}, {}


def add(cls, boxes, store=None):
    for b in boxes:
        k = f"{b['split']}/{b['stem']}/{b['line']}"
        assert boxmap.get(k, cls) == cls, f"conflict at {k}"
        boxmap[k] = cls
        if store is not None:
            store.setdefault(cls, []).append(b)


add("jar", [b for i in CLUSTER_LABELS["jar"] for b in meta[str(i)]])
for cls, keys in REFINED_LABELS.items():
    add(cls, [b for k in keys for b in ref[k]])
for cls, ids in STAGE3_LABELS.items():
    add(cls, [b for i in ids for b in meta[str(i)]], stage3)
json.dump(boxmap, open(ROOT / "others_boxmap.json", "w"), indent=0)
print("total relabelled boxes:", len(boxmap))

rng, C = random.Random(0), 150
for cls, mem in stage3.items():
    print(f"stage3 {cls}: {len(mem)} boxes")
    S = Image.new("RGB", (8 * C, 5 * C), (60, 60, 60))
    for k, m in enumerate(rng.sample(mem, min(40, len(mem)))):
        ip = next((DS / m["split"] / "images").glob(m["stem"] + ".*"))
        im = Image.open(ip).convert("RGB"); W, H = im.size
        cx, cy, w, h = map(float, (DS / m["split"] / "labels" / (m["stem"] + ".txt")).read_text().splitlines()[m["line"]].split()[1:])
        c = im.crop((max(0, int(cx*W-w*W*.55)), max(0, int(cy*H-h*H*.55)), min(W, int(cx*W+w*W*.55)), min(H, int(cy*H+h*H*.55))))
        c.thumbnail((C, C)); S.paste(c, ((k % 8) * C, (k // 8) * C))
    S.save(OUT / f"verify_stage3_{cls}.jpg", quality=88)
