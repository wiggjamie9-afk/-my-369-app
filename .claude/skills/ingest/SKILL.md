---
name: ingest
description: Ingest new sources into the second brain. Use when the user says ingest, ingest this, clip, file this, process the inbox, or shares an article, screenshot or notes to remember, and when files appear in brain/inbox.
---

Follow `brain/BRAIN.md`.

0. **Quick capture:** for a short thought, to-do or promise ("remember…", "note that…"), save it as `brain/inbox/YYYY-MM-DD-capture-short-name.md` with the date and the owner's exact words, confirm in one line, and stop; the night shift files it.
1. If the user pasted or attached something, save it unchanged as `brain/inbox/YYYY-MM-DD-short-name.md` (images go to `brain/assets/`). For long copyrighted articles, save the link plus short quoted key points and the owner's notes rather than the full text, because the repository may be shared.
2. List files in `brain/inbox/` (and new files in `brain/raw/`) that have no summary page in `brain/wiki/sources/` yet.
3. Skip exact duplicates: if `brain/wiki/sources/` already summarises the same source (same link or same content), say so and stop for that file.
4. For each new source, use the `brain-scout` agent to write the summary and candidate pages.
5. Show the user the candidate page changes. When the user approves (or when running as the scheduled night shift, which is pre-approved), use the `librarian` agent to apply them, at most 15 edits per source.
6. Keep new pages' front matter (type, status, updated, sources) and add each new page to `brain/index.md` with a one-line summary.
7. Report: pages created, pages updated, conflicts found, claims rejected.
