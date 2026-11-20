"""Propose pseudo-fridge groups for the 160 held-out real-fridge photos. PROPOSAL ONLY: Ashton must confirm.

Fridge IDs were not supplied, so photos are clustered by visual similarity: a combined distance of
  0.5 * Hellinger distance between 4-quadrant HSV colour histograms + 0.5 * min(1, 2 * phash Hamming / 64),
average-linkage clustering (scipy), cut at 0.72 (fine groups) and 0.76 (coarser groups). No model download or install is needed.
Camera model and capture day from the original photos' EXIF are listed as hints and as a sanity check (they are NOT used to
cluster, and GPS is never read). The groups are not used for any split yet.

Outputs:
    data/real_fridge/fridge_groups_proposed.csv
    ml/runs/real_fridge_diagnostics/fridge_groups_note.md

Usage:  python ml/propose_fridge_groups.py [--src <folder with the original photos, for the EXIF hints>]
"""
import argparse
import collections
import csv
import random
import re
from pathlib import Path

import imagehash
import numpy as np
from PIL import Image
from scipy.cluster.hierarchy import fcluster, linkage
from scipy.spatial.distance import squareform

REPO = Path(__file__).resolve().parents[1]
LIST = REPO / "data" / "real_fridge" / "heldout_160.txt"
OUT_CSV = REPO / "data" / "real_fridge" / "fridge_groups_proposed.csv"
OUT_MD = REPO / "ml" / "runs" / "real_fridge_diagnostics" / "fridge_groups_note.md"
FINE, COARSE = 0.72, 0.76
CUTS = (0.65, 0.70, 0.72, 0.74, 0.76, 0.80)


