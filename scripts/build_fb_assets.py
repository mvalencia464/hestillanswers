#!/usr/bin/env python3
"""Build branded Facebook / Instagram page assets from the Flow backgrounds in brand/flow_src/."""
from __future__ import annotations

import math
import os
import sys

import numpy as np
from PIL import Image, ImageDraw, ImageFilter

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, 'engine'))
import render as R  # noqa: E402

SRC = os.path.join(ROOT, 'brand', 'flow_src')
OUT = os.path.join(ROOT, 'brand')
SHEET = '/workspace/hsa-preview-shots/fb-assets-sheet.jpg'

INK, GOLD, PARCH = R.INK, R.GOLD, R.PARCH
WHITE = (255, 255, 255)
BRAND, TAGLINE = R.BRAND, R.TAGLINE

FILES = {
    'cover': 'Farmhouse_at_dawn_landscape_9f1b6625.jpg',
    'welcome': 'Leather-bound_book_on_table_9ae626a7.jpg',
    'ebook': 'Old_books_tied_with_twine_c50ecadc.jpg',
    'story': 'Country_road_winding_toward_cottage_689c249f.jpg',
    'glow': 'Black_background_with_warm_glow_708a2979.jpg',
}


def src(key):
    return os.path.join(SRC, FILES[key])


def cover_crop(im, w, h, fx=0.5, fy=0.5):
    im = im.convert('RGB')
    r = max(w / im.width, h / im.height)
    im = im.resize((math.ceil(im.width * r), math.ceil(im.height * r)), Image.LANCZOS)
    left = int((im.width - w) * fx)
    top = int((im.height - h) * fy)
    return im.crop((left, top, left + w, top + h))


def finish_wh(img, w, h, grain=3.0, vig=0.28, seed=7):
    rng = np.random.default_rng(seed)
    y, x = np.ogrid[:h, :w]
    v = 1 - vig * (((x - w / 2) / (w * 0.75)) ** 2 + ((y - h / 2) / (h * 0.75)) ** 2)
    img = img * np.clip(v, 0, 1)[:, :, None] + rng.normal(0, grain, (h, w, 1))
    return Image.fromarray(np.clip(img, 0, 255).astype(np.uint8))


def overlay_wh(img, h, top, solid, strength=0.96, color=INK):
    y = np.arange(h)
    a = np.clip((y - top) / max(1, solid - top), 0, 1)
    a = (a * a * (3 - 2 * a)) * strength
    return img * (1 - a[:, None, None]) + np.array(color, float)[None, None, :] * a[:, None, None]


def text_layer(size, draw_fn):
    layer = Image.new('RGBA', size, (0, 0, 0, 0))
    d = ImageDraw.Draw(layer)
    draw_fn(d, layer)
    return layer


def shadow_text(layer, xy, text, font, fill, shadow=(0, 0, 0, 150), blur=6, ox=0, oy=2):
    """Draw soft-shadowed text onto an RGBA layer."""
    tmp = Image.new('RGBA', layer.size, (0, 0, 0, 0))
    td = ImageDraw.Draw(tmp)
    x, y = xy
    td.text((x + ox, y + oy), text, font=font, fill=shadow)
    tmp = tmp.filter(ImageFilter.GaussianBlur(blur))
    layer.alpha_composite(tmp)
    ImageDraw.Draw(layer).text((x, y), text, font=font, fill=fill)


def shadow_spaced(layer, text, font, x0, y, fill, track, shadow=(0, 0, 0, 150), blur=5, ox=0, oy=2):
    tmp = Image.new('RGBA', layer.size, (0, 0, 0, 0))
    td = ImageDraw.Draw(tmp)
    x = x0
    for c in text:
        td.text((x + ox, y + oy), c, font=font, fill=shadow)
        x += td.textlength(c, font=font) + track
    tmp = tmp.filter(ImageFilter.GaussianBlur(blur))
    layer.alpha_composite(tmp)
    d = ImageDraw.Draw(layer)
    x = x0
    for c in text:
        d.text((x, y), c, font=font, fill=fill)
        x += d.textlength(c, font=font) + track


def spaced_width(d, text, font, track):
    return sum(d.textlength(c, font=font) + track for c in text) - track


