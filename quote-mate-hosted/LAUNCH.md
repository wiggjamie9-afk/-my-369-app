# Launch checklist

Everything that can be built is built. What's left is on your side, in this order.

## 1. Get it running (about 20 minutes)

1. Put both folders on your server, side by side: `quote-mate-hosted/` and `roof-quote-mate/`.
2. `cd quote-mate-hosted && bash deploy.sh`. It runs the tests, makes your owner password (shown once) and starts the app.
3. Point a domain at the server and add the Caddy lines the script prints. HTTPS matters: phones expect it, and
   sign-in cookies are only safe over it.
4. Run `PUBLIC_URL=https://your-domain bash deploy.sh` once more so emailed links use your real address.

## 2. Fill in your side

Open `/admin` and, under "Sales page details", set your service name, phone, email and the prices you want shown.
Until you do, the page says "Ask for pricing".

Optional but worth it: email for leads. Add `SMTP_HOST`, `SMTP_PORT`, `SMTP_USER`, `SMTP_PASSWORD` and `SMTP_FROM`
to the env file (`/etc/quote-mate.env`, or `data/.env`) and run `deploy.sh` again. Without it, leads are still saved
in each tradie's inbox, but they won't be told by email.

## 3. Check before the first customer

- **Home batteries.** The preset's rebate is **$250 per kWh at the full rate**. I could not verify that figure: I confirmed the
  federal rebate's structure (full rate on the first 14 kWh, 60% to 28 kWh, 15% to 50 kWh, with a factor of 6.8 from May
  2026 that falls to 5.7 on 1 January 2027) but not what a certificate is worth in dollars. Each battery installer sets
  their own figure under Settings, and the page tells the customer it is an estimate. **Do not sell this to installers
  without checking the current figure with the Clean Energy Regulator or an installer, and tell them to re-check it on
  1 January 2027.**
- **Pet grooming.** The preset assumes the groomer does *not* charge GST (many small ones aren't registered). A groomer who
  is registered ticks one box in Settings and the page adds GST and says so.
- **Home care.** The rates are made-up examples. This is the most sensitive trade: someone asking about care for a relative
  is giving you personal information, even though the form asks for no health details and takes no photos. Get privacy
  advice before selling it, and have each provider confirm the wording about government funding (Support at Home) and
  how they're allowed to advertise. The price shown is a private-pay weekly estimate only.
- **Bookkeeping (Payday Check).** The seven-business-day rule on the page is from the ATO: super must be *received by
  the fund* within 7 business days of payday (20 for a new employee's or a new fund's first payment). The line about the
  free clearing house says only that the ATO told employers to move off it before July 2026, because I couldn't confirm
  the exact closure date. The page says it is general information, not advice. Check what a bookkeeper may say under
  their own registration (for example, tax and BAS agent rules) before they use it.
- **All trades.** Every preset's rates are made up examples. Each business's quote page says "example rates" until that
  business enters its own and confirms them.

## 4. Get customers

This is the part no code does. Start with the people you already know: roofers, painters, groomers and solar installers
you can ring or message today. Send them the demo link for their trade (the sales page lists all four), offer to set
them up, and add them under "Add a business". Aim for five paying customers before building anything else.

## 5. Before you charge anyone

- **Privacy and terms.** You'll hold homeowners' names, phone numbers, emails and photos on behalf of your customers.
  Get proper advice on a privacy policy and terms of service.
- **Payments.** There's no card handling. Invoice however you already do, then record "Paid until" in `/admin`. An
  overdue business gets a badge. Nothing switches off by itself.

## Backups

All business data is one file, `data/quotemate.db`, plus the photos in `data/photos/`. Copy the `data/` folder
somewhere safe on a schedule (a nightly copy to another machine is enough to start).
