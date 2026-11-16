# He Still Answers website (Astro)

Every page is generated from `../content/posts_master.csv`, so the site always matches the Facebook posts.
Images load from R2 (`https://media.stokeleads.com/hestillanswers/...`). No database.

## Run it locally

    cd site
    npm install
    npm run dev          # http://localhost:4321

## Deploy (Cloudflare Pages)

Option A, from your computer:

    cd site
    npm run build
    npx wrangler pages deploy dist --project-name hestillanswers

Option B, connected to GitHub: in Cloudflare Pages create a project from the repo with
root directory `site`, build command `npm run build`, output directory `dist`.

Either way the `functions/` folder deploys with it and handles the signup form.

Until you have a domain the site lives at `https://hestillanswers.pages.dev`. When you add one, set the
environment variable `SITE_URL` (for example `https://hestillanswers.com`) in the Pages project and rebuild,
and rebuild the ebook with `python3 engine/build_ebook.py --site https://yourdomain` so its last page points there.

## Email signup → HighLevel

1. In HighLevel, create a workflow with the trigger **Inbound Webhook** and copy its URL.
2. In Cloudflare Pages → Settings → Variables and secrets, add `SIGNUP_WEBHOOK_URL` = that URL (as a secret).
3. Send one test signup from the live site so HighLevel sees the fields, then map them in the workflow:
   `email`, `first_name`, `source`, `page`, `tags` (always `he-still-answers`, `ebook-30-stories`).
4. Workflow actions: Create/Update Contact → Add Tag → Send Email with the ebook link:
   `https://hestillanswers.pages.dev/ebook/30-true-stories-of-answered-prayer.pdf`

The form needs no JavaScript. A hidden "company" field catches bots. After signup the reader lands on
`/thanks/`, which also offers the download.

## The free ebook

`python3 engine/build_ebook.py` rebuilds `public/ebook/30-true-stories-of-answered-prayer.pdf` and its cover from
the same CSV. The 30 stories are listed at the top of that script (`ORDER`).
