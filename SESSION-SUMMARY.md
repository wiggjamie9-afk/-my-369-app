# 369 content engine: everything from this session

## 1. The "steal sheet" guide (Argona / Viktor post)

**The idea:** don't ask AI for business ideas. Start from small online businesses that already
get paid, and copy three things: what people want, what's sold, and where buyers come from.
Never copy the code, brand, text or images.

**Tools it named:**
- **TrustMRR** (trustmrr.com): free list of small businesses whose revenue is read from their payment provider (Stripe).
- **Claude app route:** a `steal` folder with a `CLAUDE.md` of rules, `list.md` (winners), `maybe.md`, `sheets/`, and a weekly scheduled task.
- **Viktor:** a paid AI assistant in Slack that runs the same job weekly. The post is sponsored by Viktor.

**My take:**
- The method is sound, and trusting only payment-verified revenue is good advice.
- I couldn't check its numbers.
- A steal sheet tells you what to build, not how to get customers.

**Status:** not set up. TrustMRR is blocked from this cloud session, and it needs you to pick a niche.

## 2. Screenshots you shared

- **"Build your first AI team with Claude" prompt:** useful once you pick one real workflow. It produces a plan, not software.
- **Creative toolkit list (Bark, Pedalboard, OBS, Shotcut, FFmpeg):** legitimate free tools, each a building block.
- **social-auto-upload repos:** they post by driving a logged-in browser. They break often and can get accounts flagged. Use official posting connections or a scheduler instead.
- **CVE-2019-9978 repo:** WordPress hacking code. Avoid.
- **claude-content-skills (Ootto):** mostly saved prompts plus a pitch for Ootto. Its video step uses paid Runway (about $6–12 per reel).
- **Ripping:** auto-posts Instagram trial reels. Needs an Instagram business account and Meta approval.

## 3. What I built

Everything is on the GitHub branch `claude/369-post-studio` in `wiggjamie9-afk/-my-369-app`. Nothing is on `main` yet.

### Post Studio: `studio.html`
Link: https://claude.ai/artifact/2Yr3JcfdweGS5nBp1w6FDP
- Write a post once and get versions for Threads, X, Instagram, TikTok, YouTube Shorts, LinkedIn and Facebook, each with character limits checked.
- Long posts split into numbered threads on X and Threads.
- On Instagram and TikTok, links become "Link in bio".
- Hashtags are trimmed per platform.
- Every version has a copy button.
- Queue posts at 3, 6 or 9 PM and mark them as posted.
- Export: copy as CSV. The calendar reminders (.ics) button works only when the file is opened from the repo.
- It can pull your latest Vision Log entry when hosted on the same site as the app.

### Reel Maker: `reel.html`
Link: https://claude.ai/artifact/AzTyi5MQb53VHsH94Afyda
- Hook + beats + call to action produce a 1080×1920 vertical video.
- The background is the 369 spiral, and the sound is your node's tone (3 = 174 Hz, 6 = 528 Hz, 9 = 963 Hz).
- **Make video** records it, and **Save** gives you the file (MP4 on iPhone and Safari, WebM in some browsers).
- Tested: a 16-second MP4 with sound was produced.

### 369-reel Claude skill: `.claude/skills/369-reel/SKILL.md`
- Idea or Vision Log entry in; out come 3 hook options, 6 beats, a call to action, the node, a caption, 5 hashtags and a posting slot.
- Rules: hook up to 9 words, beats up to 12 words, one call to action, plain human wording, no promised results, never copy another creator's words.

## 4. How to use it (daily loop)

1. Tell Claude: "369 reel" plus your idea or Vision Log entry.
2. Paste the script into **Reel Maker**, then press **Make video**, then **Save**.
3. Paste the caption into **Post Studio** and copy each platform's version.
4. Post at 3, 6 or 9 PM. Optionally post as an Instagram trial reel first.
5. Reply to "369" comments with your app link.

## 5. What's NOT connected yet

- **Automatic posting:** nothing posts by itself. Options:
  - Zapier (attached to this session) to post to Facebook, LinkedIn, X and Instagram business accounts, or to Buffer.
  - The Higgsfield tools for TikTok.
  - Each post would need your OK.
- **The app has no public web address.** Reels need somewhere to send people.
- **The queue is saved only in the browser you use.** It doesn't sync between devices.

## 6. How good is it for the 369 app

- **Good for:** posting regularly for free, testing hooks, and a look that's clearly your app.
- **Weak:** reels that are only text get fewer views than ones with a face or voice. Film yourself for the hooks that perform.
- **Biggest gap:** a public link to the app, so viewers can actually use it.

## 7. Next steps to choose from

1. Put the 369 app online (GitHub Pages) so reels and posts link somewhere.
2. Connect posting through Zapier or Buffer, approving each post.
3. Merge the branch into `main` (pull request).
4. Run the steal-sheet search once you pick a niche.
