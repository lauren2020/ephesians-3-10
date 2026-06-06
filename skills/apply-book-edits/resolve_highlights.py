#!/usr/bin/env python3
"""
resolve_highlights.py — turn an exported highlights JSON into a precise edit plan.

The book's text lives in the editable manuscript:
    manuscript/ch01.txt … ch13.txt   (one file per chapter)
    manuscript/dedication.txt        (chapter 0, the Dedication)
Paragraphs are separated by a blank line. `build_site.py` reads these files and
regenerates the whole site/, so an edit is made in ONE place: the manuscript file.

A highlight (from the reader's export) is anchored by location:
    chap  : chapter number (0 = the Dedication -> manuscript/dedication.txt)
    cidx  : zero-based paragraph index within that chapter's manuscript file
    start : start char offset within the paragraph's text
    end   : end char offset
    text  : the exact highlighted text
    note  : the author's instruction for that passage (may be empty)

This script is READ-ONLY. For each NOTED highlight it finds the manuscript file and
paragraph, sanity-checks the stored offsets against the live text, shows the passage in
context, and tells you exactly what to edit. After editing, re-run with --verify and then
rebuild with `python3 build_site.py`.

Usage:
    python3 resolve_highlights.py HIGHLIGHTS.json [--manuscript DIR] [--all] [--json] [--verify]

    --manuscript DIR  manuscript directory (default: ./manuscript)
    --all             include highlights that have no note (default: noted only)
    --json            emit a machine-readable plan instead of the human report
    --verify          report whether each highlight's ORIGINAL text is still present
                      (after editing, "present: no" means the passage was changed)
"""
import argparse, json, os, re, sys

CTX = 45  # characters of context shown on each side of a highlight


def die(msg):
    print(f"ERROR: {msg}", file=sys.stderr)
    sys.exit(1)


def manuscript_file(mdir, chap):
    return os.path.join(mdir, "dedication.txt" if chap == 0 else f"ch{chap:02d}.txt")


def read_paras(path):
    """Same paragraph rule as build_site.py: split on blank lines, normalize whitespace."""
    if not os.path.exists(path):
        return None
    with open(path, encoding="utf-8") as f:
        raw = f.read()
    out = []
    for block in re.split(r"\n\s*\n", raw):
        t = re.sub(r"\s+", " ", block).strip()
        if t:
            out.append(t)
    return out


def snippet(text, start, end):
    pre = text[max(0, start - CTX):start]
    mid = text[start:end]
    post = text[end:end + CTX]
    lead = "…" if start - CTX > 0 else ""
    trail = "…" if end + CTX < len(text) else ""
    return f"{lead}{pre}《{mid}》{post}{trail}"  # 《 highlighted 》


def resolve_one(h, mdir):
    chap = h.get("chap")
    cidx = h.get("cidx")
    path = manuscript_file(mdir, chap)
    rec = {
        "id": h.get("id"),
        "chap": chap,
        "cidx": cidx,
        "note": (h.get("note") or "").strip(),
        "stored_text": h.get("text", ""),
        "start": h.get("start"),
        "end": h.get("end"),
        "file": path,
        "warnings": [],
        "paragraph": None,
        "context": None,
        "found": False,
    }
    paras = read_paras(path)
    if paras is None:
        rec["warnings"].append(f"manuscript file not found: {path}")
        return rec
    if cidx is None or cidx < 0 or cidx >= len(paras):
        rec["warnings"].append(
            f"paragraph index {cidx} out of range ({path} has {len(paras)} paragraphs)")
        return rec

    para = paras[cidx]
    rec["paragraph"] = para
    try:
        live = para[h["start"]:h["end"]]
    except Exception:
        live = None
    if live != rec["stored_text"]:
        rec["warnings"].append(
            "stored offsets no longer match the live text — the paragraph may have been "
            "edited already; locate the passage by its text, not its offsets")
    if live == rec["stored_text"]:
        rec["context"] = snippet(para, h.get("start", 0), h.get("end", 0))
    elif rec["stored_text"] and rec["stored_text"] in para:
        i = para.find(rec["stored_text"])
        rec["context"] = snippet(para, i, i + len(rec["stored_text"]))
    rec["found"] = (rec["stored_text"] in para) if rec["stored_text"] else False
    return rec


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("highlights")
    ap.add_argument("--manuscript", default="manuscript")
    ap.add_argument("--all", action="store_true")
    ap.add_argument("--json", action="store_true")
    ap.add_argument("--verify", action="store_true")
    args = ap.parse_args()

    data = None
    if os.path.exists(args.highlights):
        with open(args.highlights, encoding="utf-8") as f:
            data = f.read()
    if data is None:
        die(f"highlights file not found: {args.highlights}")
    try:
        parsed = json.loads(data)
    except json.JSONDecodeError as e:
        die(f"highlights file is not valid JSON: {e}")
    hls = parsed["highlights"] if isinstance(parsed, dict) and "highlights" in parsed else parsed
    if not isinstance(hls, list):
        die("could not find a highlights array in that file")
    if not os.path.isdir(args.manuscript):
        die(f"manuscript directory not found: {args.manuscript}")

    noted = [h for h in hls if (h.get("note") or "").strip()]
    work = hls if args.all else noted
    plan = [resolve_one(h, args.manuscript) for h in work]

    if args.json:
        print(json.dumps({"count": len(plan), "edits": plan}, ensure_ascii=False, indent=2))
        return

    bookname = parsed.get("book", "?") if isinstance(parsed, dict) else "?"
    print(f"Highlights file : {args.highlights}")
    print(f"Book            : {bookname}")
    print(f"Manuscript      : {args.manuscript}/")
    print(f"Total highlights: {len(hls)}   With notes (edit requests): {len(noted)}")
    if not args.all and len(hls) != len(noted):
        print(f"({len(hls) - len(noted)} note-less highlights skipped; pass --all to include them.)")
    print("=" * 78)

    if not plan:
        print("No highlights with notes — nothing to do.")
        return

    for i, r in enumerate(plan, 1):
        loc = "Dedication" if r["chap"] == 0 else f"chapter {r['chap']}"
        print(f"\n[{i}] highlight {r['id']}  —  {loc}, paragraph {r['cidx']}")
        print(f"    NOTE: {r['note'] or '(none)'}")
        print(f"    Highlighted text: “{r['stored_text']}”")
        if r.get("context"):
            print(f"    In context: {r['context']}")
        print(f"    Edit: {r['file']}  (paragraph #{r['cidx']}, counting blank-line-separated blocks from 0)")
        if args.verify:
            print(f"    VERIFY: original text still present? {r['found']}")
            print("            (after editing, expect False = the passage was changed)")
        for w in r["warnings"]:
            print(f"    !! {w}")

    print("\n" + "=" * 78)
    print("Next: propose each change, apply on approval to the manuscript file, log it in")
    print("EDITS_CHANGELOG.md, re-run with --verify, then rebuild: python3 build_site.py")
    nwarn = sum(len(r["warnings"]) for r in plan)
    if nwarn:
        print(f"\n{nwarn} warning(s) above — review before editing.")


if __name__ == "__main__":
    main()
