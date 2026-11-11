// Word Orbit offline support.
// The app itself loads from the network first (so updates arrive straight away) and
// falls back to the cached copy offline. Fonts and letter sounds are cached once used.
// Account and payment requests are never cached.
const CACHE = 'word-orbit-v1';
const SHELL = [
  './', './index.html', './manifest.webmanifest', './privacy.html',
  './icons/icon.svg', './icons/icon-192.png', './icons/icon-512.png', './icons/apple-touch-icon.png'
];

self.addEventListener('install', e => {
  e.waitUntil(caches.open(CACHE).then(c => c.addAll(SHELL)).then(() => self.skipWaiting()));
});

self.addEventListener('activate', e => {
  e.waitUntil(
    caches.keys()
      .then(keys => Promise.all(keys.filter(k => k !== CACHE).map(k => caches.delete(k))))
      .then(() => self.clients.claim())
  );
});

self.addEventListener('fetch', e => {
  const req = e.request;
  if (req.method !== 'GET') return;
  const url = new URL(req.url);
  const sameOrigin = url.origin === self.location.origin;
  const isFont = /fonts\.(googleapis|gstatic)\.com$/.test(url.hostname);
  const isLibrary = url.hostname === 'cdn.jsdelivr.net';
  if (!sameOrigin && !isFont && !isLibrary) return; // Supabase, Stripe and anything else go straight to the network

  // Fonts, the sign-in library and letter sounds rarely change: use the cache first
  if (isFont || isLibrary || url.pathname.includes('/sounds/')) {
    e.respondWith(
      caches.match(req).then(hit => hit || fetch(req).then(res => {
        if (res.ok || res.type === 'opaque') { const copy = res.clone(); caches.open(CACHE).then(c => c.put(req, copy)); }
        return res;
      }))
    );
    return;
  }

  // The app: network first, cached copy when offline
  e.respondWith(
    fetch(req).then(res => {
      if (res.ok) { const copy = res.clone(); caches.open(CACHE).then(c => c.put(req, copy)); }
      return res;
    }).catch(() => caches.match(req).then(hit => hit || caches.match('./index.html')))
  );
});
