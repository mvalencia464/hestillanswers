#!/usr/bin/env python3
"""HE STILL ANSWERS - image template engine.

Turns rows of content/posts_master.csv into finished 1080x1350 (4:5) Facebook images.

  python3 engine/render.py                 # render every post that has no image yet
  python3 engine/render.py --force         # re-render everything
  python3 engine/render.py --only S001 Q004
  python3 engine/render.py --brand         # (re)build avatar + cover in brand/

BACKGROUNDS: drop a photo named after the post id into backgrounds/ (e.g. backgrounds/S001.jpg)
and that post uses it automatically: cropped to 4:5, dark gradient laid over it, text on top.
No photo? The engine paints its own original scene (sky, hills, sea, cabin, ship ...) from the
post's `scene` and `element` columns, so every post always has an image.
"""
import os, sys, csv, re, math, hashlib, argparse
import numpy as np
from PIL import Image, ImageDraw, ImageFont, ImageFilter

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
FONTS = os.path.join(ROOT, 'engine', 'fonts')
W, H = 1080, 1350
INK, GOLD, PARCH, SLATE = (10, 13, 20), (246, 183, 40), (255, 246, 230), (156, 164, 182)
BRAND, TAGLINE = 'HE STILL ANSWERS', 'TRUE STORIES OF ANSWERED PRAYER'

def font(name, size): return ImageFont.truetype(os.path.join(FONTS, name), int(size))
def sans(size, w='ExtraBold'): return font(f'Poppins-{w}.ttf', size)
def serif(size, weight=600, italic=False):
    f = font('Lora-Italic-Variable.ttf' if italic else 'Lora-Variable.ttf', size)
    try: f.set_variation_by_axes([weight])
    except Exception: pass
    return f
def hexc(s): return np.array([int(s[i:i+2], 16) for i in (1, 3, 5)], float)
def seed_of(s): return int(hashlib.md5(s.encode()).hexdigest()[:8], 16)

# ------------------------------------------------------------------ procedural scenes
MOODS = {
 'dawn':  dict(sky=['#14213d', '#8a4a5c', '#f4a95c'], glow='#ffd595', ridge=['#6a5470', '#0b0d16'], stars=0.0, orb='sun'),
 'dusk':  dict(sky=['#0e0f2e', '#6b2f5b', '#ef7d43'], glow='#ffb070', ridge=['#553660', '#0a0b14'], stars=0.2, orb='sun'),
 'night': dict(sky=['#03050c', '#0b1530', '#23406b'], glow='#d6e4ff', ridge=['#22375c', '#05070c'], stars=1.0, orb='moon'),
 'storm': dict(sky=['#06080c', '#1c252d', '#5b6870'], glow='#e6eef2', ridge=['#323d45', '#06080b'], stars=0.0, orb='none'),
 'gold':  dict(sky=['#2b1b10', '#a9622a', '#f8cb78'], glow='#fff1c4', ridge=['#74492a', '#0e0a07'], stars=0.0, orb='sun'),
 'snow':  dict(sky=['#0c1424', '#3a4e6e', '#b3c3d6'], glow='#ffffff', ridge=['#9fb1c8', '#1b2434'], stars=0.25, orb='moon'),
}

def noise1d(rng, n, octaves=5, rough=0.5, freq=3):
    y, amp, tot = np.zeros(n), 1.0, 0.0
    for _ in range(octaves):
        pts = rng.random(freq + 2); x = np.linspace(0, freq, n)
        i = np.clip(np.floor(x).astype(int), 0, freq); t = x - i; t = t * t * (3 - 2 * t)
        y += amp * (pts[i] * (1 - t) + pts[i + 1] * t); tot += amp; amp *= rough; freq *= 2
    return y / tot

def noise2d(rng, w, h, gw, gh, blur=0):
    a = (rng.random((gh, gw)) * 255).astype(np.uint8)
    im = Image.fromarray(a).resize((w, h), Image.BICUBIC)
    if blur: im = im.filter(ImageFilter.GaussianBlur(blur))
    return np.asarray(im, float) / 255.0

def glow(img, cx, cy, r, color, strength):
    y, x = np.ogrid[:H, :W]
    g = np.exp(-(((x - cx) ** 2 + (y - cy) ** 2) / (2.0 * r * r)))
    img += g[:, :, None] * color[None, None, :] * strength

