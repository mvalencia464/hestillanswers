#!/usr/bin/env python3
"""Reassign batch 01 slots to start 2026-11-16 at 16:45 Pacific.

The 05:45 and 09:30 slots on Nov 16 are already past, so day 1 is a single
post at 16:45. Nov 17–Dec 15 keep 05:45 / 09:30 / 16:45. Dec 16 takes the
last two posts at 05:45 and 09:30.

Run after `python3 engine/build_csv.py`. Dates only — captions, images, and
post order are left unchanged. Other batches are left unchanged.
"""
from __future__ import annotations

import csv
import datetime as dt
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
START = dt.date(2026, 11, 16)
MID_END = dt.date(2026, 12, 15)
LAST = dt.date(2026, 12, 16)
TIMES = ["05:45", "09:30", "16:45"]
MASTER_COLS = [
    "id", "batch", "day", "date", "time", "type", "headline", "attribution",
    "tag", "scene", "element", "caption", "full_text", "first_comment",
    "alt_text", "image_file", "image_url", "source",
]


def slots() -> list[tuple[dt.date, str]]:
    out = [(START, "16:45")]
    d = START + dt.timedelta(days=1)
    while d <= MID_END:
        for t in TIMES:
            out.append((d, t))
        d += dt.timedelta(days=1)
    out.append((LAST, "05:45"))
    out.append((LAST, "09:30"))
    if len(out) != 90:
        raise SystemExit(f"expected 90 slots, got {len(out)}")
    return out


def main() -> None:
    master_path = os.path.join(ROOT, "content", "posts_master.csv")
    with open(master_path, newline="", encoding="utf-8") as f:
        rows = list(csv.DictReader(f))

    batch01 = [r for r in rows if r["batch"] == "batch01"]
    others = [r for r in rows if r["batch"] != "batch01"]
    if len(batch01) != 90:
        raise SystemExit(f"expected 90 batch01 rows, got {len(batch01)}")

    # Preserve the rebuilt post order (date/time after build_csv).
    batch01.sort(key=lambda r: (r["date"], r["time"]))
    assigned = slots()
    for row, (day, time) in zip(batch01, assigned):
        row["date"] = day.isoformat()
        row["time"] = time
        row["day"] = str((day - START).days + 1)

    if batch01[0]["id"] != "P001" or batch01[0]["date"] != "2026-11-16" or batch01[0]["time"] != "16:45":
        raise SystemExit(f"first row is {batch01[0]['id']} {batch01[0]['date']} {batch01[0]['time']}")
    if batch01[-1]["id"] != "T015" or batch01[-1]["date"] != "2026-12-16" or batch01[-1]["time"] != "09:30":
        raise SystemExit(f"last row is {batch01[-1]['id']} {batch01[-1]['date']} {batch01[-1]['time']}")
    t001 = next(r for r in batch01 if r["id"] == "T001")
    if t001["date"] != "2026-11-18" or t001["time"] != "09:30":
        raise SystemExit(f"T001 is {t001['date']} {t001['time']}")

    allrows = batch01 + others
    allrows.sort(key=lambda r: (r["date"], r["time"]))
    with open(master_path, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=MASTER_COLS, extrasaction="ignore")
        w.writeheader()
        w.writerows(allrows)

    publer_path = os.path.join(ROOT, "schedule", "publer_batch01.csv")
    with open(publer_path, "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow([
            "Date", "Text", "Link", "Media URLs", "Title", "Labels", "Alt text(s)",
            "Comment(s)", "Pin board, FB album, or Google category", "Post subtype",
            "CTA", "Reminder",
        ])
        for p in batch01:
            w.writerow([
                f'{p["date"].replace("-", "/")} {p["time"]}',
                p["caption"], "", p["image_url"], "", f'batch01,{p["type"]}',
                p["alt_text"], p["first_comment"], "", "", "", "",
            ])

    hl_path = os.path.join(ROOT, "schedule", "highlevel_batch01.csv")
    with open(hl_path, "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["postAtSpecificTime", "content", "OGmetaUrl", "imageUrls", "gifUrl", "videoUrls"])
        for p in batch01:
            w.writerow([f'{p["date"]} {p["time"]}:00', p["caption"], "", p["image_url"], "", ""])

    from collections import Counter
    counts = Counter(r["date"] for r in batch01)
    print(f"reslot_batch01: {len(batch01)} posts, {batch01[0]['date']} {batch01[0]['time']} to {batch01[-1]['date']} {batch01[-1]['time']}")
    print("per-day counts:", dict(sorted(counts.items())))
    print("T001:", t001["date"], t001["time"])


if __name__ == "__main__":
    main()
