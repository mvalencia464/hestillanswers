#!/usr/bin/env python3
"""Builds the free ebook "30 True Stories of Answered Prayer" from content/posts_master.csv.

  python3 engine/build_ebook.py [--site https://hestillanswers.pages.dev]

Writes site/public/ebook/30-true-stories-of-answered-prayer.pdf and site/public/ebook/cover.jpg.
Where a word-for-word source passage was recovered, that full text is used. Otherwise the story is the Facebook retelling, minus Facebook-only lines.
"""
import os, re, csv, argparse
from PIL import Image, ImageDraw, ImageFont
from reportlab.lib.pagesizes import inch
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.enums import TA_CENTER
from reportlab.lib.colors import HexColor
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.platypus import (BaseDocTemplate, PageTemplate, Frame, Paragraph, Spacer, PageBreak,
                                NextPageTemplate, Flowable, KeepTogether)
from reportlab.platypus.tableofcontents import TableOfContents

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
FONTS = os.path.join(ROOT, 'engine', 'fonts')
OUT = os.path.join(ROOT, 'site', 'public', 'ebook')
TITLE = '30 True Stories of Answered Prayer'
ORDER = ('S001 S002 S003 S011 S008 PH02 S009 S010 CA03 S012 PH03 S007 S006 S014 S015 '
         'CA01 S004 S005 S016 S017 S018 PH04 PH05 S013 S019 S020 S021 PH06 CA05 PH01').split()
INK, GOLD, GOLD_DK, MUTED = HexColor('#0A0D14'), HexColor('#F6B728'), HexColor('#9A6A08'), HexColor('#6B6457')
FB_ONLY = re.compile(r'(swipe through|leave a first name below|before you scroll on)', re.I)

for name, file in (('Poppins-XB', 'Poppins-ExtraBold.ttf'), ('Poppins-B', 'Poppins-Bold.ttf'), ('Poppins-SB', 'Poppins-SemiBold.ttf'),
                   ('Lora', 'Lora-Variable.ttf'), ('Lora-I', 'Lora-Italic-Variable.ttf')):
    pdfmetrics.registerFont(TTFont(name, os.path.join(FONTS, file)))
pdfmetrics.registerFontFamily('Lora', normal='Lora', bold='Poppins-B', italic='Lora-I', boldItalic='Lora-I')

def sentence_case(head, src):
    if head != head.upper() or not re.search('[A-Z]', head): return head
    seen = {}
    for m in re.finditer(r'(^|[.!?]\s+|["“‘(]\s*)?([A-Za-z][A-Za-z’\']*)', src):
        if m.group(1): continue
        w = m.group(2); k = re.sub(r"['’]s$", '', w.lower())
        if w[0].islower(): seen[k] = 'low'
        elif k not in seen: seen[k] = 'cap'
    words = []; first = True
    for w in re.findall(r"[A-Za-z’']+|[^A-Za-z’']+", head.lower()):
        if re.match(r"[a-z]", w):
            k = re.sub(r"['’]s$", '', w)
            if first or w == 'i' or re.match(r"i['’]", w) or seen.get(k) == 'cap': w = w[0].upper() + w[1:]
            first = False
        words.append(w)
    t = ''.join(words)
    t = re.sub(r'([.!?:]["”]?\s+["“]?)([a-z])', lambda m: m.group(1) + m.group(2).upper(), t)
    return re.sub(r'(["“])([a-z])', lambda m: m.group(1) + m.group(2).upper(), t)

def esc(s): return s.replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;')
def clean(s): return re.sub(r'\s+', ' ', s.replace('*', '').replace('|', ' ').replace('>>', '')).strip()

def site_source(r):
    src = re.sub(r'\s*Image:.*$', '', r['first_comment']).strip()
    if (r.get('full_text') or '').strip():
        if re.search(r'Retold here in modern English\.?', src):
            src = re.sub(r'Retold here in modern English\.?', 'Quoted word for word.', src)
        elif 'Quoted word for word' not in src:
            src = src.rstrip('.') + '. Quoted word for word.'
    src = re.sub(r'^Source:\s*', '', src)
    return src

