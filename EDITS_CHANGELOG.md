# Edits changelog

A human-readable history of edits to the book's text. The book's text lives in
`manuscript/*.txt` (the source of truth), so **git history is the authoritative record**
of exactly what changed. This file complements that with the *why*: the author's note
behind each change and a readable before → after.

## How to add an entry

Add a new dated section at the top (newest first). One entry per applied change: the
highlight id it came from, the location (manuscript file + paragraph), the author's note,
and the before → after text.

## Template

```
## YYYY-MM-DD — <short description / source file>

### [<highlight-id>] Chapter <N>, paragraph <cidx>  —  manuscript/ch<NN>.txt
- **Note:** <the author's instruction>
- **Before:** <original text of the changed span or paragraph>
- **After:**  <new text>
```

---

<!-- Add entries below this line, newest first. -->

_No edits recorded yet._
