"use strict";

var CACHE_NAME = "rohgpt-shell-v2";
var SHELL_FILES = [
    "/static/css/style.css?v=2",
    "/static/manifest.webmanifest",
    "/static/images/roh-gpt.svg",
    "/static/offline.html"
];

self.addEventListener("install", function (event) {
    event.waitUntil(
        caches.open(CACHE_NAME).then(function (cache) {
            return cache.addAll(SHELL_FILES);
        })
    );
    self.skipWaiting();
});

self.addEventListener("activate", function (event) {
    event.waitUntil(
        caches.keys().then(function (keys) {
            return Promise.all(keys.map(function (key) {
                if (key !== CACHE_NAME) return caches.delete(key);
                return Promise.resolve(false);
            }));
        })
    );
    self.clients.claim();
});

self.addEventListener("fetch", function (event) {
    var request = event.request;
    var url = new URL(request.url);
    if (request.method !== "GET" || url.origin !== self.location.origin) return;

    if (request.mode === "navigate") {
        event.respondWith(
            fetch(request).catch(function () {
                return caches.match("/static/offline.html");
            })
        );
        return;
    }

    if (url.pathname.indexOf("/static/") === 0) {
        event.respondWith(
            caches.match(request).then(function (cached) {
                return cached || fetch(request);
            })
        );
    }
});
