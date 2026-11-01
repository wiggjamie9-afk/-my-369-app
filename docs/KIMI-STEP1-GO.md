# Kimi Step 1: paste this after Step 0

Use this once Kimi has done Step 0 (told you what the site is built with and shown a plan). It builds the website fixes — the overlapping buttons, hidden phone number, cramped header, and hard-to-read animation. Small, safe, visible, and it proves the whole Kimi loop works.

---

Go — do STEP 1 now: Part 1 of 48ai-website-improvement-brief.md only.

Fix these on the live site, in this order:
1. The floating bars that cover the main "Start" button on mobile — remove the "Where are you leaking jobs?" floating bar (move it into the page as a normal section later), and keep at most one sticky bar at the very bottom with "Call Jane" and "Start free trial". Add bottom padding equal to that bar's height so it never covers content.
2. Make the phone number visible and tappable (a `tel:` link) in the hero, not hidden behind the bars.
3. Fix the header so "THE 48 AI CREW" doesn't run into the Command Center button at phone width — on mobile show the logo plus a small "Log in" link instead.
4. Make the background animation much fainter (opacity ~0.15), keep it off behind text, and turn it off when the phone has "reduce motion" on.

Rules (from CLAUDE.md):
- Change only what Part 1 covers. No new features, no redesign.
- Don't touch my prices, text, or anything else on the page.
- Test at 390px (phone) and desktop: no horizontal scroll, no console errors, every button tappable and fully visible.
- No secrets in the code. Nothing gets sent, posted or charged.

When done, send me:
- Before and after screenshots on a phone and on desktop.
- Exactly what you changed (which files), what you tested, what passed, and anything you did NOT test.
- Push the code to my private GitHub repo and tell me the repo name so Claude can review it.

Do not start Step 2. Wait for me to check Step 1 first.

---

## After Kimi sends it back

1. Look at the before/after on your phone. Are the Start button and phone number now fully visible? Does nothing overlap?
2. Push Kimi's code to your **private** repo.
3. Tell me: **"audit Kimi's step 1"** and give me the repo name. I'll run the reviewer and tester agents over it and tell you if it's solid or what to fix.
4. Only then move to Step 2.