def story(r):
    parts = [p.strip() for p in r['headline'].split('||') if p.strip()]
    title = sentence_case(clean(parts[0]), r['caption'] + ' and God, Lord, Jesus, Christ')
    full = (r.get('full_text') or '').strip()
    if full:
        paras = [p.strip() for p in re.split(r'\n\s*\n', full) if p.strip()]
        return title, paras, site_source(r)
    paras = []
    if r['type'] == 'carousel':
        paras += [sentence_case(clean(p), r['caption']) if clean(p).isupper() else clean(p) for p in parts[1:]]
    for p in re.split(r'\n\s*\n', r['caption']):
        sents = [s for s in re.split(r'(?<=[.!?"”])\s+(?=[A-Z"“])', p.strip()) if s and not FB_ONLY.search(s)]
        if sents: paras.append(' '.join(sents))
    return title, paras, site_source(r)

class Rule(Flowable):
    def __init__(self, w=36, color=GOLD, thick=2.2): super().__init__(); self.w, self.c, self.t = w, color, thick
    def wrap(self, aw, ah): self.aw = aw; return aw, self.t + 4
    def draw(self): self.canv.setStrokeColor(self.c); self.canv.setLineWidth(self.t); self.canv.line((self.aw - self.w) / 2, 2, (self.aw + self.w) / 2, 2)

