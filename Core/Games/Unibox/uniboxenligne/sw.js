/* Unibox — service worker.

   Objectif : une fois la page visitée, le jeu reste jouable sans réseau,


   Stratégie, volontairement simple pour un jeu d'un seul fichier :
     - navigation  réseau d'abord, cache en secours. On profite des mises
                     à jour quand la connexion est là, on joue quand elle
                     ne l'est pas.
     - le reste    cache d'abord, et on rafraîchit en arrière-plan.

   À chaque nouvelle version du jeu, changez VERSION : l'ancien cache est
   alors supprimé et les visiteurs reçoivent la nouvelle page. */

const VERSION = 'unibox-v1';

const ASSETS = [
  './',
  './index.html',
  './manifest.webmanifest',
  './icons/icon-192.png',
  './icons/icon-512.png',
  './icons/icon-maskable.png',
  './icons/apple-touch-icon.png',
  './icons/favicon.png',
];

self.addEventListener('install', event => {
  event.waitUntil((async () => {
    const cache = await caches.open(VERSION);
    // Un fichier absent ne doit pas faire échouer toute l'installation,
    // d'où les mises en cache une à une plutôt qu'un addAll.
    await Promise.all(ASSETS.map(url =>
      cache.add(new Request(url, { cache: 'reload' })).catch(() => {})
    ));
    self.skipWaiting();
  })());
});

self.addEventListener('activate', event => {
  event.waitUntil((async () => {
    const names = await caches.keys();
    await Promise.all(names.filter(n => n !== VERSION).map(n => caches.delete(n)));
    await self.clients.claim();
  })());
});

self.addEventListener('fetch', event => {
  const { request } = event;
  if (request.method !== 'GET') return;

  const url = new URL(request.url);
  if (url.origin !== self.location.origin) return;

  if (request.mode === 'navigate') {
    event.respondWith((async () => {
      try {
        const fresh = await fetch(request);
        const cache = await caches.open(VERSION);
        cache.put('./index.html', fresh.clone());
        return fresh;
      } catch (_) {
        return (await caches.match('./index.html')) ||
               (await caches.match('./')) ||
               Response.error();
      }
    })());
    return;
  }

  event.respondWith((async () => {
    const hit = await caches.match(request);
    const network = fetch(request).then(res => {
      if (res && res.ok) caches.open(VERSION).then(c => c.put(request, res.clone()));
      return res;
    }).catch(() => null);
    return hit || (await network) || Response.error();
  })());
});
