# Vitruvian 369 Core

A small "frequency & spatial-dynamics" meditation app: tap one of the **3 / 6 / 9**
vector nodes to play a sine tone (174 / 528 / 963 Hz) with auto-panning stereo
movement, watch a golden-ratio vortex animate on the canvas, and keep a persistent
log of the "visions" you jot down along the way.

Originally a single static HTML file, now rebuilt as a **Vue 3 + Vite** app using
**[ant-design-vue](https://antdv.com/)** for the UI.

## Tech stack

- [Vue 3](https://vuejs.org/) (Composition API, `<script setup>`)
- [Vite](https://vitejs.dev/) for dev/build
- [ant-design-vue](https://antdv.com/) component library (dark theme)
- Web Audio API (oscillator + `StereoPanner`) and Canvas 2D for the visuals

## Getting started

```bash
npm install      # install dependencies
npm run dev      # start the dev server (http://localhost:5173)
npm run build    # production build into dist/
npm run preview  # preview the production build
```

## Project structure

```
.
├── index.html                    # Vite entry
├── vite.config.js
├── package.json
└── src/
    ├── main.js                   # app bootstrap + ant-design-vue registration
    ├── style.css                 # global dark theme base
    ├── App.vue                   # main UI: vortex canvas, audio engine, vision log
    └── composables/
        └── useVisionLog.js       # reactive, localStorage-backed vision log
```

## Notes from the rebuild

- **XSS fixed.** The original rendered logged text via `innerHTML`, which allowed
  stored self-XSS. Vue's `{{ }}` interpolation auto-escapes, so that class of bug
  is gone.
- **Responsive canvas.** The vortex now re-sizes on window `resize` instead of
  measuring only once at load.
- **Audio cleanup.** Oscillator and panner nodes are disconnected on stop / unmount,
  and the `AudioContext` is closed when the component tears down.

## How to use

1. (Optional) type a vision / intention into the text area.
2. Tap **NODE 3**, **NODE 6**, or **NODE 9** to start the corresponding tone and
   log the entry. Tap the active node again to stop.
3. Manage past entries in the **Persistent Vision Log** panel (stored locally in
   your browser).

> Audio starts only after a user interaction (tapping a node), per browser autoplay
> policies.
