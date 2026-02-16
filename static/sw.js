/**
 * Service Worker for Convertica
 * Provides offline support and caching for static assets
 */

const CACHE_VERSION = 'convertica-v5';
const STATIC_CACHE = `${CACHE_VERSION}-static`;
const DYNAMIC_CACHE = `${CACHE_VERSION}-dynamic`;
const IMAGE_CACHE = `${CACHE_VERSION}-images`;

// Assets to cache on install
const STATIC_ASSETS = [
    '/static/css/tailwind.css',
    '/static/js/utils.js',
    '/static/js/task-cancellation.js',
    '/static/js/websocket-progress.js',
    '/static/images/logo-56.webp',
    '/static/images/logo-56.png',
    '/offline.html',
    '/static/site.webmanifest',
];

// Install event - cache static assets
self.addEventListener('install', (event) => {
    console.log('[SW] Installing Service Worker...');
    event.waitUntil(
        caches.open(STATIC_CACHE)
            .then((cache) => {
                console.log('[SW] Caching static assets');
                return cache.addAll(STATIC_ASSETS);
            })
            .catch((error) => {
                console.error('[SW] Failed to cache static assets:', error);
            })
    );
    // Activate immediately
    self.skipWaiting();
});

// Activate event - clean up old caches
self.addEventListener('activate', (event) => {
    console.log('[SW] Activating Service Worker...');
    event.waitUntil(
        caches.keys()
            .then((cacheNames) => {
                return Promise.all(
                    cacheNames
                        .filter((cacheName) => {
                            return cacheName.startsWith('convertica-') &&
                                   cacheName !== STATIC_CACHE &&
                                   cacheName !== DYNAMIC_CACHE;
                        })
                        .map((cacheName) => {
                            console.log('[SW] Deleting old cache:', cacheName);
                            return caches.delete(cacheName);
                        })
                );
            })
    );
    // Take control immediately
    return self.clients.claim();
});

// Fetch event - serve from cache, fallback to network
self.addEventListener('fetch', (event) => {
    const { request } = event;
    const url = new URL(request.url);

    // Skip non-GET requests
    if (request.method !== 'GET') {
        return;
    }

    // Skip API requests (they should always be fresh)
    if (url.pathname.startsWith('/api/')) {
        return;
    }

    // Skip admin requests
    if (url.pathname.startsWith('/admin/')) {
        return;
    }

    // Never cache HTML/navigation requests.
    // Otherwise we can serve cached HTML for a different language and it will look like
    // language switching does not persist.
    const acceptHeader = request.headers.get('accept') || '';
    const isHtmlRequest = request.mode === 'navigate' || acceptHeader.includes('text/html');
    if (isHtmlRequest) {
        event.respondWith(
            fetch(request).catch(() => caches.match('/offline.html'))
        );
        return;
    }

    event.respondWith(
        caches.match(request)
            .then((cachedResponse) => {
                if (cachedResponse) {
                    // Return cached response and update cache in background
                    event.waitUntil(updateCache(request));
                    return cachedResponse;
                }

                // Not in cache, fetch from network
                return fetch(request)
                    .then((networkResponse) => {
                        // Cache successful responses
                        if (networkResponse && networkResponse.status === 200) {
                            const responseToCache = networkResponse.clone();
                            caches.open(DYNAMIC_CACHE)
                                .then((cache) => {
                                    cache.put(request, responseToCache);
                                });
                        }
                        return networkResponse;
                    })
                    .catch((error) => {
                        console.error('[SW] Fetch failed:', error);
                        // Return offline page for navigation requests
                        if (request.mode === 'navigate') {
                            return caches.match('/offline.html');
                        }
                        throw error;
                    });
            })
    );
});

// Update cache in background
async function updateCache(request) {
    try {
        const networkResponse = await fetch(request);
        if (networkResponse && networkResponse.status === 200) {
            const url = new URL(request.url);
            const isStaticAsset = url.pathname.startsWith('/static/');
            const targetCacheName = isStaticAsset ? STATIC_CACHE : DYNAMIC_CACHE;
            const cache = await caches.open(targetCacheName);
            await cache.put(request, networkResponse);
        }
    } catch (error) {
        // Silently fail - we already have cached version
        console.log('[SW] Background update failed:', error);
    }
}

// Message event - handle messages from clients
self.addEventListener('message', (event) => {
    if (event.data && event.data.type === 'SKIP_WAITING') {
        self.skipWaiting();
    }
});

// Push notification event - show notification when conversion completes
self.addEventListener('push', (event) => {
    console.log('[SW] Push notification received');

    let data = {
        title: 'Convertica',
        body: 'Your file conversion is complete!',
        icon: '/static/favicon-192x192.png',
        badge: '/static/favicon-96x96.png',
        tag: 'conversion-complete',
        requireInteraction: false,
        data: {
            url: '/'
        }
    };

    if (event.data) {
        try {
            const pushData = event.data.json();
            data = { ...data, ...pushData };
        } catch (e) {
            console.error('[SW] Failed to parse push data:', e);
        }
    }

    event.waitUntil(
        self.registration.showNotification(data.title, {
            body: data.body,
            icon: data.icon,
            badge: data.badge,
            tag: data.tag,
            requireInteraction: data.requireInteraction,
            data: data.data,
            actions: [
                {
                    action: 'open',
                    title: 'Open',
                    icon: '/static/icons/open.png'
                },
                {
                    action: 'close',
                    title: 'Close',
                    icon: '/static/icons/close.png'
                }
            ]
        })
    );
});

// Notification click event - handle notification clicks
self.addEventListener('notificationclick', (event) => {
    console.log('[SW] Notification clicked:', event.action);

    event.notification.close();

    if (event.action === 'close') {
        return;
    }

    // Open the app
    const urlToOpen = event.notification.data?.url || '/';

    event.waitUntil(
        clients.matchAll({ type: 'window', includeUncontrolled: true })
            .then((clientList) => {
                // Check if app is already open
                for (const client of clientList) {
                    if (client.url === urlToOpen && 'focus' in client) {
                        return client.focus();
                    }
                }
                // Open new window
                if (clients.openWindow) {
                    return clients.openWindow(urlToOpen);
                }
            })
    );
});

// Background sync event - retry failed requests
self.addEventListener('sync', (event) => {
    console.log('[SW] Background sync:', event.tag);

    if (event.tag === 'sync-conversions') {
        event.waitUntil(syncConversions());
    }
});

async function syncConversions() {
    // Placeholder for syncing failed conversion requests
    console.log('[SW] Syncing conversions...');
    // Implementation would retrieve failed requests from IndexedDB and retry them
}
