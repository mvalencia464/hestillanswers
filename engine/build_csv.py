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
import os, re, csv, glob, argparse, datetime as dt
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
    return {r['id']: r['credit'] for r in csv.DictReader(open(f, encoding='utf-8'))} if os.path.exists(f) else {}
CREDITS = _credits()

def parse(path):
    posts, cur, field = [], None, None
    for raw in open(path, encoding='utf-8').read().split('\n'):
        if raw.startswith('#'): continue
        if raw.startswith('@@'):
            a = [x.strip() for x in raw[2:].split('|')] + [''] * 5
            cur = dict(id=a[0], type=a[1], scene=a[2], element=a[3], tag=a[4], headline='', attribution='', caption='', src=''); posts.append(cur); field = None; continue
        if cur is None: continue
        m = re.match(r'^([HBCR]): ?(.*)$', raw)
        if m:
            field = {'H': 'headline', 'B': 'attribution', 'C': 'caption', 'R': 'src'}[m.group(1)]
            cur[field] = (cur[field] + ' || ' + m.group(2)) if (field == 'headline' and cur[field]) else m.group(2)
        elif field == 'caption': cur['caption'] += '\n' + raw
    for p in posts:
        p['caption'] = p['caption'].strip()
        parts = [x.strip() for x in p['src'].split('|')] + ['']; code, title = parts[0], parts[1]
        t = ''
        if title: t = f' ("{title}")' if code in ('W', 'CY') else ''
        p['first_comment'] = SOURCES.get(code, '').format(t=t)
        if code == 'OR' and title: p['first_comment'] = ('An original prayer. ' if p['type'] == 'prayer' else '') + title + '.'
        if code == 'HX': p['first_comment'] = 'Source: ' + title
        if p['id'] in CREDITS and any(os.path.exists(os.path.join(ROOT, 'backgrounds', p['id'] + e)) for e in ('.jpg', '.jpeg', '.png', '.webp')): p['first_comment'] = (p['first_comment'] + ' Image: ' + CREDITS[p['id']] + '. The Metropolitan Museum of Art, Open Access (public domain).').strip()
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
            para = next((l.strip() for l in open(os.path.join(ROOT, 'Prayers of C.H. Spurgeon.txt'), encoding='utf-8-sig') if l.strip().startswith(m.group(1))), None)
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
    cols = ['id', 'batch', 'day', 'date', 'time', 'type', 'headline', 'attribution', 'tag', 'scene', 'element', 'caption', 'first_comment', 'alt_text', 'image_file', 'image_url', 'source']
    os.makedirs(os.path.join(ROOT, 'schedule'), exist_ok=True); allrows = []
    for batch, b in sorted(cfg['batches'].items()):
        posts = parse(os.path.join(ROOT, 'content', batch)); name = os.path.splitext(batch)[0].replace('posts_', '')
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
        with open(os.path.join(ROOT, 'schedule', f'highlevel_{name}.csv'), 'w', newline='', encoding='utf-8') as f:
            w = csv.writer(f); w.writerow(['postAtSpecificTime', 'content', 'OGmetaUrl', 'imageUrls', 'gifUrl', 'videoUrls'])
            for p in rows: w.writerow([f'{p["date"]} {p["time"]}:00', p['caption'], '', p['image_url'], '', ''])
        print(f'{name}: {len(rows)} posts, {rows[0]["date"]} to {rows[-1]["date"]} at {", ".join(times)}'); allrows += rows
    allrows.sort(key=lambda p: (p['date'], p['time']))
    with open(os.path.join(ROOT, 'content', 'posts_master.csv'), 'w', newline='', encoding='utf-8') as f:
        w = csv.DictWriter(f, fieldnames=cols, extrasaction='ignore'); w.writeheader(); w.writerows(allrows)
    print(f'posts_master.csv: {len(allrows)} posts. Image links point at {base}')

if __name__ == '__main__': main()
