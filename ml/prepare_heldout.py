"""Set up the 160-photo HELD-OUT real-fridge evaluation set (never used for training or tuning).

Copies the EXIF-upright images and their YOLO labels into data/real_fridge/upright/{images,labels}, writes
data/real_fridge/heldout_160.txt (one repo-relative image path per line) and data/real_fridge/data_heldout.yaml, and verifies:
  * every upright copy has the size of exif_transpose(original) and (nearly) the same pixels
  * every label file equals the original annotation file and is valid YOLO (5 values, class id in range, coordinates in [0,1])
  * the class order equals food_classes.txt and data/cleaned_v3/data.yaml
Originals are only read.

Usage:
    python ml/prepare_heldout.py --src <fridge_qa_reproducibility>/images_original --labels <fridge_qa_reproducibility>/ground_truth \\
        --classes <fridge_qa_reproducibility>/food_classes.txt --upright <folder holding upright/images and upright/labels>
"""
import argparse
import hashlib
import shutil
from pathlib import Path

import numpy as np
import yaml
from PIL import Image, ImageOps

REPO = Path(__file__).resolve().parents[1]
DEST = REPO / "data" / "real_fridge"
IMG_EXT = {".jpg", ".jpeg", ".png"}


def md5(p):
    return hashlib.md5(Path(p).read_bytes()).hexdigest()


def small(im):
    return np.asarray(im.convert("L").resize((32, 32)), dtype=float)


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--src", required=True, help="original photos (EXIF intact)")
    ap.add_argument("--labels", required=True, help="original YOLO annotation files")
    ap.add_argument("--classes", required=True, help="food_classes.txt used for the annotations")
    ap.add_argument("--upright", required=True, help="folder with upright/images and upright/labels (EXIF applied)")
    a = ap.parse_args()
    src, lab, up = Path(a.src).expanduser(), Path(a.labels).expanduser(), Path(a.upright).expanduser()
    names = yaml.safe_load((REPO / "data" / "cleaned_v3" / "data.yaml").read_text())["names"]
    cls_file = Path(a.classes).expanduser().read_text().splitlines()

    rows = []

    def check(name, ok, detail=""):
        rows.append((name, "PASS" if ok else "FAIL", detail))

    imgs = sorted(p for p in src.iterdir() if p.suffix.lower() in IMG_EXT)
    check("160 original photos", len(imgs) == 160, f"{len(imgs)} found")
    check("class order: food_classes.txt == data/cleaned_v3/data.yaml", cls_file == names, f"{len(names)} classes")

    size_bad, pix_bad, lab_missing, lab_diff, lab_bad, rotated = [], [], [], [], 0, 0
    for p in imgs:
        upimg = up / "upright" / "images" / f"{p.stem}.jpg"
        uplab = up / "upright" / "labels" / f"{p.stem}.txt"
        orig_lab = lab / f"{p.stem}.txt"
        with Image.open(p) as im:
            rotated += int(im.getexif().get(0x0112, 1) != 1)
            t = ImageOps.exif_transpose(im).convert("RGB")
        if not upimg.exists():
            size_bad.append(p.name)
            continue
        with Image.open(upimg) as u:
            u = u.convert("RGB")
            if u.size != t.size:
                size_bad.append(p.name)
            elif float(np.abs(small(u) - small(t)).mean()) > 6.0:
                pix_bad.append(p.name)
        if not uplab.exists() or not orig_lab.exists():
            lab_missing.append(p.name)
            continue
        if md5(uplab) != md5(orig_lab):
            lab_diff.append(p.name)
        for line in orig_lab.read_text().splitlines():
            v = line.split()
            if v and (len(v) != 5 or not 0 <= int(v[0]) < len(names) or not all(0 <= float(x) <= 1 for x in v[1:])):
                lab_bad += 1
    check("upright copy size == exif_transpose(original) size", not size_bad, f"{len(size_bad)} mismatches ({rotated} photos carry a rotation tag)")
    check("upright copy pixels match exif_transpose(original)", not pix_bad, f"{len(pix_bad)} differ")
    check("every photo has a label file", not lab_missing, f"{len(lab_missing)} missing")
    check("labels identical to the original annotations", not lab_diff, f"{len(lab_diff)} differ")
    check("label lines valid (5 values, class id in range, coordinates in [0,1])", lab_bad == 0, f"{lab_bad} bad lines")

    ok_so_far = all(s == "PASS" for _, s, _ in rows)
    if ok_so_far:
        (DEST / "upright" / "images").mkdir(parents=True, exist_ok=True)
        (DEST / "upright" / "labels").mkdir(parents=True, exist_ok=True)
        for p in imgs:
            for kind, ext in (("images", ".jpg"), ("labels", ".txt")):
                d = DEST / "upright" / kind / f"{p.stem}{ext}"
                if not d.exists():
                    shutil.copy2(up / "upright" / kind / f"{p.stem}{ext}", d)
        (DEST / "heldout_160.txt").write_text("".join(f"data/real_fridge/upright/images/{p.stem}.jpg\n" for p in imgs))
        (DEST / "data_heldout.yaml").write_text(
            "# HELD-OUT EVALUATION SET: 160 real-fridge photos. Never use these for training or tuning.\n"
            "# Images are EXIF-upright; labels follow the upright view. Paths are relative to this file.\n"
            "# The 'train' key is left out on purpose: Ultralytics refuses to train without it. Evaluate with\n"
            "#   python ml/diagnose_real_fridge.py --data data/real_fridge/data_heldout.yaml\n"
            + yaml.safe_dump({"val": "upright/images", "test": "upright/images", "nc": len(names), "names": names}, sort_keys=False))
        listed = (DEST / "heldout_160.txt").read_text().splitlines()
        check("heldout_160.txt lists 160 existing files", len(listed) == 160 and all((REPO / l).exists() for l in listed))
        check("data_heldout.yaml has relative paths only", not any(str(yaml.safe_load((DEST / "data_heldout.yaml").read_text())[k]).startswith("/") for k in ("val", "test")))
    print("HELD-OUT SET CHECKS")
    for n, s, d in rows:
        print(f"  [{s}] {n} {d}")
    raise SystemExit(0 if all(s == "PASS" for _, s, _ in rows) else 1)


if __name__ == "__main__":
    main()
