---
paths:
  - "demo/**"
  - "retention/**"
  - "command-center/**"
---
# Customer-facing pages
- Insert any user/URL/model text as text only (textContent), never as HTML. XSS-test it.
- Nothing auto-sends, posts, charges or signs up. Those go through the owner's approval.
- No fabricated numbers, reviews or results. Estimates are labelled estimates.
- Works at 390px and desktop. Wrap localStorage/IndexedDB in try/catch.
- Run the page's test before committing (e.g. `node tests/retention-e2e.js`).
