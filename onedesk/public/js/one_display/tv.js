/* The TV player (www/tv.html, one_display/screens.py). Plain ES5 on purpose:
   a TV from 2017 runs Chromium 53, which has no arrow functions, no fetch and
   no let. Nothing here is bundled, so nothing may need to be. */
(function () {
	"use strict";

	var TV = window.ONE_TV || { words: {} };
	var W = TV.words;
	var API = "/api/method/onedesk.one_display.screens.";
	var KEY = "one_tv";
	var EVERY = 2000;

	var saved = load();
	var heard = null;
	var lastCommand = null;
	var lastAlert = null;
	var lastTicker = null;
	var timer = null;
	var audio = null;
	var sayQueue = [];
	var speaking = false;
	var shown = null;

	function $(id) {
		return document.getElementById(id);
	}

	function show(id, on) {
		var el = $(id);
		if (el) el.className = el.className.replace(/\s*hidden/g, "") + (on ? "" : " hidden");
	}

	function text(id, value) {
		var el = $(id);
		if (el) el.textContent = value == null ? "" : String(value);
	}

	function load() {
		try {
			return JSON.parse(window.localStorage.getItem(KEY)) || {};
		} catch (e) {
			return {};
		}
	}

	function store() {
		try {
			window.localStorage.setItem(KEY, JSON.stringify(saved));
		} catch (e) {}
	}

	function call(method, args, post, done, fail) {
		var xhr = new XMLHttpRequest();
		var body = [];
		for (var k in args) {
			if (args.hasOwnProperty(k) && args[k] != null) body.push(encodeURIComponent(k) + "=" + encodeURIComponent(args[k]));
		}
		var url = API + method + (post ? "" : "?" + body.join("&"));
		xhr.open(post ? "POST" : "GET", url, true);
		xhr.setRequestHeader("Accept", "application/json");
		if (post) xhr.setRequestHeader("Content-Type", "application/x-www-form-urlencoded");
		if (TV.csrf) xhr.setRequestHeader("X-Frappe-CSRF-Token", TV.csrf);
		xhr.timeout = 10000;
		xhr.onreadystatechange = function () {
			if (xhr.readyState !== 4) return;
			var reply = null;
			try {
				reply = JSON.parse(xhr.responseText);
			} catch (e) {}
			if (xhr.status === 200 && reply) return done(reply.message);
			if (fail) fail(xhr.status, reply);
		};
		xhr.send(post ? body.join("&") : null);
	}

	function later(fn, ms) {
		clearTimeout(timer);
		timer = setTimeout(fn, ms);
	}

	function offline(on) {
		show("offline", on);
	}

	/* Pairing: ask for a code, show it, and ask until somebody has entered it. */

	function begin() {
		if (saved.token) return poll();
		if (saved.screen && saved.secret) return waitForPair();
		call("start", { device: navigator.userAgent }, true, function (m) {
			saved = { screen: m.screen, secret: m.secret };
			store();
			showCode(m.code);
			later(waitForPair, 3000);
		}, function () {
			offline(true);
			later(begin, 15000);
		});
	}

	function showCode(code) {
		text("pair-title", W.pair);
		text("pair-how", W.how);
		text("code", code);
		pick("pair");
	}

	function waitForPair() {
		call("status", { screen: saved.screen, secret: saved.secret }, true, function (m) {
			offline(false);
			if (m.gone) {
				saved = {};
				store();
				return begin();
			}
			if (m.token) {
				saved.token = m.token;
				delete saved.secret;
				store();
				return poll();
			}
			showCode(m.code);
			later(waitForPair, 3000);
		}, function () {
			offline(true);
			later(waitForPair, 5000);
		});
	}

	/* A paired screen asks every two seconds for everything it shows. */

	function poll() {
		call("state", { screen: saved.screen, token: saved.token }, true, function (m) {
			offline(false);
			if (m.gone) {
				saved = {};
				store();
				return begin();
			}
			draw(m);
			later(poll, EVERY);
		}, function () {
			offline(true);
			later(poll, EVERY * 3);
		});
	}

	function pick(which) {
		if (shown === which) return;
		shown = which;
		show("pair", which === "pair");
		show("board", which === "board");
		show("kiosk", which === "kiosk");
	}

	function draw(m) {
		var screen = m.screen || {};
		var command = m.command || {};
		if (lastCommand !== null && command.at && command.at !== lastCommand && command.name === "reload") {
			window.location.reload();
			return;
		}
		lastCommand = command.at || "";
		brand(m.brand || {});
		show("dark", !!screen.dark);
		drawAlert(m.alert, screen);
		var channel = m.channel || {};
		drawTicker(channel.ticker);
		if (screen.mode === "Kiosk") {
			pick("kiosk");
			drawKiosk(channel, m.board);
		} else {
			pick("board");
			drawBoard(channel, m.board, screen);
		}
	}

	function brand(b) {
		text("name", b.name || "OneDisplay");
		if (b.colour) $("head").style.background = b.colour;
		var logo = $("logo");
		if (b.logo && logo.getAttribute("src") !== b.logo) logo.setAttribute("src", b.logo);
		show("logo", !!b.logo);
	}

	function drawAlert(message, screen) {
		show("alert", !!message);
		text("alert", message || "");
		if (message && message !== lastAlert && !screen.muted) {
			chime(3);
			say(message, null);
		}
		lastAlert = message || null;
	}

	function drawTicker(ticker) {
		if (ticker === lastTicker) return;
		lastTicker = ticker;
		text("ticker", ticker || "");
		show("foot", !!ticker);
	}

	function drawBoard(channel, board, screen) {
		text("serving-label", channel.headline || W.serving);
		text("waiting-label", W.waiting);
		var called = (board && board.called) || [];
		var now = $("now");
		var list = $("called");
		if (!called.length) {
			now.innerHTML = "";
			list.innerHTML = '<div class="empty"></div>';
			list.firstChild.textContent = W.nobody;
		} else {
			var first = called[0];
			var html = '<div class="now' + (heard && !heard[first.id] ? " fresh" : "") + '"><div class="t"></div><div class="c"></div></div>';
			if (now.getAttribute("data-id") !== first.id) {
				now.innerHTML = html;
				now.setAttribute("data-id", first.id);
				now.firstChild.childNodes[0].textContent = first.ticket;
				now.firstChild.childNodes[1].textContent = W.counter + " " + (first.counter || "");
			}
			list.innerHTML = "";
			for (var i = 1; i < called.length; i++) {
				var row = document.createElement("div");
				row.className = "row";
				row.innerHTML = '<div class="t"></div><div class="c"></div>';
				row.childNodes[0].textContent = called[i].ticket;
				row.childNodes[1].textContent = W.counter + " " + (called[i].counter || "");
				list.appendChild(row);
			}
		}
		drawServices((board && board.services) || []);
		announce(called, channel, screen);
	}

	function drawServices(services) {
		var box = $("services");
		box.innerHTML = "";
		for (var i = 0; i < services.length; i++) {
			var row = document.createElement("div");
			row.className = "svc";
			row.innerHTML = '<div class="p"></div><div class="n"></div><div class="w"></div>';
			row.childNodes[0].textContent = services[i].prefix;
			row.childNodes[1].textContent = services[i].service;
			row.childNodes[2].textContent = services[i].waiting;
			box.appendChild(row);
		}
	}

	/* A call the board has not seen is announced: a chime, then the voice. The
	   first answer only fills what has been heard, so a reload says nothing. */
	function announce(called, channel, screen) {
		var fresh = [];
		var now = {};
		for (var i = 0; i < called.length; i++) {
			now[called[i].id] = 1;
			if (heard && !heard[called[i].id]) fresh.unshift(called[i]);
		}
		heard = now;
		if (screen.muted || !channel.announce) return;
		for (var j = 0; j < fresh.length; j++) {
			chime(1);
			say(fresh[j].say || fresh[j].ticket, channel.language);
		}
	}

	var kioskDrawn = null;

	function drawKiosk(channel, board) {
		text("kiosk-title", channel.headline || W.take);
		var services = (board && board.services) || [];
		var key = JSON.stringify(services.map(function (s) {
			return s.service;
		}));
		if (key === kioskDrawn) return;
		kioskDrawn = key;
		var box = $("buttons");
		box.innerHTML = "";
		for (var i = 0; i < services.length; i++) {
			var b = document.createElement("button");
			b.innerHTML = "<span></span>";
			b.insertBefore(document.createTextNode(services[i].service), b.firstChild);
			b.setAttribute("data-service", services[i].service);
			b.onclick = take;
			box.appendChild(b);
		}
		document.body.style.cursor = "default";
	}

	var taking = false;

	function take(e) {
		if (taking) return;
		taking = true;
		var service = e.currentTarget.getAttribute("data-service");
		call("take", { screen: saved.screen, token: saved.token, service: service }, true, function (m) {
			taking = false;
			text("ticket-label", W.your);
			text("ticket-number", m.ticket);
			text("ticket-ahead", W.ahead.replace("{0}", m.ahead));
			show("ticket", true);
			setTimeout(function () {
				show("ticket", false);
			}, 8000);
		}, function () {
			taking = false;
			text("ticket-label", "");
			text("ticket-number", "");
			text("ticket-ahead", W.busy);
			show("ticket", true);
			setTimeout(function () {
				show("ticket", false);
			}, 4000);
		});
	}

	/* Sound. Browsers keep it off until somebody presses something, so the
	   first key or tap turns it on and the hint goes. */

	function context() {
		if (audio) return audio;
		var Ctx = window.AudioContext || window.webkitAudioContext;
		if (!Ctx) return null;
		try {
			audio = new Ctx();
		} catch (e) {
			audio = null;
		}
		return audio;
	}

	function unlock() {
		var ctx = context();
		if (ctx && ctx.state === "suspended" && ctx.resume) ctx.resume();
		if (window.speechSynthesis) {
			var hush = new SpeechSynthesisUtterance(" ");
			hush.volume = 0;
			window.speechSynthesis.speak(hush);
		}
		show("hint", false);
	}

	function chime(times) {
		var ctx = context();
		if (!ctx || ctx.state === "suspended") return;
		var notes = [880, 659];
		var t = ctx.currentTime;
		for (var r = 0; r < times; r++) {
			for (var i = 0; i < notes.length; i++) {
				var osc = ctx.createOscillator();
				var gain = ctx.createGain();
				osc.frequency.value = notes[i];
				gain.gain.setValueAtTime(0.0001, t);
				gain.gain.exponentialRampToValueAtTime(0.3, t + 0.02);
				gain.gain.exponentialRampToValueAtTime(0.0001, t + 0.5);
				osc.connect(gain);
				gain.connect(ctx.destination);
				osc.start(t);
				osc.stop(t + 0.55);
				t += 0.35;
			}
			t += 0.3;
		}
	}

	function say(words, lang) {
		if (!window.speechSynthesis || !words) return;
		sayQueue.push({ words: words, lang: lang });
		if (!speaking) next();
	}

	function next() {
		var item = sayQueue.shift();
		if (!item) {
			speaking = false;
			return;
		}
		speaking = true;
		setTimeout(function () {
			var u = new SpeechSynthesisUtterance(item.words);
			if (item.lang) u.lang = item.lang;
			u.rate = 0.9;
			u.onend = u.onerror = function () {
				setTimeout(next, 600);
			};
			window.speechSynthesis.speak(u);
		}, 900);
	}

	function tick() {
		var d = new Date();
		var h = d.getHours();
		var m = d.getMinutes();
		text("clock", (h < 10 ? "0" : "") + h + ":" + (m < 10 ? "0" : "") + m);
	}

	document.addEventListener("keydown", unlock);
	document.addEventListener("click", unlock);
	text("hint", W.sound);
	var ctx = context();
	show("hint", !ctx || ctx.state === "suspended");
	tick();
	setInterval(tick, 10000);
	begin();
})();
