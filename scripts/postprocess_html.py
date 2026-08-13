#!/usr/bin/env python3
from __future__ import annotations

import html
import json
import re
import shutil
import sys
from dataclasses import dataclass, field
from pathlib import Path
from html.parser import HTMLParser

RAW = Path(sys.argv[1])
OUT = Path(sys.argv[2])
ASSETS = Path(__file__).resolve().parents[1] / "web" / "assets"

@dataclass
class NavItem:
    kind: str
    number: str
    title: str
    url: str
    children: list["NavItem"] = field(default_factory=list)

class TocParser(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.current_class = ""
        self.current_href = ""
        self.current_text: list[str] = []
        self.entries: list[tuple[str, str, str]] = []

    def handle_starttag(self, tag, attrs):
        attrs = dict(attrs)
        if tag == "span":
            self.current_class = attrs.get("class", "")
            self.current_text = []
        elif tag == "a" and self.current_class:
            self.current_href = attrs.get("href", "")

    def handle_data(self, data):
        if self.current_class:
            self.current_text.append(data)

    def handle_endtag(self, tag):
        if tag == "span" and self.current_class:
            raw_kind = self.current_class.replace("Toc", "")
            if raw_kind in {"part", "section", "subsection"} and self.current_href:
                self.entries.append((raw_kind, " ".join("".join(self.current_text).split()), self.current_href))
            self.current_class = ""
            self.current_href = ""
            self.current_text = []

class TextParser(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.text: list[str] = []
    def handle_data(self, data):
        self.text.append(data)
    def result(self):
        return " ".join(" ".join(self.text).replace("\x00", "f").split())

def read(path: Path) -> str:
    data = path.read_bytes().decode("utf-8", errors="replace")
    # TeX4ht represents several ligatures and en-dashes as NUL when the
    # Source Sans web font map is unavailable. Recover the intended text.
    replacements = {
        "De\x00nition": "Definition", "Su\x00icient": "Sufficient",
        "su\x00icient": "sufficient", "Su\x00iciency": "Sufficiency",
        "su\x00iciency": "sufficiency", "Di\x00usion": "Diffusion",
        "di\x00usion": "diffusion", "Sche\x00e": "Scheffe",
        "Cherno\x00": "Chernoff", "Hoe\x00ding": "Hoeffding",
        "Azuma-Hoe\x00ding": "Azuma-Hoeffding",
        "Johnson\x00Lindenstrauss": "Johnson–Lindenstrauss",
        "Glivenko\x00Cantelli": "Glivenko–Cantelli",
        "Marchenko\x00Pastur": "Marchenko–Pastur",
        "Wang\x00Ramdas": "Wang–Ramdas",
    }
    for source, target in replacements.items():
        data = data.replace(source, target)
    return data.replace("\x00", "")

def strip_tags(fragment: str) -> str:
    p = TextParser(); p.feed(fragment); return p.result()

def clean_title(raw: str) -> tuple[str, str]:
    raw = " ".join(raw.split())
    m = re.match(r"^(I{1,3}|\d+(?:\.\d+)*)\s+(.*)$", raw)
    return (m.group(1), m.group(2)) if m else ("", raw)

def extract_body(doc: str) -> str:
    m = re.search(r"<body[^>]*>(.*)</body>", doc, re.S | re.I)
    return m.group(1) if m else doc

def extract_headings(fragment: str):
    out = []
    for m in re.finditer(r"<(h[3-5]) class='([^']*(?:sectionHead|paragraphHead)[^']*)' id='([^']+)'>(.*?)</\1>", fragment, re.S | re.I):
        level = {"h3": 2, "h4": 2, "h5": 3}[m.group(1).lower()]
        title = strip_tags(m.group(4))
        title = re.sub(r"^\d+(?:\.\d+)*\s+", "", title).strip()
        out.append((level, m.group(3), title))
    return out

def theorem_kind(box: str) -> str:
    text = strip_tags(box).lower()
    for label, kind in [
        ("definition", "definition"), ("theorem", "theorem"), ("lemma", "theorem"),
        ("proposition", "theorem"), ("corollary", "theorem"), ("remark", "remark"),
        ("example", "example"), ("observation", "observation"), ("approach", "approach"),
        ("convention", "definition")
    ]:
        if text.startswith(label): return kind
    return "theorem"

def convert_theorem_boxes(fragment: str) -> str:
    opening = re.compile(r"<div class='tcolorbox tcolorbox'([^>]*)>")
    div_tag = re.compile(r"</?div\b[^>]*>", re.I)
    cursor = 0
    output = []
    while True:
        match = opening.search(fragment, cursor)
        if not match:
            output.append(fragment[cursor:])
            break
        output.append(fragment[cursor:match.start()])
        depth = 0
        closing = None
        for tag in div_tag.finditer(fragment, match.start()):
            if tag.group(0).lower().startswith("</div"):
                depth -= 1
                if depth == 0:
                    closing = tag
                    break
            else:
                depth += 1
        if closing is None:
            output.append(fragment[match.start():])
            break
        inner = fragment[match.end():closing.start()]
        kind = theorem_kind(inner)
        output.append(f"<aside class='theorem-card {kind}'{match.group(1)}>{inner}</aside>")
        cursor = closing.end()
    return "".join(output)

def transform_content(fragment: str) -> str:
    # Remove TeX4ht's generated previous/up/next controls; the site adds its own.
    fragment = re.sub(r"<div class='crosslinks'>.*?</div>", "", fragment, flags=re.S)
    fragment = re.sub(r"<p class='noindent'><a id='tail[^']*'></a>\s*</p>", "", fragment)
    # Preserve semantic boxes while replacing only the balanced outer container.
    fragment = convert_theorem_boxes(fragment)
    fragment = fragment.replace("class='SourceSans3-Semibold-tlf-t1-'", "class='web-semibold'")
    fragment = fragment.replace("class='SourceSans3-Regular-tlf-t1-'", "class='web-sans'")
    fragment = re.sub(r"class='zpl-(Bold|Italic|Regular)[^']*'", lambda m: "class='web-bold'" if m.group(1)=="Bold" else ("class='web-italic'" if m.group(1)=="Italic" else "class='web-serif'"), fragment)
    fragment = fragment.replace("__________________________________________________", "").replace("_____", "")
    return fragment

def nav_html(items: list[NavItem], current: str, prefix="") -> str:
    chunks = []
    for item in items:
        if item.kind == "part":
            chunks.append(f"<div class='nav-part'>{html.escape(item.number)} · {html.escape(item.title)}</div>")
            chunks.append(nav_html(item.children, current, prefix))
        elif item.kind == "section":
            active = " active" if item.url.split("#")[0] == current else ""
            chunks.append(f"<a class='nav-link{active}' href='{prefix}{html.escape(item.url)}'><span class='nav-number'>{html.escape(item.number)}</span><span>{html.escape(item.title)}</span></a>")
            for child in item.children:
                child_active = " active" if child.url.split("#")[0] == current else ""
                chunks.append(f"<a class='nav-link sub{child_active}' href='{prefix}{html.escape(child.url)}'><span class='nav-number'>{html.escape(child.number)}</span><span>{html.escape(child.title)}</span></a>")
    return "".join(chunks)

def shell(*, title: str, context: str, body_html: str, nav: str, toc: str, prev=None, next=None, base="", landing=False) -> str:
    prev_url = prev.url if prev else ""
    next_url = next.url if next else ""
    navigation = ""
    if not landing and (prev or next):
        navigation = "<nav class='page-navigation'>"
        if prev:
            navigation += f"<a class='page-nav-link prev' href='{html.escape(prev.url)}'><span class='page-nav-direction'>← Previous</span><span class='page-nav-title'>{html.escape(prev.title)}</span></a>"
        else: navigation += "<span></span>"
        if next:
            navigation += f"<a class='page-nav-link next' href='{html.escape(next.url)}'><span class='page-nav-direction'>Next →</span><span class='page-nav-title'>{html.escape(next.title)}</span></a>"
        navigation += "</nav>"
    header = f"""
<header class='site-header'>
  <a class='brand' href='{base}index.html'><span class='brand-mark'>Σ</span><span class='brand-text'>Modern Statistics</span></a>
  <div class='header-context'>{html.escape(context)}</div>
  <div class='header-actions'>
    <button class='icon-button menu-button' data-menu-toggle aria-label='Open contents'>☰</button>
    <button class='icon-button' data-search-open aria-label='Search notes'>⌕</button>
    <button class='icon-button theme-button' data-theme-toggle aria-label='Change theme'>◐</button>
    <a class='text-button' href='{base}notes.pdf'><span class='pdf-label'>PDF</span> ↓</a>
  </div>
</header>"""
    search = f"""
<dialog class='search-dialog' id='search-dialog'>
  <div class='search-box'><input id='search-input' type='search' placeholder='Search the lecture notes…' autocomplete='off'><button class='icon-button' onclick='this.closest("dialog").close()' aria-label='Close'>×</button></div>
  <div class='search-results' id='search-results'><div class='search-empty'>Search definitions, theorems, and topics across the notes.</div></div>
</dialog>"""
    body_attrs = f"data-base='{base}' data-prev='{html.escape(prev_url)}' data-next='{html.escape(next_url)}'"
    layout = body_html if landing else f"""
<div class='reading-progress'></div>
<aside class='book-sidebar'><div class='sidebar-label'>Contents</div><nav class='book-nav'>{nav}</nav></aside>
<div class='sidebar-scrim'></div>
<div class='reader-shell'><main class='reader-main'><article class='document-page'>{body_html}</article>{navigation}</main></div>
<aside class='on-this-page'>{toc}</aside>"""
    return f"""<!doctype html>
<html lang='en' data-theme='light'>
<head>
<meta charset='utf-8'>
<meta name='viewport' content='width=device-width, initial-scale=1'>
<meta name='theme-color' content='#faf9f6'>
<meta name='description' content='A Guided Tour of Modern Statistics — online lecture notes by Zixun Huang'>
<title>{html.escape(title)} — A Guided Tour of Modern Statistics</title>
<link rel='stylesheet' href='{base}assets/book.css'>
<script>window.MathJax={{tex:{{tags:'ams'}},options:{{enableMenu:false}}}};</script>
<script defer src='https://cdn.jsdelivr.net/npm/mathjax@3/es5/tex-chtml-full.js'></script>
<script defer src='{base}assets/book.js'></script>
</head>
<body {body_attrs}>{header}{layout}{search}</body>
</html>"""

OUT.mkdir(parents=True, exist_ok=True)
(OUT / "assets").mkdir(exist_ok=True)
shutil.copy2(ASSETS / "book.css", OUT / "assets" / "book.css")
shutil.copy2(ASSETS / "book.js", OUT / "assets" / "book.js")
if (RAW / "figures").exists(): shutil.copytree(RAW / "figures", OUT / "figures", dirs_exist_ok=True)

main_doc = read(RAW / "main.html")
parser = TocParser(); parser.feed(main_doc)
parts: list[NavItem] = []
current_part = None
current_section = None
flat_pages: list[NavItem] = []
for kind, raw_title, url in parser.entries:
    number, title = clean_title(raw_title)
    if kind == "likesection": continue
    item = NavItem(kind, number, title, url)
    if kind == "part":
        parts.append(item); current_part = item; current_section = None
    elif kind == "section":
        if current_part is None:
            current_part = NavItem("part", "", "Notes", ""); parts.append(current_part)
        current_part.children.append(item); current_section = item; flat_pages.append(item)
    elif kind == "subsection" and current_section:
        current_section.children.append(item)
        flat_pages.append(item)

# Add bibliography if TeX4ht generated it.
if (RAW / "mainli2.html").exists():
    bib = NavItem("section", "", "References", "mainli2.html#references")
    parts[-1].children.append(bib); flat_pages.append(bib)

search_index = []
for idx, item in enumerate(flat_pages):
    filename = item.url.split("#")[0]
    raw_file = RAW / filename
    if not raw_file.exists(): continue
    document = read(raw_file)
    content = transform_content(extract_body(document))
    headings = extract_headings(content)
    toc = ""
    if headings:
        toc = "<h2>On this page</h2>" + "".join(f"<a class='depth-{level}' href='#{html.escape(anchor)}'>{html.escape(title)}</a>" for level, anchor, title in headings)
    parent_title = "A Guided Tour of Modern Statistics"
    for part in parts:
        if item in part.children:
            parent_title = part.title
            break
        for section in part.children:
            if item in section.children:
                parent_title = section.title
                break
    breadcrumbs = f"<div class='breadcrumbs'><a href='index.html'>Notes</a> / {html.escape(parent_title)}</div>"
    page_body = breadcrumbs + content
    prev_item = flat_pages[idx-1] if idx else None
    next_item = flat_pages[idx+1] if idx+1 < len(flat_pages) else None
    html_doc = shell(title=item.title, context=f"{item.number} {item.title}".strip(), body_html=page_body,
                     nav=nav_html(parts, filename), toc=toc, prev=prev_item, next=next_item)
    (OUT / filename).write_text(html_doc, encoding="utf-8")
    text = strip_tags(content)
    search_index.append({"title": f"{item.number} {item.title}".strip(), "url": item.url, "text": text[:12000]})

part_cards = []
for i, part in enumerate(parts, 1):
    links = "".join(f"<li><a href='{html.escape(sec.url)}'>{html.escape((sec.number + ' ' + sec.title).strip())}</a></li>" for sec in part.children)
    part_cards.append(f"<article class='part-card'><div class='part-card-number'>Part {part.number or i}</div><h2>{html.escape(part.title)}</h2><ul>{links}</ul></article>")
first_url = flat_pages[0].url if flat_pages else "notes.pdf"
landing_body = f"""
<div class='landing'>
<section class='landing-hero'><div class='landing-hero-inner'>
  <div class='landing-eyebrow'>Zixun Huang · Lecture Notes</div>
  <h1>A Guided Tour of Modern Statistics</h1>
  <p class='landing-subtitle'>A structured journey from classical probability and statistical theory to high-dimensional methods, random matrices, computation, and learning theory.</p>
  <div class='landing-actions'><a class='primary-action' href='{html.escape(first_url)}'>Start reading →</a><button class='secondary-action' data-search-open>Search the notes</button><a class='secondary-action' href='notes.pdf'>Download PDF</a></div>
  <div class='landing-meta'><span><strong>{sum(1 for p in parts for s in p.children if s.number)}</strong>chapters</span><span><strong>{sum(len(s.children) for p in parts for s in p.children)}</strong>topics</span><span><strong>132</strong>PDF pages</span><span><strong>Auto</strong>updated from GitHub</span></div>
</div></section>
<section class='landing-content'><h2 class='landing-section-title'>Explore the notes</h2><div class='part-grid'>{''.join(part_cards)}</div></section>
<footer class='landing-footer'>Built automatically from the LaTeX source. The online text and PDF update with every push to <code>main</code>.</footer>
</div>"""
index_doc = shell(title="Online Lecture Notes", context="Online lecture notes", body_html=landing_body, nav="", toc="", base="", landing=True)
(OUT / "index.html").write_text(index_doc, encoding="utf-8")
(OUT / "search-index.json").write_text(json.dumps(search_index, ensure_ascii=False, separators=(",", ":")), encoding="utf-8")
(OUT / "404.html").write_text("<!doctype html><meta charset='utf-8'><meta name='viewport' content='width=device-width'><title>Not found</title><style>body{display:grid;min-height:100vh;place-items:center;background:#faf9f6;color:#4a463f;font:18px Georgia}</style><main><h1>Page not found</h1><a href='./'>Return to the notes</a></main>", encoding="utf-8")
print(f"Generated {len(flat_pages)} chapter pages and {len(search_index)} search records in {OUT}")
