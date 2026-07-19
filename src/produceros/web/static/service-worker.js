// ProducerOS service worker: caches the offline application shell only.
// It does NOT cache live catalog data, and it never claims the full app
// works offline -- see /offline.html and docs/ANDROID_PWA.md. Viewing the
// catalog, editing projects, running scans, etc. all require ProducerOS
// to be running and reachable (desktop mode or LAN mode).

const CACHE_NAME = "produceros-shell-v1";
const SHELL_ASSETS = [
  "/offline.html",
  "/static/css/app.css",
  "/static/js/app.js",
  "/static/svg/icons.svg",
  "/static/manifest.webmanifest",
  "/static/icons/icon-192.png",
  "/static/icons/icon-512.png",
];

self.addEventListener("install", (event) => {
  event.waitUntil(
    caches.open(CACHE_NAME).then((cache) => cache.addAll(SHELL_ASSETS)).then(() => self.skipWaiting())
  );
});

self.addEventListener("activate", (event) => {
  event.waitUntil(
    caches.keys().then((keys) =>
      Promise.all(keys.filter((key) => key !== CACHE_NAME).map((key) => caches.delete(key)))
    ).then(() => self.clients.claim())
  );
});

self.addEventListener("fetch", (event) => {
  const request = event.request;
  if (request.method !== "GET") return;

  const url = new URL(request.url);
  const isShellAsset = SHELL_ASSETS.some((path) => url.pathname === path);

  if (isShellAsset) {
    event.respondWith(
      caches.match(request).then((cached) => cached || fetch(request))
    );
    return;
  }

  if (request.mode === "navigate") {
    event.respondWith(
      fetch(request).catch(() => caches.match("/offline.html"))
    );
  }
});
