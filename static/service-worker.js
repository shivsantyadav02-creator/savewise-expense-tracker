/**
 * Savewise PWA Service Worker
 * Versioned app-shell caching with strict exclusion of user-specific API & HTML state.
 */

const CACHE_VERSION = "savewise-v1";
const APP_SHELL_CACHE = `${CACHE_VERSION}-shell`;

const APP_SHELL_ASSETS = [
    "/offline.html",
    "/static/manifest.json",
    "/static/css/style.css",
    "/static/js/api.js",
    "/static/js/utils.js",
    "/static/js/dashboard.js",
    "/static/js/insights.js",
    "/static/js/udhar.js",
    "/static/js/pwa.js",
    "/static/vendor/chart.umd.min.js",
    "/static/icons/icon-192.png",
    "/static/icons/icon-512.png",
    "/static/icons/icon-maskable-512.png",
    "/static/icons/apple-touch-icon.png"
];

// 1. Install lifecycle: pre-cache static application shell
self.addEventListener("install", (event) => {
    event.waitUntil(
        caches.open(APP_SHELL_CACHE).then((cache) => {
            return cache.addAll(APP_SHELL_ASSETS);
        })
    );
});

// 2. Activate lifecycle: purge older cache versions
self.addEventListener("activate", (event) => {
    event.waitUntil(
        caches.keys().then((cacheNames) => {
            return Promise.all(
                cacheNames.map((name) => {
                    if (name !== APP_SHELL_CACHE) {
                        return caches.delete(name);
                    }
                })
            );
        }).then(() => self.clients.claim())
    );
});

// 3. Message handler: allow client to trigger skipWaiting on update
self.addEventListener("message", (event) => {
    if (event.data && event.data.type === "SKIP_WAITING") {
        self.skipWaiting();
    }
});

// 4. Fetch lifecycle: strict isolation & offline support
self.addEventListener("fetch", (event) => {
    const request = event.request;
    const url = new URL(request.url);

    // Rule 1: NEVER cache anything under /api/ (dynamic financial data & auth endpoints)
    if (url.pathname.startsWith("/api/")) {
        event.respondWith(fetch(request));
        return;
    }

    // Rule 2: Non-GET requests should always bypass cache
    if (request.method !== "GET") {
        event.respondWith(fetch(request));
        return;
    }

    // Rule 3: HTML Pages (/ and /login) depend on login session.
    // Use network-first and NEVER cache HTML responses to prevent cross-user data leaks.
    const isHtmlNavigation = request.mode === "navigate" ||
        (request.headers.get("accept") && request.headers.get("accept").includes("text/html"));

    if (isHtmlNavigation) {
        event.respondWith(
            fetch(request).catch(() => {
                // When network fails, show the offline page
                return caches.match("/offline.html");
            })
        );
        return;
    }

    // Rule 4: App shell static assets (CSS, JS, icons, vendor) -> Cache first, network fallback
    event.respondWith(
        caches.match(request).then((cachedResponse) => {
            if (cachedResponse) {
                return cachedResponse;
            }

            return fetch(request).then((networkResponse) => {
                // Only cache successful basic same-origin or static asset responses
                if (networkResponse && networkResponse.status === 200 && url.pathname.startsWith("/static/")) {
                    const responseToCache = networkResponse.clone();
                    caches.open(APP_SHELL_CACHE).then((cache) => {
                        cache.put(request, responseToCache);
                    });
                }
                return networkResponse;
            });
        })
    );
});
