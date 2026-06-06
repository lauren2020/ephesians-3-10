#!/usr/bin/env python3
"""
resolve_highlights.py — turn an exported highlights JSON into a precise edit plan.

The reading site stores each highlight by location:
    chap  : chapter number (0 = the Dedication on contents.html)
    cidx  : zero-based paragraph index within that chapter (the <p data-cidx="N">)
    start : start char offset within the paragraph's plain text
    end   : end char offset
    text  : the exact highlighted text (plain, entity-decoded)
    note  : the author's instruction for that passage (may be empty)

A single book paragraph lives in TWO places that must stay in sync:
    1. site/chapter-<chap>.html  — scroll view, inside <p data-cidx="N">…</p>
                                    (HTML-escaped text: & < > are &amp; &lt; &gt;)
       (chap 0 lives in site/contents.html, in the Dedication's <div class="prose">)
    2. site/book.html            — flip view, inside the #bookdata JSON,
                                    BOOK[chap-1]["paras"][cidx]  (raw text)
       (the Dedication is NOT in the flip view, so chap 0 has no flip target)

This script is READ-ONLY. It locates each highlight, sanity-checks that the stored
offsets still match the live text, and prints exactly what to change and where.
The agent then makes the edits, records them in EDITS_CHANGELOG.md, and re-runs
this script with --verify to confirm.

Usage:
    python3 resolve_highlights.py HIGHLIGHTS.json [--site DIR] [--all] [--json] [--verify]

    --site DIR   path to the built site (default: ./site)
    --all        include highlights that have no note (default: noted only)
    --json       emit a machine-readable plan instead of the human report
    --verify     check whether each highlight's ORIGINAL text is still present
                 verbatim (use after editing: "present" means not yet changed)
"""
import argparse, html, json, os, re, sys

CTX = 45  # characters of context shown on each side of a highlight


def die(msg):
    print(f"ERROR: {msg}", file=sys.stderr)
    sys.exit(1)


def chapter_file(site, chap):
    if chap == 0:
        return os.path.join(site, "contents.html")
    return os.path.join(site, f"chapter-{chap}.html")


def read(path):
    if not os.path.exists(path):
        return None
    with open(path, encoding="utf-8") as f:
        return f.read()


def para_from_html(doc, cidx):
    """Return the entity-DECODED plain text of <p data-cidx="cidx"> in an HTML doc."""
    if doc is None:
        return None
    m = re.search(rf'<p data-cidx="{cidx}">(.*?)</p>', doc, re.S)
    if not m:
        return None
    return html.unescape(m.group(1))


def load_bookdata(site):
    """Return the flip-view BOOK array from site/book.html, or None."""
    doc = read(os.path.join(site, "book.html"))
    if doc is None:
        return None
    m = re.search(r'<script type="application/json" id="bookdata">(.*?)</script>', doc, re.S)
    if not m:
        return None
    try:
        return json.loads(m.group(1))
    except json.JSONDecodeError:
        return None


def flip_para(book, chap, cidx):
    """Return the flip-view paragraph text, or (None, reason)."""
    if chap == 0:
        return None, "dedication is not in the flip view (no flip target)"
    if book is None:
        return None, "could not read #bookdata from site/book.html"
    idx = chap - 1
    if idx < 0 or idx >= len(book):
        return None, f"chapter {chap} not found in flip data"
    paras = book[idx].get("paras", [])
    if cidx < 0 or cidx >= len(paras):
        return None, f"paragraph {cidx} not found in flip chapter {chap}"
    return paras[cidx], None


def snippet(text, start, end):
    pre = text[max(0, start - CTX):start]
    mid = text[start:end]
    post = text[end:end + CTX]
    lead = "…" if start - CTX > 0 else ""
    trail = "…" if end + CTX < len(text) else ""
    return f"{lead}{pre}《{mid}》{post}{trail}"  # 《 highlighted 》


