# The 48 AI Crew: website improvement brief

For: Kimi (or any developer) working on https://48ai.jamiewiggautomation.au/ and its Command Center.
Written by: Claude, 2026-10-31, from a mobile screenshot of the homepage. The live site and the Command Center could not be opened from Claude's session, so items marked **(check)** need confirming on the real site first.

Goal: more Perth tradies start the free trial, and the site and Command Center are built properly, fast, secure and legal.

Work in this order. After each part, test on a real phone (390px wide) and on desktop, and send screenshots.

---

## Part 1: Fix what is broken (do first)

1. **Floating bars cover the main button.** On mobile, the green "⚡ Where are you leaking jobs?" bar sits on top of the blue **Start** button (only "STAR" shows), and the "The crew is on shift right now · Call Jane · Text it" bar covers the line underneath.
   - Remove the "Where are you leaking jobs?" floating bar (move it into the page as its own section, see Part 2).
   - Keep only **one** sticky bar on mobile, at the very bottom, with two buttons: **Call Jane** and **Start free trial**.
   - Add bottom padding to the page equal to the sticky bar's height so it never covers content.
2. **The phone number is hidden.** "7-day free trial · cancel anytime · or just ring …9785 068 218…" is unreadable behind the bars. Show the number as a tappable `tel:` link in the hero, not in a strip behind overlays. **(check the exact number)**
3. **The header is cramped.** "THE 48 AI CREW" runs into the "Command Center" button at phone width. On mobile, show the logo plus a smaller "Log in" link instead of the full button.
4. **Readability.** The falling Matrix characters sit behind body text. Make them much fainter (opacity about 0.15), stop them behind text blocks, and turn them off when the phone has "reduce motion" on (`prefers-reduced-motion`).

## Part 2: Make people buy (homepage)

Rewrite the hero in plain tradie language:

- **Headline (keep):** NEVER MISS A JOB AGAIN
- **Sub-headline (replace):** "Jane answers your phone while you're on the tools, books the job and texts you the details. 24/7, in your business name."
- **Main button:** "📞 Call Jane now — hear her answer" (`tel:` link). Hearing her is the best proof.
- **Second button:** "Start 7-day free trial"
- **Under the buttons:** "From $___/week · No lock-in · Perth-based support" **(fill in the real price)**

Then these sections, in this order:

1. **"How much are missed calls costing you?" calculator** (replaces the floating "leaking jobs" bar):
   - Inputs: missed calls per week (slider 1–30), average job value ($), how many of those would have booked (default 30%).
   - Output: "You're losing about $X a month. Jane costs $Y." in big numbers, then the trial button.
2. **How it works in 3 steps:** forward your calls → Jane answers, quotes your prices and books → you get a text with the job details.
3. **Hear Jane:** a 30-second audio or video of Jane taking a real booking, with the caller's permission, or a clearly labelled demo.
4. **Proof:** 2–3 Perth tradie testimonials with first name, trade and suburb (real ones only), plus any numbers you can back up, e.g. "calls answered last month".
5. **Pricing:** one simple card, or at most three tiers, with what's included, the trial, and "cancel anytime".
6. **FAQ:** "Will customers know it's AI?", "Does it sound like me?", "What if it gets something wrong?", "How do I get my calls back?", "Where is my data stored?".
7. **Final call to action:** "Stop losing jobs tonight" + both buttons.

Remove or tone down:
- "All systems nominal", "Build 2026.08", "Command Center" in the hero, and "the crew loops every job until it's done". Tradies don't speak this; it reads as a tech demo.
- "48 AI workers": it confuses buyers (do they get 48 assistants?). Use "Jane, your AI receptionist" as the product; keep "The 48 AI Crew" as the brand.

## Part 3: Legal and trust (Australia)

1. **AI disclosure:** Jane's greeting should say she is an AI assistant, e.g. "Hi, you've reached Dave's Plumbing, I'm Jane, Dave's AI assistant." Mention this in the FAQ.
2. **"Sounding like you":** only clone a customer's voice with their written consent, and make sure every claim on the page is true (Australian Consumer Law). If voice cloning isn't standard in every plan, say which plans include it.
3. **Texts:** only text people who contacted the business or agreed to it, identify the business in each text and include an opt-out (Spam Act 2003).
4. **Call recording:** if calls are recorded, Jane must say so at the start; check WA's Surveillance Devices Act requirements.
5. **Add pages:** Privacy Policy (what data is kept, where, for how long, who can see it), Terms, and contact details including an ABN.
6. Footer: ABN, Perth address or service area, email, phone.

## Part 4: Speed, Google and accessibility

1. Lighthouse (Chrome DevTools → Lighthouse, mobile) scores of at least 90 for Performance, Accessibility, Best Practices and SEO. **(check current scores)**
2. Page title and description: "AI Receptionist for Perth Tradies | The 48 AI Crew" and a one-line description with "Perth", "tradies", "never miss a call".
3. Open Graph image, so links shared on Facebook and in texts show a proper preview.
4. Local SEO: a Google Business Profile, and `LocalBusiness` structured data with the service area (Perth and WA).
5. Accessibility: text contrast at least 4.5:1, every button with a readable label, tap targets at least 44px, and the page usable with a keyboard.
6. Images compressed (WebP/AVIF) and lazy-loaded; fonts limited to one or two.

## Part 5: Command Center: built properly? (check all)

Security:
1. Every Command Center page requires login; open the URLs in a private window and confirm they redirect to login.
2. One customer can never see another customer's calls, contacts or recordings: test with two test accounts.
3. No secret keys (Twilio, OpenAI, Supabase service keys) in the browser: search the page source and network requests for `sk_`, `AC`, `service_role`, `secret`.
4. Passwords handled by a proper auth provider (e.g. Supabase Auth, Clerk); password reset works; sessions expire.
5. Customer data is stored in Australia or the privacy policy says where.

Works properly:
1. Each screen loads with an empty account (new customer) and with lots of data, without errors.
2. Clear loading states and error messages ("Couldn't load calls — try again"), never a blank screen.
3. Works at phone width; tables scroll or become cards on mobile.
4. Call log shows time, caller, summary, outcome (booked / message / urgent) and a link to the recording if recorded.
5. Every setting the customer changes (business hours, prices, greeting) is saved and actually used by Jane on the next call.
6. Browser console shows no errors on any screen.

## Part 6: Tests so it stays fixed

Add automated browser tests (Playwright) that check, on mobile and desktop:
- the hero buttons are visible and not covered,
- "Call Jane" is a `tel:` link to the right number,
- the calculator shows a result,
- the trial sign-up form submits,
- Command Center pages redirect to login when logged out.

Run them before every change goes live.

---

## What to send back to Claude

- Screenshots of every page and Command Center screen after the changes (mobile and desktop).
- Lighthouse scores.
- Or push the site's code to GitHub and tell Claude the repository name, so Claude can test and fix it directly.