# ------------------------------------------------------------------ cover
def build_cover():
    W, H = 1640, 924
    photo = cover_crop(Image.open(src('cover')), W, H, 0.5, 0.5)
    img = np.asarray(photo, float)
    # A very light ink wash across the mid-sky so white type stays crisp on dusk.
    y = np.arange(H)[:, None]
    band = np.clip(1 - np.abs(y - 340) / 280.0, 0, 1) * 0.22
    # fade the wash toward the right so the house glow stays warm
    x = np.linspace(1, 0.15, W)[None, :]
    a = (band * x)[:, :, None]
    img = img * (1 - a) + np.array(INK, float) * a
    im = finish_wh(img, W, H, grain=2.4, vig=0.22, seed=3)

    title_font = R.sans(100)
    tag_font = R.sans(32, 'Bold')
    left = 150
    title_y = 214
    # measure
    scratch = ImageDraw.Draw(im)
    title_w = scratch.textlength(BRAND, font=title_font)
    tag_w = spaced_width(scratch, TAGLINE, tag_font, 7)
    # keep the lockup in the open left sky and inside the 90px side margins
    assert left + title_w < 1550
    assert left >= 90

    layer = Image.new('RGBA', im.size, (0, 0, 0, 0))
    shadow_text(layer, (left, title_y), BRAND, title_font, WHITE,
                shadow=(0, 0, 0, 170), blur=7, oy=3)
    rule_y = title_y + 132
    rule_w = 160
    rd = ImageDraw.Draw(layer)
    # gold rule, left-aligned under the title
    rd.line([left, rule_y, left + rule_w, rule_y], fill=GOLD + (255,), width=5)
    shadow_spaced(layer, TAGLINE, tag_font, left, rule_y + 22, GOLD, 7,
                  shadow=(0, 0, 0, 150), blur=5, oy=2)
    im = Image.alpha_composite(im.convert('RGBA'), layer).convert('RGB')
    path = os.path.join(OUT, 'fb_cover_1640x924.jpg')
    im.save(path, quality=95, optimize=True, subsampling=0)

    # Mobile preview: 16:9 cover (the full image) with the avatar overlapping, as on a phone.
    preview = build_mobile_preview(im)
    preview_path = os.path.join(OUT, 'fb_cover_mobile_preview.jpg')
    preview.save(preview_path, quality=95, optimize=True, subsampling=0)
    return im, preview


def build_mobile_preview(cover):
    """Show the 16:9 mobile crop with the profile photo overlapping the bottom-left."""
    cw, ch = 1080, 608  # 16:9
    cover_m = cover.resize((cw, ch), Image.LANCZOS)
    # Canvas: cover plus a white name plate below, like a mobile profile header.
    W, H = 1080, 980
    canvas = Image.new('RGB', (W, H), (255, 255, 255))
    canvas.paste(cover_m, (0, 0))
    avatar = Image.open(os.path.join(OUT, 'avatar_1080.png')).convert('RGBA')
    av_size = 220
    avatar = avatar.resize((av_size, av_size), Image.LANCZOS)
    # circular mask with a white ring, Facebook-style
    ring = 8
    outer = av_size + ring * 2
    badge = Image.new('RGBA', (outer, outer), (0, 0, 0, 0))
    bd = ImageDraw.Draw(badge)
    bd.ellipse([0, 0, outer - 1, outer - 1], fill=(255, 255, 255, 255))
    mask = Image.new('L', (av_size, av_size), 0)
    ImageDraw.Draw(mask).ellipse([0, 0, av_size - 1, av_size - 1], fill=255)
    badge.paste(avatar, (ring, ring), mask)
    # Overlap: about 40% of the avatar sits on the cover
    ax, ay = 40, ch - int(av_size * 0.48) - ring
    canvas.paste(badge, (ax, ay), badge)

    d = ImageDraw.Draw(canvas)
    name_x = 48
    name_y = ay + outer + 18
    d.text((name_x, name_y), 'He Still Answers', font=R.sans(44), fill=(20, 20, 20))
    d.text((name_x, name_y + 62), 'True stories of answered prayer.',
           font=R.serif(26, 500), fill=(90, 94, 102))
    # Sign Up pill
    btn = 'Sign Up'
    bf = R.sans(22, 'Bold')
    bw = d.textlength(btn, font=bf)
    bx0, by0 = name_x, name_y + 118
    d.rounded_rectangle([bx0, by0, bx0 + bw + 48, by0 + 52], radius=8, fill=GOLD)
    d.text((bx0 + 24, by0 + 10), btn, font=bf, fill=INK)
    # small caption so it's obviously a preview
    cap = R.sans(16, 'Medium')
    d.text((W - 24 - d.textlength('MOBILE PREVIEW', font=cap), H - 36),
           'MOBILE PREVIEW', font=cap, fill=(160, 160, 160))
    return canvas


