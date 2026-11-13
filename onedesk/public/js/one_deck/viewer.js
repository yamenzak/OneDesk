/* A presentation through a OneCloud link (www/s.html, one_deck/shared.py).

   The slides arrive with the page, already filled as whoever shared the
   link, and are drawn by play.js as the TV draws them. While the presenter
   presents live, the page follows them: the socket says where they are
   (realtime/handlers.js, onedesk_slide_join), and a page without one asks
   every few seconds. How long each slide was on screen is sent as the guest
   goes, so the presenter can see it as Views. Phone Remote pairs a phone
   with this page alone (one_deck/remote.py, pair_link): whoever is in front
   of the screen drives it, with no signing in. */
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
	var phone = deck.querySelector("[data-one-phone]");
	var phoned = deck.querySelector("[data-one-phoned]");
	var pair = deck.querySelector("[data-one-pair]");
	var pointer = deck.querySelector("[data-one-pointer]");
	var socket = null;
	// the phone paired with this page: its token, and this page's own key
	var remote = null;
	var connected = false;
	var at = 0;
	var live = data.live ? data.live.slide || 0 : null;
	var following = true;
	var socketed = false;
	var since = Date.now();
	var seconds = {};

	function method(name) {
		return "/api/method/onedesk.one_deck.shared." + name;
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
		window.onedesk.play.draw(shown.slide, stage, following && live !== null);
		var drawn = stage.firstChild;
		if (fades && drawn) {
			drawn.style.opacity = "0";
			requestAnimationFrame(function () {
				drawn.style.opacity = "1";
			});
		}
		count.textContent = at + 1 + " / " + slides.length;
		paint();
		tellPhone();
	}

	function paint() {
		badge.hidden = live === null;
		follow.hidden = live === null || following;
	}

	function go(step) {
		// what comes on a click comes before the next slide does
		if (step > 0 && window.onedesk.play.step(stage)) return;
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
		frappe.call({ method: "onedesk.one_deck.shared.where", type: "GET", args: { token: data.token, item: data.item || undefined }, freeze: false, callback: function (r) { heard(r.message); } });
	}

	function listen() {
		var where = data.socket || {};
		if (!where.site) return;
		var base = where.port ? location.protocol + "//" + location.hostname + ":" + where.port : location.origin;
		var script = document.createElement("script");
		script.src = base + "/socket.io/socket.io.js";
		script.onload = function () {
			if (!window.io) return;
			socket = window.io(base + "/" + where.site, { withCredentials: true });
			phone.hidden = false;
			socket.on("connect", function () {
				if (remote) joinRemote();
				socket.emit("onedesk_slide_join", data.token, data.item || "", data.ticket, function (answer) {
					socketed = !!(answer && answer.ok);
					if (socketed) ask();
				});
			});
			socket.on("disconnect", function () {
				socketed = false;
			});
			socket.on("onedesk_slide_at", heard);
			socket.on("onedesk_remote", heardPhone);
		};
		document.head.appendChild(script);
	}

	// the phone remote: this page joins the token's room with its own key, the
	// phone with the key it made, and the first phone in keeps it
	function joinRemote() {
		if (socket && remote) socket.emit("onedesk_remote_join", remote.token, remote.screen, function () {});
	}

	function tellPhone() {
		if (socket && remote && connected) socket.emit("onedesk_remote_say", "state", { at: at, of: slides.length });
	}

	function heardPhone(message) {
		var said = (message && message.payload) || {};
		if (!message) return;
		if (message.event === "hello") {
			connected = true;
			pair.hidden = true;
			phoned.hidden = false;
			tellPhone();
		} else if (message.event === "go") go(said.step > 0 ? 1 : -1);
		else if (message.event === "point") pointAt(said);
	}

	// where the phone points, as parts of the slide drawn on the stage
	function pointAt(said) {
		if (!said.on) {
			pointer.hidden = true;
			return;
		}
		var box = (stage.firstChild || stage).getBoundingClientRect();
		var within = deck.getBoundingClientRect();
		var x = Math.max(0, Math.min(1, +said.x || 0));
		var y = Math.max(0, Math.min(1, +said.y || 0));
		pointer.style.left = box.left - within.left + x * box.width + "px";
		pointer.style.top = box.top - within.top + y * box.height + "px";
		pointer.hidden = false;
	}

	function unpairPhone(leaving) {
		if (!remote) return;
		var form = new FormData();
		form.append("token", remote.token);
		form.append("screen", remote.screen);
		if (data.csrf) form.append("csrf_token", data.csrf);
		if (leaving && navigator.sendBeacon) navigator.sendBeacon("/api/method/onedesk.one_deck.remote.unpair", form);
		else frappe.call({ method: "onedesk.one_deck.remote.unpair", args: { token: remote.token, screen: remote.screen }, freeze: false });
		remote = null;
		connected = false;
		phoned.hidden = true;
		pointer.hidden = true;
	}

	// a fresh code each time, filling the screen on the same click
	function pairPhone() {
		if (!document.fullscreenElement && deck.requestFullscreen) deck.requestFullscreen();
		unpairPhone(false);
		frappe.call({
			method: "onedesk.one_deck.remote.pair_link",
			args: { token: data.token, ticket: data.ticket, item: data.item || undefined },
			freeze: false,
			callback: function (r) {
				if (!r.message) return;
				remote = r.message;
				deck.querySelector("[data-one-qr]").innerHTML = remote.qr;
				deck.querySelector("[data-one-url]").textContent = remote.url;
				pair.hidden = false;
				joinRemote();
			},
		});
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
		frappe.call({ method: "onedesk.one_deck.shared.viewed", args: { token: data.token, session: data.session, seconds: JSON.stringify(seconds), item: data.item || undefined } });
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
		unpairPhone(true);
	});
	phone.addEventListener("click", pairPhone);
	deck.querySelector("[data-one-pair-close]").addEventListener("click", function () {
		pair.hidden = true;
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
