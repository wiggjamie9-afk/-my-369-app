---
type: project
status: active
updated: 2026-10-31
sources: 6
---
# 369 Forge

The Vitruvian 369 Forge Clover Studio: a single-page AI image and video studio where several models compete on each prompt and a judge picks the winner.

## Facts
- Lives in `generator.html`; one HTML file, no build step. [source: repo CLAUDE.md]
- Tabs: Create, Storyboard, Library, Stats, Settings. [source: repo docs/369-forge-build-brief.md]
- Runs up to four model "leaves" at once, judges each result, rewrites the prompt and retries until a target score or round limit. [source: repo docs/369-forge-build-brief.md]
- Has standing rules and a failure ledger that benches models no provider serves. [source: repo docs/369-forge-build-brief.md]
- Not yet tested against the live Hugging Face API; tested only with a fake client. [source: repo docs/369-forge-build-brief.md]
- Remaining stages: script writer and hooks, voiceover and captions, MP4 export, templates, thumbnails and analytics, server for premium models, Digital You. [source: repo docs/369-forge-build-brief.md]

## Links
- [[Clover system]] · [[Vitruvian 369 Core]] · [[Business Organism]] · [[Open-source video tools]] · [[Consistent AI characters]]

## Open questions
- Which judge model works best on the live API?

Updated: 2026-10-31