def resolve_one(h, site, book):
    chap = h.get("chap")
    cidx = h.get("cidx")
    rec = {
        "id": h.get("id"),
        "chap": chap,
        "cidx": cidx,
        "note": (h.get("note") or "").strip(),
        "stored_text": h.get("text", ""),
        "start": h.get("start"),
        "end": h.get("end"),
        "warnings": [],
        "scroll_file": chapter_file(site, chap),
        "flip_file": None if chap == 0 else os.path.join(site, "book.html"),
    }

    # ---- scroll view (chapter-N.html / contents.html) ----
    para = para_from_html(read(rec["scroll_file"]), cidx)
    if para is None:
        rec["warnings"].append(
            f"could not find <p data-cidx=\"{cidx}\"> in {os.path.basename(rec['scroll_file'])}")
        rec["paragraph"] = None
        rec["context"] = None
        rec["found_in_scroll"] = False
    else:
        rec["paragraph"] = para
        try:
            live = para[h["start"]:h["end"]]
        except Exception:
            live = None
        if live != rec["stored_text"]:
            rec["warnings"].append(
                "stored offsets no longer match the live text — the paragraph may "
                "have already been edited; locate the passage by its text, not offsets")
        if live == rec["stored_text"]:
            rec["context"] = snippet(para, h.get("start", 0), h.get("end", 0))
        elif rec["stored_text"] and rec["stored_text"] in para:
            i = para.find(rec["stored_text"])
            rec["context"] = snippet(para, i, i + len(rec["stored_text"]))
        else:
            rec["context"] = None
        rec["found_in_scroll"] = rec["stored_text"] in para if rec["stored_text"] else False

    # ---- flip view (book.html) ----
    fp, reason = flip_para(book, chap, cidx)
    rec["flip_paragraph"] = fp
    if fp is None:
        rec["flip_note"] = reason
        rec["found_in_flip"] = None
    else:
        rec["found_in_flip"] = rec["stored_text"] in fp if rec["stored_text"] else False
        if rec.get("paragraph") is not None and fp != rec["paragraph"]:
            rec["warnings"].append(
                "scroll-view and flip-view text differ for this paragraph — they are "
                "out of sync; bring both to the same final text")
    return rec


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("highlights")
    ap.add_argument("--site", default="site")
    ap.add_argument("--all", action="store_true")
    ap.add_argument("--json", action="store_true")
    ap.add_argument("--verify", action="store_true")
    args = ap.parse_args()

    data = read(args.highlights)
    if data is None:
        die(f"highlights file not found: {args.highlights}")
    try:
        parsed = json.loads(data)
    except json.JSONDecodeError as e:
        die(f"highlights file is not valid JSON: {e}")
    hls = parsed["highlights"] if isinstance(parsed, dict) and "highlights" in parsed else parsed
    if not isinstance(hls, list):
        die("could not find a highlights array in that file")

    if not os.path.isdir(args.site):
        die(f"site directory not found: {args.site}")

    noted = [h for h in hls if (h.get("note") or "").strip()]
    work = hls if args.all else noted
    book = load_bookdata(args.site)

    plan = [resolve_one(h, args.site, book) for h in work]

    if args.json:
        print(json.dumps({"count": len(plan), "edits": plan}, ensure_ascii=False, indent=2))
        return

    # ---- human report ----
    bookname = parsed.get("book", "?") if isinstance(parsed, dict) else "?"
    print(f"Highlights file : {args.highlights}")
    print(f"Book            : {bookname}")
    print(f"Total highlights: {len(hls)}   With notes (edit requests): {len(noted)}")
    if not args.all and len(hls) != len(noted):
        print(f"({len(hls) - len(noted)} note-less highlights skipped; pass --all to include them.)")
    print("=" * 78)

    if not plan:
        print("No highlights with notes — nothing to do.")
        return

    for i, r in enumerate(plan, 1):
        print(f"\n[{i}] highlight {r['id']}  —  chapter {r['chap']}, paragraph {r['cidx']}")
        print(f"    NOTE: {r['note'] or '(none)'}")
        print(f"    Highlighted text: “{r['stored_text']}”")
        if r.get("context"):
            print(f"    In context: {r['context']}")
        print(f"    Edit BOTH of these so they end up identical:")
        sf = os.path.basename(r["scroll_file"])
        print(f"      • scroll view : {sf}  →  <p data-cidx=\"{r['cidx']}\">  "
              f"(HTML-escape & < > as &amp; &lt; &gt;)")
        if r["flip_file"]:
            print(f"      • flip view   : book.html  →  #bookdata "
                  f"BOOK[{r['chap']-1}].paras[{r['cidx']}]  (raw text, JSON-escaped)")
        else:
            print(f"      • flip view   : (none — {r.get('flip_note','n/a')})")
        if args.verify:
            s = r.get("found_in_scroll")
            f = r.get("found_in_flip")
            print(f"    VERIFY: original text still present?  scroll={s}  flip={f}")
            print("            (after editing, expect False/False = the passage was changed)")
        for w in r["warnings"]:
            print(f"    !! {w}")

    print("\n" + "=" * 78)
    print("Next: propose each change to the author, apply on approval to BOTH files,")
    print("log it in EDITS_CHANGELOG.md, then re-run with --verify.")
    nwarn = sum(len(r["warnings"]) for r in plan)
    if nwarn:
        print(f"\n{nwarn} warning(s) above — review before editing.")


if __name__ == "__main__":
    main()
