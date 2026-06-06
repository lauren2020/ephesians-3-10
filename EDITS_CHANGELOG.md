# Edits changelog

The authoritative record of every **manual** edit to the book's text in `site/`.

Why this file matters: `build_site.py` regenerates `site/` from the PDF and overwrites
direct HTML edits (see `CLAUDE.md`). This log is the source of truth for the book's true
text. If the site is ever rebuilt from the PDF, re-apply every change below to the freshly
generated HTML.

## How to add an entry

Add a new dated section at the top (newest first). One entry per applied change. Record
enough that the edit could be re-applied from this file alone: the highlight id it came
from, the location, the author's note, and the exact before → after text. Note which
files were touched (scroll view `chapter-N.html` / `contents.html`, and flip view
`book.html`).

## Template

```
## YYYY-MM-DD — <short description / source file>

### [<highlight-id>] Chapter <N>, paragraph <cidx>
- **Note:** <the author's instruction>
- **Files:** site/chapter-<N>.html, site/book.html  (BOOK[<N-1>].paras[<cidx>])
- **Before:** <original text of the changed span or paragraph>
- **After:**  <new text>
```

---

<!-- Add entries below this line, newest first. -->

_No edits recorded yet._
