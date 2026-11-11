"""Plot train vs val box/cls/dfl loss from an Ultralytics results.csv.

Usage: python ml/plot_losses.py [run_name]   (default: baseline_v8n)
Saves ml/runs/<run_name>/loss_curves.png
"""
import csv
import sys
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

run = sys.argv[1] if len(sys.argv) > 1 else "baseline_v8n"
run_dir = Path(__file__).resolve().parent / "runs" / run

with open(run_dir / "results.csv", newline="") as f:
    rows = [{k.strip(): v.strip() for k, v in r.items()} for r in csv.DictReader(f)]

epochs = [int(float(r["epoch"])) for r in rows]
fig, axes = plt.subplots(2, 3, figsize=(15, 8), sharex=True)
for col, kind in enumerate(["box", "cls", "dfl"]):
    for row, split in enumerate(["train", "val"]):
        key = f"{split}/{kind}_loss"
        ax = axes[row][col]
        ax.plot(epochs, [float(r[key]) for r in rows], marker="o", ms=3,
                color="tab:blue" if split == "train" else "tab:orange")
        ax.set_title(key)
        ax.grid(alpha=0.3)
        if row == 1:
            ax.set_xlabel("epoch")
fig.suptitle(f"Loss curves: {run}")
fig.tight_layout()
out = run_dir / "loss_curves.png"
fig.savefig(out, dpi=120)
print(f"saved {out}")
for kind in ["box", "cls", "dfl"]:
    print(f"final {kind}: train={rows[-1][f'train/{kind}_loss']} val={rows[-1][f'val/{kind}_loss']}")
