"""Draw boxes on 50 random cleaned images into ./data/cleaned/preview/."""
import random
import shutil
from pathlib import Path

import yaml
from PIL import Image, ImageDraw

OUT = Path(__file__).resolve().parent / "data" / "cleaned"
N = 50


def main():
    names = yaml.safe_load((OUT / "data.yaml").read_text())["names"]
    imgs = sorted(p for sp in ("train", "valid", "test") for p in (OUT / sp / "images").iterdir())
    random.Random(0).shuffle(imgs)
    pv = OUT / "preview"
    shutil.rmtree(pv, ignore_errors=True)
    pv.mkdir()
    for p in imgs[:N]:
        im = Image.open(p).convert("RGB")
        W, H = im.size
        d = ImageDraw.Draw(im)
        lab = p.parent.parent / "labels" / (p.stem + ".txt")
        for line in lab.read_text().splitlines():
            c, cx, cy, w, h = line.split()
            cx, cy, w, h = float(cx) * W, float(cy) * H, float(w) * W, float(h) * H
            box = [cx - w / 2, cy - h / 2, cx + w / 2, cy + h / 2]
            d.rectangle(box, outline=(255, 0, 0), width=3)
            d.text((box[0] + 3, box[1] + 3), names[int(c)], fill=(255, 255, 0))
        im.save(pv / (p.stem + ".jpg"))
    print(f"Wrote {min(N, len(imgs))} previews to {pv}")


if __name__ == "__main__":
    main()
