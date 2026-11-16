#!/usr/bin/env python3
"""Extract word-for-word source passages for story posts and store them
as F: fields in content/posts_batch*.txt.

Only passages that can be bounded and verified cleanly are written.
Facebook captions are not changed. Run, then rebuild with engine/build_csv.py.

  python3 engine/extract_full_text.py           # report only
  python3 engine/extract_full_text.py --write    # insert F: fields
"""
from __future__ import annotations
import argparse, csv, json, os, re, unicodedata
from collections import Counter, defaultdict

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SRC = os.path.join(ROOT, 'sources', 'wonders of prayer.txt')
BATCHES = [os.path.join(ROOT, 'content', f'posts_batch{n:02d}.txt') for n in (1, 2, 3, 4, 5)]

OCR_RE = re.compile(
    r"\b(Grod|Tlie|tbe|wbicb|wbich|tlie|tiie|liis|Ihe|fbe|fhe|Witb|hte)\b|went oh my",
    re.I,
)
FB_ONLY = re.compile(r'(swipe through|leave a first name below|before you scroll on)', re.I)
# Only actual signatures / speaker names, never short story titles.
NAME_ONLY = re.compile(
    r"^(?:[A-Z]\.){1,3}\s*[A-Z][A-Za-z\-]+$"                          # D.L. MOODY
    r"|^(?:Mr|Mrs|Miss|Ms|Dr|Rev)\.?\s+(?:[A-Z]\.?\s*)?[A-Z][A-Za-z\-]+$"  # Miss E. Dryer
    r"|^[A-Z][A-Z\-]+(?:\s+[A-Z][A-Z\-]+){0,2}$"                      # CHARLES SPURGEON
)
SKIP_AS_STORY = {
    'answers to prayer',  # generic section; S076 is handled as a special case
}
# These are still used as end-boundaries even when they are not story titles.
SECTION_OR_SKIP = {
    'answers to prayer', 'lives of faith and trust', 'the faith of little children',
    'how god honors their trust and answers their prayers', 'god loveth a cheerful giver',
    'in business and social anxieties', 'the fulton st prayer meeting', 'discerning prayer',
    'concurrent testimony of the value of prayer', 'healing', 'introductory',
    'answers to prayer from its history records and correspondence',
}

def wc(s): return len((s or '').split())

def norm(s):
    s = unicodedata.normalize('NFKD', s or '').lower()
    s = re.sub(r"[\"“”‘’'`.,;:!?()$]", ' ', s)
    s = re.sub(r'[^a-z0-9 ]+', ' ', s)
    return re.sub(r'\s+', ' ', s).strip()

def toks(s):
    return {w for w in norm(s).split() if len(w) > 3}

def unwrap(s):
    s = s.strip()
    if len(s) >= 2 and s[0] in '"“' and s[-1] in '"”':
        return s[1:-1].strip()
    return s

def cap_clean(cap):
    parts = []
    for p in re.split(r'\n\s*\n', cap or ''):
        sents = [s for s in re.split(r'(?<=[.!?"”])\s+(?=[A-Z"“])', p.strip())
                 if s and not FB_ONLY.search(s)]
        if sents:
            parts.append(' '.join(sents))
    return ' '.join(parts)


def load_source():
    raw = open(SRC, encoding='utf-8').read()
    end = raw.find('*** END OF THE PROJECT GUTENBERG')
    if end > 0:
        raw = raw[:end]
    return raw.split('\n')


def is_name_only(s):
    core = unwrap(s).rstrip('.')
    if not core or wc(core) > 3:
        return False
    return bool(NAME_ONLY.match(core))


