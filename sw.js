// Service Worker for 株価チャート PWA
const CACHE = 'stock-chart-v5';
const SHELL = [
  './stock_chart_development.html',
  './manifest.json',
  './icons/icon-192.png',
  './icons/icon-512.png',
];

// Install: cache app shell
self.addEventListener('install', e => {
  e.waitUntil(
    caches.open(CACHE).then(c => c.addAll(SHELL))
  );
  self.skipWaiting();
});

// Activate: clean up old caches
self.addEventListener('activate', e => {
  e.waitUntil(
    caches.keys().then(keys =>
      Promise.all(keys.filter(k => k !== CACHE).map(k => caches.delete(k)))
    )
  );
  self.clients.claim();
});

// Fetch: network-first for navigation, cache-first for assets
self.addEventListener('fetch', e => {
  const { request } = e;
  const url = new URL(request.url);

  // Only handle same-origin requests
  if (url.origin !== location.origin) return;

  if (request.mode === 'navigate') {
    // Navigation: try network, fall back to cached HTML
    e.respondWith(
      fetch(request)
        .then(res => {
          const clone = res.clone();
          caches.open(CACHE).then(c => c.put(request, clone));
          return res;
        })
        .catch(() => caches.match('./stock_chart_development.html'))
    );
  } else {
    // Assets: cache-first
    e.respondWith(
      caches.match(request).then(cached => cached || fetch(request))
    );
  }
});
