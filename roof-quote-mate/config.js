/* ============================================================================
   ROOF QUOTE MATE - config.js
   Everything you can change lives in this one file. You never need to open
   the other files. Save, refresh the page, done.

   Quick setup (5 minutes):
     1. Put your business name, phone and logo file name under "business".
     2. Put YOUR rates under "jobTypes", then set ratesConfirmed to true.
     3. Paste your webhook address into "webhookUrl" (Zapier, Make, n8n,
        your own server - anything that accepts a form POST).
     4. Set "tier" to "lite" or "full".

   Until steps 2 and 3 are done the page shows a yellow SETUP notice so you
   can't put it in front of customers half-finished by accident.
   ========================================================================= */

window.RQM_CONFIG = {

  /* "lite" = quote + lead form.
     "full" = the same, plus roof photos and your own name and logo on every
              screen. (Full needs the file full.js to be in the folder.) */
  tier: "lite",

  business: {
    name: "Your Roofing Co",
    logoPath: "logo.svg",          // a file in this folder: logo.png, logo.jpg, logo.svg
    phone: "",                     // shown to the customer if a lead fails to send
    licence: ""                    // optional, shown in the small print
  },

  /* Where leads are sent. Leave empty and the app runs in demo mode:
     it works end to end but sends nothing, and says so. */
  webhookUrl: "",

  /* The rates below are EXAMPLES so the app has something to show.
     They are not real prices. Put in your own, then change this to true. */
  ratesConfirmed: false,

  /* What you sell. Change these words to switch the app to another trade. */
  trade: {
    productName: "Roof Quote Mate",    // shown in lite mode
    jobName: "new roof",               // "Ballpark for your new roof"
    unit: "m²"                         // what the rates below are per
  },

  /* One entry per roof type. Rates are dollars per m², before GST. */
  jobTypes: [
    { id: "tile",      label: "Tile",      hint: "Concrete or terracotta", labourPerUnit: 60, materialPerUnit: 70 },
    { id: "colorbond", label: "Colorbond", hint: "Steel sheet roofing",    labourPerUnit: 55, materialPerUnit: 65 },
    { id: "tin",       label: "Tin",       hint: "Corrugated iron",        labourPerUnit: 45, materialPerUnit: 40 }
  ],

  /* How much harder (dearer) the job gets. 1 = normal, 1.25 = 25% more. */
  difficulty: [
    { id: "single", label: "Single storey",   hint: "Ground floor only",  multiplier: 1 },
    { id: "double", label: "Double storey",   hint: "Two levels",         multiplier: 1.25 },
    { id: "triple", label: "Three or more",   hint: "Or a very steep roof", multiplier: 1.5 }
  ],

  /* Rough sizes. min and max are in the unit above (m²). */
  sizes: [
    { id: "small",  label: "Small",    hint: "Up to 120 m² · 2 to 3 bedrooms",  min: 80,  max: 120 },
    { id: "medium", label: "Medium",   hint: "120 to 200 m² · 3 to 4 bedrooms", min: 120, max: 200 },
    { id: "large",  label: "Large",    hint: "200 to 320 m² · 5 bedrooms plus", min: 200, max: 320 },
    { id: "unsure", label: "Not sure", hint: "We'll work it out on site",       min: 80,  max: 320 }
  ],

  pricing: {
    gstRegistered: true,      // false = you don't charge GST: nothing is added and GST is never mentioned
    ratesIncludeGst: false,   // false = the app adds GST and shows prices "including GST"
    gstRate: 0.10,
    spread: 0.10,             // widen the range 10% each way to cover unknowns
    roundTo: 100,             // round to the nearest $100 (low end down, high end up)
    minimumJob: 3000,         // never show a ballpark below this
    /* Optional: a rebate taken off the price, sized by the job. Leave as null if there isn't one.
       Example for a trade with a per-unit subsidy that tapers on bigger jobs:
         rebate: { label: "Government rebate", perUnit: 250, note: "Paid as a discount on your invoice.",
                   bands: [ { upTo: 14, share: 1 }, { upTo: 28, share: 0.6 }, { upTo: 50, share: 0.15 } ] }  */
    rebate: null
  },

  /* Full tier only. */
  photos: {
    max: 4,
    maxEdgePx: 1600,          // photos are shrunk on the phone before sending
    quality: 0.82
  },

  /* Every word the customer reads. Plain words work best. */
  words: {
    headline: "What's a new roof going to cost?",
    subline: "Four quick taps. Ballpark price straight away.",
    askType: "What's on your roof now?",
    askDifficulty: "How tall is the house?",
    askSize: "Roughly how big is the roof?",
    askSuburb: "What suburb is the job in?",
    suburbPlaceholder: "e.g. Fremantle",
    ballparkTitle: "Your ballpark",
    ballparkNote: "Ballpark only. The exact price depends on the roof's condition, pitch and access.",
    leadTitle: "Want the exact quote?",
    leadSub: "Tell us where to send it. No spam, no call centres.",
    photosTitle: "Add up to 4 photos of the roof",
    photosSub: "Optional, but it gets you a sharper quote.",
    sendButton: "Send me the exact quote",
    // optional: privacyNote (use {business} for your name) and watchTitle; any job type, difficulty or size
    // can carry a  watch: "..."  line that is listed under the ballpark when the customer picks it

    thanksTitle: "Got it. Thanks, mate.",
    thanksSub: "We'll be in touch with your exact quote."
  }
};
