---
name: publish-to-netlify
description: >
  Publish the book site to Netlify after the manuscript text has changed. Use this
  whenever someone asks to deploy, publish, ship, push live, or "update the live site" —
  e.g. "deploy these changes", "publish to Netlify", "push the edits live", "update the
  website", "make it live", "ship it". The site is git-connected: Netlify serves the
  pre-built `site/` folder from the GitHub repo with no build step, so publishing means
  rebuilding `site/` from the manuscript, committing both the manuscript and the
  regenerated `site/`, and pushing to `main`. Netlify auto-deploys on push. Do NOT use
  this skill to *edit* the book text — use `apply-book-edits` for that; this skill only
  publishes whatever is already in the manuscript.
---

# Publish the book site to Netlify

This site has **no build step on Netlify**. `netlify.toml` publishes the pre-built
`site/` folder directly, and `site/` is committed to the repo. Netlify is connected to the
GitHub remote (`origin`, branch `main`) and **auto-deploys whenever you push to `main`**.

So "publish" / "deploy" = **rebuild `site/` from the manuscript → commit → push to `main`**.
There is no separate Netlify command to run; the push is the deploy.

> If you were just asked to *change* the text, do the edit with the `apply-book-edits`
> skill (or a manual manuscript edit) first, then run this skill to publish.

## Steps

1. **Make sure build dependencies are installed.** The build needs the KJV text or it
   aborts:

   ```bash
   pip install pythonbible pythonbible-kjv --break-system-packages
   ```

2. **Rebuild `site/` from the manuscript.** Never publish a hand-edited `site/`; always
   regenerate so the deployed pages match `manuscript/`:

   ```bash
   python3 build_site.py
   ```

   The build prints each chapter's source and a scripture summary, then `Done. Files in
   site`. If it errors (e.g. missing `pythonbible-kjv`), fix that and rebuild before
   continuing — do not push a half-built site.

3. **Review what changed.** Confirm the diff is only what you expect — edited
   `manuscript/*.txt` files plus their regenerated `site/` counterparts (and possibly
   `site/search-index.js`):

   ```bash
   git status -s
   git diff --stat
   ```

   `site/style.css` is hand-maintained, not generated — leave it alone unless a style
   change was the point. Ignore incidental `.DS_Store` churn (don't commit it).

4. **Log the text change** in `EDITS_CHANGELOG.md` if the manuscript changed and it isn't
   already recorded. (Pure rebuilds with no text change don't need a changelog entry.)

5. **Commit the manuscript + regenerated site together** so the source and the served
   files stay in sync:

   ```bash
   git add manuscript site EDITS_CHANGELOG.md
   git commit -m "Publish: <short description of the change>"
   ```

6. **Push to `main` — this is the deploy.**

   ```bash
   git push origin main
   ```

   Netlify picks up the push and deploys automatically. The live site is
   **https://ephesians-3-10** ... (the project's primary URL on Netlify). Tell the author
   the push succeeded and that Netlify is now deploying; a deploy typically goes live
   within a minute or two.

## Verify the deploy

- `git status` should show a clean tree and `main` up to date with `origin/main`.
- Confirm the new commit is on GitHub (`git log origin/main -1 --oneline`).
- Optionally open the live URL and check the changed passage once Netlify reports the
  deploy is "Published". If a Netlify connector for this site is available, the latest
  deploy's state can be checked there; otherwise the Netlify dashboard for the project
  shows deploy progress.

## If git auto-deploy is ever not wired up

The expected path is git auto-deploy. If a push does **not** trigger a deploy (the site
isn't linked to the repo, or you need a one-off manual publish), publish the `site/`
folder directly with the Netlify CLI after rebuilding:

```bash
npx netlify deploy --prod --dir=site
```

Prefer the git push whenever the site is linked, so the repo and the live site never drift
apart.

## Reminders

- Always **rebuild before publishing** — the manuscript is the source of truth and `site/`
  is generated; pushing a stale `site/` ships old text.
- Commit `manuscript/` and `site/` **together** in the same commit.
- Don't hand-edit files under `site/` (except `style.css`); they'll be overwritten on the
  next build.
