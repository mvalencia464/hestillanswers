# He Still Answers: start here

Brand, image engine, website, and scheduled posts for a Facebook and Instagram page built on
true stories of answered prayer. Pull `main` before you change anything.

## What is in this folder

| Folder / file | What it is |
|---|---|
| `START_HERE.md` | This map and the working rules |
| `sources/` | The four public-domain source books: *Wonders of Prayer*, *New Cyclopaedia of Prose Illustrations*, *Prayers of C.H. Spurgeon*, and Matthew Henry's *A Method for Prayer* (1710 PDF) |
| `docs/` | Batch 03–05 plans, program notes, storytelling notes, and `Get Photos.command` |
| `content/` | Editable batch text (`posts_batchNN.txt`), generated `posts_master.csv`, Flow prompt and match CSVs, and `schedule.json` |
| `engine/` | Image renderer, CSV builder, full-text extractor, ebook builder, and fonts |
| `scripts/` | `rename_flow_images.py` matches Flow downloads to post ids |
| `flow/batchNN/` | Raw Google Flow images for that batch, as downloaded. Drop new renders here. |
| `backgrounds/` | Photos the renderer uses, named by post id (`S001.jpg`) |
| `output/` | 461 finished images, 1080×1350 (4:5), named by post id (`S001.jpg`, `CA01-1.jpg`, …) |
| `preview/` | Contact sheets for each finished batch |
| `schedule/` | Publer and HighLevel upload CSVs |
| `site/` | The Astro website and free ebook, built from `content/posts_master.csv` |
| `brand/` | Page avatar and cover image |
| `bank/` | The four source books parsed into spreadsheets, for later batches |
| `archive/` | Old folders and stale files, kept for reference |

Batches 01–05 are 420 scheduled posts (461 images, counting carousel slides), from 2026-11-23 through 2027-10-18.

## How images get from Flow to a post

1. Generate images in Google Flow at 3:4. Keep the subject in the upper two-thirds with a plain dark bottom third. Vary the main subject; folded hands, a Bible, or a praying figure should appear in at most about three prompts per batch.
2. Save the downloads into `flow/batchNN/`. Flow names files with its own caption, not the post id.
3. Match them with `python3 scripts/rename_flow_images.py flow/batchNN`. Confirmed matches live in `content/flow_matches_batchNN.csv`.
4. Copy verified matches into `backgrounds/` with `python3 scripts/rename_flow_images.py --from-matches`.
5. Render with `python3 engine/render.py`. Re-upload to R2 only if an image file actually changed. R2 is flat: everything goes under `hestillanswers/`, with no subfolders.

## The brand

- **Name:** He Still Answers (alternates: Answered Prayer Stories, The Praying Remnant). Check the name is free on Facebook before you commit.
- **Tagline:** True stories of answered prayer.
- **Bio:** True stories of answered prayer from the last 300 years, and old words that still burn. Spurgeon, Matthew Henry, and ordinary people God showed up for.
- **Colors:** ink `#0A0D14`, gold `#F6B728`, parchment `#FFF6E6`.
- **Type:** Poppins ExtraBold (headlines), Lora (quotes). Both free under the Open Font License.
- **Four post formats:** Story (scene + hook headline, full story in the caption), Quote (word-for-word, gold highlight), Prayer (title card, full prayer in the caption), Question (light card, for real conversation).

## To launch

1. Create the page, upload `brand/avatar_1080.png` and `brand/cover_1640x924.png`, paste the bio.
2. Upload the contents of `output/` to R2 under `hestillanswers/` (see "Hosting on R2" below). The CSVs already carry those links.
3. Upload the files in `schedule/` to Publer or HighLevel. Check the first few rows in the preview before confirming. Posting starts 2026-11-23.
4. Times in the CSV are 05:45, 09:30 and 16:45 for batch 01, plus 12:45 for batches 02–05, written for a Pacific-time scheduler account (8:45am, 12:30pm, 3:45pm, and 7:45pm Eastern). Change with `--times`.