def make_cover(path, w=900, h=1350):
    F = lambda n, s: ImageFont.truetype(os.path.join(FONTS, n), s)
    im = Image.new('RGB', (w, h), (10, 13, 20)); d = ImageDraw.Draw(im)
    for r_ in range(520, 0, -8):          # soft gold glow behind the emblem
        a = int(26 * (1 - r_ / 520)); d.ellipse([w/2 - r_, 420 - r_, w/2 + r_, 420 + r_], fill=(10 + a, 13 + int(a * .75), 20))
    av = Image.open(os.path.join(ROOT, 'brand', 'avatar_1080.png')).convert('RGB').resize((300, 300), Image.LANCZOS)
    m = Image.new('L', (300, 300), 0); ImageDraw.Draw(m).ellipse([0, 0, 299, 299], fill=255); im.paste(av, (w//2 - 150, 270), m)
    def center(txt, y, font, fill):
        d.text(((w - d.textlength(txt, font=font)) / 2, y), txt, font=font, fill=fill)
    center('30 TRUE STORIES', 680, F('Poppins-ExtraBold.ttf', 84), (255, 255, 255))
    center('OF ANSWERED PRAYER', 780, F('Poppins-ExtraBold.ttf', 64), (246, 183, 40))
    d.line([w/2 - 60, 892, w/2 + 60, 892], fill=(246, 183, 40), width=4)
    center('Recorded in the 1800s.', 930, F('Lora-Italic-Variable.ttf', 36), (232, 224, 208))
    center('Quoted from the old accounts.', 978, F('Lora-Italic-Variable.ttf', 36), (232, 224, 208))
    sp = F('Poppins-Bold.ttf', 26); t = 'HE STILL ANSWERS'; x = (w - sum(d.textlength(c, font=sp) + 6 for c in t)) / 2
    for c in t: d.text((x, 1230), c, font=sp, fill=(200, 192, 176)); x += d.textlength(c, font=sp) + 6
    im.save(path, quality=90)

class Doc(BaseDocTemplate):
    def afterFlowable(self, f):
        if isinstance(f, Paragraph) and f.style.name == 'StoryTitle':
            self.notify('TOCEntry', (0, f.getPlainText(), self.page))

def main():
    ap = argparse.ArgumentParser(); ap.add_argument('--site', default='https://hestillanswers.pages.dev'); a = ap.parse_args()
    rows = {r['id']: r for r in csv.DictReader(open(os.path.join(ROOT, 'content', 'posts_master.csv'), encoding='utf-8'))}
    os.makedirs(OUT, exist_ok=True); cover = os.path.join(OUT, 'cover.jpg'); make_cover(cover)
    W, H = 6 * inch, 9 * inch; M = 0.75 * inch
    body = ParagraphStyle('Body', fontName='Lora', fontSize=11.2, leading=16.6, spaceAfter=8.5, textColor=HexColor('#1D1B17'))
    kick = ParagraphStyle('Kick', fontName='Poppins-B', fontSize=8, leading=11, textColor=GOLD_DK, alignment=TA_CENTER, spaceAfter=6)
    st = ParagraphStyle('StoryTitle', fontName='Poppins-XB', fontSize=17, leading=22, textColor=INK, alignment=TA_CENTER, spaceAfter=10)
    src = ParagraphStyle('Src', fontName='Lora-I', fontSize=8.8, leading=12.5, textColor=MUTED, alignment=TA_CENTER, spaceBefore=10)
    h1 = ParagraphStyle('H1', parent=st, fontSize=20, leading=26)
    toc = TableOfContents(); toc.levelStyles = [ParagraphStyle('TOC', fontName='Lora', fontSize=9.6, leading=13.5, leftIndent=0, rightIndent=24, spaceAfter=3.2)]
    toc.dotsMinLevel = 0

    def page(c, d):
        c.saveState(); c.setFont('Poppins-SB', 7.5); c.setFillColor(MUTED)
        c.drawCentredString(W / 2, 0.45 * inch, f'HE STILL ANSWERS  ·  {d.page}'); c.restoreState()
    def cover_page(c, d): c.drawImage(cover, 0, 0, W, H)
    doc = Doc(os.path.join(OUT, '30-true-stories-of-answered-prayer.pdf'), pagesize=(W, H), title=TITLE,
              author='He Still Answers', subject='True stories of answered prayer', leftMargin=M, rightMargin=M, topMargin=M, bottomMargin=M)
    frame = Frame(M, M, W - 2 * M, H - 2 * M, id='f')
    doc.addPageTemplates([PageTemplate('cover', [Frame(0, 0, W, H)], onPage=cover_page), PageTemplate('body', [frame], onPage=page)])

    flow = [NextPageTemplate('body'), PageBreak()]
    flow += [Spacer(1, 40), Paragraph('Before you read', h1), Rule(), Spacer(1, 14)]
    intro = ['The thirty accounts in this book were written down in the 1800s by the people who lived them, or by pastors, editors and friends who heard them first-hand. Most were gathered in 1885 in a book called <i>The Wonders of Prayer</i>. A few come from other records of the time, and one is Abraham Lincoln\'s own farewell to his neighbors.',
             'Where the original account could be recovered cleanly, it is quoted word for word from <i>The Wonders of Prayer</i> (1885) or from Lincoln\'s Springfield farewell as printed there. A few stories are still given in a careful modern retelling. Nothing has been invented: where an old account leaves something out, so does this one. Each story ends with a note on where it was first recorded.',
             'Read one a day if you like. Several end with a question. Sit with it before you turn the page.']
    flow += [Paragraph(t, body) for t in intro]
    flow += [PageBreak(), Spacer(1, 24), Paragraph('Contents', h1), Rule(), Spacer(1, 12), toc, PageBreak()]
    for n, sid in enumerate(ORDER, 1):
        title, paras, source = story(rows[sid])
        flow += [Spacer(1, 18), KeepTogether([Paragraph(f'STORY {n}', kick), Paragraph(esc(title), st), Rule(), Spacer(1, 12)])]
        flow += [Paragraph(esc(p), body) for p in paras]
        if source: flow += [Rule(18, HexColor('#E7DCC6'), 1), Paragraph(esc(source), src)]
        flow.append(PageBreak())
    flow += [Spacer(1, 120), Paragraph('Keep reading', h1), Rule(), Spacer(1, 14),
             Paragraph(f'There are hundreds more stories, prayers and old words at <b>{a.site.replace("https://", "")}</b>, and a new letter in your inbox each week.', ParagraphStyle('C', parent=body, alignment=TA_CENTER)),
             Spacer(1, 8), Paragraph('If one of these stories helped you, send it to someone who needs it today.', ParagraphStyle('C2', parent=body, alignment=TA_CENTER, fontName='Lora-I')),
             Spacer(1, 60), Paragraph('A note on sources', ParagraphStyle('H3', parent=kick, fontSize=8.5)),
             Paragraph('The Wonders of Prayer (1885), the New Cyclopaedia of Prose Illustrations (1875), Lincoln\'s Springfield farewell (1861) and the histories of the Fulton Street prayer meeting (1857) are all in the public domain. A few modern retellings in this book are by He Still Answers.', ParagraphStyle('S2', parent=src))]
    doc.multiBuild(flow)
    print('ebook:', os.path.relpath(doc.filename, ROOT))

if __name__ == '__main__': main()
