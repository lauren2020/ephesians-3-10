---
name: apply-book-edits
description: >
  Apply an author's revisions to the book text from an exported highlights JSON file.
  Use this whenever someone provides a highlights export (a .json file with an
  app:"cpds" / type:"highlights" wrapper, or a bare array of highlight objects with
  chap/cidx/start/end/text/note fields) and wants the notes turned into edits to the
  book — e.g. "apply these highlights", "make the changes from this highlights file",
  "the author marked up some passages", "here are my notes on the book", "process this
  highlights.json". Each highlight's `note` is the author's instruction for the
  highlighted passage. This skill resolves every noted highlight to its paragraph in the
  editable manuscript, proposes the change for approval, applies it, and rebuilds the site.
---

# Apply book edits from a highlights export

The author reads the book on the site, highlights passages, and writes a **note** on
each one describing the change they want. They export those highlights to a JSON file
and hand it to you. Your job is to turn each note into an edit to the book's text.

## What the input looks like

An export is either a wrapper object or a bare array of highlight records:

```json
{
  "app": "cpds", "type": "highlights", "version": 1,
  "book": "Christian Preaching That Devalues Scripture",
  "exportedAt": "2026-06-06T12:00:00.000Z",
  "highlights": [
    { "id": "h…", "chap": 1, "cidx": 0, "start": 27, "end": 41,
      "text": "1Kings 4:29-34", "note": "Spell out '1 Kings' with a space.", "ts": 1 }
  ]
}
```

Field meaning:

- **chap** — chapter number. `0` is the **Dedication**.
- **cidx** — zero-based paragraph index within that chapter.
- **start / end** — character offsets of the highlight within the paragraph's text.
- **text** — the exact highlighted text.
- **note** — the author's instruction. **A highlight with an empty note is not an edit
  request** — it's just a reading highlight. Skip it unless told otherwise.

## Where the text lives (this is the whole point)

The book's text is the **editable manuscript** — one plain-text file per chapter, with
paragraphs separated by a blank line:

```
manuscript/ch01.txt … ch13.txt    (chapters 1–13)
manuscript/dedication.txt         (chapter 0, the Dedication)
```

`build_site.py` reads the manuscript and regenerates the entire `site/` (both the scroll
view and the flip view) from it. So:

- **You edit the text in ONE place: the manuscript file.** No HTML, no JSON, no escaping,
  no keeping two views in sync — the build handles all of that.
- A highlight's `chap` selects the file (`ch{NN}.txt`, or `dedication.txt` for chap 0)
  and `cidx` selects the paragraph (the `cidx`-th blank-line-separated block, from 0).
- Keep the book's curly quotes (`“ ” ‘ ’`) as literal characters. Write `&`, `<`, `>` as
  themselves — the build HTML-escapes them. Don't introduce hard line wraps inside a
  paragraph unless you want them; lines within a block are joined with a space.
- Don't worry about scripture references — `build_site.py` re-detects them and the links
  are added in the browser at runtime.

## Workflow (propose first, then apply, then rebuild)

### 1. Locate the highlights file
If the user gave a path, use it. Otherwise ask, or look in the working folder / uploads
for a `*.json` highlights export. Run from the repo root (where `build_site.py` and
`manuscript/` live).

### 2. Build the edit plan with the resolver (read-only)
```bash
python3 skills/apply-book-edits/resolve_highlights.py <HIGHLIGHTS.json>
```
It maps every noted highlight to its manuscript file + paragraph, prints the passage in
context, and flags problems (`!!`) — out-of-range paragraphs, or stored offsets that no
longer match (meaning the paragraph was already edited; then locate the passage by its
**text**, not its offsets). Add `--json` for a machine-readable plan, `--all` to include
note-less highlights, `--verify` to check whether the original text is still present.

### 3. Interpret each note and draft the change
Notes are natural language. Read the note with the highlighted text **in its paragraph
context** (the resolver prints it) and decide the minimal edit that satisfies the intent:

- *"fix typo: X → Y"*, *"change A to B"* — literal replacement.
- *"reword / tighten / clarify this"* — rewrite the span (or its sentence) while
  preserving meaning, tense, and the author's voice. Change as little as the note requires.
- *"delete this" / "cut"* — remove the span and repair surrounding spacing/punctuation.
- *"add … here" / "insert …"* — add text at the highlighted point.
- Structural requests (split/merge/move paragraphs, renumber chapters) are bigger than a
  paragraph edit — surface them to the author and handle separately. (Splitting a
  paragraph = adding a blank line; merging = removing one. Adding/removing paragraphs
  shifts the `cidx` of everything after it, so do those last and re-run the resolver.)

When the intent is ambiguous, ask the author rather than guessing.

### 4. Propose, then wait for approval
Present a concise, numbered proposal — one row per noted highlight — showing chapter/
paragraph, the note, and a **before → after** of the affected text. Do not edit any file
until the author approves. (If the author has pre-approved "apply directly," you may skip
the wait, but still produce the summary.)

### 5. Apply each approved change to the manuscript
Edit the paragraph in the relevant `manuscript/*.txt` file. Keep paragraphs blank-line
separated. Edit only the paragraphs the notes call for; don't reflow the rest of the file.

### 6. Record every change in the changelog
Append an entry to `EDITS_CHANGELOG.md` for each applied edit: date, highlight id,
chapter/paragraph, the note, and before → after. Git tracks the manuscript too, but the
changelog is the readable human history of *why* each change was made.

### 7. Rebuild and verify
```bash
python3 build_site.py            # regenerates site/ from the manuscript
```
- Re-run the resolver with `--verify`: passages whose text changed should report
  `present? False`. (Non-text notes, e.g. "add a margin comment," may still be present.)
- Confirm the build printed each edited chapter as sourced from `manuscript/…` (not the
  PDF) and reported no errors.
- Optionally spot-check the rendered text in `site/chapter-N.html`.

### 8. Report
Summarize what changed and what was skipped (note-less highlights, structural requests,
anything needing author input).

## Notes
- Rebuilding is now the **normal, safe** step — it regenerates the site from the
  manuscript, so your edits are preserved and propagate to both reading views.
- The original `Book After Xulon Version.pdf` is kept only as a historical artifact and is
  no longer the source of truth. `build_site.py` falls back to it only for a chapter whose
  manuscript file is missing.
