// Cache only public assets. Never store API responses, uploads or authenticated pages.
const CACHE = 'class-public-v2-sk2441'
const OFFLINE = '/offline.html'
self.addEventListener('install', event => { event.waitUntil(caches.open(CACHE).then(cache => cache.addAll([OFFLINE, '/offline.css', '/icons/icon-192.png', '/icons/icon-512.png']))); self.skipWaiting() })
self.addEventListener('activate', event => event.waitUntil(caches.keys().then(keys => Promise.all(keys.filter(key => key.startsWith('class-public-') && key !== CACHE).map(key => caches.delete(key)))).then(() => self.clients.claim())))
self.addEventListener('fetch', event => {
  const url = new URL(event.request.url)
  if (event.request.method !== 'GET' || url.origin !== self.location.origin || url.pathname.startsWith('/api/') || url.pathname.startsWith('/static/')) return
  if (event.request.mode === 'navigate') { event.respondWith(fetch(event.request).catch(() => caches.match(OFFLINE))); return }
  if (!url.pathname.startsWith('/assets/')) return
  event.respondWith(caches.open(CACHE).then(async cache => {
    const existing = await cache.match(event.request); if (existing) return existing
    const response = await fetch(event.request)
    if (response.ok) { await cache.put(event.request,response.clone()); const keys = await cache.keys(); if (keys.length > 64) await cache.delete(keys.find(key => new URL(key.url).pathname.startsWith('/assets/')) || keys[0]) }
    return response
  }))
})