def is_heading(line, following, forced_norms):
    raw = line.strip()
    if not raw or raw.startswith(('***', '*', '[', '(')):
        return False
    if raw.startswith(("'", '‘')) and not raw.startswith(('"', '“')):
        return False
    s = unwrap(raw)
    if not s or len(s) > 120 or wc(s) < 1 or wc(s) > 20:
        return False
    if is_name_only(s):
        return False
    ns = norm(s)
    forced = ns in forced_norms or any(
        f and (ns == f or ns.startswith(f + ' ') or ns.startswith(f) or (len(ns) > 12 and f.startswith(ns)))
        for f in forced_norms
    )
    if re.match(r'^(yours|dear |chapter |contents|introduction to|revised by|new edition|as narrated|and hosts|150 madison)', s, re.I):
        return forced
    if re.search(r'\bYours\b', s) or re.search(r'[A-Z]--[A-Z]', s):
        return False
    if re.search(r'\b(January|February|March|April|May|June|July|August|September|October|November|December)\b', s) and wc(s) <= 6:
        return False
    words = re.findall(r"[A-Za-z']+", s)
    if not words:
        return False
    caps = sum(1 for w in words if w[0].isupper())
    capr = caps / len(words)
    ends = s.endswith(('.', '?', '!'))
    no_punct = not re.search(r'[.!?,;:]$', s)
    body = ' '.join(x for x in following if x.strip())
    if ns in SECTION_OR_SKIP:
        return True  # boundary marker
    if forced:
        return wc(body) >= 15 or True
    # one-word section heads: Healing.
    if wc(s) == 1 and ends and s[0].isupper() and wc(body) >= 20:
        return True
    if capr < (0.4 if wc(s) >= 8 else 0.5):
        return False
    if not ends and not (no_punct and wc(s) <= 8 and capr >= 0.7):
        return False
    if wc(body) < 25:
        return False
    return True


def collect_titles(lines, forced_norms):
    titles = []
    for i, l in enumerate(lines):
        if is_heading(l, lines[i + 1:i + 6], forced_norms):
            titles.append((i, unwrap(l.strip())))
    return titles


def find_title(post_title, titles):
    nt = norm(post_title)
    if not nt:
        return None
    by = defaultdict(list)
    for i, t in titles:
        by[norm(t)].append((i, t))
    if nt in by:
        return by[nt][0] + (1.0, 'exact')
    best, sc = None, 0
    tset = set(nt.split())
    for i, t in titles:
        k = norm(t)
        kset = set(k.split())
        if not kset:
            continue
        j = len(tset & kset) / len(tset | kset)
        cov = len(tset & kset) / len(tset)
        if nt in k or k in nt:
            ratio = min(len(nt), len(k)) / max(len(nt), len(k))
            j = max(j, 0.92 if ratio > 0.7 else 0.78)
        score = max(j, cov if cov >= 0.88 else 0)
        if score > sc:
            best, sc = (i, t, score, 'fuzzy'), score
    return best if sc >= 0.82 else None


def body_between(lines, start, titles):
    nxt = [(j, t) for j, t in titles if j > start]
    end = nxt[0][0] if nxt else len(lines)
    body = '\n\n'.join(x.strip() for x in lines[start + 1:end] if x.strip())
    next_title = nxt[0][1] if nxt else '(end)'
    return body, end, next_title


def special_lincoln(lines):
    for i, l in enumerate(lines):
        if norm(unwrap(l.strip())) == norm("Abraham Lincoln's Faith In Prayer."):
            # The farewell speech sits in the paragraph immediately after the title.
            # Stop after the closing of the quoted address; later Lincoln anecdotes
            # in the same section are a different story.
            chunk = '\n\n'.join(x.strip() for x in lines[i + 1:i + 4] if x.strip())
            m = re.search(r'(.+?affectionate farewell\.”|.+?affectionate farewell\.")', chunk, re.S)
            if not m:
                return None
            return unwrap(lines[i].strip()), i + 1, m.group(1).strip()
    return None


def special_newman_hall(lines):
    needle = 'Dr. Newman Hall, minister of Surrey Chapel'
    for i, l in enumerate(lines):
        if l.startswith(needle):
            # Intro sentence plus the first incident only (the Bible-class visit).
            # The next quoted paragraph is a second, separate mountain story.
            paras = [l.strip()]
            j = i + 1
            while j < len(lines) and not lines[j].strip():
                j += 1
            if j < len(lines):
                paras.append(lines[j].strip())
            body = '\n\n'.join(paras)
            if 'Bible-class' in body or 'Bible class' in body or 'Sunday School' in body:
                return 'Dr. Newman Hall, minister of Surrey Chapel, London, gives the following instances of answers to prayer from his own experience.', i + 1, body
    return None


def load_posts():
    path = os.path.join(ROOT, 'content', 'posts_master.csv')
    return list(csv.DictReader(open(path, encoding='utf-8')))