## Swapping in a photo

Drop any photo into `backgrounds/` named after the post, e.g. `backgrounds/S004.jpg`, then run
`python3 engine/render.py`. The engine crops it to 4:5, lays the dark gradient over it, and sets the
headline, divider, tag and footer on top. No photo = the engine paints its own scene, so nothing is ever blank.

Needs Python 3 with `pillow` and `numpy` (`pip3 install pillow numpy`).

## Batch 02: the format lab

30 more posts, one a day at 12:45 Pacific alongside batch 01, built to find out which formats win.
Files: `content/posts_batch02.txt`, `schedule/publer_batch02.csv`, `schedule/highlevel_batch02.csv`,
preview sheets `preview/batch02_*.jpg`.

| Code | Format | Count | What it tests |
|---|---|---|---|
| PH | Story over a real 1800s painting or photograph | 6 | Does real art beat the painted scenes? |
| CA | Carousel mini-story, 5 to 6 slides | 5 | Do swipes beat a single image plus caption? |
| NL | Numbered-list carousel | 3 | How-to and list content |
| OL | One-liner on gold | 5 | Shareability of a single sentence |
| TN | Then / Now: a 1710 sentence, then plain words | 4 | Matthew Henry made easy |
| VW | Verse plus "and it happened" | 4 | Scripture tied to a true account |
| TX | Long text, no image | 3 | Spurgeon paragraphs, word for word |

Carousel posts list all their slides in one CSV cell, comma-separated, in order.

### Real artwork

`backgrounds/credits.csv` lists nine public-domain works from The Met's Open Access collection, matched to
posts (Lincoln, a Currier & Ives sleigh, Heade's thunderstorm, Homer's wheat field ...).
Double-click **docs/Get Photos.command** to download them into `backgrounds/`. If macOS refuses, right-click it
and choose Open. Then re-render, and those posts switch from painted scenes to the real art,
with the credit added to the first comment. Add your own rows to `credits.csv` (id, focus point, credit, url)
to pull in more.

### Hosting on R2

All image links now point at `https://media.stokeleads.com/hestillanswers/<file>.jpg`.
Upload everything inside `output/` into a `hestillanswers/` folder in the bucket behind media.stokeleads.com,
keeping the file names. Test one link in a browser before uploading the CSVs.
Settings are saved in `content/schedule.json`; `python3 engine/build_csv.py` rebuilds every CSV from it.

## Website and free ebook

The site is live at `https://hestillanswers.pages.dev`. `site/` is the Astro project, built from
`content/posts_master.csv`: one page per story, prayer, quote, verse and question, plus an email signup
that sends readers the free ebook *30 True Stories of Answered Prayer* (`engine/build_ebook.py`).
See `site/README.md` to run, deploy, and connect HighLevel.

    cd site
    npm run build
    npx wrangler pages deploy dist --project-name hestillanswers

## Rebuilding after an edit

Edit `content/posts_batchNN.txt`, then rebuild. Do not hand-edit the CSVs.

    python3 engine/extract_full_text.py --write   # only when adding or fixing F: full-text fields
    python3 engine/build_csv.py
    python3 engine/render.py                      # only for posts whose image actually changed

Facebook captions stay the short retellings. The site and ebook use the `full_text` field, word for word from the source.

## Rules that protect monetization

- Every quote is word for word from the source. Every story names where it was recorded.
- Never post "type Amen", "share if you agree", or "tag someone". Meta treats it as engagement bait.
- No outbound links in captions. No more than two hashtags (this batch uses none).
- No claims about living people. No celebrity photos. No "prayer cured cancer" posts.
- Do not upload all 3,000 at once. Post a month, read the numbers, write the next month around the winners.
- Do not re-upload to R2 unless an image file actually changed.
- Reply to comments in the first hour. Prayer-request posts need a human answering them.

## What to watch after two weeks

Reach per post by format (story / quote / prayer / question), shares per post, and comments per post.
Whichever format wins gets half of the next batch. Whichever loses gets cut to one a week.
