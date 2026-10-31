---
name: curate
description: Curate and check the second brain. Use when the user says curate, tidy the brain, lint the brain, file the scout run, or for the nightly night shift.
---

Follow `brain/BRAIN.md`.

1. **Catch up:** for every summary in `brain/wiki/sources/` whose candidate pages haven't been applied yet (check `brain/log.md`), use the `librarian` agent to apply them (max 15 edits per source).
2. **Scout run:** if `scout/list.md` has winners newer than the last "file the scout run" entry in `brain/log.md`, have the librarian file them as idea pages citing `scout/list.md` and the steal sheet.
3. **Lint:** use the `brain-scout` agent to check broken links, unsourced facts, orphan pages, stale pages (front matter `updated` 90+ days old), front matter missing or wrong, conflicts, and pages listed in `brain/index.md` without a one-line summary.
4. **Evals:** answer every question in `brain/evals.md` using only the brain (index first, then linked pages) and score it. Report `score/total`, each failed question and why.
5. **Gaps:** list up to 5 missing pages, open questions worth researching, and sources worth finding (these feed the Scout and the owner's briefing).
6. **Report:** write `brain/reports/YYYY-MM-DD.md` with what changed, the eval score, conflicts found, gaps, and proposed fixes not applied. Fixes that delete, retire or rewrite existing facts are proposals only; the owner approves them.
7. Append one line to `brain/log.md`.
