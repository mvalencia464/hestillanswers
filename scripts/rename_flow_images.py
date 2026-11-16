#!/usr/bin/env python3
"""Match Google Flow downloads to He Still Answers post ids.

Flow writes its own short caption, not the start of our prompt, for example
Glass_shards_in_wet_rye_50a0f3de.jpg. The default match scores those caption
words against each row's scene summary, foreground phrase, and flow_key,
then assigns each image to at most one post.

Usage:
    python3 scripts/rename_flow_images.py <folder> [--dry-run]
    python3 scripts/rename_flow_images.py --from-matches [--dry-run]

The first form prints the assignment. With no --dry-run it copies matches
to <folder>/matched/<id>.jpg. It never deletes and never writes backgrounds/.

--from-matches reads content/flow_matches_batch*.csv and copies each file
to backgrounds/<id>.jpg (or <id>_altN.jpg when the match file name says so).
Copy only.

Needs Python 3 and Pillow.
"""

from __future__ import annotations

import argparse
import csv
import re
import shutil
import sys
from pathlib import Path

IMAGE_SUFFIXES = {".jpg", ".jpeg", ".png", ".webp"}
HASH_RE = re.compile(r"_[0-9a-fA-F]{6,12}$")
STOP = set(
    "a an the on in of with and at by to from into over under near beside along "
    "against its his her their for as is was were be no not or but that this them they "
    "blurred background foreground shot mid close wide still life".split()
)


def normalize(text: str) -> str:
    text = text.lower().replace("'", "").replace("'", "").replace("…", " ")
    text = re.sub(r"[_\-]+", " ", text)
    text = re.sub(r"[^a-z0-9 ]+", " ", text)
    return re.sub(r"\s+", " ", text).strip()


def stem(word: str) -> str:
    if word.endswith("ies") and len(word) > 4:
        word = word[:-3] + "y"
    elif word.endswith("es") and len(word) > 4:
        word = word[:-2]
    elif word.endswith("s") and len(word) > 3 and not word.endswith("ss"):
        word = word[:-1]
    if word.endswith("ing") and len(word) > 5:
        word = word[:-3]
    return word


def tokens(text: str) -> set[str]:
    out = set()
    for word in normalize(text).split():
        if word in STOP or len(word) < 3:
            continue
        out.add(stem(word))
    return out


def caption_from_filename(name: str) -> str:
    stem_name = HASH_RE.sub("", Path(name).stem)
    return normalize(stem_name)


def load_rows(content_dir: Path, batch: str | None = None) -> list[dict]:
    paths = sorted(content_dir.glob("flow_prompts_batch*.csv"))
    if batch:
        paths = [p for p in paths if batch in p.name]
    rows = []
    for path in paths:
        with path.open(newline="", encoding="utf-8") as handle:
            for row in csv.DictReader(handle):
                prompt = row.get("flow_prompt") or ""
                match = re.search(r"Foreground:\s*([^.]+)", prompt)
                row["_fg"] = match.group(1) if match else ""
                row["_file"] = path.name
                rows.append(row)
    return rows


def score_caption(caption: str, row: dict) -> float:
    words = tokens(caption)
    if not words:
        return 0.0
    fields = {
        "fg": tokens(row.get("_fg") or ""),
        "key": tokens(row.get("flow_key") or ""),
        "scene": tokens(row.get("scene_summary") or ""),
        "prompt": tokens(row.get("flow_prompt") or ""),
    }
    def overlap(field: set[str]) -> float:
        return len(words & field) / len(words)

    hit = len(words & set().union(*fields.values())) / len(words)
    return round(
        4 * overlap(fields["fg"])
        + 3 * overlap(fields["key"])
        + 2 * overlap(fields["scene"])
        + overlap(fields["prompt"])
        + 2 * hit,
        3,
    )


