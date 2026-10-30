/* The TV's service worker (one_display/worker.py serves it at /tv-worker.js).
   The page and its script come from the network when there is one and from
   here when there isn't; pictures, videos, music and fonts are kept the
   first time they are played, so a screen that restarts offline plays what it had.
   What a screen asks the server is never kept: its last answer is in the
   page's own storage (tv.js). */
var CACHE = "one-tv-3";
var SHELL = ["/tv", "/assets/onedesk/js/one_slide/play.js", "/assets/frappe/css/fonts/inter/inter.css", "/assets/onedesk/slide/fonts.css", "/api/method/onedesk.one_slide.fonts.css", "/assets/onedesk/js/one_display/tv.js"];

self.addEventListener("install", function (event) {
	event.waitUntil(
		caches.open(CACHE).then(function (cache) {
			return cache.addAll(SHELL);
		})
	);
	self.skipWaiting();
});

self.addEventListener("activate", function (event) {
	event.waitUntil(
		caches.keys().then(function (keys) {
			return Promise.all(
				keys.filter(function (key) {
					return key !== CACHE;
				}).map(function (key) {
					return caches.delete(key);
				})
			);
		})
	);
	self.clients.claim();
});

// what never changes at its address: files, a slide's pictures and videos, and font faces
var KEPT = ["/files/", "/assets/onedesk/slide/fonts/", "/assets/frappe/css/fonts/", "/api/method/onedesk.one_slide.api.shown", "/api/method/onedesk.one_slide.fonts.face"];

function media(url) {
	return KEPT.some(function (start) {
		return url.pathname.indexOf(start) === 0;
	});
}

self.addEventListener("fetch", function (event) {
	var request = event.request;
	if (request.method !== "GET") return;
	var url = new URL(request.url);
	if (url.origin !== self.location.origin) return;
	if (media(url)) {
		event.respondWith(
			caches.open(CACHE).then(function (cache) {
				return cache.match(request).then(function (kept) {
					return (
						kept ||
						fetch(request).then(function (answer) {
							if (answer.ok && answer.status === 200) cache.put(request, answer.clone());
							return answer;
						})
					);
				});
			})
		);
		return;
	}
	if (url.pathname === "/tv" || SHELL.indexOf(url.pathname) > -1) {
		event.respondWith(
			fetch(request)
				.then(function (answer) {
					if (answer.ok) {
						var copy = answer.clone();
						caches.open(CACHE).then(function (cache) {
							cache.put(url.pathname === "/tv" ? "/tv" : request, copy);
						});
					}
					return answer;
				})
				.catch(function () {
					return caches.match(url.pathname === "/tv" ? "/tv" : request);
				})
		);
	}
});
