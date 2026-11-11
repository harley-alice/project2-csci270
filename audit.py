"""Read-only audit of the raw Roboflow datasets in ./data/raw/."""
from collections import Counter
from pathlib import Path
import yaml

RAW = Path(__file__).parent / "data" / "raw"
SPLITS = ["train", "valid", "test"]
IMG_EXT = {".jpg", ".jpeg", ".png", ".bmp", ".webp"}


def main():
    grand = Counter()
    for ds in sorted(p for p in RAW.iterdir() if p.is_dir()):
        cfg = yaml.safe_load((ds / "data.yaml").read_text())
        names = cfg["names"]
        if isinstance(names, dict):
            names = [names[k] for k in sorted(names)]
        print(f"\n=== {ds.name} ===")
        print(f"classes ({len(names)}): {names}")
        boxes = Counter()
        imgs_per_split = {}
        for sp in SPLITS:
            idir, ldir = ds / sp / "images", ds / sp / "labels"
            imgs = [p for p in idir.glob("*") if p.suffix.lower() in IMG_EXT] if idir.exists() else []
            imgs_per_split[sp] = len(imgs)
            if ldir.exists():
                for lf in ldir.glob("*.txt"):
                    for line in lf.read_text().splitlines():
                        parts = line.split()
                        if parts:
                            boxes[names[int(float(parts[0]))]] += 1
        print("images per split:", imgs_per_split, "total:", sum(imgs_per_split.values()))
        print("boxes per class:")
        for n in names:
            print(f"  {n:20s} {boxes[n]}")
        print(f"  total boxes: {sum(boxes.values())}")
        for n, c in boxes.items():
            grand[n] += c
    print("\n=== combined boxes by raw class name (same-name classes summed) ===")
    for n, c in sorted(grand.items(), key=lambda x: -x[1]):
        print(f"  {n:20s} {c}")


if __name__ == "__main__":
    main()