def extract(lines, posts):
    wanted = [p for p in posts if p['type'] in ('story', 'carousel')
              and (p['source'].startswith('W') or p['source'].startswith('HX'))]
    forced = []
    for p in wanted:
        t = p['source'].split('|', 1)[1].strip() if '|' in p['source'] else ''
        if p['id'] == 'PH04' and not t:
            t = "The Widow's Tree"
        if t:
            forced.append(norm(t))
    forced += [
        norm("The Widow's Tree"),
        norm("Abraham Lincoln's Faith In Prayer."),
        norm("God's Raven."),
        norm("None Of The Lord's Children Left Desolate."),
        norm("You Must Not Go."),
        norm("I Can't Stop To Pray."),
        norm("Of Course He Will."),
        norm('"Aunt Sally\'s" Faith.'),
        norm("The Lord Woke Me Up in Time to Save My Clothes."),
        norm("He Could Not Flee from the Power of the Holy Spirit."),
    ]
    forced_norms = set(forced)
    titles = collect_titles(lines, forced_norms)

    rows = []
    for p in wanted:
        title = p['source'].split('|', 1)[1].strip() if '|' in p['source'] else ''
        if p['id'] == 'PH04' and not title:
            title = "The Widow's Tree"
        cap = cap_clean(p['caption'])
        rec = dict(id=p['id'], type=p['type'], batch=p['batch'], post_title=title,
                   cap_w=wc(cap), status='skip', reason='', src_title='', src_line=0,
                   src_w=0, overlap=0, ratio=0, next_title='', ocr=[], body='',
                   match_how='', match_score=0)

        # Special cases
        if p['id'] == 'PH02':
            rec['reason'] = 'composite history; the founding narrative is not a single passage in Wonders of Prayer (that section is later meeting records)'
            rows.append(rec); continue
        if p['id'] == 'S071':
            rec['reason'] = 'doubtful internal boundary: the titled section also includes a later paralysis incident before the next heading'
            rows.append(rec); continue
        if p['id'] == 'PH01':
            sp = special_lincoln(lines)
            if not sp:
                rec['reason'] = 'could not cleanly isolate the Springfield farewell in the Lincoln section'
                rows.append(rec); continue
            t, line, body = sp
            rec.update(src_title=t, src_line=line, body=body, src_w=wc(body),
                       next_title='(end of farewell address)', overlap=round(len(toks(cap) & toks(body)) / max(1, len(toks(cap))), 3),
                       ratio=round(wc(cap) / max(1, wc(body)), 3), match_how='special', match_score=1,
                       status='ok', reason='special: farewell address only, later Lincoln anecdotes omitted')
            rows.append(rec); continue
        if p['id'] == 'S076':
            sp = special_newman_hall(lines)
            if not sp:
                rec['reason'] = 'post title is a generic section head; could not isolate the Newman Hall Bible-class incident'
                rows.append(rec); continue
            t, line, body = sp
            rec.update(src_title=t, src_line=line, body=body, src_w=wc(body),
                       next_title='(second Newman Hall incident omitted)',
                       overlap=round(len(toks(cap) & toks(body)) / max(1, len(toks(cap))), 3),
                       ratio=round(wc(cap) / max(1, wc(body)), 3), match_how='special', match_score=1,
                       status='ok', reason='special: first Newman Hall incident only')
            rows.append(rec); continue

        if p['source'].startswith('HX'):
            rec['reason'] = 'HX source is not a single titled Wonders passage'
            rows.append(rec); continue

        found = find_title(title, titles) if title else None
        if not found:
            rec['reason'] = 'title not found in source or match too weak'
            rows.append(rec); continue
        i, t, score, how = found
        body, end, next_title = body_between(lines, i, titles)
        ocr = OCR_RE.findall(body)
        rec.update(src_title=t, src_line=i + 1, src_w=wc(body), next_title=next_title,
                   overlap=round(len(toks(cap) & toks(body)) / max(1, len(toks(cap))), 3),
                   ratio=round(wc(cap) / max(1, wc(body)), 3), body=body, ocr=ocr,
                   match_how=how, match_score=round(score, 3))
        reasons = []
        if score < 0.82:
            reasons.append(f'weak title match ({score:.2f}: {t!r})')
        min_ov = 0.18 if p['type'] == 'carousel' else 0.35
        if rec['overlap'] < min_ov:
            reasons.append(f'low lexical overlap with caption ({rec["overlap"]})')
        if rec['src_w'] < 40:
            reasons.append(f'source passage too short ({rec["src_w"]} words)')
        if rec['src_w'] > 1200:
            reasons.append(f'source passage very long ({rec["src_w"]} words), possible swallow')
        if ocr:
            reasons.append(f'OCR noise: {ocr}')
        rec['reason'] = '; '.join(reasons)
        rec['status'] = 'ok' if not reasons else 'skip'
        rows.append(rec)
    return rows, titles


