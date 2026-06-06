#!/usr/bin/env python3
"""Generate a minimalist literary reading website from the book PDF."""
import os, re, subprocess, html

PDF = "Book After Xulon Version.pdf"
OUT = "site"
TITLE = "Christian Preaching That Devalues Scripture"
SUBTITLE = "A critique of how Bible-school hermeneutics displace the plain Word of God"
AUTHOR = "Theophilus"

# (number, title, first_pdf_page) — end is next chapter's start - 1
CHAPTERS = [
    (1,  "All Bible scholars are wisdom deficient", 9),
    (2,  "God planned every step of creation", 17),
    (3,  "God created Christian conflict", 34),
    (4,  "My introduction to this book", 37),
    (5,  "The importance of Bible school education", 51),
    (6,  "The dispensations reported in Scripture", 63),
    (7,  "God had a Purpose for Creation", 64),
    (8,  "God's purpose was deliberately hidden", 72),
    (9,  "Critical definitions and distinctions", 83),
    (10, "The philosophical basis for this book", 90),
    (11, "The Biblical justification for this book", 102),
    (12, "The rationale of God's plan", 114),
    (13, "The conclusion of this book", 124),
]
LAST_PAGE = 125
HEADER_PHRASE = "Christian preaching that devalues Scripture"

def page_text(a, b):
    r = subprocess.run(["pdftotext", "-layout", "-f", str(a), "-l", str(b),
                        "-enc", "UTF-8", PDF, "-"], capture_output=True, text=True)
    return r.stdout

def clean_to_paragraphs(raw, chap_num, chap_title):
    paras, cur = [], []
    title_words = set(re.sub(r"[^a-z ]", "", chap_title.lower()).split())
    for line in raw.split("\n"):
        s = line.rstrip()
        stripped = s.strip()
        if not stripped:
            continue
        # drop running header
        if stripped.lower().rstrip(".") == HEADER_PHRASE.lower():
            continue
        # drop page-number-only lines
        if re.fullmatch(r"\d{1,3}", stripped):
            continue
        # drop "Chapter N" heading lines
        if re.fullmatch(r"Chapter\s+\d+", stripped, re.I):
            continue
        # drop the chapter title line (mostly overlaps with known title words)
        tw = set(re.sub(r"[^a-z ]", "", stripped.lower()).split())
        if tw and len(tw - title_words) == 0 and len(stripped) < 70:
            continue
        # new paragraph if line is indented (layout preserves first-line indent)
        indented = len(s) - len(s.lstrip(" ")) >= 2
        if indented and cur:
            paras.append(" ".join(cur)); cur = []
        cur.append(stripped)
    if cur:
        paras.append(" ".join(cur))
    # collapse internal whitespace
    return [re.sub(r"\s+", " ", p).strip() for p in paras if len(p.strip()) > 1]

def esc(t):
    return html.escape(t, quote=False)

# ---- extract all chapters ----
chapter_data = []
for i, (num, title, start) in enumerate(CHAPTERS):
    end = (CHAPTERS[i+1][2] - 1) if i+1 < len(CHAPTERS) else LAST_PAGE
    raw = page_text(start, end)
    paras = clean_to_paragraphs(raw, num, title)
    chapter_data.append((num, title, paras))
    print(f"Chapter {num}: {len(paras)} paragraphs (pp.{start}-{end})")

# dedication (pages 5-6)
ded_raw = page_text(5, 6)
ded = clean_to_paragraphs(ded_raw, 0, "Dedication of this book")

os.makedirs(OUT, exist_ok=True)

# ---------- shared head ----------
def head(page_title, depth_home="index.html"):
    return f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{esc(page_title)}</title>
<meta name="description" content="{esc(SUBTITLE)}">
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link href="https://fonts.googleapis.com/css2?family=EB+Garamond:ital,wght@0,400;0,500;1,400&family=Spectral:wght@500;600&display=swap" rel="stylesheet">
<link rel="stylesheet" href="style.css">
</head>"""

THEME_SCRIPT = """<script>
(function(){
  var k='cpds-theme';
  var saved=localStorage.getItem(k);
  if(saved){document.documentElement.setAttribute('data-theme',saved);}
  window.toggleTheme=function(){
    var cur=document.documentElement.getAttribute('data-theme')==='dark'?'light':'dark';
    document.documentElement.setAttribute('data-theme',cur);
    localStorage.setItem(k,cur);
  };
})();
</script>"""

def topbar(show_contents=True):
    c = '<a class="bar-link" href="contents.html">Contents</a>' if show_contents else ''
    return f"""<div class="topbar">
  <a class="bar-link" href="index.html">{esc(TITLE)}</a>
  <div class="bar-right">{c}<button class="bar-link theme-btn" onclick="toggleTheme()" aria-label="Toggle light or dark mode">◑</button></div>
