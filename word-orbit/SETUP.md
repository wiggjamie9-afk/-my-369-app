# Word Orbit: launch guide

Word Orbit is a phonics, reading and spelling app for dyslexic and ADHD learners, kids and adults.
It is a web app: one HTML page plus a few files. It installs on phones from the browser and works offline.

The app works straight away with no setup (progress saved on one device, Family Plan in free test mode).
Follow the steps below to switch on **accounts, cloud backup and real payments**.

---

## What's in this folder

| File | What it is |
|---|---|
| `index.html` | The whole app. The `CONFIG` block near the top of the script is the only part you need to edit. |
| `manifest.webmanifest`, `sw.js`, `icons/` | Make it installable on phones and work offline. |
| `privacy.html` | Privacy policy **template**: fill in the highlighted parts. |
| `sounds/` | Put the 38 letter-sound recordings here (see `sounds/README.txt`). |
| `supabase/migrations/001_word_orbit.sql` | Creates the database tables and security rules. |
| `supabase/functions/stripe-webhook/index.ts` | Receives payments from Stripe and unlocks the Family Plan. |

---

## Step 1: Put it online (about 10 minutes, free)

Any static host works. Netlify is the easiest:

1. Create a free account at netlify.com.
2. Choose **Add new site → Deploy manually** and drag this whole `word-orbit` folder onto the page.
3. Netlify gives you an address like `https://word-orbit-123.netlify.app`. Open it on your phone.
4. Later, add your own domain in **Domain settings**.

The site must be on **https** (Netlify does this automatically) for installing, offline use and recording sounds.

## Step 2: Accounts and cloud backup with Supabase (about 20 minutes, free tier)

1. Create a project at supabase.com. Pick a region near your customers (for example London).
2. **Create the tables:** open **SQL Editor → New query**, paste everything from
   `supabase/migrations/001_word_orbit.sql`, and press **Run**.
3. **Email sign-in:** go to **Authentication → Sign In / Providers** and make sure **Email** is on.
   In **Authentication → URL Configuration**:
   - set **Site URL** to your app address, for example `https://word-orbit-123.netlify.app/`
   - add the same address to **Redirect URLs**.
4. **Use your own email sender** before launch: Supabase's built-in email is only for testing and is
   heavily limited. In **Authentication → Emails → SMTP Settings**, connect a sender such as
   Resend, Postmark or Brevo. You can also edit the sign-in email's wording there.
5. Copy your keys from **Project Settings → API**:
   - **Project URL** → paste into `SUPABASE_URL`
   - **anon public** key → paste into `SUPABASE_ANON_KEY`

   The anon key is designed to be public; the security rules from step 2 protect each family's data.
   **Never** put the `service_role` key in the app.

## Step 3: Payments with Stripe

1. Create an account at stripe.com and complete the business details.
2. **Product:** Product catalogue → Add product → "Word Orbit Family Plan" with two recurring prices:
   **£5.99 per month** and **£39.99 per year**.
3. **Payment Links:** create one Payment Link for each price.
   - Under **After payment**, choose "Don't show confirmation page" and redirect to
     `https://YOUR-APP-ADDRESS/index.html?checkout=done`
   - Paste the links into `STRIPE_MONTHLY_LINK` and `STRIPE_YEARLY_LINK`.
4. **Customer portal** (lets parents cancel or switch plans): Settings → Billing → Customer portal →
   turn it on, then copy the **login link** into `STRIPE_PORTAL_LINK`.
5. **Webhook** (tells the app someone has paid). Install the Supabase CLI (supabase.com/docs/guides/cli), then from this folder run:

   ```bash
   supabase login
   supabase link --project-ref YOUR-PROJECT-REF
   supabase functions deploy stripe-webhook --no-verify-jwt
   ```

   In Stripe: Developers → Webhooks → **Add endpoint**:
   - URL: `https://YOUR-PROJECT-REF.supabase.co/functions/v1/stripe-webhook`
   - Events: `checkout.session.completed`, `customer.subscription.created`,
     `customer.subscription.updated`, `customer.subscription.deleted`

   Copy the endpoint's **Signing secret** (`whsec_...`) and your **Secret key** (`sk_...`), then run:

   ```bash
   supabase secrets set STRIPE_SECRET_KEY=sk_live_... STRIPE_WEBHOOK_SECRET=whsec_...
   ```

6. Add your help address to `SUPPORT_EMAIL`.

**Test first:** use Stripe's **test mode** keys and test Payment Links, and pay with the test card
`4242 4242 4242 4242` (any future date, any CVC). Check that the Family Plan unlocks within a few seconds
and that cancelling in the customer portal locks it again. Then repeat steps 3–5 with live keys.

## Step 4: Fill in the settings and upload again

Open `index.html`, find `const CONFIG = {` near the top of the script, fill in the values, save,
and drag the folder onto Netlify again.

```js
const CONFIG = {
  SUPABASE_URL: 'https://abcdefgh.supabase.co',
  SUPABASE_ANON_KEY: 'eyJ...',
  STRIPE_MONTHLY_LINK: 'https://buy.stripe.com/...',
  STRIPE_YEARLY_LINK: 'https://buy.stripe.com/...',
  STRIPE_PORTAL_LINK: 'https://billing.stripe.com/p/login/...',
  SUPPORT_EMAIL: 'hello@yourdomain.com'
};
```

How it behaves once set up:
- Parents sign in from the Grown-ups area (⚙️) with an email link; there are no passwords.
- Progress backs up automatically and appears on any device they sign in on. If two devices change at
  once, the most recent change wins.
- The pay buttons only work once signed in, so every payment is tied to an account.
- The Family Plan is read from the database, which only the Stripe webhook can write, so nobody can
  unlock it by editing their device.

## Step 5: Letter sounds

Record the 38 sounds (about an hour with a voice actor) and put them in `sounds/` as described in
`sounds/README.txt`. Until then, the app says a keyword for each sound ("sun" for /s/).
Families can also record their own in Grown-ups → Letter sounds; those stay on that device.

## Step 6: Before launch

- [ ] Fill in and check `privacy.html` (ideally with a lawyer or a privacy service).
- [ ] Have a dyslexia specialist or phonics teacher review the sound order, words and stories.
- [ ] Test with 10–20 families for 2–4 weeks; ask what they'd change and collect testimonials.
- [ ] Describe it as "teaches reading and spelling with structured phonics". Never claim it treats or cures dyslexia or ADHD.
- [ ] UK children's privacy: the app has no ads, no tracking, and grown-up areas behind a maths question. Keep it that way.

## Step 7 (optional): App Store and Google Play

The web app can be wrapped as store apps:
- **Google Play:** pwabuilder.com packages the site as an Android app (a Trusted Web Activity).
- **Apple App Store:** use Capacitor (capacitorjs.com) to wrap the same files in an iOS app.
  Apple generally requires subscriptions sold inside an iPhone app to use Apple's in-app purchase,
  and the rules differ by country. Read section 3.1 of Apple's App Review Guidelines before you submit.
- Both stores have extra rules for children's apps (Apple's Kids category, Google's Families policy).

## Monthly costs at launch

| Service | Cost |
|---|---|
| Netlify hosting | Free to start |
| Supabase | Free tier (50,000 monthly active users) |
| Email sender (Resend, Postmark or Brevo) | Free tier, then from about £10/month |
| Stripe | No monthly fee; about 1.5% + 20p per UK card payment |
| Domain name | About £10/year |
