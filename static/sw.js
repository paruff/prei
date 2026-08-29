// Service Worker for PREI - Cache-first strategy for offline support
// Version: 1.0.0

const CACHE_NAME = 'prei-v1';
const OFFLINE_URL = '/offline/';

// Static assets to cache on install
const STATIC_ASSETS = [
  '/',
  '/offline/',
  '/static/css/tokens.css',
  '/static/css/base.css',
  '/static/js/theme.js',
  '/static/js/notifications.js',
  '/static/manifest.json',
];

// Cache-first strategy for static assets
async function cacheFirst(request) {
  const cache = await caches.open(CACHE_NAME);
  const cachedResponse = await cache.match(request);

  if (cachedResponse) {
    // Return cached response and update cache in background
    const fetchPromise = fetch(request).then(response => {
      if (response.ok) {
        cache.put(request, response.clone());
      }
      return response;
    }).catch(() => cachedResponse); // Return cached if network fails

    return cachedResponse;
  }

  // Not in cache, fetch and cache
  try {
    const networkResponse = await fetch(request);
    if (networkResponse.ok) {
      const cache = await caches.open(CACHE_NAME);
      cache.put(request, networkResponse.clone());
    }
    return networkResponse;
  } catch (error) {
    // If it's a navigation request and we're offline, show offline page
    if (request.mode === 'navigate') {
      const cache = await caches.open(CACHE_NAME);
      const offlineResponse = await cache.match(OFFLINE_URL);
      if (offlineResponse) {
        return offlineResponse;
      }
    }
    throw error;
  }
}

// Network-first strategy for API calls
async function networkFirst(request) {
  const cache = await caches.open(CACHE_NAME);

  try {
    const networkResponse = await fetch(request);
    if (networkResponse.ok) {
      cache.put(request, networkResponse.clone());
    }
    return networkResponse;
  } catch (error) {
    const cachedResponse = await cache.match(request);
    if (cachedResponse) {
      return cachedResponse;
    }
    if (request.mode === 'navigate') {
      const offlineResponse = await cache.match(OFFLINE_URL);
      if (offlineResponse) {
        return offlineResponse;
      }
    }
    throw error;
  }
}

// Stale-while-revalidate for API responses
async function staleWhileRevalidate(request) {
  const cache = await caches.open(CACHE_NAME);
  const cachedResponse = await cache.match(request);

  const fetchPromise = fetch(request).then(async (networkResponse) => {
    if (networkResponse.ok) {
      cache.put(request, networkResponse.clone());
    }
    return networkResponse;
  });

  if (cachedResponse) {
    // Return cached immediately, update in background
    fetchPromise.catch(() => {}); // suppress error
    return cachedResponse;
  }

  return fetchPromise;
}

// Install event - cache static assets
self.addEventListener('install', event => {
  event.waitUntil(
    caches.open(CACHE_NAME)
      .then(cache => cache.addAll(STATIC_ASSETS))
      .then(() => self.skipWaiting())
  );
});

// Activate event - clean up old caches
self.addEventListener('activate', event => {
  event.waitUntil(
    caches.keys().then(cacheNames => {
      return Promise.all(
        cacheNames
          .filter(name => name !== CACHE_NAME)
          .map(name => caches.delete(name))
      );
    }).then(() => self.clients.claim())
  );
});

// Fetch event - route requests to appropriate strategy
self.addEventListener('fetch', event => {
  const { request } = event;
  const url = new URL(request.url);

  // Skip non-GET requests
  if (request.method !== 'GET') {
    return;
  }

  // Skip cross-origin requests
  if (url.origin !== location.origin) {
    return;
  }

  // Handle different routes with appropriate strategies
  if (url.pathname.startsWith('/static/')) {
    // Static assets: cache-first
    event.respondWith(cacheFirst(event.request));
  } else if (url.pathname.startsWith('/api/')) {
    // API calls: stale-while-revalidate
    event.respondWith(staleWhileRevalidate(event.request));
  } else if (request.mode === 'navigate') {
    // Navigation requests: network-first with offline fallback
    event.respondWith(networkFirst(event.request));
  } else {
    // Default: stale-while-revalidate
    event.respondWith(staleWhileRevalidate(event.request));
  }
});

// Background sync for offline form submissions
self.addEventListener('sync', event => {
  if (event.tag === 'sync-forms') {
    event.waitUntil(syncForms());
  }
});

async function syncForms() {
  const cache = await caches.open('form-submissions');
  const requests = await cache.keys();

  for (const request of requests) {
    try {
      await fetch(request);
      await cache.delete(request);
    } catch (error) {
      console.error('Sync failed for', request.url, error);
    }
  }
}

// Push notification handling
self.addEventListener('push', event => {
  if (!event.data) return;

  const data = event.data.json();
  const options = {
    body: data.body,
    icon: '/static/icons/icon-192x192.png',
    badge: '/static/icons/badge-72x72.png',
    vibrate: [100, 50, 100],
    data: {
      url: data.url || '/'
    }
  };

  event.waitUntil(
    self.registration.showNotification(data.title, options)
  );
});

self.addEventListener('notificationclick', event => {
  event.notification.close();

  event.waitUntil(
    clients.matchAll({ type: 'window', includeUncontrolled: true })
      .then(clientList => {
        for (const client of clientList) {
          if (client.url === event.notification.data.url && 'focus' in client) {
            return client.focus();
          }
        }
        return clients.openWindow(event.notification.data.url);
      })
  );
});

// Periodic background sync (if supported)
self.addEventListener('periodicsync', event => {
  if (event.tag === 'update-indicators') {
    event.waitUntil(updateMarketIndicators());
  }
});

async function updateMarketIndicators() {
  // This would trigger a background update of market indicators
  // Implementation depends on your backend API
  console.log('Periodic sync: updating market indicators');
}
