#!/usr/bin/env python3
"""Rename Google Flow downloads to He Still Answers post ids.

Flow names a file from the start of the prompt plus a hash, for example
Lantern_on_dirt_road_550d1881.jpg. Each flow_prompts CSV has a flow_key,
and each prompt begins with that key. This script matches the filename
back to the key and renames the file to <id>.jpg.

Usage:
    python3 scripts/rename_flow_images.py <folder> [--dry-run]

Needs Python 3 and Pillow. It never deletes a file.
"""

from __future__ import annotations

import argparse
import csv
import difflib
import re
import sys
from pathlib import Path

IMAGE_SUFFIXES = {".jpg", ".jpeg", ".png", ".webp"}
HASH_RE = re.compile(r"_[0-9a-fA-F]{6,12}$")


def normalize(text: str) -> str:
    text = text.lower().replace("'", "").replace("’", "")
    text = re.sub(r"[_\-]+", " ", text)
    text = re.sub(r"[^a-z0-9 ]+", " ", text)
    return re.sub(r"\s+", " ", text).strip()


def stem_from_filename(name: str) -> str:
    stem = Path(name).stem
    return HASH_RE.sub("", stem)


def load_keys(content_dir: Path) -> list[dict]:
    rows = []
    for path in sorted(content_dir.glob("flow_prompts_batch*.csv")):
        with path.open(newline="", encoding="utf-8") as handle:
            for row in csv.DictReader(handle):
                key = (row.get("flow_key") or "").strip()
                if not key:
                    continue
                rows.append(
                    {
                        "id": row["id"].strip(),
                        "key": key,
                        "norm": normalize(key),
                        "source": path.name,
                    }
                )
    return rows


def match_name(norm_name: str, keys: list[dict]) -> tuple[dict | None, str]:
    if not norm_name:
        return None, ""
    exact = [row for row in keys if row["norm"] == norm_name]
    if len(exact) == 1:
        return exact[0], "exact"
    if len(exact) > 1:
        return None, ""

    prefixes = [
        row
        for row in keys
        if len(norm_name) >= 10
        and (row["norm"].startswith(norm_name) or norm_name.startswith(row["norm"]))
    ]
    if len(prefixes) == 1:
        return prefixes[0], "prefix"
    if len(prefixes) > 1:
        prefixes.sort(key=lambda row: len(row["norm"]), reverse=True)
        # Keep the longest key only when the others are prefixes of it.
        longest = prefixes[0]["norm"]
        if all(longest.startswith(row["norm"]) or row["norm"].startswith(norm_name) for row in prefixes):
            only = [row for row in prefixes if row["norm"] == longest]
            if len(only) == 1 and longest.startswith(norm_name):
                return only[0], "prefix"

    norms = [row["norm"] for row in keys]
    scores = sorted(
        (
            (difflib.SequenceMatcher(None, norm_name, row["norm"]).ratio(), row)
            for row in keys
        ),
        key=lambda item: item[0],
        reverse=True,
    )
    best, second = scores[0], scores[1] if len(scores) > 1 else (0.0, None)
    if best[0] >= 0.84 and (second[0] <= best[0] - 0.05):
        return best[1], "fuzzy"
    return None, ""


def save_jpg(src: Path, dest: Path) -> None:
    if src.suffix.lower() in {".jpg", ".jpeg"}:
        src.rename(dest)
        return
    from PIL import Image

    with Image.open(src) as image:
        image.convert("RGB").save(dest, "JPEG", quality=92)
    # The original png or webp stays. This script does not delete files.


def unique_dest(folder: Path, post_id: str, taken: set[str]) -> Path:
    first = folder / f"{post_id}.jpg"
    if first.name not in taken and not first.exists():
        return first
    n = 1
    while True:
        alt = folder / f"{post_id}_alt{n}.jpg"
        if alt.name not in taken and not alt.exists():
            return alt
        n += 1


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("folder", type=Path)
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()
    folder = args.folder
    if not folder.is_dir():
        print(f"Not a folder: {folder}", file=sys.stderr)
        return 1

    repo = Path(__file__).resolve().parents[1]
    keys = load_keys(repo / "content")
    if not keys:
        print("No flow_key rows found in content/flow_prompts_batch*.csv", file=sys.stderr)
        return 1
    by_norm = {}
    for row in keys:
        by_norm.setdefault(row["norm"], []).append(row)

    images = [
        path
        for path in folder.iterdir()
        if path.is_file() and path.suffix.lower() in IMAGE_SUFFIXES
    ]
    images.sort(key=lambda path: path.name.lower())

    matched: dict[str, list[tuple[Path, dict, str]]] = {}
    unmatched: list[str] = []
    for path in images:
        norm_name = normalize(stem_from_filename(path.name))
        row, how = match_name(norm_name, keys)
        if row is None:
            unmatched.append(path.name)
            continue
        matched.setdefault(row["id"], []).append((path, row, how))

    print(f"{'file':<42} {'id':<8} {'how':<8} result")
    print("-" * 78)
    used_ids = set()
    planned = []
    for post_id, group in sorted(matched.items()):
        group.sort(key=lambda item: item[0].stat().st_mtime, reverse=True)
        taken: set[str] = set()
        for index, (path, row, how) in enumerate(group):
            if index == 0:
                dest = unique_dest(folder, post_id, taken)
            else:
                dest = unique_dest(folder, post_id, taken | {f"{post_id}.jpg"})
            taken.add(dest.name)
            planned.append((path, dest, how, post_id))
            action = "keep" if path.resolve() == dest.resolve() else f"-> {dest.name}"
            if path.suffix.lower() in {".png", ".webp"}:
                action += " (original kept)"
            print(f"{path.name:<42} {post_id:<8} {how:<8} {action}")
        used_ids.add(post_id)

    print()
    print(f"Matched files: {sum(len(v) for v in matched.values())}")
    print(f"Unmatched files: {len(unmatched)}")
    for name in unmatched:
        print(f"  unmatched  {name}")
    missing = [row["id"] for row in keys if row["id"] not in used_ids]
    print(f"Ids still missing: {len(missing)}")
    if missing:
        preview = ", ".join(missing[:24])
        more = "" if len(missing) <= 24 else f", ... ({len(missing) - 24} more)"
        print(f"  {preview}{more}")

    if args.dry_run:
        print("Dry run: no files renamed.")
        return 0

    for path, dest, _how, _post_id in planned:
        if path.resolve() == dest.resolve():
            continue
        if path.suffix.lower() in {".jpg", ".jpeg"}:
            path.rename(dest)
        else:
            save_jpg(path, dest)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
