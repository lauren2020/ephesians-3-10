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

## 2026-06-07 — Chapter 1 corrections (author note, direct)

### Chapter 1, paragraph 0 — manuscript/ch01.txt
- **Note:** At the end of paragraph 1 add the parenthetic citation.
- **Before:** …divinely replaced when God gifted Solomon.
- **After:**  …divinely replaced when God gifted Solomon (see also the web site biblehub.com/q/Why_are_the_men_in_1_Kings_4_31_important.htm).

### Chapter 1, paragraph 1 — manuscript/ch01.txt
- **Note:** Completely rewrite paragraph 2.
- **Before:** The Wisdom Literature inspired by God to be written by the wisest man in the world instructs you and me to “Trust in the LORD with all thine heart” (Prov 3:5) as well as “Let us hear the conclusion of the whole matter: Fear God, and keep his commandments: for this is the whole duty of man” (Eccl 12:13).
- **After:**  However, 1 Kings 11 was inspired by God to report the wisest man in the world egotistically abusing God’s gift of wisdom such that the gift of wisdom and the gift of wealth was used sinfully. Solomon finally admitted his sinful ways by the statement “Vanity of vanities, saith the Preacher, all is vanity” (Eccl 1:2ff) and concluding his admission of sin by “Let us hear the conclusion of the whole matter: Fear God and keep his commandments: for this is the whole duty of man. For God shall bring every work into judgment, with every secret thing, whether it be good, or whether it be evil” (Eccl 12:13-14). That seems to be Solomon’s basis for the wise alternative of Proverbs 3:5-6 “Trust in the LORD with all thine heart; and lean not unto thine own understanding.”

### Chapter 1, paragraph 4 — manuscript/ch01.txt
- **Note:** At the end of paragraph 5, change by adding to “…before a sovereign God can ‘predestine dead in trespasses and sin’ humans to no longer be ‘dead’ by receiving the gift of ‘everlasting life’.” (Trailing clause “as the outcome of being ‘born again of the Spirit’ (John 3:6)” kept as a minimal/additive edit.)
- **Before:** …a sovereign God can “predestine dead in trespasses and sin” humans to have “everlasting life” as the outcome of being “born again of the Spirit” (John 3:6).
- **After:**  …a sovereign God can “predestine dead in trespasses and sin” humans to no longer be “dead” by receiving the gift of “everlasting life” as the outcome of being “born again of the Spirit” (John 3:6).

### Chapter 1, paragraphs 7–onward — manuscript/ch01.txt
- **Note:** After the paragraph 7 assertion “the philosophical basis for this book is WHY > WHAT,” change all “why”/“what” to “WHY”/“WHAT” where context makes it appropriate (Chapter 1 only).
- **Change:** Capitalized the philosophical-contrast uses of why/what from paragraph 8 onward (e.g. “knowing WHY anything happens… than knowing WHAT may have happened,” “the reason WHY God created anything,” “a hermeneutical analysis of WHAT God literally said,” “WHY did God wait until AD60,” etc.). Left idiomatic uses lowercase: “That’s why” (the trigger sentence), “knew exactly what He was doing,” “exactly what God intended,” and “think about what He said.”
