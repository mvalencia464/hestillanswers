#!/usr/bin/env python3
"""Turns content/posts_batch*.txt into:
   content/posts_master.csv            every post, every field, with its scheduled time
   schedule/publer_<batch>.csv         ready for Publer > Bulk > CSV
   schedule/highlevel_<batch>.csv      ready for HighLevel Social Planner > Upload from CSV (Basic)

  python3 engine/build_csv.py --start 2026-11-23
  python3 engine/build_csv.py --start 2026-11-23 --base-url https://your-host.example/hsa

--times     three posting times, in YOUR scheduler's timezone (default suits a Pacific-time account:
            05:45 / 09:30 / 16:45 PT = 8:45am / 12:30pm / 7:45pm Eastern)
--base-url  where the finished images are hosted; each image URL becomes <base-url>/<id>.jpg
"""
import os, re, csv, glob, argparse, sys, datetime as dt
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SOURCES = {
 'W':  'Source: The Wonders of Prayer (1885), a public-domain collection of answered-prayer accounts{t}. Retold here in modern English.',
 'CY': 'Source: New Cyclopaedia of Prose Illustrations (1875), public domain{t}.',
 'SP': 'Source: the recorded pulpit prayers of Charles Haddon Spurgeon (1834-1892). Public domain. Quoted word for word.',
 'MH': 'Source: Matthew Henry, A Method for Prayer (1710), "To the Reader." Public domain. Quoted word for word.',
 'OR': '',
}
def _credits():
    f = os.path.join(ROOT, 'backgrounds', 'credits.csv')
    return {r['id']: r for r in csv.DictReader(open(f, encoding='utf-8'))} if os.path.exists(f) else {}
CREDITS = _credits()

# Engagement-bait guard (Nov 16, 2026): Meta demotes posts that ask people to
# comment, share, tag, vote, or fill in a blank. The build FAILS if a headline,
# caption, or first comment contains one of these. Each entry is (regex, label);
# the label is what gets printed, so the offending post can be found fast.
# Deliberately narrow on three points, to avoid false positives on source text:
#  - "below" is only bait when paired with a call to act ("comment below",
#    "tell us below", ...). On its own it is ordinary English in the books
#    ("gone below", "in this world below", "BELOW CHRISTIANS?").
#  - "comment" is only bait as a call to act ("leave a comment", "in the
#    comments", "comment below"). "Without a word of comment" (S025) is not.
#  - "say ..." is only bait as an instruction to the reader ("say AMEN").
#    Narration like 'She did not say "if it be possible"' (S026) is not.
#  - "..." is only bait as a fill-in ("when..."). Henry/Spurgeon quotes use
#    ellipses legitimately, so a bare "..." is not flagged.
BAIT_PATTERNS = [
    (r'\b(leave a comment|in the comments?|comment below|comment your|comment with|comment!)\b', 'comment'),
    (r'\btag\b', 'tag'),
    (r'\bshare\b', 'share'),
    (r'\bdrop a\b', 'drop a'),
    (r'\bwhich are you\b', 'which are you'),
    (r'\bfinish the sentence\b', 'finish the sentence'),
    (r'\bme too\b', 'me too'),
    (r'\btell us\b', 'tell us'),
    (r'\btype\s+(amen|yes|me too|["\'])', 'type ...'),
    (r'\bsay\s+["\'](amen|yes|me too)', 'say "..."'),
    (r'\b(comment|share|tell us|drop|type|say|leave|post)\b[^.\n]{0,50}\bbelow\b', '... below'),
    (r'\bin the comments? below\b', 'in the comments below'),
    (r'\bwhen\.\.\.', 'when... (fill-in-the-blank)'),
    (r'\bwhat is yours\?', 'what is yours?'),
    (r'\bwhen did it happen to you\?', 'when did it happen to you?'),
    (r'\bwho was it for you\?', 'who was it for you?'),
    (r'\bwhat do you remember\?', 'what do you remember?'),
    (r'\bhas someone ever shown up for you like that\?', 'has someone ever shown up for you like that?'),
    (r'\byour answer may be the one they need\b', 'your answer may be the one they need'),
    (r'\bwhat would you (actually )?say\b', 'what would you say?'),
]
_BAIT_RES = [(re.compile(p, re.IGNORECASE), label) for p, label in BAIT_PATTERNS]

