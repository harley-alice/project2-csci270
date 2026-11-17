"""Make Ultralytics run configs portable by removing absolute repo paths.

Ultralytics writes absolute paths (model, data, project, save_dir) into every
ml/runs/<run>/args.yaml. This script rewrites paths that start with the repo root
(found from this script's location) to repo-relative ones. It is idempotent, and it
only WARNS about any other absolute home-folder path (macOS, Linux or Windows user
folders) without changing it.

Usage:
    python ml/sanitize_paths.py                    # every ml/runs/*/args.yaml
    python ml/sanitize_paths.py path/to/args.yaml  # specific files
    python ml/sanitize_paths.py --root /old/repo/root path/to/args.yaml
        # --root: rewrite paths under a different checkout's root (default: this repo)
"""
import argparse
import re
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
# Built from pieces so this file does not itself contain a literal home-folder path.
_MAC, _LINUX, _WIN = "/" + "Users", "/" + "home", "Users"
OTHER_ABS = re.compile(
    "(" + _MAC + r"/[^/\s'\"]+|" + _LINUX + r"/[^/\s'\"]+|[A-Za-z]:\\+" + _WIN + r"\\+[^\\\s'\"]+)"
)


def rewrite(text, roots):
    """Return (new_text, [(line_no, before, after)])."""
    changes, out = [], []
    patterns = [re.compile(re.escape(r) + r"(?:/|(?=$|[\s'\"]))") for r in roots]
    for n, line in enumerate(text.splitlines(keepends=True), 1):
        new = line
        for pat in patterns:
            # "<root>/x" -> "x", bare "<root>" -> "."
            new = pat.sub(lambda m: "" if m.group(0).endswith("/") else ".", new)
        if new != line:
            changes.append((n, line.rstrip("\n"), new.rstrip("\n")))
        out.append(new)
    return "".join(out), changes


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("files", nargs="*", help="files to sanitize (default: ml/runs/*/args.yaml)")
    ap.add_argument("--root", action="append", default=[], help="extra repo root to strip (repeatable)")
    a = ap.parse_args()

    files = [Path(f) for f in a.files] or sorted((REPO / "ml" / "runs").glob("*/args.yaml"))
    roots = {REPO.as_posix(), str(REPO)} | {r.rstrip("/") for r in a.root}
    roots = sorted((r for r in roots if r), key=len, reverse=True)

    total = 0
    for f in files:
        if not f.exists():
            print(f"skip (not found): {f}")
            continue
        text = f.read_text()
        new, changes = rewrite(text, roots)
        if changes:
            f.write_text(new)
            total += len(changes)
            print(f"{f}: changed {len(changes)} line(s)")
            for n, before, after in changes:
                print(f"  {n}: {before.strip()}  ->  {after.strip()}")
        else:
            print(f"{f}: no change")
        for n, line in enumerate(new.splitlines(), 1):
            for m in OTHER_ABS.finditer(line):
                print(f"  WARNING {f}:{n}: absolute path not under the repo root, left unchanged: {m.group(0)}")
    print(f"done: {total} line(s) changed in {len(files)} file(s)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