def insert_into_batches(rows):
    by_id = {r['id']: r['body'] for r in rows if r['status'] == 'ok' and r['body'].strip()}
    changed = []
    for path in BATCHES:
        text = open(path, encoding='utf-8').read()
        # Ensure the file ends with a newline for clean splits
        parts = re.split(r'(?=^@@ )', text, flags=re.M)
        out = []
        n = 0
        for part in parts:
            m = re.match(r'^@@\s+(\S+)', part)
            if not m or m.group(1) not in by_id:
                out.append(part)
                continue
            pid = m.group(1)
            body = by_id[pid].rstrip() + '\n'
            # Drop an existing F: block if re-running
            part = re.sub(r'\nF:.*?(?=\n@@ |\n[HBCR]:|\Z)', '\n', part, count=1, flags=re.S)
            part = part.rstrip() + '\n'
            # Insert after the last field (usually R:)
            fblock = 'F: ' + body if not body.startswith('F: ') else body
            # If body has multiple paragraphs, first line goes on F: line
            first, _, rest = body.partition('\n')
            fblock = 'F: ' + first + (('\n' + rest) if rest else '')
            if not fblock.endswith('\n'):
                fblock += '\n'
            part = part.rstrip() + '\n' + fblock
            if not part.endswith('\n'):
                part += '\n'
            out.append(part)
            n += 1
        new = ''.join(out)
        new = re.sub(r'\n{3,}', '\n\n', new)
        if not new.startswith('@@'):
            # keep leading comments; ensure a blank line before the first @@ if missing
            new = re.sub(r'([^\n])\n@@ ', r'\1\n\n@@ ', new, count=1)
        new = re.sub(r'\n@@ ', '\n\n@@ ', new)
        new = re.sub(r'\n{3,}', '\n\n', new)
        if not new.endswith('\n'):
            new += '\n'
        if new != text:
            open(path, 'w', encoding='utf-8').write(new)
            changed.append((os.path.relpath(path, ROOT), n))
    return changed


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--write', action='store_true')
    ap.add_argument('--report', default='')
    a = ap.parse_args()
    lines = load_source()
    posts = load_posts()
    # CY stories: skip as a group (noisy OCR in the archive.org scan)
    cy = [p for p in posts if p['source'].startswith('CY') and p['type'] in ('story', 'carousel')]
    rows, titles = extract(lines, posts)
    ok = [r for r in rows if r['status'] == 'ok']
    skipped = [r for r in rows if r['status'] != 'ok']
    print(f'Detected headings: {len(titles)}')
    print(f'W/HX story+carousel: {len(rows)}  expanded: {len(ok)}  skipped: {len(skipped)}')
    print(f'CY story posts left as-is (OCR-noisy source): {len(cy)}')
    print('\nExpanded (id, caption words → source words):')
    for r in ok:
        print(f"  {r['id']:5} {r['cap_w']:3} → {r['src_w']:4}  ov={r['overlap']:.2f}  {r['post_title'][:60]}")
        if r['match_how'] == 'special':
            print(f"         {r['reason']}")
    print('\nSkipped:')
    for r in skipped:
        print(f"  {r['id']:5} {r['post_title'][:55]!r}")
        print(f"         {r['reason']}")
    print(f'\nCY skipped (all {len(cy)}): archive.org scan has frequent OCR errors; not safe to quote word for word.')
    if a.report:
        dump = [{k: v for k, v in r.items()} for r in rows]
        open(a.report, 'w', encoding='utf-8').write(json.dumps(dump, indent=1))
        print('Wrote', a.report)
    if a.write:
        changed = insert_into_batches(rows)
        for path, n in changed:
            print(f'Wrote {n} F: fields in {path}')
    # OCR scan of accepted bodies
    hits = [(r['id'], r['ocr']) for r in ok if r['ocr']]
    if hits:
        print('\nOCR hits in accepted texts (should be none):', hits)

if __name__ == '__main__':
    main()
