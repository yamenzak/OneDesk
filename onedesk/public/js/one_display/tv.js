/* The TV player (www/tv.html, one_display/screens.py and programme.py).
   Plain ES5 on purpose: a TV from 2017 runs Chromium 53, which has no arrow
   functions, no fetch and no let. Nothing here is bundled, so nothing may
   need to be.

   The channel is drawn on a frame of 1920 by 1080 (or 1080 by 1920) that is
   scaled and turned to fit the screen whole. Slides, music and ads follow one
   clock, the server's, so every screen on a channel plays the same thing at
   the same moment without talking to the others. */
(function () {
	"use strict";

	var TV = window.ONE_TV || { words: {} };
	var W = TV.words || {};
	var PREVIEW = TV.preview;
	var API = "/api/method/onedesk.one_display.screens.";
	var KEY = "one_tv";
	var KEPT = "one_tv_state";
	var EVERY = 2000;
	// While the socket is live a screen is woken by every change, so it asks
	// on its own only to catch what changes without one: a source's records.
	var EVERY_LIVE = 15000;

	var saved = PREVIEW ? {} : load(KEY);
	var timer = null;
	var live = false;
	var asking = false;
	var woken = false;
	var listening = false;
	var skew = 0;
	var zone = 0;
	var screen = { rotate: 0, muted: 0, dark: 0 };
	var brand = {};
	var today = "";
	var storedAt = 0;
	var channel = null;
	var lastCommand = null;
	var lastAlert = null;
	var built = null;
	var boxes = {};
	var heard = null;

	function $(id) {
		return document.getElementById(id);
	}

	function show(id, on) {
		var el = typeof id === "string" ? $(id) : id;
		if (!el) return;
		el.className = el.className.replace(/\s*hidden/g, "") + (on ? "" : " hidden");
	}

	function text(id, value) {
		var el = typeof id === "string" ? $(id) : id;
		if (el) el.textContent = value == null ? "" : String(value);
	}

	// The page reads in its channel's language and direction once it has
	// one, whatever its browser asked for.
	function speaks(said) {
		var lang = (said && said.language) || "";
		if (!lang) return;
		document.documentElement.lang = lang;
		document.documentElement.dir = /^(ar|he|fa|ur)\b/.test(lang) ? "rtl" : "ltr";
	}

	// A channel's own words win over the page's, so a screen speaks its
	// channel's language whatever its browser asked for.
	function word(key) {
		return (channel && channel.words && channel.words[key]) || W[key] || "";
	}

	function el(tag, cls, words) {
		var node = document.createElement(tag);
		if (cls) node.className = cls;
		if (words != null) node.textContent = String(words);
		return node;
	}

	function load(key) {
		try {
			return JSON.parse(window.localStorage.getItem(key)) || {};
		} catch (e) {
			return {};
		}
	}

	function store(key, value) {
		try {
			window.localStorage.setItem(key, JSON.stringify(value));
		} catch (e) {}
	}

	function now() {
		return Date.now() + skew;
	}

	function call(method, args, done, fail) {
		var xhr = new XMLHttpRequest();
		var body = [];
		for (var k in args) {
			if (args.hasOwnProperty(k) && args[k] != null) body.push(encodeURIComponent(k) + "=" + encodeURIComponent(args[k]));
		}
		var sent = Date.now();
		xhr.open("POST", API + method, true);
		xhr.setRequestHeader("Accept", "application/json");
		xhr.setRequestHeader("Content-Type", "application/x-www-form-urlencoded");
		if (TV.csrf) xhr.setRequestHeader("X-Frappe-CSRF-Token", TV.csrf);
		xhr.timeout = 10000;
		xhr.onreadystatechange = function () {
			if (xhr.readyState !== 4) return;
			var reply = null;
			try {
				reply = JSON.parse(xhr.responseText);
			} catch (e) {}
			if (xhr.status === 200 && reply) {
				var m = reply.message;
				if (m && m.now) skew = m.now - (sent + Date.now()) / 2;
				return done(m);
			}
			if (fail) fail(xhr.status, reply);
		};
		xhr.send(body.join("&"));
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
		if (PREVIEW) return preview();
		if (saved.token) return poll();
		if (saved.screen && saved.secret) return waitForPair();
		call("start", { device: navigator.userAgent }, function (m) {
			saved = { screen: m.screen, secret: m.secret };
			store(KEY, saved);
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
		show("pair", true);
	}

	function waitForPair() {
		call("status", { screen: saved.screen, secret: saved.secret }, function (m) {
			offline(false);
			if (m.gone) {
				saved = {};
				store(KEY, saved);
				return begin();
			}
			if (m.token) {
				saved.token = m.token;
				delete saved.secret;
				store(KEY, saved);
				show("pair", false);
				return poll();
			}
			showCode(m.code);
			later(waitForPair, 3000);
		}, function () {
			offline(true);
			later(waitForPair, 5000);
		});
	}

	/* A paired screen asks every two seconds. Once it has a channel's shape it
	   says so, and is sent only what changed: the rows, the ads, the mode. */

	function poll() {
		asking = true;
		woken = false;
		call("state", { screen: saved.screen, token: saved.token, have: channel && channel.revision }, function (m) {
			asking = false;
			offline(false);
			if (m.gone) {
				saved = {};
				store(KEY, saved);
				store(KEPT, {});
				return begin();
			}
			apply(m);
			listen();
			later(poll, woken ? 0 : live ? EVERY_LIVE : EVERY);
		}, function () {
			asking = false;
			offline(true);
			later(poll, EVERY * 3);
		});
	}

	/* The socket only wakes a screen to ask now (one_display/live.py). A
	   hundred screens woken at once spread their asking over half a second. */

	function wake() {
		if (!saved.token) return;
		if (asking) {
			woken = true;
			return;
		}
		later(poll, Math.floor(Math.random() * 500));
	}

	function listen() {
		var where = TV.socket;
		if (listening || PREVIEW || !where || !where.site) return;
		listening = true;
		var base = where.port ? location.protocol + "//" + location.hostname + ":" + where.port : location.origin;
		var script = document.createElement("script");
		script.src = base + "/socket.io/socket.io.js";
		script.onload = function () {
			if (!window.io) return;
			var socket = window.io(base + "/" + where.site, { withCredentials: true });
			socket.on("connect", function () {
				socket.emit("onedesk_display_join", saved.screen, saved.token, function (said) {
					live = !!(said && said.ok);
				});
			});
			socket.on("disconnect", function () {
				live = false;
			});
			socket.on("onedesk_display_wake", wake);
		};
		document.head.appendChild(script);
	}

	function preview() {
		call("preview", { channel: PREVIEW.channel, collection: PREVIEW.collection }, function (m) {
			apply(m);
			later(preview, EVERY * 2);
		}, function () {
			later(preview, EVERY * 5);
		});
	}

	function apply(m) {
		var command = m.command || {};
		if (lastCommand !== null && command.at && command.at !== lastCommand && command.name === "reload") {
			window.location.reload();
			return;
		}
		lastCommand = command.at || "";
		zone = m.zone || 0;
		screen = m.screen || screen;
		brand = m.brand || {};
		today = m.today || today;
		var next = m.channel;
		if (next && next.light && channel && channel.revision === next.revision) {
			channel.mode = next.mode;
			channel.muted = next.muted;
			channel.ads = next.ads;
			var list = (channel.layout && channel.layout.widgets) || [];
			for (var i = 0; i < list.length; i++) {
				if (next.data.hasOwnProperty(list[i].id)) list[i].data = next.data[list[i].id];
			}
		} else {
			channel = next || null;
			speaks(channel);
		}
		// Kept for a power cut with no connection: whenever the channel changes
		// shape, and its rows once a minute, which an old TV's storage can bear.
		if (!PREVIEW && (!(next && next.light) || Date.now() - storedAt > 60000)) {
			storedAt = Date.now();
			store(KEPT, { channel: channel, brand: brand, zone: zone, screen: screen, today: today });
		}
		draw(m.alert);
	}

	/* Drawing: the frame, then what is over it. */

	function draw(alert) {
		show("dark", !!screen.dark || (channel && channel.mode === "off"));
		drawAlert(alert);
		fit();
		if (!channel) {
			show("frame", false);
			return;
		}
		var sleeping = channel.mode === "screensaver";
		show("saver", sleeping);
		show("frame", !sleeping);
		if (channel.revision !== built) build();
		update();
	}

	function size() {
		var portrait = channel && channel.orientation === "portrait";
		return portrait ? { w: 1080, h: 1920 } : { w: 1920, h: 1080 };
	}

	function fit() {
		var frame = $("frame");
		var s = size();
		var turn = (screen.rotate || 0) % 360;
		var vw = window.innerWidth;
		var vh = window.innerHeight;
		var sideways = turn === 90 || turn === 270;
		var scale = Math.min((sideways ? vh : vw) / s.w, (sideways ? vw : vh) / s.h);
		var dw = s.w * scale;
		var dh = s.h * scale;
		var x = ((sideways ? vh : vw) - dw) / 2;
		var y = ((sideways ? vw : vh) - dh) / 2;
		var t;
		if (turn === 90) t = "translate(" + (vw - y) + "px," + x + "px) rotate(90deg)";
		else if (turn === 180) t = "translate(" + (vw - x) + "px," + (vh - y) + "px) rotate(180deg)";
		else if (turn === 270) t = "translate(" + y + "px," + (vh - x) + "px) rotate(270deg)";
		else t = "translate(" + x + "px," + y + "px)";
		t += " scale(" + scale + ")";
		frame.style.width = s.w + "px";
		frame.style.height = s.h + "px";
		frame.style.webkitTransform = t;
		frame.style.transform = t;
	}

	function drawAlert(message) {
		show("alert", !!message);
		text("alert", message || "");
		if (message && message !== lastAlert && !screen.muted) {
			sound({ chime: 3, text: message, lang: channel && channel.language });
		}
		lastAlert = message || null;
	}

	/* Build when the shape changes: the slides restart from the shared clock
	   and every widget gets a fresh box. */

	function build() {
		built = channel.revision;
		var holder = $("widgets");
		for (var id in boxes) {
			if (boxes.hasOwnProperty(id) && boxes[id].drop) boxes[id].drop();
		}
		holder.innerHTML = "";
		boxes = {};
		var s = size();
		var layout = channel.layout || { widgets: [] };
		$("frame").style.background = layout.background || brand.colour || "";
		var list = layout.widgets || [];
		for (var i = 0; i < list.length; i++) {
			var one = list[i];
			var box = el("div", "w");
			box.style.left = one.x + "%";
			box.style.top = one.y + "%";
			box.style.width = one.w + "%";
			box.style.height = one.h + "%";
			box.style.zIndex = one.layer || 1;
			holder.appendChild(box);
			var make = KINDS[one.type];
			if (!make) continue;
			boxes[one.id] = make(box, one, (one.w * s.w) / 100, (one.h * s.h) / 100) || {};
		}
		slide = { index: -1, total: 0 };
		$("slides").innerHTML = "";
		music.index = -1;
	}

	function update() {
		var list = (channel.layout && channel.layout.widgets) || [];
		for (var i = 0; i < list.length; i++) {
			var box = boxes[list[i].id];
			if (box && box.update) box.update(list[i]);
		}
	}

	/* Slides: where the playlist is now is the shared time mod its length. */

	var slide = { index: -1, total: 0 };

	function where(items, at) {
		var total = 0;
		var i;
		for (i = 0; i < items.length; i++) total += items[i].ms;
		if (!total) return null;
		var pos = at % total;
		for (i = 0; i < items.length; i++) {
			if (pos < items[i].ms) return { index: i, into: pos, total: total };
			pos -= items[i].ms;
		}
		return null;
	}

	function playSlides() {
		if (!channel || !channel.slides || channel.mode !== "show") return;
		var items = channel.slides.slides || [];
		var at = where(items, now());
		if (!at || at.index === slide.index) return;
		slide.index = at.index;
		var holder = $("slides");
		var item = items[at.index];
		var node = el("div", channel.slides.transition === "fade" ? "out" : "");
		if (item.kind === "Image") {
			var img = el("img", item.fit === "contain" ? "contain" : "cover");
			img.src = item.src;
			node.appendChild(img);
		} else if (item.kind === "Video") {
			var video = el("video", item.fit === "contain" ? "contain" : "cover");
			video.muted = true;
			video.setAttribute("muted", "");
			video.setAttribute("playsinline", "");
			video.autoplay = true;
			video.loop = true;
			video.src = item.src;
			video.addEventListener("loadedmetadata", function () {
				try {
					video.currentTime = (at.into / 1000) % (video.duration || 1);
				} catch (e) {}
			});
			node.appendChild(video);
		} else if (item.design && window.onedesk && onedesk.blocks) {
			// A designed slide is drawn from its blocks, in the page itself:
			// every value was checked by the server and its text is escaped.
			node.innerHTML = onedesk.blocks.slide(item.design, item.qrs);
		} else {
			var frame = el("iframe");
			frame.setAttribute("sandbox", "allow-scripts");
			if (item.kind === "Web Page") frame.src = item.src;
			else frame.setAttribute("srcdoc", item.html || "");
			node.appendChild(frame);
		}
		holder.appendChild(node);
		setTimeout(function () {
			node.className = "";
		}, 30);
		setTimeout(function () {
			while (holder.firstChild && holder.firstChild !== node) holder.removeChild(holder.firstChild);
		}, 1000);
		var next = items[(at.index + 1) % items.length];
		if (next && next.kind === "Image") new Image().src = next.src;
	}

	/* Music: the same clock, so a lobby's two screens play the same bar. */

	var music = { index: -1 };

	function playMusic() {
		var audio = $("music");
		var list = channel && channel.mode === "show" && channel.music ? channel.music.tracks : [];
		var quiet = !channel || screen.muted || channel.muted || !list.length;
		if (quiet) {
			if (!audio.paused) audio.pause();
			music.index = -1;
			return;
		}
		var at = where(list, now());
		if (!at) return;
		var want = at.into / 1000;
		if (at.index !== music.index) {
			music.index = at.index;
			audio.src = list[at.index].src;
			audio.addEventListener("loadedmetadata", function seek() {
				audio.removeEventListener("loadedmetadata", seek);
				try {
					var at = where(list, now());
					if (at) audio.currentTime = at.into / 1000;
				} catch (e) {}
			});
		} else if (Math.abs(audio.currentTime - want) > 0.6 && audio.readyState > 0) {
			try {
				audio.currentTime = want;
			} catch (e) {}
		}
		audio.volume = (channel.music.volume / 100) * (speaking ? 0.2 : 1);
		if (audio.paused) {
			var playing = audio.play();
			if (playing && playing.catch) playing.catch(function () {});
		}
	}

	/* Ads: each has its moment; play the ones whose moment has come. */

	var played = {};

	function playAds() {
		if (!channel || !channel.ads || screen.muted || channel.muted || channel.mode !== "show") return;
		var t = now();
		for (var i = 0; i < channel.ads.length; i++) {
			var ad = channel.ads[i];
			if (played[ad.key] || t < ad.at || t - ad.at > 20000) continue;
			played[ad.key] = 1;
			sound({ chime: ad.chime ? 1 : 0, audio: ad.audio, text: ad.text, lang: ad.lang });
		}
	}

	/* Sound: one queue for calls, ads and alerts, so nothing talks over
	   anything. Browsers keep sound off until somebody presses something. */

	var audioContext = null;
	var queue = [];
	var speaking = false;

	function context() {
		if (audioContext) return audioContext;
		var Ctx = window.AudioContext || window.webkitAudioContext;
		if (!Ctx) return null;
		try {
			audioContext = new Ctx();
		} catch (e) {
			audioContext = null;
		}
		return audioContext;
	}

	function unlock() {
		var ctx = context();
		if (ctx && ctx.state === "suspended" && ctx.resume) ctx.resume();
		if (window.speechSynthesis) {
			var hush = new SpeechSynthesisUtterance(" ");
			hush.volume = 0;
			window.speechSynthesis.speak(hush);
		}
		var audio = $("music");
		if (audio.paused && audio.src) {
			var playing = audio.play();
			if (playing && playing.catch) playing.catch(function () {});
		}
		show("hint", false);
	}

	function chime(times, then) {
		var ctx = context();
		if (!ctx || ctx.state === "suspended" || !times) return then();
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
		setTimeout(then, (t - ctx.currentTime) * 1000 + 200);
	}

	function sound(item) {
		queue.push(item);
		if (!speaking) next();
	}

	function next() {
		var item = queue.shift();
		if (!item) {
			speaking = false;
			return;
		}
		speaking = true;
		chime(item.chime || 0, function () {
			var done = function () {
				setTimeout(next, 600);
			};
			if (item.audio) {
				var voice = new Audio(item.audio);
				voice.onended = voice.onerror = done;
				var playing = voice.play();
				if (playing && playing.catch) playing.catch(done);
			} else if (window.speechSynthesis && item.text) {
				var u = new SpeechSynthesisUtterance(item.text);
				if (item.lang) u.lang = item.lang;
				u.rate = 0.9;
				u.onend = u.onerror = done;
				window.speechSynthesis.speak(u);
			} else {
				done();
			}
		});
	}

	/* The workspace's own time: the server's clock in its time zone. */

	function local() {
		return new Date(now() + zone * 60000);
	}

	function pad(n) {
		return (n < 10 ? "0" : "") + n;
	}

	function hhmm(d, twelve) {
		var h = d.getUTCHours();
		if (twelve) h = h % 12 || 12;
		return pad(h) + ":" + pad(d.getUTCMinutes());
	}

	function dateLine(d) {
		return today || d.toUTCString().slice(0, 11);
	}

	/* Widgets. Each draws into its box once and is told its data again on
	   every answer; words are sized in em from the box's own height. */

	function sized(box, px) {
		box.style.fontSize = Math.max(Math.round(px), 8) + "px";
	}

	function accent() {
		return brand.colour || "var(--accent)";
	}

	var ICONS = {
		sun: '<circle cx="12" cy="12" r="4"/><path d="M12 2v2M12 20v2M4.9 4.9l1.4 1.4M17.7 17.7l1.4 1.4M2 12h2M20 12h2M4.9 19.1l1.4-1.4M17.7 6.3l1.4-1.4"/>',
		"cloud-sun": '<path d="M12 2v2M4.9 4.9l1.4 1.4M20 12h2M19.1 4.9l-1.4 1.4M15.9 13a4 4 0 0 0-5.6-3.7"/><path d="M13 22H7a5 5 0 1 1 4.9-6H13a3 3 0 0 1 0 6z"/>',
		cloud: '<path d="M17.5 19H9a7 7 0 1 1 6.7-9h1.8a4.5 4.5 0 1 1 0 9z"/>',
		"cloud-fog": '<path d="M4 14.9A7 7 0 1 1 15.7 8h1.8a4.5 4.5 0 0 1 2.5 8.2M16 17H7M17 21H9"/>',
		"cloud-drizzle": '<path d="M4 14.9A7 7 0 1 1 15.7 8h1.8a4.5 4.5 0 0 1 2.5 8.2M8 19v1M8 14v1M16 19v1M16 14v1M12 21v1M12 16v1"/>',
		"cloud-rain": '<path d="M4 14.9A7 7 0 1 1 15.7 8h1.8a4.5 4.5 0 0 1 2.5 8.2M16 14v6M8 14v6M12 16v6"/>',
		"cloud-snow": '<path d="M4 14.9A7 7 0 1 1 15.7 8h1.8a4.5 4.5 0 0 1 2.5 8.2M8 15h.01M8 19h.01M12 17h.01M12 21h.01M16 15h.01M16 19h.01"/>',
		"cloud-lightning": '<path d="M6 16.3A7 7 0 1 1 15.7 8h1.8a4.5 4.5 0 0 1 .5 9M13 11l-4 6h6l-4 6"/>',
	};

	function icon(name) {
		return '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.6" stroke-linecap="round" stroke-linejoin="round">' + (ICONS[name] || ICONS.cloud) + "</svg>";
	}

	function rows(one) {
		return (one.data && one.data.rows) || [];
	}

	var KINDS = {
		"Queue Board": function (box, one, w, h) {
			var r = Math.max((one.settings || {}).rows || 6, 1);
			sized(box, h / (9 + r * 1.9 + ((one.settings || {}).waiting ? 6 : 0)));
			var panel = el("div", "panel");
			var eyebrow = el("div", "eyebrow");
			var current = el("div");
			var list = el("div");
			var waitLabel = el("div", "eyebrow", word("waiting"));
			waitLabel.style.marginTop = "1em";
			var waiting = el("div");
			panel.appendChild(eyebrow);
			panel.appendChild(current);
			panel.appendChild(list);
			panel.appendChild(waitLabel);
			panel.appendChild(waiting);
			box.appendChild(panel);
			return {
				update: function (one) {
					var s = one.settings || {};
					var board = (one.data && one.data.whole) || { called: [], services: [] };
					var called = (board.called || []).slice(0, Math.max(s.rows || 6, 1));
					text(eyebrow, s.heading || "");
					var first = called[0];
					if (current.getAttribute("data-id") !== (first ? first.id : "")) {
						current.innerHTML = "";
						current.setAttribute("data-id", first ? first.id : "");
						if (first) {
							var card = el("div", "now" + (heard && !heard[first.id] ? " fresh" : ""));
							card.style.background = accent();
							card.appendChild(el("div", "t", first.ticket));
							card.appendChild(el("div", "c", word("counter") + " " + (first.counter || "")));
							current.appendChild(card);
						} else {
							current.appendChild(el("div", "row", word("nobody")));
						}
					}
					list.innerHTML = "";
					for (var i = 1; i < called.length; i++) {
						var row = el("div", "row");
						row.style.fontSize = "1.4em";
						var ticket = el("div", "big", called[i].ticket);
						ticket.style.minWidth = "3.2em";
						row.appendChild(ticket);
						var counter = el("div", "c", word("counter") + " " + (called[i].counter || ""));
						counter.style.marginLeft = "auto";
						row.appendChild(counter);
						list.appendChild(row);
					}
					show(waitLabel, !!s.waiting);
					show(waiting, !!s.waiting);
					waiting.innerHTML = "";
					var services = board.services || [];
					for (var j = 0; j < services.length; j++) {
						var line = el("div", "row");
						line.appendChild(el("span", "pill", services[j].prefix));
						line.appendChild(el("div", "t", services[j].service));
						line.appendChild(el("div", "c big", services[j].waiting));
						waiting.appendChild(line);
					}
					announce(board.called || []);
				},
			};
		},

		Kiosk: function (box, one, w, h) {
			sized(box, h / 9);
			var panel = el("div", "kiosk");
			var heading = el("h1");
			var buttons = el("div");
			panel.appendChild(heading);
			panel.appendChild(buttons);
			box.appendChild(panel);
			var drawn = null;
			document.body.style.cursor = "default";
			return {
				update: function (one) {
					text(heading, (one.settings || {}).heading || "");
					var services = ((one.data && one.data.whole) || {}).services || [];
					var key = services.map(function (s) {
						return s.service;
					}).join("|");
					if (key === drawn) return;
					drawn = key;
					buttons.innerHTML = "";
					for (var i = 0; i < services.length; i++) {
						var b = el("button", null, services[i].service);
						b.style.background = accent();
						b.setAttribute("data-service", services[i].service);
						b.onclick = function (e) {
							take(one.id, e.currentTarget.getAttribute("data-service"));
						};
						buttons.appendChild(b);
					}
				},
			};
		},

		Ticker: function (box, one, w, h) {
			sized(box, h);
			var band = el("div", "ticker");
			var line = el("span");
			band.appendChild(line);
			box.appendChild(band);
			var said = null;
			var rtl = document.documentElement.dir === "rtl";
			return {
				update: function (one) {
					var s = one.settings || {};
					var words = rows(one).map(function (r) {
						return r.text;
					}).filter(Boolean);
					if (s.text) words.unshift(s.text);
					var joined = words.join("     •     ");
					if (joined === said) return;
					said = joined;
					line.textContent = joined;
					var across = (line.offsetWidth + w) / Math.max(w / Math.max(s.speed || 30, 5), 20);
					var name = "tick" + one.id.replace(/\W/g, "");
					var from = rtl ? -line.offsetWidth : w;
					var to = rtl ? w : -line.offsetWidth;
					var css = "@keyframes " + name + "{from{transform:translateX(" + from + "px)}to{transform:translateX(" + to + "px)}}" +
						"@-webkit-keyframes " + name + "{from{-webkit-transform:translateX(" + from + "px)}to{-webkit-transform:translateX(" + to + "px)}}";
					var style = el("style");
					style.textContent = css;
					band.appendChild(style);
					line.style.webkitAnimation = name + " " + across + "s linear infinite";
					line.style.animation = name + " " + across + "s linear infinite";
				},
			};
		},

		Text: function (box, one, w, h) {
			var node = el("div");
			node.style.height = "100%";
			node.style.display = "flex";
			node.style.alignItems = "center";
			box.appendChild(node);
			return {
				update: function (one) {
					var s = one.settings || {};
					sized(box, ((s.size || 5) / 100) * (size().h));
					node.style.justifyContent = s.align === "center" ? "center" : s.align === "end" ? "flex-end" : "flex-start";
					node.style.textAlign = s.align || "start";
					node.style.color = s.colour || "";
					text(node, (rows(one)[0] || {}).text || s.text || "");
				},
			};
		},

		Clock: function (box, one, w, h) {
			sized(box, h / 2.4);
			var time = el("div", "big");
			var date = el("div");
			date.style.fontSize = "0.32em";
			date.style.opacity = "0.8";
			date.style.marginTop = "0.2em";
			box.appendChild(time);
			box.appendChild(date);
			var s = one.settings || {};
			var tick = function () {
				var d = local();
				text(time, hhmm(d, s.hours === "12"));
				text(date, s.date ? dateLine(d) : "");
			};
			tick();
			var every = setInterval(tick, 5000);
			return {
				update: function (one) {
					s = one.settings || {};
					tick();
				},
				drop: function () {
					clearInterval(every);
				},
			};
		},

		Weather: function (box, one, w, h) {
			sized(box, h / 8);
			var panel = el("div", "panel weather");
			box.appendChild(panel);
			return {
				update: function (one) {
					var said = one.data && one.data.whole;
					show(box, !!said);
					if (!said) return;
					panel.innerHTML = "";
					var top = el("div");
					var i = el("span", "icon");
					i.innerHTML = icon(said.icon);
					top.appendChild(i);
					top.appendChild(el("span", "temp", " " + said.temperature));
					panel.appendChild(top);
					panel.appendChild(el("div", null, said.condition));
					var days = el("div", "days");
					var list = (said.days || []).slice(1, 1 + Math.max((one.settings || {}).days || 3, 0));
					for (var d = 0; d < list.length; d++) {
						var day = el("div");
						var di = el("div");
						di.innerHTML = icon(list[d].icon);
						day.appendChild(el("div", null, dayName(list[d])));
						day.appendChild(di);
						day.appendChild(el("div", null, list[d].high + " / " + list[d].low));
						days.appendChild(day);
					}
					panel.appendChild(days);
				},
			};
		},

		List: function (box, one, w, h) {
			var s = one.settings || {};
			sized(box, h / ((s.rows || 6) * 1.9 + 3));
			var panel = el("div", "panel");
			var heading = el("div", "eyebrow");
			var list = el("div");
			panel.appendChild(heading);
			panel.appendChild(list);
			box.appendChild(panel);
			return {
				update: function (one) {
					var s = one.settings || {};
					text(heading, s.heading || "");
					show(heading, !!s.heading);
					list.innerHTML = "";
					var all = rows(one).slice(0, s.rows || 6);
					for (var i = 0; i < all.length; i++) {
						var row = el("div", "row");
						if (all[i].image) {
							var img = el("img");
							img.src = all[i].image;
							row.appendChild(img);
						}
						var t = el("div", "t", all[i].title || "");
						if (all[i].subtitle) t.appendChild(el("span", "sub", all[i].subtitle));
						row.appendChild(t);
						if (all[i].value) row.appendChild(el("div", "c big", all[i].value));
						list.appendChild(row);
					}
					// A row is shown whole or not at all: rows with a second line are
					// taller than the size was worked out for.
					var room = box.clientHeight - (parseFloat(window.getComputedStyle(panel).paddingBottom) || 0);
					while (list.childNodes.length > 1 && list.lastChild.offsetTop + list.lastChild.offsetHeight > room) {
						list.removeChild(list.lastChild);
					}
				},
			};
		},

		Number: function (box, one, w, h) {
			sized(box, Math.min(h / 4, w / 6));
			var panel = el("div", "panel");
			var value = el("div", "big");
			value.style.fontSize = "1.8em";
			var label = el("div");
			label.style.fontSize = "0.5em";
			label.style.opacity = "0.8";
			label.style.marginTop = "0.3em";
			panel.appendChild(value);
			panel.appendChild(label);
			box.appendChild(panel);
			return {
				update: function (one) {
					var first = rows(one)[0] || {};
					text(value, first.value || "0");
					text(label, first.label || (one.settings || {}).label || "");
				},
			};
		},

		Image: function (box, one) {
			var img = el("img");
			img.style.width = "100%";
			img.style.height = "100%";
			box.appendChild(img);
			return {
				update: function (one) {
					var s = one.settings || {};
					var src = (rows(one)[0] || {}).image || s.image || "";
					img.className = s.fit === "cover" ? "cover" : "contain";
					if (img.getAttribute("src") !== src) img.setAttribute("src", src);
					show(img, !!src);
				},
			};
		},

		"QR Code": function (box, one, w, h) {
			sized(box, h / 10);
			var panel = el("div", "qr");
			var code = el("div");
			code.style.height = "85%";
			var caption = el("div");
			panel.appendChild(code);
			panel.appendChild(caption);
			box.appendChild(panel);
			return {
				update: function (one) {
					code.innerHTML = (one.data && one.data.svg) || "";
					text(caption, (one.settings || {}).caption || "");
				},
			};
		},

		Custom: function (box, one) {
			var holder = el("div", "custom");
			holder.style.height = "100%";
			var frame = el("iframe");
			frame.setAttribute("sandbox", "allow-scripts");
			var data = JSON.stringify(one.data || {}).replace(/</g, "\\u003c");
			frame.setAttribute(
				"srcdoc",
				"<script>window.one_display_rows=" + data + ".rows||[];window.one_display_whole=" + data + ".whole||null;" +
					"window.addEventListener('message',function(e){if(e.data&&e.data.one_display){window.one_display_rows=e.data.rows||[];" +
					"window.one_display_whole=e.data.whole||null;if(window.one_display_changed)window.one_display_changed();}});<\/script>" +
					((one.settings || {}).html || "")
			);
			holder.appendChild(frame);
			box.appendChild(holder);
			return {
				update: function (one) {
					try {
						frame.contentWindow.postMessage({ one_display: 1, rows: (one.data || {}).rows || [], whole: (one.data || {}).whole || null }, "*");
					} catch (e) {}
				},
			};
		},
	};

	function dayName(one) {
		return one.label || String(one.date || "").slice(5);
	}

	/* A call the board has not seen is announced: a chime, then the voice.
	   The first answer only fills what has been heard, so a reload says
	   nothing. */
	function announce(called) {
		var fresh = [];
		var seen = {};
		var i;
		for (i = 0; i < called.length; i++) {
			seen[called[i].id] = 1;
			if (heard && !heard[called[i].id]) fresh.unshift(called[i]);
		}
		heard = seen;
		if (!channel || !channel.announce || screen.muted || channel.muted || PREVIEW) {
			pending = {};
			return;
		}
		for (i = 0; i < fresh.length; i++) pending[fresh[i].id] = Date.now() + 4000;
		for (i = 0; i < called.length; i++) {
			var call = called[i];
			if (!pending[call.id]) continue;
			if (call.audio || Date.now() > pending[call.id]) {
				delete pending[call.id];
				sound({ chime: 1, audio: call.audio, text: call.say || call.ticket, lang: channel.language });
			}
		}
	}

	/* A call waits a few seconds for OneAI's recording of it, which is made
	   the first time a screen shows the call, before the screen's own voice
	   says it instead. */
	var pending = {};

	var taking = false;

	function take(widget, service) {
		if (taking || PREVIEW) return;
		taking = true;
		call("take", { screen: saved.screen, token: saved.token, widget: widget, service: service }, function (m) {
			taking = false;
			text("ticket-label", word("your"));
			text("ticket-number", m.ticket);
			text("ticket-ahead", word("ahead").replace("{0}", m.ahead));
			show("ticket", true);
			setTimeout(function () {
				show("ticket", false);
			}, 8000);
		}, function () {
			taking = false;
			text("ticket-label", "");
			text("ticket-number", "");
			text("ticket-ahead", word("busy"));
			show("ticket", true);
			setTimeout(function () {
				show("ticket", false);
			}, 4000);
		});
	}

	/* The screensaver keeps the time and the logo moving, so nothing burns
	   into an old panel. */

	function saver() {
		var drift = $("drift");
		text("saver-clock", hhmm(local(), false));
		var logo = $("saver-logo");
		if (brand.logo && logo.getAttribute("src") !== brand.logo) logo.setAttribute("src", brand.logo);
		show(logo, !!brand.logo);
		drift.style.left = Math.round(Math.random() * 60 + 5) + "%";
		drift.style.top = Math.round(Math.random() * 60 + 5) + "%";
	}

	function tick() {
		try {
			playSlides();
			playMusic();
			playAds();
		} catch (e) {}
	}

	/* Offline: the page and its script come from the service worker's cache,
	   and the last answer from this browser, so a screen restarted with no
	   network plays what it had. */

	function offlineStart() {
		var kept = load(KEPT);
		if (kept && kept.channel) {
			zone = kept.zone || 0;
			brand = kept.brand || {};
			today = kept.today || "";
			screen = kept.screen || screen;
			channel = kept.channel;
			speaks(channel);
			draw(null);
		}
	}

	if ("serviceWorker" in navigator && !PREVIEW) {
		try {
			navigator.serviceWorker.register("/tv-worker.js", { scope: "/tv" }).catch(function () {});
		} catch (e) {}
	}

	document.addEventListener("keydown", unlock);
	document.addEventListener("click", unlock);
	window.addEventListener("resize", fit);
	text("hint", W.sound);
	var ctx = context();
	show("hint", !PREVIEW && (!ctx || ctx.state === "suspended"));
	if (PREVIEW && PREVIEW.embed) show("status", false);
	if (!PREVIEW && saved.token) offlineStart();
	setInterval(tick, 250);
	setInterval(saver, 30000);
	saver();
	begin();
})();
