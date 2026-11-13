// Offline support. The app shell and the last quotes, parts and settings this phone fetched
// are kept so a tradie with one bar of reception can still open and read their quotes.
// Nothing is ever written while offline: changes are refused with a clear message instead.
const SHELL = "bm-shell-v1";
const DATA = "bm-data-v1";
const ASSETS = ["/", "/app.css", "/app.js", "/jarvis.js", "/manifest.webmanifest", "/logo-mark.jpg",
                "/icons/icon-192.png", "/icons/icon-180.png"];
const KEEP = /^\/api\/(quotes(\/\d+)?|settings|parts|jarvis\/summary)$/;

self.addEventListener("install", (e) => {
  e.waitUntil(caches.open(SHELL).then((c) => c.addAll(ASSETS)).then(() => self.skipWaiting()));
});

self.addEventListener("activate", (e) => {
  e.waitUntil(caches.keys()
    .then((keys) => Promise.all(keys.filter((k) => k !== SHELL && k !== DATA).map((k) => caches.delete(k))))
    .then(() => self.clients.claim()));
});

async function networkFirst(request, cacheName, fallbackKey) {
  const cache = await caches.open(cacheName);
  try {
    const fresh = await fetch(request);
    if (fresh.ok) cache.put(fallbackKey || request, fresh.clone());
    return fresh;
  } catch (err) {
    const saved = await cache.match(fallbackKey || request);
    if (!saved) throw err;
    const headers = new Headers(saved.headers);
    headers.set("X-From-Cache", "1");
    return new Response(await saved.blob(), { status: saved.status, headers });
  }
}

self.addEventListener("fetch", (e) => {
  const url = new URL(e.request.url);
  if (e.request.method !== "GET" || url.origin !== location.origin) return;
  if (e.request.mode === "navigate") {
    e.respondWith(networkFirst(e.request, SHELL, "/"));
  } else if (url.pathname.startsWith("/api/")) {
    if (!KEEP.test(url.pathname)) return;
    e.respondWith(networkFirst(e.request, DATA).catch(() => new Response(
      JSON.stringify({ error: "You're offline and this hasn't been saved on the phone yet." }),
      { status: 503, headers: { "Content-Type": "application/json", "X-From-Cache": "1" } })));
  } else {
    e.respondWith(networkFirst(e.request, SHELL));
  }
});