def assign(files: list[Path], rows: list[dict]) -> list[tuple[Path, dict | None, float]]:
    """Greedy one-to-one assignment. Highest score takes the row."""
    pairs = []
    for file_index, path in enumerate(files):
        caption = caption_from_filename(path.name)
        for row_index, row in enumerate(rows):
            pairs.append((score_caption(caption, row), file_index, row_index))
    pairs.sort(reverse=True)
    used_files: set[int] = set()
    used_rows: set[int] = set()
    chosen: dict[int, tuple[int, float]] = {}
    for value, file_index, row_index in pairs:
        if value <= 0 or file_index in used_files or row_index in used_rows:
            continue
        used_files.add(file_index)
        used_rows.add(row_index)
        chosen[file_index] = (row_index, value)
    result = []
    for file_index, path in enumerate(files):
        if file_index in chosen:
            row_index, value = chosen[file_index]
            result.append((path, rows[row_index], value))
        else:
            result.append((path, None, 0.0))
    return result


def images_in(folder: Path) -> list[Path]:
    return sorted(
        (p for p in folder.iterdir() if p.is_file() and p.suffix.lower() in IMAGE_SUFFIXES),
        key=lambda p: p.name.lower(),
    )


def print_assignment(folder: Path, rows: list[dict]) -> list[tuple[Path, dict | None, float]]:
    files = images_in(folder)
    result = assign(files, rows)
    print(f"{'file':<46} {'id':<8} score")
    print("-" * 68)
    matched = 0
    for path, row, value in result:
        if row is None:
            print(f"{path.name:<46} {'—':<8} unmatched")
        else:
            matched += 1
            print(f"{path.name:<46} {row['id']:<8} {value:.2f}")
    used = {row["id"] for _p, row, _s in result if row}
    missing = [row["id"] for row in rows if row["id"] not in used]
    print()
    print(f"Matched files: {matched}")
    print(f"Unmatched files: {len(files) - matched}")
    print(f"Ids still missing: {len(missing)}")
    if missing:
        preview = ", ".join(missing[:24])
        more = "" if len(missing) <= 24 else f", ... ({len(missing) - 24} more)"
        print(f"  {preview}{more}")
    return result


def copy_matches(content_dir: Path, backgrounds: Path, dry_run: bool) -> int:
    backgrounds.mkdir(parents=True, exist_ok=True)
    rows = []
    for path in sorted(content_dir.glob("flow_matches_batch*.csv")):
        with path.open(newline="", encoding="utf-8") as handle:
            for row in csv.DictReader(handle):
                row["_csv"] = path
                rows.append(row)
    print(f"{'flow_file':<46} {'dest':<16} verified")
    print("-" * 72)
    for row in rows:
        batch = re.search(r"batch(\d+)", row["_csv"].name)
        folder = content_dir.parent / "flow" / f"batch{batch.group(1)}" if batch else None
        src = folder / row["flow_file"] if folder else None
        post_id = row["id"].strip()
        alt = re.search(r"_alt(\d+)", row.get("note") or "")
        dest_name = f"{post_id}_alt{alt.group(1)}.jpg" if alt else f"{post_id}.jpg"
        dest = backgrounds / dest_name
        print(f"{row['flow_file']:<46} {dest_name:<16} {row.get('verified','')}")
        if dry_run or src is None or not src.exists():
            if src is not None and not src.exists():
                print(f"  missing source {src}")
            continue
        shutil.copy2(src, dest)
    if dry_run:
        print("Dry run: nothing copied.")
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("folder", nargs="?", type=Path)
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument(
        "--from-matches",
        action="store_true",
        help="Copy files listed in content/flow_matches_batch*.csv to backgrounds/",
    )
    args = parser.parse_args()
    repo = Path(__file__).resolve().parents[1]
    content = repo / "content"
    if args.from_matches:
        return copy_matches(content, repo / "backgrounds", args.dry_run)
    if args.folder is None or not args.folder.is_dir():
        print("Give a folder of Flow downloads, or pass --from-matches.", file=sys.stderr)
        return 1
    batch = None
    found = re.search(r"batch(\d+)", args.folder.name)
    if found:
        batch = f"batch{found.group(1)}"
    rows = load_rows(content, batch)
    if not rows:
        print("No flow prompt rows found.", file=sys.stderr)
        return 1
    print_assignment(args.folder, rows)
    if args.dry_run:
        print("Dry run: no files copied.")
    else:
        print("No files copied. Confirm content/flow_matches_batch*.csv, then use --from-matches.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
