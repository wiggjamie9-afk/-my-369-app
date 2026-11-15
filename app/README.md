# 369 Lab (MVP)

Expo / React Native app (iOS, Android, web preview). Four tools in one:

- **Learn**: 12-week AI engineer plan + agent concepts, with progress tracking
- **Team**: generates an AI agent-team blueprint (agents, prompts, workflow, QA, 7-day plan)
- **Research**: live web-search market research that finds startup ideas backed by real quotes
- **Ideas**: every idea, scored out of 25, with status and notes

## Run it

```bash
cd app
npm install
npx expo start        # scan the QR with Expo Go on your phone
npm run web           # or try it in a browser
```

Then open **Settings** and paste your Anthropic API key (console.anthropic.com).
The key is stored in the device Keychain/Keystore and sent only to api.anthropic.com.

## Personal-use mode

The app calls Anthropic directly from the phone with your own key. Do not distribute
this build to other people. To sell it, add a backend that holds the key, enforces
usage limits and runs research jobs on a schedule.

## Before submitting to the stores

Change `ios.bundleIdentifier` and `android.package` in `app.json` (currently `com.example.lab369`),
add real icons in `assets/`, then build with EAS (`npx eas build`).
