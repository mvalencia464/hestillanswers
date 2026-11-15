#!/usr/bin/env python3
"""Parses the four public-domain source texts into a structured content bank (bank/*.csv).
Run from the project folder:  python3 engine/build_bank.py
"""
import re, csv, os, subprocess, sys
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
BANK = os.path.join(ROOT, 'bank'); os.makedirs(BANK, exist_ok=True)
def rd(name): return open(os.path.join(ROOT, name), encoding='utf-8', errors='ignore').read().replace('﻿','')
def wc(s): return len(s.split())
def sentences(text):
    text = re.sub(r'\s+', ' ', text)
    return [s.strip() for s in re.split(r'(?<=[.!?])["”’\']?\s+(?=["“‘\']?[A-Z])', text) if s.strip()]

# ---------- 1. Wonders of Prayer: one row per story ----------
def wonders():
    lines = [l.strip() for l in rd('wonders of prayer.txt').split('\n')]
    idx = []
    for i, l in enumerate(lines):
        if not l or len(l) > 95 or wc(l) < 2 or wc(l) > 14: continue
        core = l.strip('"“”')
        if not core.endswith('.') and not core.endswith('?') and not core.endswith('!'): continue
        if core.startswith("'") or core.lower().startswith(('yours','mr.','dear')): continue
        words = [w for w in re.findall(r"[A-Za-z']+", core)]
        caps = sum(1 for w in words if w[0].isupper())
        if words and caps / len(words) >= 0.5 and i + 1 < len(lines) and wc(' '.join(lines[i+1:i+4])) > 40:
            idx.append(i)
    rows = []
    for k, i in enumerate(idx):
        j = idx[k+1] if k + 1 < len(idx) else len(lines)
        body = '\n\n'.join(x for x in lines[i+1:j] if x)
        rows.append({'id': f'W{k+1:03d}', 'line': i+1, 'title': lines[i].strip('"“”'), 'words': wc(body), 'text': body})
    return rows

# ---------- 2. Cyclopaedia: one row per numbered entry ----------
def cyclo():
    raw = rd('New cyclopaedia of prose illustrations.txt')
    raw = re.sub(r'-\s*\n\s*', '', raw)            # re-join hyphenated line breaks
    parts = re.split(r'\n\s*(?=\d{1,5}\.\s+[A-Z][A-Za-z\'’\- ]{2,40},)', raw)
    rows = []
    for p in parts:
        m = re.match(r'(\d{1,5})\.\s+([A-Z][A-Za-z\'’\- ]{2,40}),\s*([^.]{0,60})\.\s*(.*)', p, re.S)
        if not m: continue
        num, topic, sub, body = m.groups()
        body = re.sub(r'\s+', ' ', body).strip()
        am = re.search(r'[.!?"”]\s+((?:Dr\.|Rev\.|Bp\.|Mrs\.|Sir)?\s?[A-Z][A-Za-z.\' ]{2,28})\.?$', body)
        author = am.group(1).strip() if am and wc(am.group(1)) <= 4 else ''
        if author: body = body[:am.start()+1].strip()
        if wc(body) < 12: continue
        rows.append({'id': f'C{int(num):05d}', 'topic': topic.strip().title(), 'subtopic': sub.strip(), 'author': author, 'words': wc(body), 'text': body})
    return rows

# ---------- 3. Spurgeon prayers: one row per sentence ----------
def spurgeon():
    rows, title, n = [], '', 0
    for l in rd('Prayers of C.H. Spurgeon.txt').split('\n'):
        l = l.strip()
        if not l: continue
        if re.match(r'Prayer \d+', l): title = l; continue
        for s in sentences(l):
            n += 1
            rows.append({'id': f'S{n:04d}', 'prayer': title, 'words': wc(s), 'text': s})
    return rows

# ---------- 4. Matthew Henry: one row per sentence of Henry's own 1710 text ----------
def henry():
    pdf = os.path.join(ROOT, 'a-method-for-prayer-1710-edition.pdf')
    try: txt = subprocess.run(['pdftotext', '-layout', pdf, '-'], capture_output=True, text=True).stdout
    except FileNotFoundError: print('pdftotext not installed; skipping Henry'); return []
    pages = txt.split('\f'); rows = []; n = 0
    for pi, pg in enumerate(pages):
        pg = re.sub(r'-\n\s*', '', pg)
        for s in sentences(pg):
            if wc(s) < 6 or wc(s) > 60: continue
            n += 1
            rows.append({'id': f'H{n:05d}', 'page': pi+1, 'words': wc(s), 'text': s})
    return rows

def dump(name, rows):
    if not rows: return
    with open(os.path.join(BANK, name), 'w', newline='', encoding='utf-8') as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0].keys())); w.writeheader(); w.writerows(rows)
    print(f'{name}: {len(rows)} rows')

if __name__ == '__main__':
    dump('wonders_stories.csv', wonders())
    dump('cyclopaedia_entries.csv', cyclo())
    dump('spurgeon_sentences.csv', spurgeon())
    dump('henry_sentences.csv', henry())