def check_bait(posts):
    """Fail the build if any post's headline, caption, or first comment
    contains engagement bait. Prints one line per hit: post ID, field,
    and the matching phrase. Returns the posts unchanged when clean."""
    hits = []
    for p in posts:
        for field in ('headline', 'caption', 'first_comment'):
            text = re.sub(r'[*|]', ' ', p.get(field) or '')
            for rx, label in _BAIT_RES:
                if rx.search(text):
                    hits.append((p['id'], field, label))
    if hits:
        for pid, field, label in hits:
            print(f'ENGAGEMENT BAIT {pid} [{field}]: matched {label!r}', file=sys.stderr)
        raise SystemExit(f'build failed: engagement bait in {len(hits)} field(s), see above')
    return posts

def parse(path):
    posts, cur, field = [], None, None
    for raw in open(path, encoding='utf-8').read().split('\n'):
        if raw.startswith('#'): continue
        if raw.startswith('@@'):
            a = [x.strip() for x in raw[2:].split('|')] + [''] * 5
            cur = dict(id=a[0], type=a[1], scene=a[2], element=a[3], tag=a[4], headline='', attribution='', caption='', full_text='', src=''); posts.append(cur); field = None; continue
        if cur is None: continue
        m = re.match(r'^([HBCFR]): ?(.*)$', raw)
        if m:
            field = {'H': 'headline', 'B': 'attribution', 'C': 'caption', 'R': 'src', 'F': 'full_text'}[m.group(1)]
            cur[field] = (cur[field] + ' || ' + m.group(2)) if (field == 'headline' and cur[field]) else m.group(2)
        elif field in ('caption', 'full_text'): cur[field] += '\n' + raw
    for p in posts:
        p['caption'] = p['caption'].strip()
        p['full_text'] = p.get('full_text', '').strip()
        parts = [x.strip() for x in p['src'].split('|')] + ['']; code, title = parts[0], parts[1]
        t = ''
        if title: t = f' ("{title}")' if code in ('W', 'CY') else ''
        p['first_comment'] = SOURCES.get(code, '').format(t=t)
        if code == 'OR' and title: p['first_comment'] = ('An original prayer. ' if p['type'] == 'prayer' else '') + title + '.'
        if code == 'HX': p['first_comment'] = 'Source: ' + title
        if code == 'MH' and title: p['first_comment'] = f'Source: Matthew Henry, {title}. Public domain. Quoted word for word.'
        if p['id'] in CREDITS and CREDITS[p['id']].get('credit') and any(os.path.exists(os.path.join(ROOT, 'backgrounds', p['id'] + e)) for e in ('.jpg', '.jpeg', '.png', '.webp')):
            c = CREDITS[p['id']]; note = c['credit']
            if 'metmuseum.org' in (c.get('url') or ''): note += '. The Metropolitan Museum of Art, Open Access (public domain).'
            elif not note.endswith('.'): note += '.'
            p['first_comment'] = (p['first_comment'] + ' Image: ' + note).strip()
        slides = [re.sub(r'\s+', ' ', x.replace('|', ' ').replace('*', '').replace('>>', '').replace('::', ':')).strip() for x in p['headline'].split('||')]
        kind = {'story': 'Illustrated scene with the headline', 'quote': 'Quote card reading', 'prayer': 'Prayer card titled', 'question': 'Question card reading'}.get(p['type'], 'Image reading')
        multi = p['type'] in ('carousel', 'list')
        if p['type'] == 'text': p['alt_text'] = p['image_file'] = ''
        elif multi:
            p['alt_text'] = ' || '.join(f'Slide {i + 1}: {t}' for i, t in enumerate(slides))
            p['image_file'] = ','.join(f'{p["id"]}-{i + 1}.jpg' for i in range(len(slides)))
        else:
            p['alt_text'] = f'{kind}: ' + ' / '.join(slides) + (f' - {p["attribution"]}' if p['type'] in ('quote', 'thennow', 'verse') else '')
            p['image_file'] = p['id'] + '.jpg'
        m = re.search(r'<<SPURGEON: (.+?)>>', p['caption'])
        if m:   # pull a paragraph word for word from the source file
            para = next((l.strip() for l in open(os.path.join(ROOT, 'sources', 'Prayers of C.H. Spurgeon.txt'), encoding='utf-8-sig') if l.strip().startswith(m.group(1))), None)
            assert para, f'{p["id"]}: Spurgeon paragraph not found: {m.group(1)}'
            p['caption'] = p['caption'].replace(m.group(0), para)
        p['source'] = p.pop('src')
    return posts