def features(path):
    with Image.open(path) as im:
        im = im.convert("RGB")
        im.thumbnail((256, 256))
        hsv = np.asarray(im.convert("HSV"))
        h, w = hsv.shape[:2]
        parts = []
        for ys, xs in ((slice(0, h // 2), slice(0, w // 2)), (slice(0, h // 2), slice(w // 2, w)),
                       (slice(h // 2, h), slice(0, w // 2)), (slice(h // 2, h), slice(w // 2, w))):
            hist, _ = np.histogramdd(hsv[ys, xs].reshape(-1, 3), bins=(8, 4, 4), range=((0, 256),) * 3)
            parts.append(hist.ravel() / max(hist.sum(), 1))
        return np.concatenate(parts) / 4, np.array(imagehash.phash(im).hash, dtype=bool).ravel()


def family(name):
    if re.match(r"^\d{11}__[0-9A-F-]{36}", name):
        return "iOS prefix + UUID"
    if re.match(r"^[0-9A-F]{8}-[0-9A-F]{4}-", name):
        return "bare UUID"
    if re.match(r"^IMG_\d+", name):
        return "IMG_####"
    if re.match(r"^1000\d+", name):
        return "1000###### (Android)"
    return "other"


def exif_hint(src, stem):
    """(camera model, capture day) from the original photo, or ('', '')."""
    if src is None:
        return "", ""
    p = next((q for q in src.glob(stem + ".*")), None)
    if p is None:
        return "", ""
    with Image.open(p) as im:
        ex = im.getexif()
        sub = ex.get_ifd(0x8769)
        return (ex.get(0x0110) or "").strip(), (sub.get(0x9003) or ex.get(0x0132) or "")[:10].replace(":", "-")


def pair_agreement(groups, values):
    """Share of within-group pairs (both values known) that agree, versus the same share over all pairs."""
    members = collections.defaultdict(list)
    for i, g in enumerate(groups):
        members[g].append(i)
    known = lambda i, j: bool(values[i]) and bool(values[j])
    within = [(i, j) for ix in members.values() for k, i in enumerate(ix) for j in ix[k + 1:] if known(i, j)]
    every = [(i, j) for i in range(len(values)) for j in range(i + 1, len(values)) if known(i, j)]
    rate = lambda ps: sum(values[i] == values[j] for i, j in ps) / len(ps) if ps else float("nan")
    return rate(within), len(within), rate(every), len(every)


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--src", default=None, help="folder with the original photos (for camera/date hints)")
    a = ap.parse_args()
    src = Path(a.src).expanduser() if a.src else None
    files = [REPO / l for l in LIST.read_text().splitlines()]
    H, PH = zip(*[features(p) for p in files])
    H, PH = np.array(H), np.array(PH)
    n = len(files)
    sq = np.sqrt(H)
    dh = np.sqrt(0.5 * ((sq[:, None, :] - sq[None, :, :]) ** 2).sum(-1))
    dp = (PH[:, None, :] != PH[None, :, :]).sum(-1) / 64.0
    D = 0.5 * dh + 0.5 * np.minimum(1, 2 * dp)
    Z = linkage(squareform(D, checks=False), "average")
    fine, coarse = fcluster(Z, FINE, "distance"), fcluster(Z, COARSE, "distance")
    sizes = collections.Counter(fine)
    order = {g: f"G{k + 1:02d}" for k, (g, _) in enumerate(sizes.most_common())}
    corder = {g: f"C{k + 1:02d}" for k, (g, _) in enumerate(collections.Counter(coarse).most_common())}
    hints = [exif_hint(src, p.stem) for p in files]
    models, days = [h[0] for h in hints], [h[1] for h in hints]

    OUT_CSV.parent.mkdir(parents=True, exist_ok=True)
    with OUT_CSV.open("w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["image", "proposed_group", "group_size", "coarse_group", "camera_model_hint", "capture_day_hint", "filename_family", "note"])
        for i in sorted(range(n), key=lambda i: (order[fine[i]], files[i].name)):
            w.writerow([str(files[i].relative_to(REPO)), order[fine[i]], sizes[fine[i]], corder[coarse[i]], models[i], days[i],
                        family(files[i].name), "PROPOSED from visual similarity - Ashton to confirm"])

    g_fine = [order[x] for x in fine]
    mrate, mn, mbase, mbn = pair_agreement(g_fine, models)
    drate, dn, dbase, dbn = pair_agreement(g_fine, days)
    rnd = random.Random(270)
    shuf = list(g_fine)
    rnd.shuffle(shuf)
    smrate = pair_agreement(shuf, models)[0]
    sdrate = pair_agreement(shuf, days)[0]
    L = ["# Proposed pseudo-fridge groups (not confirmed)\n",
         "Produced by `ml/propose_fridge_groups.py` for the 160 held-out photos. **Ashton should confirm these groups.** They come from visual similarity only "
         "(colour histograms plus phash), because fridge IDs were not supplied, and they are **not used for any split yet**. "
         "Output: `data/real_fridge/fridge_groups_proposed.csv`.\n",
         "## Cut sensitivity (average linkage on the combined distance)\n",
         "| Cut | Groups | Singletons | Largest group | Groups with 5+ photos |\n|---|---|---|---|---|"]
    for t in CUTS:
        c = collections.Counter(fcluster(Z, t, "distance"))
        L.append(f"| {t} | {len(c)} | {sum(1 for v in c.values() if v == 1)} | {max(c.values())} | {sum(1 for v in c.values() if v >= 5)} |")
    L.append(f"\nProposed groups use the {FINE} cut ({len(sizes)} groups: sizes {sorted(sizes.values(), reverse=True)}); `coarse_group` uses the {COARSE} cut "
             f"({len(set(coarse))} groups). Above about 0.74 one giant cluster forms, so the cut cannot be raised much.\n")
    L.append("## Sanity check against EXIF hints (not used for clustering)\n")
    L.append(f"Photos with a camera model: {sum(1 for m in models if m)} of {n}; with a capture day: {sum(1 for d in days if d)} of {n}.\n")
    L.append("| Hint | Pairs inside a proposed group that agree | All pairs that agree | Same measure with shuffled group labels |\n|---|---|---|---|")
    L.append(f"| camera model | {100 * mrate:.0f}% ({mn} pairs) | {100 * mbase:.0f}% ({mbn} pairs) | {100 * smrate:.0f}% |")
    L.append(f"| capture day | {100 * drate:.0f}% ({dn} pairs) | {100 * dbase:.0f}% ({dbn} pairs) | {100 * sdrate:.0f}% |")
    no_signal = mrate <= smrate + 0.03 and drate <= sdrate + 0.03
    L.append("\n**Result:** " + ("pairs inside a proposed group agree on camera model and capture day no more often than pairs with shuffled labels "
             f"(camera {100 * mrate:.0f}% vs {100 * smrate:.0f}%, day {100 * drate:.0f}% vs {100 * sdrate:.0f}%), so this check gives **no support** that the groups follow fridges. "
             if no_signal else
             "pairs inside a proposed group agree on camera model or capture day more often than shuffled labels, a weak sign that the groups follow fridges. ")
             + "The check is also weak by nature: one person with one phone can photograph several fridges on one day, so agreement is not proof either way. "
             "The groups can over-split one fridge (shelves look different) and can merge two fridges with similar white interiors. "
             "Treat them only as a starting point for Ashton to correct; they are not fridge IDs and must not be used for a split until she confirms.\n")
    OUT_MD.write_text("\n".join(L) + "\n")
    print(f"groups: fine {len(sizes)} (largest {max(sizes.values())}, singletons {sum(1 for v in sizes.values() if v == 1)}), coarse {len(set(coarse))}")
    print(f"camera-model agreement inside groups {100 * mrate:.0f}% vs all pairs {100 * mbase:.0f}% vs shuffled {100 * smrate:.0f}%")
    print(f"capture-day agreement inside groups {100 * drate:.0f}% vs all pairs {100 * dbase:.0f}% vs shuffled {100 * sdrate:.0f}%")


if __name__ == "__main__":
    main()
