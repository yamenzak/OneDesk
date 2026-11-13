/* A presenter's phone as the remote (www/slide-remote.html, one_deck/remote.py).

   The phone and the presenter view meet in a socket room for the token in
   the QR code (realtime/handlers.js). The phone says where to go and where
   to point; the presenter view says which slide is showing and its notes.

   The pointer is a gyroscope, not a laser: a phone knows how it turns, not
   where the screen is. Pressing Hold to Point takes where the phone points
   now as the middle of the slide, and turning it moves the dot by how far
   it turned. Letting go hides the dot; pressing again starts from the
   middle again. A phone that has no gyroscope, or says no, gets a pad to
   drag a finger on instead. */
(function () {
	"use strict";

	var said = document.getElementById("one-remote-data");
	if (!said) return;
	var data = JSON.parse(said.textContent);
	var say = function () {};
	var words = data.words || {};
	var t = function (key, args) {
		return String(words[key] || "").replace(/\{(\d+)\}/g, function (m, i) {
			return args && args[i] != null ? args[i] : m;
		});
	};

	// this phone's own key, from the page: the first phone in keeps the remote
	var key = data.key;
	// each slide's notes, when the person holding the phone may read them
	var kept = [];

	var state = document.querySelector("[data-one-state]");
	var notes = document.querySelector("[data-one-notes]");
	var clock = document.querySelector("[data-one-clock]");
	var point = document.querySelector("[data-one-point]");
	var pad = document.querySelector("[data-one-pad]");

	// how far the phone turns to cross the slide: 40 degrees across, 30 down
	var WIDE = 40;
	var HIGH = 30;
	var EVERY = 33;

	function heard(message) {
		if (!message || message.event !== "state") return;
		var shown = message.payload || {};
		state.textContent = shown.at < shown.of ? t("slide", [shown.at + 1, shown.of]) : t("end");
		notes.textContent = (shown.notes != null ? shown.notes : kept[shown.at]) || "";
		// the presenter's clock, as their workspace writes a time, and how long they have been going
		clock.textContent = [shown.clock, shown.elapsed].filter(Boolean).join(" · ");
	}

	function connect() {
		var where = data.socket || {};
		var base = where.port ? location.protocol + "//" + location.hostname + ":" + where.port : location.origin;
		var script = document.createElement("script");
		script.src = base + "/socket.io/socket.io.js";
		script.onload = function () {
			if (!window.io) return;
			var socket = window.io(base + "/" + where.site, { withCredentials: true });
			socket.on("connect", function () {
				socket.emit("onedesk_remote_join", data.token, key, function (answer) {
					if (!answer || !answer.ok) {
						state.textContent = t(answer && answer.taken ? "taken" : "ended");
						return;
					}
					state.textContent = t("connected");
					say = function (event, payload) {
						socket.emit("onedesk_remote_say", event, payload);
					};
					say("hello", {});
					// the notes, if whoever holds this phone is signed in and may read them
					frappe.call({ method: "onedesk.one_deck.remote.notes", type: "GET", args: { token: data.token, key: key }, freeze: false, callback: function (r) {
						kept = r.message || [];
					} });
				});
			});
			socket.on("disconnect", function () {
				state.textContent = t("connecting");
			});
			socket.on("onedesk_remote", heard);
		};
		script.onerror = function () {
			state.textContent = t("failed");
		};
		document.head.appendChild(script);
	}

	document.querySelector("[data-one-next]").addEventListener("click", function () {
		say("go", { step: 1 });
	});
	document.querySelector("[data-one-back]").addEventListener("click", function () {
		say("go", { step: -1 });
	});

	// the pointer, from where the phone pointed when the button went down
	var aim = null;
	var last = 0;
	var heardTurn = false;

	function send(x, y, on) {
		var now = Date.now();
		if (on && now - last < EVERY) return;
		last = now;
		say("point", { x: Math.max(0, Math.min(1, x)), y: Math.max(0, Math.min(1, y)), on: on });
	}

	function turned(event) {
		if (event.alpha == null) return;
		heardTurn = true;
		if (!aim) {
			aim = { alpha: event.alpha, beta: event.beta };
			return;
		}
		var across = ((aim.alpha - event.alpha + 540) % 360) - 180;
		var down = aim.beta - event.beta;
		send(0.5 + across / WIDE, 0.5 + down / HIGH, true);
	}

	function press(event) {
		event.preventDefault();
		point.classList.add("is-on");
		aim = null;
		var ask = window.DeviceOrientationEvent && DeviceOrientationEvent.requestPermission;
		var begin = function () {
			window.addEventListener("deviceorientation", turned);
			send(0.5, 0.5, true);
			setTimeout(function () {
				if (!heardTurn) pad.hidden = false;
			}, 600);
		};
		if (ask) ask.call(DeviceOrientationEvent).then(begin, function () {
			pad.hidden = false;
		});
		else begin();
	}

	function lift() {
		point.classList.remove("is-on");
		window.removeEventListener("deviceorientation", turned);
		aim = null;
		send(0.5, 0.5, false);
	}

	point.addEventListener("pointerdown", press);
	point.addEventListener("pointerup", lift);
	point.addEventListener("pointercancel", lift);

	// a finger on the pad is the pointer, for a phone with no gyroscope
	function dragged(event) {
		var box = pad.getBoundingClientRect();
		send((event.clientX - box.left) / box.width, (event.clientY - box.top) / box.height, event.type !== "pointerup");
	}
	pad.addEventListener("pointerdown", function (event) {
		pad.setPointerCapture(event.pointerId);
		dragged(event);
	});
	pad.addEventListener("pointermove", function (event) {
		if (event.buttons) dragged(event);
	});
	pad.addEventListener("pointerup", dragged);


	connect();
})();