def order(posts):
    """3 a day: morning = prayer / quote, midday = story, evening = quote / question."""
    by = lambda t: [p for p in posts if p['type'] == t]
    S, Q, P, T = by('story'), by('quote'), by('prayer'), by('question'); out = []
    q = list(Q)
    for d in range(max(len(S), 1)):
        am = (P.pop(0) if P and d % 2 == 0 else (q.pop(0) if q else (P.pop(0) if P else None)))
        mid = S[d] if d < len(S) else None
        pm = (T.pop(0) if T and d % 2 == 1 else (q.pop(0) if q else (T.pop(0) if T else None)))
        out.append([am, mid, pm])
    return out

def main():
    """Settings live in content/schedule.json so a plain `python3 engine/build_csv.py` always rebuilds everything the same way."""
    import json
    cfg_path = os.path.join(ROOT, 'content', 'schedule.json')
    cfg = json.load(open(cfg_path)) if os.path.exists(cfg_path) else {'base_url': 'https://YOUR-IMAGE-HOST', 'batches': {}}
    ap = argparse.ArgumentParser()
    ap.add_argument('--batch'); ap.add_argument('--start'); ap.add_argument('--times'); ap.add_argument('--base-url')
    a = ap.parse_args()
    if a.base_url: cfg['base_url'] = a.base_url.rstrip('/')
    if a.batch:
        b = cfg['batches'].setdefault(a.batch, {'start': '2026-11-23', 'times': ['05:45', '09:30', '16:45']})
        if a.start: b['start'] = a.start
        if a.times: b['times'] = [t.strip() for t in a.times.split(',')]
    json.dump(cfg, open(cfg_path, 'w'), indent=2); base = cfg['base_url']
    cols = ['id', 'batch', 'day', 'date', 'time', 'type', 'headline', 'attribution', 'tag', 'scene', 'element', 'caption', 'full_text', 'first_comment', 'alt_text', 'image_file', 'image_url', 'source']
    os.makedirs(os.path.join(ROOT, 'schedule'), exist_ok=True); allrows = []
    for batch, b in sorted(cfg['batches'].items()):
        posts = check_bait(parse(os.path.join(ROOT, 'content', batch))); name = os.path.splitext(batch)[0].replace('posts_', '')
        d0 = dt.date.fromisoformat(b['start']); times = b['times']; rows = []
        days = order(posts) if len(times) == 3 and {p['type'] for p in posts} <= {'story', 'quote', 'prayer', 'question'} else [posts[i:i + len(times)] for i in range(0, len(posts), len(times))]
        for d, slots in enumerate(days):
            for t, p in zip(times, slots):
                if not p: continue
                p['batch'] = name; p['date'] = (d0 + dt.timedelta(days=d)).isoformat(); p['time'] = t; p['day'] = d + 1
                p['image_url'] = ','.join(f'{base}/{f}' for f in p['image_file'].split(',')) if p['image_file'] else ''; rows.append(p)
        with open(os.path.join(ROOT, 'schedule', f'publer_{name}.csv'), 'w', newline='', encoding='utf-8') as f:
            w = csv.writer(f)
            w.writerow(['Date', 'Text', 'Link', 'Media URLs', 'Title', 'Labels', 'Alt text(s)', 'Comment(s)', 'Pin board, FB album, or Google category', 'Post subtype', 'CTA', 'Reminder'])
            for p in rows: w.writerow([f'{p["date"].replace("-", "/")} {p["time"]}', p['caption'], '', p['image_url'], '', f'{name},{p["type"]}', p['alt_text'], p['first_comment'], '', '', '', ''])
        parts = -(-len(rows) // 90); size = -(-len(rows) // parts)          # HighLevel takes at most 90 posts per CSV
        for k in range(parts):
            fn = f'highlevel_{name}.csv' if parts == 1 else f'highlevel_{name}_part{k + 1}.csv'
            with open(os.path.join(ROOT, 'schedule', fn), 'w', newline='', encoding='utf-8') as f:
                w = csv.writer(f); w.writerow(['postAtSpecificTime', 'content', 'OGmetaUrl', 'imageUrls', 'gifUrl', 'videoUrls'])
                for p in rows[k * size:(k + 1) * size]: w.writerow([f'{p["date"]} {p["time"]}:00', p['caption'], '', p['image_url'], '', ''])
        print(f'{name}: {len(rows)} posts, {rows[0]["date"]} to {rows[-1]["date"]} at {", ".join(times)}'); allrows += rows
    allrows.sort(key=lambda p: (p['date'], p['time']))
    with open(os.path.join(ROOT, 'content', 'posts_master.csv'), 'w', newline='', encoding='utf-8') as f:
        w = csv.DictWriter(f, fieldnames=cols, extrasaction='ignore'); w.writeheader(); w.writerows(allrows)
    print(f'posts_master.csv: {len(allrows)} posts. Image links point at {base}')

if __name__ == '__main__': main()
