# He Still Answers: start here

Brand, image engine and the first 30 days of posts (90 posts, 3 a day) for a Facebook page built on
true stories of answered prayer.

## What is in this folder

| Folder / file | What it is |
|---|---|
| `output/` | 159 finished images, 1080x1350 (4:5), named by post id (`S001.jpg`, `CA01-1.jpg` ...) |
| `preview/` | Three contact sheets so you can see the whole batch at a glance |
| `content/posts_master.csv` | Every post: date, time, caption, image text, first comment, alt text, source |
| `content/posts_batch01.txt` | The same posts in an easy-to-edit text form (edit here, then rebuild) |
| `schedule/publer_batch01.csv` | Upload file for Publer (Bulk > CSV) |
| `schedule/highlevel_batch01.csv` | Upload file for HighLevel Social Planner (Basic CSV, 90-post limit) |
| `brand/` | Page avatar and cover image |
| `engine/` | The image template engine, CSV builder, content-bank builder, fonts |
| `bank/` | Your four source books parsed into spreadsheets: 381 prayer stories, 4,294 illustrations, 1,927 Spurgeon sentences, 4,141 Matthew Henry sentences. Raw material for the next batches. |
| `backgrounds/` | Drop photos here to replace a painted scene (see below) |
| `_to_delete/` | My test files. Safe to delete. |

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
3. Upload `schedule/publer_batch01.csv` (or the HighLevel one). Check the first few rows in the preview before confirming.
4. Times in the CSV are 05:45, 09:30 and 16:45, written for a Pacific-time scheduler account
   (8:45am, 12:30pm, 7:45pm Eastern). Change with `--times`.

## Swapping in a photo

Drop any photo into `backgrounds/` named after the post, e.g. `backgrounds/S004.jpg`, then run
`python3 engine/render.py`. The engine crops it to 4:5, lays the dark gradient over it, and sets the
headline, divider, tag and footer on top. No photo = the engine paints its own scene, so nothing is ever blank.

Needs Python 3 with `pillow` and `numpy` (`pip3 install pillow numpy`). Or just ask Claude to re-render.

## Batch 02: the format lab (added)

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
Double-click **Get Photos.command** to download them into `backgrounds/`. If macOS refuses, right-click it
and choose Open. Then ask Claude to re-render, and those posts switch from painted scenes to the real art,
with the credit added to the first comment. Add your own rows to `credits.csv` (id, focus point, credit, url)
to pull in more.

### Hosting on R2

All image links now point at `https://media.stokeleads.com/hestillanswers/<file>.jpg`.
Upload everything inside `output/` into a `hestillanswers/` folder in the bucket behind media.stokeleads.com,
keeping the file names. Test one link in a browser before uploading the CSVs.
Settings are saved in `content/schedule.json`; `python3 engine/build_csv.py` rebuilds every CSV from it.

## Rules that protect monetization

- Never post "type Amen", "share if you agree", or "tag someone". Meta treats it as engagement bait.
- No outbound links in captions. No more than two hashtags (this batch uses none).
- Every quote is word for word from the source. Every story names where it was recorded.
- No claims about living people. No celebrity photos. No "prayer cured cancer" posts.
- Do not upload all 3,000 at once. Post a month, read the numbers, write the next month around the winners.
- Reply to comments in the first hour. Prayer-request posts need a human answering them.

## What to watch after two weeks

Reach per post by format (story / quote / prayer / question), shares per post, and comments per post.
Whichever format wins gets half of batch 02. Whichever loses gets cut to one a week.