def draw_element(im, kind, x, y, s, dark, lit):
    """Small original silhouettes. (x, y) = ground point, s = scale."""
    d = ImageDraw.Draw(im); dk = tuple(int(c) for c in dark); lt = tuple(int(c) for c in lit)
    if kind == 'cabin':
        d.rectangle([x - 62*s, y - 62*s, x + 62*s, y + 30*s], fill=dk)
        d.polygon([(x - 80*s, y - 60*s), (x, y - 118*s), (x + 80*s, y - 60*s)], fill=dk)
        d.rectangle([x + 30*s, y - 122*s, x + 46*s, y - 80*s], fill=dk)
        d.rectangle([x - 34*s, y - 40*s, x - 6*s, y - 8*s], fill=lt)
        d.line([x - 20*s, y - 40*s, x - 20*s, y - 8*s], fill=dk, width=max(1, int(3*s)))
        d.line([x - 34*s, y - 24*s, x - 6*s, y - 24*s], fill=dk, width=max(1, int(3*s)))
    elif kind == 'church':
        d.rectangle([x - 70*s, y - 70*s, x + 70*s, y + 30*s], fill=dk)
        d.polygon([(x - 84*s, y - 68*s), (x - 10*s, y - 120*s), (x + 84*s, y - 68*s)], fill=dk)
        d.rectangle([x - 78*s, y - 150*s, x - 38*s, y + 30*s], fill=dk)
        d.polygon([(x - 84*s, y - 148*s), (x - 58*s, y - 236*s), (x - 32*s, y - 148*s)], fill=dk)
        d.line([x - 58*s, y - 262*s, x - 58*s, y - 230*s], fill=dk, width=max(2, int(5*s)))
        d.line([x - 68*s, y - 250*s, x - 48*s, y - 250*s], fill=dk, width=max(2, int(5*s)))
        for wx in (-8, 24, 50): d.rounded_rectangle([x + wx*s - 7*s, y - 46*s, x + wx*s + 7*s, y - 10*s], radius=int(6*s), fill=lt)
    elif kind == 'windmill':
        d.polygon([(x - 34*s, y + 30*s), (x - 20*s, y - 120*s), (x + 20*s, y - 120*s), (x + 34*s, y + 30*s)], fill=dk)
        d.polygon([(x - 26*s, y - 118*s), (x, y - 150*s), (x + 26*s, y - 118*s)], fill=dk)
        for a in (25, 115, 205, 295):
            r = math.radians(a); ex, ey = x + math.cos(r)*150*s, y - 128*s + math.sin(r)*150*s
            d.line([x, y - 128*s, ex, ey], fill=dk, width=max(2, int(7*s)))
            px, py = -math.sin(r)*20*s, math.cos(r)*20*s
            d.polygon([(x + math.cos(r)*40*s, y - 128*s + math.sin(r)*40*s), (ex, ey), (ex + px, ey + py),
                       (x + math.cos(r)*40*s + px, y - 128*s + math.sin(r)*40*s + py)], fill=dk)
        d.rectangle([x - 8*s, y - 40*s, x + 8*s, y - 14*s], fill=lt)
    elif kind == 'tree':
        for ox, sc in ((-150, 0.62), (-70, 0.9), (20, 1.25), (112, 0.8), (180, 0.55)):
            bx, hh = x + ox*s, 210*s*sc
            d.rectangle([bx - 5*s*sc, y - 20*s, bx + 5*s*sc, y + 30*s], fill=dk)
            for k in range(4):
                wy = y - 10*s - hh * (k / 4.0); ww = (64 - 12*k)*s*sc
                d.polygon([(bx - ww, wy), (bx, wy - hh * 0.42), (bx + ww, wy)], fill=dk)
    elif kind == 'ship':
        d.polygon([(x - 120*s, y - 26*s), (x + 130*s, y - 26*s), (x + 100*s, y + 8*s), (x - 96*s, y + 8*s)], fill=dk)
        for mx, mh in ((-60, 150), (10, 190), (76, 140)):
            d.line([x + mx*s, y - 26*s, x + mx*s, y - (26 + mh)*s], fill=dk, width=max(2, int(4*s)))
            for k in range(3):
                top = y - (26 + mh - 8)*s + k * (mh/3.2)*s; hgt = (mh/3.6)*s; wd = (46 - k*4)*s
                d.polygon([(x + mx*s - wd*0.86, top), (x + mx*s + wd*0.86, top), (x + mx*s + wd, top + hgt), (x + mx*s - wd, top + hgt)], fill=dk)
        d.polygon([(x + 130*s, y - 26*s), (x + 196*s, y - 60*s), (x + 100*s, y - 40*s)], fill=dk)
        d.ellipse([x - 70*s, y - 20*s, x - 60*s, y - 10*s], fill=lt)
    elif kind == 'city':
        rng = np.random.default_rng(int(x) + 7); cx = x - 330*s
        while cx < x + 330*s:
            bw, bh = rng.integers(34, 78)*s, rng.integers(70, 230)*s
            d.rectangle([cx, y - bh, cx + bw, y + 40*s], fill=dk)
            if rng.random() < 0.35: d.polygon([(cx, y - bh), (cx + bw/2, y - bh - 34*s), (cx + bw, y - bh)], fill=dk)
            for wy in np.arange(y - bh + 14*s, y, 26*s):
                for wx in np.arange(cx + 8*s, cx + bw - 10*s, 18*s):
                    if rng.random() < 0.22: d.rectangle([wx, wy, wx + 7*s, wy + 11*s], fill=lt)
            cx += bw + rng.integers(0, 8)*s
    elif kind == 'peak':
        d.polygon([(x - 300*s, y + 60*s), (x - 30*s, y - 330*s), (x + 20*s, y - 300*s), (x + 310*s, y + 60*s)], fill=dk)
        d.polygon([(x - 30*s, y - 330*s), (x + 20*s, y - 300*s), (x + 62*s, y - 236*s), (x + 18*s, y - 256*s),
                   (x - 16*s, y - 226*s), (x - 44*s, y - 262*s), (x - 82*s, y - 252*s)], fill=lt)
    elif kind == 'cross':
        d.line([x, y + 30*s, x, y - 170*s], fill=dk, width=max(3, int(12*s)))
        d.line([x - 52*s, y - 112*s, x + 52*s, y - 112*s], fill=dk, width=max(3, int(12*s)))