</div>"""

# ---------- index / cover ----------
toc_items = "\n".join(
    f'    <li><a href="chapter-{n}.html"><span class="toc-num">{n}</span>'
    f'<span class="toc-title">{esc(t)}</span></a></li>'
    for n, t, _ in chapter_data
)
index = f"""{head(TITLE)}
<body class="cover-page">
{THEME_SCRIPT}
{topbar(show_contents=False)}
<main class="cover">
  <div class="cover-inner">
    <p class="kicker">An essay in {len(chapter_data)} chapters</p>
    <h1 class="cover-title">{esc(TITLE)}</h1>
    <p class="cover-sub">{esc(SUBTITLE)}</p>
    <p class="cover-author">{esc(AUTHOR)}</p>
    <p class="cover-blurb">A sustained argument that Bible-school hermeneutics teach preachers to
      &ldquo;lean unto their own understanding&rdquo; rather than report what God plainly inspired &mdash;
      and a case for exposition grounded in the conviction that <em>why</em> God spoke matters more than
      competing opinions about <em>what</em> He meant.</p>
    <a class="begin" href="chapter-1.html">Begin reading &rarr;</a>
  </div>
</main>
<section class="contents-block">
  <h2 class="contents-h">Contents</h2>
  <ol class="toc">
{toc_items}
  </ol>
  <p class="ded-link"><a href="contents.html">Full table of contents &amp; dedication &rarr;</a></p>
</section>
<footer class="site-foot">{esc(TITLE)} &middot; {esc(AUTHOR)}</footer>
</body></html>"""
open(f"{OUT}/index.html", "w").write(index)

# ---------- contents page (with dedication) ----------
ded_html = "\n".join(f"    <p>{esc(p)}</p>" for p in ded)
contents = f"""{head('Contents — ' + TITLE)}
<body>
{THEME_SCRIPT}
{topbar(show_contents=False)}
<main class="reader">
  <h1 class="page-h">Contents</h1>
  <ol class="toc toc-full">
{toc_items}
  </ol>
  <hr class="rule">
  <h2 class="page-h" id="dedication">Dedication</h2>
  <div class="prose">
{ded_html}
  </div>
  <nav class="chap-nav"><a href="chapter-1.html">Begin reading: Chapter 1 &rarr;</a></nav>
</main>
<footer class="site-foot">{esc(TITLE)} &middot; {esc(AUTHOR)}</footer>
</body></html>"""
open(f"{OUT}/contents.html", "w").write(contents)

# ---------- chapter pages ----------
for idx, (num, title, paras) in enumerate(chapter_data):
    body = "\n".join(f"    <p>{esc(p)}</p>" for p in paras)
    prev_link = (f'<a class="nav-prev" href="chapter-{num-1}.html">&larr; Chapter {num-1}</a>'
                 if idx > 0 else '<a class="nav-prev" href="contents.html">&larr; Contents</a>')
    nxt = chapter_data[idx+1] if idx+1 < len(chapter_data) else None
    next_link = (f'<a class="nav-next" href="chapter-{nxt[0]}.html">Chapter {nxt[0]} &rarr;</a>'
                 if nxt else '<a class="nav-next" href="index.html">Back to cover &rarr;</a>')
    page = f"""{head(f'Chapter {num}: {title} — ' + TITLE)}
<body>
{THEME_SCRIPT}
{topbar()}
<div class="progress"><div class="progress-bar" id="pb"></div></div>
<main class="reader">
  <header class="chap-head">
    <p class="chap-num">Chapter {num}</p>
    <h1 class="chap-title">{esc(title)}</h1>
  </header>
  <article class="prose">
{body}
  </article>
  <nav class="chap-nav">
    {prev_link}
    <a class="nav-top" href="#" onclick="window.scrollTo({{top:0,behavior:'smooth'}});return false;">Top</a>
    {next_link}
  </nav>
</main>
<footer class="site-foot">{esc(TITLE)} &middot; {esc(AUTHOR)}</footer>
<script>
var pb=document.getElementById('pb');
window.addEventListener('scroll',function(){{
  var h=document.documentElement;
  var p=(h.scrollTop)/(h.scrollHeight-h.clientHeight);
  pb.style.width=(p*100)+'%';
}});
</script>
</body></html>"""
    open(f"{OUT}/chapter-{num}.html", "w").write(page)

print("Done. Files in", OUT)
