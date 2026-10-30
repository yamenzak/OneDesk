/* A presentation through a OneCloud link (www/s.html, one_slide/shared.py).

   The slides arrive with the page, already filled as whoever shared the
   link, and are drawn by play.js as the TV draws them. While the presenter
   presents live, the page follows them: the socket says where they are
   (realtime/handlers.js, onedesk_slide_join), and a page without one asks
   every few seconds. How long each slide was on screen is sent as the guest
   goes, so the presenter can see it as Views. */
(function () {
	"use strict";

	var EVERY = 4000;
	var TELL_EVERY = 15000;
	var deck = document.querySelector("[data-one-deck]");
	var said = document.getElementById("one-deck-data");
	if (!deck || !said || !window.onedesk || !window.onedesk.play) return;
	var data = JSON.parse(said.textContent);
	var slides = data.slides || [];
	var stage = deck.querySelector("[data-one-stage]");
	var count = deck.querySelector("[data-one-count]");
	var badge = deck.querySelector("[data-one-live]");
	var follow = deck.querySelector("[data-one-follow]");
	var at = 0;
	var live = data.live ? data.live.slide || 0 : null;
	var following = true;
	var socketed = false;
	var since = Date.now();
	var seconds = {};

	function method(name) {
		return "/api/method/onedesk.one_slide.shared." + name;
	}

	// the time on the slide being left, counted before moving
	function counted() {
		var now = Date.now();
		seconds[at] = (seconds[at] || 0) + Math.round((now - since) / 1000);
		since = now;
	}

	function show(index) {
		if (!slides.length) return;
		counted();
		at = Math.max(0, Math.min(slides.length - 1, index));
		var shown = slides[at];
		var fades = shown.transition && shown.transition !== "none";
		window.onedesk.play.draw(shown.slide, stage);
		var drawn = stage.firstChild;
		if (fades && drawn) {
			drawn.style.opacity = "0";
			requestAnimationFrame(function () {
				drawn.style.opacity = "1";
			});
		}
		count.textContent = at + 1 + " / " + slides.length;
		paint();
	}

	function paint() {
		badge.hidden = live === null;
		follow.hidden = live === null || following;
	}

	function go(step) {
		following = false;
		show(at + step);
	}

	// where the presenter is now; a guest who went their own way is offered the way back
	function heard(where) {
		if (!where || !where.live) {
			live = null;
			following = true;
			return paint();
		}
		live = where.slide || 0;
		if (following) show(live);
		else paint();
	}

	function ask() {
		frappe.call({ method: "onedesk.one_slide.shared.where", type: "GET", args: { token: data.token, item: data.item || undefined }, freeze: false, callback: function (r) { heard(r.message); } });
	}

	function listen() {
		var where = data.socket || {};
		if (!where.site) return;
		var base = where.port ? location.protocol + "//" + location.hostname + ":" + where.port : location.origin;
		var script = document.createElement("script");
		script.src = base + "/socket.io/socket.io.js";
		script.onload = function () {
			if (!window.io) return;
			var socket = window.io(base + "/" + where.site, { withCredentials: true });
			socket.on("connect", function () {
				socket.emit("onedesk_slide_join", data.token, data.item || "", data.ticket, function (answer) {
					socketed = !!(answer && answer.ok);
					if (socketed) ask();
				});
			});
			socket.on("disconnect", function () {
				socketed = false;
			});
			socket.on("onedesk_slide_at", heard);
		};
		document.head.appendChild(script);
	}

	function tell(leaving) {
		counted();
		var form = new FormData();
		form.append("token", data.token);
		form.append("session", data.session);
		form.append("seconds", JSON.stringify(seconds));
		if (data.item) form.append("item", data.item);
		if (data.csrf) form.append("csrf_token", data.csrf);
		// a page being left cannot wait for an answer, so it leaves a beacon
		if (leaving && navigator.sendBeacon) return navigator.sendBeacon(method("viewed"), form);
		frappe.call({ method: "onedesk.one_slide.shared.viewed", args: { token: data.token, session: data.session, seconds: JSON.stringify(seconds), item: data.item || undefined } });
	}

	deck.querySelector("[data-one-back]").addEventListener("click", function () {
		go(-1);
	});
	deck.querySelector("[data-one-next]").addEventListener("click", function () {
		go(1);
	});
	follow.addEventListener("click", function () {
		following = true;
		show(live || 0);
	});
	deck.querySelector("[data-one-full]").addEventListener("click", function () {
		if (document.fullscreenElement) document.exitFullscreen();
		else if (deck.requestFullscreen) deck.requestFullscreen();
	});
	stage.addEventListener("click", function () {
		go(1);
	});
	document.addEventListener("keydown", function (event) {
		var key = event.key;
		if (key === "ArrowRight" || key === "PageDown" || key === " ") go(1);
		else if (key === "ArrowLeft" || key === "PageUp") go(-1);
		else if (key === "Home") go(-at);
		else if (key === "End") go(slides.length);
		else if (key === "f" || key === "F") deck.querySelector("[data-one-full]").click();
		else return;
		event.preventDefault();
	});
	window.addEventListener("resize", function () {
		window.onedesk.play.fit(stage);
	});
	document.addEventListener("fullscreenchange", function () {
		window.onedesk.play.fit(stage);
	});
	window.addEventListener("pagehide", function () {
		tell(true);
	});

	show(live !== null ? live : 0);
	listen();
	setInterval(function () {
		if (!socketed) ask();
	}, EVERY);
	setInterval(function () {
		tell(false);
	}, TELL_EVERY);
})();