def scene(key, mood='dawn', element='', horizon=0.36, orb=True):
    """Paint an original 1080x1350 scene. Deterministic per key: same post id -> same picture."""
    water = mood.startswith('sea-'); mood = mood.replace('sea-', '')
    m = MOODS.get(mood, MOODS['dawn']); rng = np.random.default_rng(seed_of(key))
    hz = int(H * (horizon + rng.uniform(-0.02, 0.02)))
    top, mid, bot = [hexc(c) for c in m['sky']]; gl = hexc(m['glow'])
    t = np.clip(np.arange(H) / hz, 0, 1)[:, None]
    sky = np.where(t < 0.55, top + (mid - top) * (t / 0.55), mid + (bot - mid) * ((t - 0.55) / 0.45))
    img = np.repeat(sky[:, None, :], W, axis=1)
    cx = W * rng.uniform(0.28, 0.72)
    if m['stars']:
        n = int(900 * m['stars']); sx, sy = rng.integers(0, W, n), (rng.random(n) ** 1.6 * hz).astype(int)
        b = rng.random(n) ** 2 * 230
        for dx, dy, f in ((0, 0, 1), (1, 0, .45), (0, 1, .45)):
            img[np.clip(sy + dy, 0, H - 1), np.clip(sx + dx, 0, W - 1)] += (b * f)[:, None]
    if not orb: pass
    elif m['orb'] == 'sun':
        glow(img, cx, hz, 420, gl, 0.55); glow(img, cx, hz, 120, gl, 0.75); glow(img, cx, hz - 10, 40, np.array([255., 250, 235]), 1.0)
    elif m['orb'] == 'moon':
        my = hz * rng.uniform(0.28, 0.5); glow(img, cx, my, 210, gl, 0.22)
        y, x = np.ogrid[:H, :W]; disc = ((x - cx) ** 2 + (y - my) ** 2) <= 50 ** 2
        img[disc] = np.array([244., 244, 232]); glow(img, cx, my, 60, gl, 0.18)
    cl = noise2d(rng, W, hz, 7, 5, blur=18); a = np.clip((cl - 0.52) * 2.4, 0, 1)[:, :, None]
    if mood == 'storm':
        img[:hz] = img[:hz] * (1 - a * 0.75) + np.array([12., 16, 20]) * a * 0.75
        lx = W * rng.uniform(0.2, 0.8); glow(img, lx, hz * 0.55, 260, gl, 0.28)
    else:
        img[:hz] = img[:hz] * (1 - a * 0.30) + (bot * 0.6 + gl * 0.4) * a * 0.30
    far, near = hexc(m['ridge'][0]), hexc(m['ridge'][1]); Y = np.arange(H)[:, None]
    lit = gl * 0.2 + np.array([255., 196, 70]) * 0.8
    if water:
        d = np.arange(H - hz)[:, None] / max(1, H - hz)
        mir = sky[np.clip((hz - np.arange(H - hz) * 0.55).astype(int), 0, H - 1)]
        wat = mir[:, None, :] * (0.50 - 0.25 * d[:, :, None]) * np.ones((1, W, 1))
        sh = noise2d(rng, W, H - hz, 60, (H - hz) // 5)
        wat *= (0.80 + 0.45 * sh)[:, :, None]
        if orb and m['orb'] != 'none':
            xs = np.arange(W)[None, :]; width = 30 + 260 * d
            col = np.exp(-((xs - cx) ** 2) / (2 * width ** 2)) * (0.35 + 0.65 * sh) * (1 - 0.7 * d)
            wat += col[:, :, None] * gl[None, None, :] * 0.85
        img[hz:] = wat
        ln = hz - (noise1d(rng, W, 4, 0.5, 2) * 26).astype(int) + 6
        img[(Y >= ln[None, :]) & (Y < hz + 2)] = far * 0.55 + bot * 0.10
        pil = Image.fromarray(np.clip(img, 0, 255).astype(np.uint8))
        if element: draw_element(pil, element, int(W * rng.uniform(0.34, 0.66)), hz + int(H * 0.035), 1.25, near * 0.6, lit)
        img = np.asarray(pil, float).copy()
    else:
        L = 5
        for k in range(L):
            f = k / (L - 1); amp = H * (0.085 - 0.035 * f)
            line = hz + H * 0.05 * k - noise1d(rng, W, 5, 0.52, 2 + k) * amp + amp * 0.35
            if k == 2 and element == 'peak':
                pil = Image.fromarray(np.clip(img, 0, 255).astype(np.uint8))
                draw_element(pil, 'peak', int(W * rng.uniform(0.35, 0.65)), int(hz + H * 0.07), 1.5, far * 0.55 + near * 0.45, np.array([232., 238, 246]))
                img = np.asarray(pil, float).copy()
            col = far + (near - far) * f; col = col * (0.75 + 0.25 * f) + bot * 0.25 * (1 - f)
            mask = Y >= line[None, :]
            shade = 1 - 0.35 * np.clip((Y - line[None, :]) / (H * 0.25), 0, 1)
            img = np.where(mask[:, :, None], col[None, None, :] * shade[:, :, None], img)
            if k == 2 and element and element != 'peak':
                ex = int(W * rng.uniform(0.3, 0.7)); ey = int(line[ex])
                pil = Image.fromarray(np.clip(img, 0, 255).astype(np.uint8))
                draw_element(pil, element, ex, ey, 1.15, near * 0.7, lit)
                img = np.asarray(pil, float).copy()
                if element in ('cabin', 'church', 'windmill', 'city'): glow(img, ex - 20, ey - 26, 46, lit, 0.5)
    if mood == 'storm':
        pil = Image.fromarray(np.clip(img, 0, 255).astype(np.uint8)); d = ImageDraw.Draw(pil, 'RGBA')
        for _ in range(520):
            x, y, l = rng.integers(-100, W), rng.integers(0, H), rng.integers(18, 46)
            d.line([x, y, x + l * 0.32, y + l], fill=(220, 230, 240, int(rng.integers(18, 60))), width=1)
        img = np.asarray(pil, float).copy()
    return np.clip(img, 0, 255)

def finish(img, grain=5.0, vig=0.42, seed=1):
    rng = np.random.default_rng(seed); y, x = np.ogrid[:H, :W]
    v = 1 - vig * (((x - W / 2) / (W * 0.75)) ** 2 + ((y - H / 2) / (H * 0.75)) ** 2)
    img = img * np.clip(v, 0, 1)[:, :, None] + rng.normal(0, grain, (H, W, 1))
    return Image.fromarray(np.clip(img, 0, 255).astype(np.uint8))

def _focus():
    f = os.path.join(ROOT, 'backgrounds', 'credits.csv')
    return {r['id']: (float(r['focus_x'] or 0.5), float(r['focus_y'] or 0.3)) for r in csv.DictReader(open(f, encoding='utf-8'))} if os.path.exists(f) else {}
FOCUS = _focus()

def photo_bg(path, focus_y=0.30):
    """Cover-crop any photo to 4:5. Optional per-image focus point comes from backgrounds/credits.csv."""
    fx, fy = FOCUS.get(os.path.splitext(os.path.basename(path))[0], (0.5, focus_y))
    im = Image.open(path).convert('RGB'); r = max(W / im.width, H / im.height)
    im = im.resize((math.ceil(im.width * r), math.ceil(im.height * r)), Image.LANCZOS)
    left = int((im.width - W) * fx); topy = int((im.height - H) * fy)
    return np.asarray(im.crop((left, topy, left + W, topy + H)), float)

def find_bg(pid):
    for ext in ('jpg', 'jpeg', 'png', 'webp', 'JPG', 'PNG'):
        p = os.path.join(ROOT, 'backgrounds', f'{pid}.{ext}')
        if os.path.exists(p): return p

# ------------------------------------------------------------------ text
def tokens(s):
    out, gold = [], False
    for part in re.split(r'(\*)', s):
        if part == '*': gold = not gold; continue
        out += [(w, gold) for w in part.split()]
    return out

def wrap(toks, f, maxw, d):
    lines, cur, sp = [], [], d.textlength(' ', font=f)
    for w, g in toks:
        if cur and sum(d.textlength(x, font=f) for x, _ in cur) + sp * len(cur) + d.textlength(w, font=f) > maxw:
            lines.append(cur); cur = []
        cur.append((w, g))
    if cur: lines.append(cur)
    return lines

def fit(text, mk, sizes, maxw, maxh, max_lines, lh, d):
    """Largest size at which text fits. '|' in text forces line breaks."""
    for s in sizes:
        f = mk(s)
        if '|' in text:
            lines = [tokens(p) for p in text.split('|')]
            # carry highlight state across manual breaks
            lines, g = [], False
            for p in text.split('|'):
                row = []
                for part in re.split(r'(\*)', p):
                    if part == '*': g = not g; continue
                    row += [(w, g) for w in part.split()]
                lines.append(row)
            ok = all(sum(d.textlength(w, font=f) for w, _ in ln) + d.textlength(' ', font=f) * (len(ln) - 1) <= maxw for ln in lines)
        else:
            lines = wrap(tokens(text), f, maxw, d)
            ok = all(sum(d.textlength(w, font=f) for w, _ in ln) + d.textlength(' ', font=f) * (len(ln) - 1) <= maxw for ln in lines)
        if ok and len(lines) <= max_lines and len(lines) * s * lh <= maxh: return f, s, lines
    return f, s, lines

def draw_lines(d, lines, f, s, lh, cx, y, base, hi, marker=None):
    sp = d.textlength(' ', font=f)
    for ln in lines:
        wds = [d.textlength(w, font=f) for w, _ in ln]; x = cx - (sum(wds) + sp * (len(ln) - 1)) / 2
        if marker:
            i = 0
            while i < len(ln):
                if ln[i][1]:
                    j = i
                    while j + 1 < len(ln) and ln[j + 1][1]: j += 1
                    x0 = x + sum(wds[:i]) + sp * i; x1 = x + sum(wds[:j + 1]) + sp * j
                    d.rounded_rectangle([x0 - 10, y + s * 0.16, x1 + 10, y + s * 1.10], radius=10, fill=marker); i = j
                i += 1
        for (w, g), wd in zip(ln, wds):
            d.text((x, y), w, font=f, fill=(hi if g else base)); x += wd + sp
        y += s * lh
    return y

def spaced(d, text, f, cx, y, fill, track=4):
    wd = sum(d.textlength(c, font=f) + track for c in text) - track; x = cx - wd / 2
    for c in text: d.text((x, y), c, font=f, fill=fill); x += d.textlength(c, font=f) + track

def emblem(size, ring=GOLD, flame=GOLD, bg=INK):
    S = size * 4; im = Image.new('RGBA', (S, S), (0, 0, 0, 0)); d = ImageDraw.Draw(im)
    d.ellipse([0, 0, S - 1, S - 1], fill=ring); d.ellipse([S * .07, S * .07, S * .93, S * .93], fill=bg)
    def drop(cx, cy, w, h):
        return [(cx + w * math.sin(t) * math.sin(t / 2) ** 1.25, cy - h * math.cos(t)) for t in np.linspace(0, 2 * math.pi, 90)]
    d.polygon(drop(S * .5, S * .50, S * .30, S * .30), fill=flame)
    d.polygon(drop(S * .5, S * .60, S * .14, S * .15), fill=bg)
    d.rounded_rectangle([S * .30, S * .80, S * .70, S * .845], radius=int(S * .02), fill=flame)
    return im.resize((size, size), Image.LANCZOS)

def footer(d, y=H - 62, color=(235, 232, 224)):
    spaced(d, f'{BRAND}  |  {TAGLINE}', sans(21, 'SemiBold'), W / 2, y, color, 3)

def overlay(img, top, solid, strength=0.96, color=INK):
    """Dark gradient: clear above `top`, fully dark from `solid` down."""
    y = np.arange(H); a = np.clip((y - top) / max(1, solid - top), 0, 1); a = (a * a * (3 - 2 * a)) * strength
    return img * (1 - a[:, None, None]) + np.array(color, float)[None, None, :] * a[:, None, None]

# ------------------------------------------------------------------ templates
def t_story(p, slide=None):
    lift = 62 if slide else 0
    scratch = ImageDraw.Draw(Image.new('RGB', (10, 10)))
    f, s, lines = fit(p['headline'].upper(), sans, range(88, 46, -2), W - 110, 520, 5, 1.14, scratch)
    block = len(lines) * s * 1.14; text_top = H - 108 - lift - block; div_y = text_top - 58
    bgp = find_bg(p['id'])
    base = photo_bg(bgp) if bgp else scene(p['id'], p.get('scene') or 'dawn', p.get('element') or '', horizon=max(0.30, min(0.50, (div_y - 300) / H)))
    img = overlay(base, div_y - 230, div_y + 20)
    a = np.clip(1 - np.arange(H) / 190.0, 0, 1)[:, None, None] * 0.45; img = img * (1 - a) + np.array(INK, float) * a
    im = finish(img, seed=seed_of(p['id'])); d = ImageDraw.Draw(im)
    d.line([90, div_y, W / 2 - 50, div_y], fill=PARCH, width=3); d.line([W / 2 + 50, div_y, W - 90, div_y], fill=PARCH, width=3)
    e = emblem(72); im.paste(e, (W // 2 - 36, int(div_y) - 36), e)
    draw_lines(d, lines, f, s, 1.14, W / 2, text_top - s * 0.12, (255, 255, 255), GOLD)
    if p.get('tag'):
        tf = sans(22, 'Bold'); tw = sum(d.textlength(c, font=tf) + 3 for c in p['tag'].upper())
        d.rounded_rectangle([44, 44, 44 + tw + 44, 96], radius=26, fill=GOLD)
        spaced(d, p['tag'].upper(), tf, 44 + (tw + 44) / 2, 54, INK, 3)
    if slide: dots(d, slide[0], slide[1]); swipe(d)
    footer(d); return im

def t_quote(p):
    base = scene(p['id'], p.get('scene') or 'night', '', horizon=0.62, orb=False)
    img = base * 0.30 + np.array(INK, float) * 0.70
    glow(img, W / 2, H * 0.30, 420, hexc('#f6b728'), 0.10)
    im = finish(img, grain=4, vig=0.55, seed=seed_of(p['id'])).filter(ImageFilter.GaussianBlur(1.2)); d = ImageDraw.Draw(im)
    f, s, lines = fit(p['headline'], lambda z: serif(z, 600), range(80, 38, -2), W - 190, 620, 9, 1.30, d)
    block = len(lines) * s * 1.30; total = 150 + block + 150; y0 = min((H - 70 - total) / 2 + 105, H - 215 - total)
    qf = serif(300, 700); d.text((W / 2 - d.textlength('“', font=qf) / 2, y0 - 150), '“', font=qf, fill=GOLD)
    y = draw_lines(d, lines, f, s, 1.30, W / 2, y0 + 150, PARCH, GOLD) + 36
    d.line([W / 2 - 70, y, W / 2 + 70, y], fill=GOLD, width=4)
    spaced(d, (p.get('attribution') or '').upper(), sans(30, 'Bold'), W / 2, y + 30, (255, 255, 255), 5)
    if p.get('tag'): spaced(d, p['tag'].upper(), sans(20, 'Medium'), W / 2, y + 78, SLATE, 4)
    e = emblem(54); im.paste(e, (W // 2 - 27, H - 152), e); footer(d); return im

def t_prayer(p):
    bgp = find_bg(p['id'])
    base = photo_bg(bgp, 0.5) if bgp else scene(p['id'], p.get('scene') or 'dawn', '', horizon=0.50, orb=False)
    img = base * 0.62 + np.array(INK, float) * 0.38; img = overlay(img, H * 0.50, H * 0.92, 0.9)
    im = finish(img, seed=seed_of(p['id'])); d = ImageDraw.Draw(im)
    f, s, lines = fit(p['headline'].upper(), sans, range(116, 54, -2), W - 170, 400, 3, 1.10, d)
    sub = p.get('attribution') or ''
    sf, ss, sl = fit(sub, lambda z: serif(z, 500, True), range(54, 34, -2), W - 230, 300, 4, 1.34, d)
    block = 70 + len(lines) * s * 1.10 + 40 + len(sl) * ss * 1.34; y = (H - 90 - block) / 2
    pan = Image.new('RGBA', im.size, (0, 0, 0, 0)); pd = ImageDraw.Draw(pan)
    pd.rounded_rectangle([60, y - 60, W - 60, y + block + 50], radius=36, fill=(10, 13, 20, 150))
    im = Image.alpha_composite(im.convert('RGBA'), pan).convert('RGB'); d = ImageDraw.Draw(im)
    spaced(d, (p.get('tag') or 'A PRAYER FOR').upper(), sans(34, 'Bold'), W / 2, y, GOLD, 9)
    y = draw_lines(d, lines, f, s, 1.10, W / 2, y + 62, (255, 255, 255), GOLD) + 26
    d.line([W / 2 - 60, y, W / 2 + 60, y], fill=GOLD, width=4)
    draw_lines(d, sl, sf, ss, 1.34, W / 2, y + 22, PARCH, GOLD)
    e = emblem(54); im.paste(e, (W // 2 - 27, H - 152), e); footer(d); return im

def t_question(p):
    rng = np.random.default_rng(seed_of(p['id']))
    img = np.ones((H, W, 3)) * np.array(PARCH, float); img += (noise2d(rng, W, H, 9, 11, blur=30)[:, :, None] - 0.5) * 22
    im = finish(img, grain=3, vig=0.16, seed=seed_of(p['id'])); d = ImageDraw.Draw(im)
    d.rounded_rectangle([34, 34, W - 34, H - 34], radius=30, outline=INK, width=5)
    f, s, lines = fit(p['headline'].upper(), sans, range(96, 50, -2), W - 190, 700, 6, 1.20, d)
    block = len(lines) * s * 1.20; y = (H - block) / 2 - 20
    spaced(d, (p.get('tag') or 'TELL US').upper(), sans(30, 'Bold'), W / 2, y - 96, (150, 96, 8), 8)
    draw_lines(d, lines, f, s, 1.20, W / 2, y, INK, INK, marker=GOLD)
    e = emblem(64, ring=INK, flame=INK, bg=PARCH); im.paste(e, (W // 2 - 32, H - 176), e)
    footer(d, H - 92, INK); return im


def dots(d, i, n, y=H - 118, on=GOLD, off=(92, 98, 112)):
    x0 = W / 2 - (n - 1) * 17
    for k in range(n):
        r = 8 if k == i else 6
        d.ellipse([x0 + k * 34 - r, y - r, x0 + k * 34 + r, y + r], fill=on if k == i else off)

def swipe(d, color=GOLD):
    spaced(d, 'SWIPE', sans(24, 'Bold'), W - 150, H - 135, color, 5)
    d.polygon([(W - 96, H - 132), (W - 96, H - 106), (W - 74, H - 119)], fill=color)

def parts(p): return [x.strip() for x in p['headline'].split('||') if x.strip()]

def dark_bg(p, k=0, mix=0.26, blur=3, horizon=0.40):
    bgp = find_bg(p['id'])
    base = photo_bg(bgp) if bgp else scene(p['id'], p.get('scene') or 'night', p.get('element') or '', horizon=horizon, orb=bool(bgp))
    img = base * mix + np.array(INK, float) * (1 - mix)
    return finish(img, grain=4, vig=0.5, seed=seed_of(p['id'] + str(k))).filter(ImageFilter.GaussianBlur(blur))

def t_carousel(p):
    """Mini-story: slide 1 is a story-style hook, the rest are big-type text slides on the same scene."""
    sl = parts(p); n = len(sl); out = [t_story(dict(p, headline=sl[0]), slide=(0, n))]
    for i in range(1, n):
        im = dark_bg(p, i); d = ImageDraw.Draw(im)
        f, s, lines = fit(sl[i].upper(), sans, range(92, 46, -2), W - 130, 840, 9, 1.17, d)
        y = (H - 130 - len(lines) * s * 1.17) / 2 + 30
        spaced(d, f'{i + 1} / {n}', sans(28, 'Bold'), W / 2, 72, GOLD, 6)
        draw_lines(d, lines, f, s, 1.17, W / 2, y, (255, 255, 255), GOLD)
        dots(d, i, n)
        if i < n - 1: swipe(d)
        footer(d); out.append(im)
    return out

def t_list(p):
    """Numbered list: first part is 'N :: title', then one item per slide. An item starting with '>>' is a closing slide."""
    sl = parts(p); n = len(sl); out = []; num, _, title = sl[0].partition('::')
    im = dark_bg(p, 0, mix=0.34); d = ImageDraw.Draw(im)
    nf = sans(380, 'Black'); d.text((W / 2 - d.textlength(num.strip(), font=nf) / 2, 120), num.strip(), font=nf, fill=GOLD)
    f, s, lines = fit(title.strip().upper(), sans, range(96, 50, -2), W - 150, 420, 4, 1.14, d)
    y = draw_lines(d, lines, f, s, 1.14, W / 2, 640, (255, 255, 255), GOLD) + 34
    if p.get('attribution'): spaced(d, p['attribution'].upper(), sans(26, 'Bold'), W / 2, y, SLATE, 5)
    dots(d, 0, n); swipe(d); footer(d); out.append(im)
    for i in range(1, n):
        im = dark_bg(p, i); d = ImageDraw.Draw(im); txt = sl[i]
        if txt.startswith('>>'):
            f, s, lines = fit(txt[2:].strip().upper(), sans, range(92, 48, -2), W - 150, 760, 7, 1.17, d)
            draw_lines(d, lines, f, s, 1.17, W / 2, (H - 130 - len(lines) * s * 1.17) / 2 + 20, (255, 255, 255), GOLD)
        else:
            nf = sans(210, 'Black'); d.text((W / 2 - d.textlength(str(i), font=nf) / 2, 110), str(i), font=nf, fill=GOLD)
            f, s, lines = fit(txt, lambda z: serif(z, 600), range(92, 40, -2), W - 170, 640, 8, 1.30, d)
            y = 400 + (700 - len(lines) * s * 1.30) / 2
            y = draw_lines(d, lines, f, s, 1.30, W / 2, y, PARCH, GOLD) + 30
            d.line([W / 2 - 60, y, W / 2 + 60, y], fill=GOLD, width=4)
            if p.get('tag'): spaced(d, p['tag'].upper(), sans(24, 'Bold'), W / 2, y + 26, (255, 255, 255), 5)
        dots(d, i, n)
        if i < n - 1: swipe(d)
        footer(d); out.append(im)
    return out

def t_oneliner(p):
    rng = np.random.default_rng(seed_of(p['id']))
    img = np.ones((H, W, 3)) * np.array(GOLD, float); img += (noise2d(rng, W, H, 7, 9, blur=40)[:, :, None] - 0.5) * 30
    im = finish(img, grain=3, vig=0.20, seed=seed_of(p['id'])); d = ImageDraw.Draw(im)
    f, s, lines = fit(p['headline'].upper(), sans, range(112, 54, -2), W - 170, 860, 8, 1.16, d)
    y = (H - 150 - len(lines) * s * 1.16) / 2 + 30
    draw_lines(d, lines, f, s, 1.16, W / 2, y, INK, PARCH, marker=INK)
    e = emblem(64, ring=INK, flame=INK, bg=GOLD); im.paste(e, (W // 2 - 32, H - 176), e)
    footer(d, H - 92, INK); return im

def t_thennow(p):
    old, new = (parts(p) + [''])[:2]; split = int(H * 0.47)
    rng = np.random.default_rng(seed_of(p['id'])); img = np.ones((H, W, 3)) * np.array(INK, float)
    img[:split] = np.array(PARCH, float) + (noise2d(rng, W, split, 9, 6, blur=30)[:, :, None] - 0.5) * 20
    im = finish(img, grain=3, vig=0.18, seed=seed_of(p['id'])); d = ImageDraw.Draw(im)
    def chip(text, y, bg, fg):
        tf = sans(26, 'Bold'); tw = sum(d.textlength(c, font=tf) + 6 for c in text)
        d.rounded_rectangle([W / 2 - tw / 2 - 26, y, W / 2 + tw / 2 + 26, y + 54], radius=27, fill=bg); spaced(d, text, tf, W / 2 + 3, y + 9, fg, 6)
    chip((p.get('tag') or '1710').upper(), 64, INK, PARCH)
    f, s, lines = fit('“' + old + '”', lambda z: serif(z, 600, True), range(68, 34, -2), W - 130, split - 215, 8, 1.28, d)
    y = 132 + (split - 205 - len(lines) * s * 1.28) / 2
    y = draw_lines(d, lines, f, s, 1.28, W / 2, y, INK, (150, 96, 8))
    spaced(d, (p.get('attribution') or '').upper(), sans(24, 'Bold'), W / 2, split - 62, (90, 84, 70), 5)
    chip('IN PLAIN WORDS', split + 46, GOLD, INK)
    f, s, lines = fit(new.upper(), sans, range(88, 46, -2), W - 150, H - split - 330, 6, 1.16, d)
    y = split + 130 + (H - split - 290 - len(lines) * s * 1.16) / 2
    draw_lines(d, lines, f, s, 1.16, W / 2, y, (255, 255, 255), GOLD)
    e = emblem(54); im.paste(e, (W // 2 - 27, H - 152), e); footer(d); return im

def t_verse(p):
    verse, witness = (parts(p) + [''])[:2]
    im = dark_bg(p, 0, mix=0.50, blur=1.5, horizon=0.55); d = ImageDraw.Draw(im)
    f, s, lines = fit(verse, lambda z: serif(z, 600), range(76, 40, -2), W - 180, 520, 8, 1.30, d)
    y = 150 + (520 - len(lines) * s * 1.30) / 2
    y = draw_lines(d, lines, f, s, 1.30, W / 2, y, (255, 255, 255), GOLD) + 30
    spaced(d, (p.get('attribution') or '').upper(), sans(32, 'Bold'), W / 2, y, GOLD, 6)
    wf, ws, wl = fit(witness, lambda z: sans(z, 'SemiBold'), range(46, 30, -2), W - 260, 250, 5, 1.36, d)
    bh = 96 + len(wl) * ws * 1.36 + 40; by = H - 190 - bh
    pan = Image.new('RGBA', im.size, (0, 0, 0, 0)); pd = ImageDraw.Draw(pan)
    pd.rounded_rectangle([70, by, W - 70, by + bh], radius=30, fill=(10, 13, 20, 185), outline=GOLD + (255,), width=3)
    im = Image.alpha_composite(im.convert('RGBA'), pan).convert('RGB'); d = ImageDraw.Draw(im)
    spaced(d, (p.get('tag') or 'AND IT HAPPENED').upper(), sans(26, 'Bold'), W / 2, by + 34, GOLD, 7)
    draw_lines(d, wl, wf, ws, 1.36, W / 2, by + 88, PARCH, GOLD)
    e = emblem(54); im.paste(e, (W // 2 - 27, H - 152), e); footer(d); return im

TEMPLATES = {'story': t_story, 'quote': t_quote, 'prayer': t_prayer, 'question': t_question, 'carousel': t_carousel,
             'list': t_list, 'oneliner': t_oneliner, 'thennow': t_thennow, 'verse': t_verse}

def brand_assets():
    out = os.path.join(ROOT, 'brand'); os.makedirs(out, exist_ok=True)
    S = 1080; a = np.ones((S, S, 3)) * np.array(INK, float); y, x = np.ogrid[:S, :S]
    a += np.exp(-(((x - S / 2) ** 2 + (y - S * .52) ** 2) / (2 * 300.0 ** 2)))[:, :, None] * hexc('#f6b728')[None, None, :] * 0.16
    av = Image.fromarray(np.clip(a, 0, 255).astype(np.uint8)); e = emblem(620); av.paste(e, (230, 230), e)
    av.save(os.path.join(out, 'avatar_1080.png'))
    global W, H; W0, H0 = W, H; W, H = 1640, 924
    img = scene('cover-he-still-answers-2', 'dusk', 'cabin', horizon=0.70); img = overlay(img, H * 0.62, H * 1.1, 0.7)
    a = np.clip(1 - np.abs(np.arange(H) - 360) / 300.0, 0, 1)[:, None, None] * 0.55; img = img * (1 - a) + np.array(INK, float) * a; c = finish(img, seed=3); d = ImageDraw.Draw(c)
    f = sans(118); d.text((W / 2 - d.textlength(BRAND, font=f) / 2, 250), BRAND, font=f, fill=(255, 255, 255))
    d.line([W / 2 - 90, 420, W / 2 + 90, 420], fill=GOLD, width=5)
    spaced(d, TAGLINE, sans(36, 'Bold'), W / 2, 446, GOLD, 8)
    c.save(os.path.join(out, 'cover_1640x924.png')); W, H = W0, H0
    print('brand assets written to brand/')

def main():
    ap = argparse.ArgumentParser(); ap.add_argument('--csv', default=os.path.join(ROOT, 'content', 'posts_master.csv'))
    ap.add_argument('--only', nargs='*'); ap.add_argument('--force', action='store_true'); ap.add_argument('--brand', action='store_true')
    a = ap.parse_args()
    if a.brand: return brand_assets()
    out = os.path.join(ROOT, 'output'); os.makedirs(out, exist_ok=True); n = 0
    for p in csv.DictReader(open(a.csv, encoding='utf-8')):
        if a.only and p['id'] not in a.only: continue
        if p['type'] not in TEMPLATES or not p.get('image_file'): continue      # text-only posts have no image
        files = [os.path.join(out, f) for f in p['image_file'].split(',')]
        bg = find_bg(p['id'])
        if all(os.path.exists(f) for f in files) and not a.force and not (bg and os.path.getmtime(bg) > os.path.getmtime(files[0])): continue
        res = TEMPLATES[p['type']](p); res = res if isinstance(res, list) else [res]
        for f, im in zip(files, res): im.save(f, quality=90, optimize=True); n += 1
        if n % 10 == 0: print(f'  {n} rendered ...', flush=True)
    print(f'{n} image(s) rendered to output/')

if __name__ == '__main__': main()
