// Reads ../content/posts_master.csv at build time and turns each Facebook post into a site entry.
import fs from 'node:fs';
import path from 'node:path';

export type Section = 'stories' | 'prayers' | 'words' | 'verses' | 'questions';
export interface Entry {
  id: string; section: Section; type: string; slug: string; url: string;
  title: string;            // readable title (sentence case)
  display: string;          // headline as shown on the image (no markup)
  attribution: string; tag: string;
  slides: string[];         // carousel / list slides after the first
  quoteOld: string;         // then/now: the old sentence
  body: string[];           // caption paragraphs, Facebook-only lines removed
  source: string;           // the "first comment" source line
  images: string[]; alt: string; description: string; date: string;
}

export const SECTIONS: Record<Section, { name: string; blurb: string }> = {
  stories:   { name: 'Stories',   blurb: 'True accounts of answered prayer, most of them recorded in 1885 and retold in plain English.' },
  prayers:   { name: 'Prayers',   blurb: 'Prayers of C. H. Spurgeon and Matthew Henry, and prayers written for the hard places of life.' },
  words:     { name: 'Old Words', blurb: 'Lines from Spurgeon, Matthew Henry and the old guides that still burn.' },
  verses:    { name: 'Verses',    blurb: 'Promises of Scripture, each set beside a true account.' },
  questions: { name: 'Questions', blurb: 'Questions to sit with, many of them asked by Matthew Henry in 1710.' },
};
const SECTION_OF: Record<string, Section> = {
  story: 'stories', carousel: 'stories', prayer: 'prayers', text: 'prayers',
  quote: 'words', oneliner: 'words', thennow: 'words', list: 'words',
  verse: 'verses', question: 'questions',
};

function parseCSV(text: string): Record<string, string>[] {
  const rows: string[][] = []; let row: string[] = []; let f = ''; let q = false;
  for (let i = 0; i < text.length; i++) {
    const c = text[i];
    if (q) { if (c === '"') { if (text[i + 1] === '"') { f += '"'; i++; } else q = false; } else f += c; }
    else if (c === '"') q = true;
    else if (c === ',') { row.push(f); f = ''; }
    else if (c === '\n') { row.push(f); rows.push(row); row = []; f = ''; }
    else if (c !== '\r') f += c;
  }
  if (f || row.length) { row.push(f); rows.push(row); }
  const [head, ...data] = rows;
  return data.filter((r) => r.length > 1).map((r) => Object.fromEntries(head.map((h, i) => [h, r[i] ?? ''])));
}

const clean = (s: string) => s.replace(/\*/g, '').replace(/\|/g, ' ').replace(/>>/g, '').replace(/\s+/g, ' ').trim();

// Turn an ALL-CAPS headline into sentence case, borrowing capitalisation from the caption itself.
function sentenceCase(head: string, caption: string): string {
  if (head !== head.toUpperCase() || !/[A-Z]/.test(head)) return head;
  const seen = new Map<string, 'cap' | 'low'>();
  for (const m of caption.matchAll(/(^|[.!?]\s+|["“‘(]\s*)?([A-Za-z][A-Za-z’']*)/g)) {
    if (m[1] !== undefined && m[1] !== '') continue;        // sentence-initial: tells us nothing
    const w = m[2]; const key = w.toLowerCase().replace(/['’]s$/, '');
    const isCap = w[0] === w[0].toUpperCase();
    if (!isCap) seen.set(key, 'low'); else if (!seen.has(key)) seen.set(key, 'cap');
  }
  let first = true;
  return head.toLowerCase().replace(/[a-z][a-z’']*/g, (w) => {
    const key = w.replace(/['’]s$/, '');
    let out = w;
    if (first || w === 'i' || /^i['’]/.test(w) || seen.get(key) === 'cap') out = w[0].toUpperCase() + w.slice(1);
    first = false; return out;
  }).replace(/([.!?:]["”]?\s+["“]?)([a-z])/g, (_, a, b) => a + b.toUpperCase()).replace(/(["“])([a-z])/g, (_, a, b) => a + b.toUpperCase());
}

// Lines that only make sense on Facebook ("swipe", "leave a name below"). Story text is never matched.
export const FB_ONLY = /(swipe through|leave a first name below|say their name here|just say "me too|before you scroll on|car keys count|tell us how long, and we will stand|say their name\. It is good)/i;
function paragraphs(caption: string): string[] {
  return caption.split(/\n\s*\n/).map((p) => p.trim()).filter(Boolean)
    .map((p) => p.split('\n').map((line) => line.split(/(?<=[.!?"”])\s+(?=[A-Z"“])/).filter((s) => !FB_ONLY.test(s)).join(' ').trim())
      .filter(Boolean).join('\n'))
    .filter(Boolean);
}
const slugify = (s: string) => {
  const full = s.toLowerCase().normalize('NFKD').replace(/[’']/g, '').replace(/[^a-z0-9]+/g, '-').replace(/^-|-$/g, '');
  if (full.length <= 60) return full;
  const cut = full.slice(0, 61); return cut.slice(0, cut.lastIndexOf('-'));   // never end mid-word
};

let cache: Entry[] | null = null;
export function getEntries(): Entry[] {
  if (cache) return cache;
  const file = path.resolve(process.cwd(), '..', 'content', 'posts_master.csv');
  const rows = parseCSV(fs.readFileSync(file, 'utf8'));
  const out: Entry[] = [];
  for (const r of rows) {
    const section = SECTION_OF[r.type]; if (!section) continue;
    const parts = r.headline.split('||').map((s) => s.trim()).filter(Boolean);
    let title = clean(parts[0] || ''); let slides: string[] = []; let quoteOld = '';
    if (r.type === 'carousel') slides = parts.slice(1).map(clean);
    if (r.type === 'list') { const [n, t] = (parts[0] || '').split('::'); title = `${clean(n)} ${clean(t || '')}`; slides = parts.slice(1).map(clean); }
    if (r.type === 'thennow') { quoteOld = clean(parts[0]); title = clean(parts[1] || ''); }
    if (r.type === 'verse') slides = parts.slice(1).map(clean);
    if (r.type === 'text') title = 'A prayer of C. H. Spurgeon';
    const body = paragraphs(r.caption);
    const t = sentenceCase(title, r.caption + ' ' + r.attribution + ' and God, Lord, Jesus, Christ, Jehovah').replace(/[,;:]\s*$/, '');
    const readable = r.type === 'text' ? `${t}: ${(body[1] || body[0] || '').replace(/^["“]/, '').slice(0, 40).replace(/\s\S*$/, '')}…` : t;
    const slug = `${r.id.toLowerCase()}-${slugify(r.type === 'text' ? readable : t)}`;
    const desc = (body.join(' ') || t).replace(/\s+/g, ' ');
    out.push({
      id: r.id, section, type: r.type, slug, url: `/${section}/${slug}/`,
      title: readable, display: title, attribution: r.attribution, tag: r.tag, slides, quoteOld, body,
      source: r.first_comment, images: r.image_url ? r.image_url.split(',') : [], alt: r.alt_text,
      description: desc.length > 158 ? desc.slice(0, 155).replace(/\s\S*$/, '') + '…' : desc, date: r.date,
    });
  }
  out.sort((a, b) => (a.date + a.id).localeCompare(b.date + b.id));
  cache = out; return out;
}
export const bySection = (s: Section) => getEntries().filter((e) => e.section === s);