# ------------------------------------------------------------------ 4:5 story-style posts
def story_card(bg_path, headline, extra_line=None, seed=11):
    W, H = R.W, R.H
    scratch = ImageDraw.Draw(Image.new('RGB', (10, 10)))
    extra_h = 58 if extra_line else 0
    f, s, lines = R.fit(headline.upper(), R.sans, range(88, 46, -2),
                        W - 110, 520 - extra_h, 5, 1.14, scratch)
    block = len(lines) * s * 1.14 + extra_h
    text_top = H - 108 - block
    div_y = text_top - 58
    base = R.photo_bg(bg_path)
    img = R.overlay(base, div_y - 230, div_y + 20)
    a = np.clip(1 - np.arange(H) / 190.0, 0, 1)[:, None, None] * 0.45
    img = img * (1 - a) + np.array(INK, float) * a
    im = R.finish(img, seed=seed)
    d = ImageDraw.Draw(im)
    d.line([90, div_y, W / 2 - 50, div_y], fill=PARCH, width=3)
    d.line([W / 2 + 50, div_y, W - 90, div_y], fill=PARCH, width=3)
    e = R.emblem(72)
    im.paste(e, (W // 2 - 36, int(div_y) - 36), e)
    y = R.draw_lines(d, lines, f, s, 1.14, W / 2, text_top - s * 0.12, WHITE, GOLD)
    if extra_line:
        ef = R.sans(24, 'Medium')
        R.spaced(d, extra_line, ef, W / 2, y + 8, PARCH, 1)
    R.footer(d)
    return im


def build_posts():
    welcome = story_card(
        src('welcome'),
        'TRUE STORIES OF|ANSWERED PRAYER.|*ONE EVERY DAY.*',
        seed=11,
    )
    welcome_path = os.path.join(OUT, 'post_welcome_1080x1350.jpg')
    welcome.save(welcome_path, quality=95, optimize=True, subsampling=0)

    ebook = story_card(
        src('ebook'),
        'FREE EBOOK:|*30 TRUE STORIES OF|ANSWERED PRAYER*',
        extra_line='Free at hestillanswers.pages.dev',
        seed=13,
    )
    ebook_path = os.path.join(OUT, 'post_ebook_1080x1350.jpg')
    ebook.save(ebook_path, quality=95, optimize=True, subsampling=0)
    return welcome, ebook


# ------------------------------------------------------------------ stories / reels
def build_story_templates():
    W, H = 1080, 1920
    photo = cover_crop(Image.open(src('story')), W, H, 0.5, 0.5)
    img = np.asarray(photo, float)
    # Subtle ink at the top (logo contrast) and a gentle lift of darkness at the
    # bottom; the middle of the road and cottage stay clear for captions.
    y = np.arange(H)
    top = np.clip(1 - y / 420.0, 0, 1) ** 1.2 * 0.42
    bot = np.clip((y - 1400) / 520.0, 0, 1)
    bot = (bot * bot * (3 - 2 * bot)) * 0.40
    a = np.maximum(top, bot)[:, None, None]
    img = img * (1 - a) + np.array(INK, float) * a
    base = finish_wh(img, W, H, grain=2.2, vig=0.20, seed=5)

    blank_path = os.path.join(OUT, 'story_template_blank_1080x1920.jpg')
    base.save(blank_path, quality=95, optimize=True, subsampling=0)

    im = base.copy()
    layer = Image.new('RGBA', im.size, (0, 0, 0, 0))
    # Horizontal lockup: emblem + wordmark, centered, below typical story chrome.
    emblem_s = 78
    e = R.emblem(emblem_s)
    word_font = R.sans(36)
    scratch = ImageDraw.Draw(layer)
    word_w = scratch.textlength(BRAND, font=word_font)
    gap = 22
    total = emblem_s + gap + word_w
    x0 = (W - total) / 2
    y0 = 200
    layer.paste(e, (int(x0), y0), e)
    text_y = y0 + (emblem_s - 36) / 2 - 6
    shadow_text(layer, (x0 + emblem_s + gap, text_y), BRAND, word_font, WHITE,
                shadow=(0, 0, 0, 160), blur=5, oy=2)
    im = Image.alpha_composite(im.convert('RGBA'), layer).convert('RGB')
    path = os.path.join(OUT, 'story_template_1080x1920.jpg')
    im.save(path, quality=95, optimize=True, subsampling=0)
    return im, base


# ------------------------------------------------------------------ highlight icons
def icon_open_book(d, cx, cy, s, color, width):
    """Simple gold line icon of an open book, centered at (cx, cy)."""
    # spine
    d.line([(cx, cy - s * 0.08), (cx, cy + s * 0.42)], fill=color, width=width)
    # left page
    left = [
        (cx, cy - s * 0.08),
        (cx - s * 0.62, cy - s * 0.38),
        (cx - s * 0.70, cy + s * 0.28),
        (cx, cy + s * 0.42),
    ]
    right = [
        (cx, cy - s * 0.08),
        (cx + s * 0.62, cy - s * 0.38),
        (cx + s * 0.70, cy + s * 0.28),
        (cx, cy + s * 0.42),
    ]
    d.line(left, fill=color, width=width, joint='curve')
    d.line(right, fill=color, width=width, joint='curve')
    # page lines
    for i, t in enumerate((0.18, 0.34, 0.50)):
        y1 = cy - s * 0.18 + s * (0.42 * t)
        # left
        x1a, y1a = cx - s * 0.12, y1 + s * 0.04
        x1b, y1b = cx - s * (0.52 - i * 0.02), y1 - s * 0.16
        d.line([(x1a, y1a), (x1b, y1b)], fill=color, width=max(3, width - 4))
        # right
        x2a, y2a = cx + s * 0.12, y1 + s * 0.04
        x2b, y2b = cx + s * (0.52 - i * 0.02), y1 - s * 0.16
        d.line([(x2a, y2a), (x2b, y2b)], fill=color, width=max(3, width - 4))


def icon_flame(d, cx, cy, s, color, width):
    """Outline of the brand flame, no ring."""
    def drop(cx_, cy_, w, h, scale=1.0):
        return [(cx_ + w * math.sin(t) * math.sin(t / 2) ** 1.25,
                 cy_ - h * math.cos(t)) for t in np.linspace(0, 2 * math.pi, 80)]

    outer = drop(cx, cy - s * 0.04, s * 0.38, s * 0.42)
    inner = drop(cx, cy + s * 0.10, s * 0.16, s * 0.18)
    d.line(outer + [outer[0]], fill=color, width=width, joint='curve')
    d.line(inner + [inner[0]], fill=color, width=max(3, width - 2), joint='curve')
    # base bar
    d.rounded_rectangle([cx - s * 0.28, cy + s * 0.40, cx + s * 0.28, cy + s * 0.50],
                        radius=int(s * 0.04), outline=color, width=width)


def icon_closed_book(d, cx, cy, s, color, width):
    """Front-facing closed book with a spine and a small bookmark, gold line."""
    top = cy - s * 0.38
    bot = cy + s * 0.44
    left = cx - s * 0.40
    right = cx + s * 0.42
    spine = left + s * 0.18
    rad = max(2, int(s * 0.04))
    d.rounded_rectangle([left, top, right, bot], radius=rad, outline=color, width=width)
    d.line([(spine, top + width // 2), (spine, bot - width // 2)], fill=color, width=width)
    thin = max(3, width - 4)
    d.line([(left + s * 0.07, top + s * 0.10), (left + s * 0.07, bot - s * 0.10)],
           fill=color, width=thin)
    d.line([(spine + s * 0.10, cy - s * 0.08), (right - s * 0.12, cy - s * 0.08)],
           fill=color, width=thin)
    d.line([(spine + s * 0.10, cy + s * 0.08), (right - s * 0.20, cy + s * 0.08)],
           fill=color, width=thin)
    # rectangular bookmark tab peeking from the top of the cover
    bw, bh = s * 0.11, s * 0.14
    bx0 = (spine + right) / 2 - bw / 2
    d.line([
        (bx0, top + thin / 2),
        (bx0, top - bh),
        (bx0 + bw, top - bh),
        (bx0 + bw, top + thin / 2),
    ], fill=color, width=thin, joint='curve')


def build_highlight(icon_fn, label, filename):
    S = 1080
    bg = cover_crop(Image.open(src('glow')), S, S, 0.5, 0.5)
    img = np.asarray(bg, float)
    im = finish_wh(img, S, S, grain=2.0, vig=0.18, seed=9)

    # Draw icon at 4x for clean strokes, then composite.
    hi = Image.new('RGBA', (S * 2, S * 2), (0, 0, 0, 0))
    hd = ImageDraw.Draw(hi)
    cx, cy, s, width = S, int(S * 0.88), int(S * 0.42), 18
    icon_fn(hd, cx, cy, s, GOLD + (255,), width)
    hi = hi.resize((S, S), Image.LANCZOS)

    layer = Image.new('RGBA', (S, S), (0, 0, 0, 0))
    layer.alpha_composite(hi)
    d = ImageDraw.Draw(layer)
    lf = R.sans(36, 'Bold')
    # letter-spaced label, centered, under the icon, well inside the circle
    track = 8
    scratch = ImageDraw.Draw(Image.new('RGB', (10, 10)))
    tw = spaced_width(scratch, label, lf, track)
    lx = (S - tw) / 2
    ly = 690
    shadow_spaced(layer, label, lf, lx, ly, GOLD, track,
                  shadow=(0, 0, 0, 140), blur=4, oy=2)
    im = Image.alpha_composite(im.convert('RGBA'), layer).convert('RGB')
    path = os.path.join(OUT, filename)
    im.save(path, optimize=True)
    return im


def build_highlights():
    stories = build_highlight(icon_open_book, 'STORIES', 'highlight_stories.png')
    prayers = build_highlight(icon_flame, 'PRAYERS', 'highlight_prayers.png')
    ebook = build_highlight(icon_closed_book, 'EBOOK', 'highlight_ebook.png')
    return stories, prayers, ebook


# ------------------------------------------------------------------ contact sheet
def label(im, text):
    """Bar of ink under an image with a parchment label."""
    pad = 54
    canvas = Image.new('RGB', (im.width, im.height + pad), INK)
    canvas.paste(im, (0, 0))
    d = ImageDraw.Draw(canvas)
    f = R.sans(22, 'SemiBold')
    d.text(((im.width - d.textlength(text, font=f)) / 2, im.height + 14),
           text, font=f, fill=PARCH)
    return canvas


def circle_mask(im):
    m = Image.new('L', im.size, 0)
    ImageDraw.Draw(m).ellipse([0, 0, im.width - 1, im.height - 1], fill=255)
    out = Image.new('RGB', im.size, INK)
    out.paste(im, mask=m)
    return out


def fit_w(im, w):
    h = int(im.height * w / im.width)
    return im.resize((w, h), Image.LANCZOS)


def contact_sheet(cover, mobile, welcome, ebook, story, blank, highs):
    # Layout on ink:
    # row 1: cover (desktop crop inset?) + mobile preview
    # actually: full cover, desktop crop, mobile preview
    # row 2: welcome + ebook
    # row 3: story template + blank
    # row 4: three circular highlights
    margin, gap = 48, 36
    col = 720

    desktop = cover.crop((0, 150, 1640, 774))
    # annotate desktop crop with a thin gold "DESKTOP CROP" already by labeling

    c_full = label(fit_w(cover, 960), 'COVER  1640 × 924')
    c_desk = label(fit_w(desktop, 960), 'DESKTOP CROP  (middle 1640 × 624)')
    c_mob = label(fit_w(mobile, 640), 'MOBILE PREVIEW')

    p_w = label(fit_w(welcome, col), 'WELCOME POST  1080 × 1350')
    p_e = label(fit_w(ebook, col), 'EBOOK POST  1080 × 1350')
    s_t = label(fit_w(story, 480), 'STORY TEMPLATE  1080 × 1920')
    s_b = label(fit_w(blank, 480), 'REELS / BLANK  1080 × 1920')

    hs = []
    names = ['HIGHLIGHT · STORIES', 'HIGHLIGHT · PRAYERS', 'HIGHLIGHT · EBOOK']
    for im, name in zip(highs, names):
        circ = circle_mask(im).resize((420, 420), Image.LANCZOS)
        hs.append(label(circ, name))

    # Compute canvas size
    row1_h = max(c_full.height, c_desk.height) + c_mob.height  # we'll put mobile to the right of both stacked covers
    # Better layout:
    # Left stack: full cover + desktop crop (960 wide)
    # Right: mobile preview, then the two story templates under it? 
    # Simpler grid:

    # Row A: cover full | desktop crop | mobile (scaled to same height as cover)
    rowA_items = [c_full, c_desk, c_mob]
    # scale mobile to same height as c_full if needed - already labeled independently
    rowA_h = max(i.height for i in rowA_items)
    rowA_w = sum(i.width for i in rowA_items) + gap * 2

    rowB_items = [p_w, p_e, s_t, s_b]
    rowB_h = max(i.height for i in rowB_items)
    rowB_w = sum(i.width for i in rowB_items) + gap * 3

    rowC_w = sum(i.width for i in hs) + gap * 2
    rowC_h = hs[0].height

    width = max(rowA_w, rowB_w, rowC_w) + margin * 2
    # title block
    title_h = 160
    height = title_h + rowA_h + rowB_h + rowC_h + margin * 4 + 20
    sheet = Image.new('RGB', (width, height), INK)
    d = ImageDraw.Draw(sheet)
    tf = R.sans(48)
    sf = R.sans(20, 'SemiBold')
    title = 'HE STILL ANSWERS'
    d.text(((width - d.textlength(title, font=tf)) / 2, 40), title, font=tf, fill=WHITE)
    sub = 'FACEBOOK  &  INSTAGRAM  ASSETS'
    # gold rule + spaced subtitle
    rw = 80
    cx = width / 2
    d.line([cx - rw, 104, cx + rw, 104], fill=GOLD, width=3)
    tw = spaced_width(d, sub, sf, 5)
    x = cx - tw / 2
    y = 116
    for ch in sub:
        d.text((x, y), ch, font=sf, fill=GOLD)
        x += d.textlength(ch, font=sf) + 5

    def paste_row(items, top, row_w, align='center'):
        x = (width - row_w) / 2
        row_h = max(i.height for i in items)
        for im in items:
            if align == 'bottom':
                yy = top + (row_h - im.height)
            elif align == 'top':
                yy = top
            else:
                yy = top + (row_h - im.height) / 2
            sheet.paste(im, (int(x), int(yy)))
            x += im.width + gap

    y = title_h
    paste_row(rowA_items, y, rowA_w)
    y += rowA_h + margin
    paste_row(rowB_items, y, rowB_w)
    y += rowB_h + margin
    paste_row(hs, y, rowC_w)

    os.makedirs(os.path.dirname(SHEET), exist_ok=True)
    sheet.save(SHEET, quality=92, optimize=True)
    return sheet


def main():
    os.makedirs(OUT, exist_ok=True)
    print('building cover...')
    cover, mobile = build_cover()
    print('building posts...')
    welcome, ebook = build_posts()
    print('building story templates...')
    story, blank = build_story_templates()
    print('building highlights...')
    highs = build_highlights()
    print('building contact sheet...')
    contact_sheet(cover, mobile, welcome, ebook, story, blank, highs)
    print('done')
    for name in [
        'fb_cover_1640x924.jpg', 'fb_cover_mobile_preview.jpg',
        'post_welcome_1080x1350.jpg', 'post_ebook_1080x1350.jpg',
        'story_template_1080x1920.jpg', 'story_template_blank_1080x1920.jpg',
        'highlight_stories.png', 'highlight_prayers.png', 'highlight_ebook.png',
    ]:
        p = os.path.join(OUT, name)
        im = Image.open(p)
        print(f'  {name}: {im.size}  {os.path.getsize(p)//1024} KB')
    print('  sheet:', SHEET, Image.open(SHEET).size)


if __name__ == '__main__':
    main()
