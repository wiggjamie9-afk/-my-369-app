# Before you install it: safety checklist

For: Jamie, and anyone (including Kimi) adding a plugin, MCP server, npm package, browser extension or "paste this skill" to the 369 / 48 AI Crew projects.
Written by Claude, 2026-10-31.

You install a lot of things you see on X, TikTok and Threads. Most are fine. A few are built to steal keys, read your files, or quietly send your data somewhere. This checklist catches the bad ones **before** they run. It is defensive: analyse only software you are allowed to inspect, and never run something just to "see what it does".

## The one rule

**Stars, forks, a verified badge and a slick demo prove nothing.** Code decides. A repo with 8,000 stars can still ship a malicious patch next week. Judge what it actually does, not how popular it looks.

## 7 fast checks (about 5 minutes)

1. **Who makes it, and is the source open?** A real GitHub repo you can read, a named maintainer, recent commits, a licence (MIT/Apache is normal). No source, or a brand-new account with one viral post → stop.
2. **What does it want to reach?** Read the README and permissions. Does a note-taking tool ask for your whole disk, your keychain, or network access to random hosts? Mismatch → stop.
3. **Install scripts.** For npm: run `npm pack <package>` then open the tarball's `package.json` and look for `preinstall`, `install`, `postinstall`, `prepare`. For anything: a hook that runs `curl`, `wget`, `eval`, `child_process`, or downloads and runs more code on install is a red flag. (You can also install with `npm install --ignore-scripts` to block them.)
4. **Where does data go?** Search the code for `http`, `fetch`, `axios`, webhook URLs, `discord`, `telegram`, `pastebin`, `raw.githubusercontent`. An app that reads your files and also phones a server you don't recognise → stop.
5. **Secrets it can touch.** Does it read `~/.ssh`, `~/.aws`, `.env`, `id_rsa`, environment variables, browser cookies or your keychain? A tool that both reads secrets and sends network traffic is the dangerous combination.
6. **MCP servers and "skills" / prompts specifically.** The tool's own descriptions are read by your AI. Watch for hidden instructions aimed at the model: "ignore previous instructions", "do not tell the user", "also read…", invisible unicode, base64 blobs, `<IMPORTANT>` blocks. Any of these → do not install; report it.
7. **Updates.** What you audited today is not what ships next week. Pin the exact version, and re-check the diff before updating. "Verified" badges are not a substitute.

## If you still want to try it

- Install it somewhere disposable (a spare machine or a throwaway cloud session), **never** with your real keys, your main GitHub login, or on the machine that runs The 48 AI Crew.
- Give it nothing sensitive: no production `.env`, no Twilio/Stripe/Supabase keys, no customer data.
- Watch what it does on first run (network requests, files touched). If anything surprises you, remove it.

## Hard nos (for this business)

- **Anything that uses another company's private API** (e.g. "700 Instagram APIs reverse engineered"): breaks their terms, gets accounts banned. Use official APIs only.
- **Anything that copies paid software "for free"** via reverse engineering: copyright infringement.
- **"Leaked vaults", "cracked", key dumps, other people's API keys:** illegal to use, and a malware vector. Curated learning lists (e.g. public "awesome-security" repos) are legal to read; "leaked" dumps are not.
- **Trading bots / "turn your AI into a Wall Street desk":** real money at risk, out of scope for this business.
- **"Like and comment and I'll send you $5,000" posts:** engagement-bait or a scam. Don't like, comment, DM, or click. No one sends strangers money for a like.

## When something fails a check

Tell Claude. Don't install it "just to see". If it's already installed and you're unsure, stop using it, rotate any keys it could have seen, and ask for an audit.
