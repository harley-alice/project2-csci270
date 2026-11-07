"""Final per-class counts and 40-sample verification sheets (read-only on data/raw)."""
import json, random
from pathlib import Path
from PIL import Image
from others_relabel import CLUSTER_LABELS, REFINED_LABELS

ROOT = Path(__file__).resolve().parent
DS = ROOT / "data" / "raw" / "Hien_Fridge.v12i.yolov8"
OUT = ROOT / "data" / "cleaned" / "others_clusters"
meta, ref = json.load(open(OUT / "clusters.json")), json.load(open(OUT / "refined.json"))
final = {"jar": [m for i in CLUSTER_LABELS["jar"] for m in meta[str(i)]]}
for cls, keys in REFINED_LABELS.items():
    final[cls] = [m for k in keys for m in ref[k]]
rng, C = random.Random(0), 150
tot = 0
for cls, mem in final.items():
    tot += len(mem)
    print(f"{cls}: {len(mem)} boxes, {len({(m['split'], m['stem']) for m in mem})} images")
    S = Image.new("RGB", (8 * C, 5 * C), (60, 60, 60))
    for k, m in enumerate(rng.sample(mem, min(40, len(mem)))):
        ip = next((DS / m["split"] / "images").glob(m["stem"] + ".*"))
        im = Image.open(ip).convert("RGB"); W, H = im.size
        cx, cy, w, h = map(float, (DS / m["split"] / "labels" / (m["stem"] + ".txt")).read_text().splitlines()[m["line"]].split()[1:])
        c = im.crop((max(0, int(cx*W-w*W*.55)), max(0, int(cy*H-h*H*.55)), min(W, int(cx*W+w*W*.55)), min(H, int(cy*H+h*H*.55))))
        c.thumbnail((C, C)); S.paste(c, ((k % 8) * C, (k // 8) * C))
    S.save(OUT / f"verify_{cls}.jpg", quality=88)
print("total relabelled boxes:", tot, "of 4330 'others'")
