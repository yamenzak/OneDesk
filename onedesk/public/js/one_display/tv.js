/* The TV player (www/tv.html, one_display/screens.py and programme.py).
   Plain ES5 on purpose: a TV from 2017 runs Chromium 53, which has no arrow
   functions, no fetch and no let. Nothing here is bundled, so nothing may
   need to be.

   The channel is drawn on its own frame (1920 by 1080 unless its Screen
   Size says otherwise) that is scaled and turned to fit the screen whole. Slides, music and ads follow one
   clock, the server's, so every screen on a channel plays the same thing at
   the same moment without talking to the others. */
(function () {
	"use strict";

	var TV = window.ONE_TV || { words: {} };
	var W = TV.words || {};
	var PREVIEW = TV.preview;
	var API = "/api/method/onedesk.one_display.screens.";
	// /radio plays a sound zone and shows nothing (programme.heard); it pairs as a screen does
	var RADIO = !!TV.radio;
	var KEY = RADIO ? "one_radio" : "one_tv";
	var KEPT = RADIO ? "one_radio_state" : "one_tv_state";
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
	// the round trip the clock was last set from: the quickest answer says the time best
	var bestTrip = Infinity;
	var bestAt = 0;
	// what this player plays for its speakers, if any: a zone's music, ads and calls
	var soundZone = null;
	var zone = 0;
	var screen = { rotate: 0, muted: 0, dark: 0 };
	var brand = {};
	var today = "";
	var dayParts = null;
	var storedAt = 0;
	var channel = null;
	var lastCommand = null;
	var lastAlert = null;
	var built = null;
	var boxes = {};
	var heard = null;
	// the backdrop as last drawn, so one with chips is drawn again only when they change
	var behind = null;
	var drawnBackdrop = "";

	/* What this page is, and why the last one ended: a reason it gave itself
	   just before reloading, or else a page reloaded inside one browser
	   session (a crash) or a new session (the set turned on). */
	var WHY = "one_tv_why";
	var BOOT = Math.random().toString(16).slice(2, 10) + Date.now().toString(16);
	var bornAt = Date.now();
	var why = "start";
	try {
		why = window.localStorage.getItem(WHY) || (window.sessionStorage.getItem(WHY) ? "unexpected" : "start");
		window.localStorage.removeItem(WHY);
		window.sessionStorage.setItem(WHY, "1");
	} catch (e) {}
	// what the page holds, sampled every half minute (weigh)
	var weight = { pictures: 0, peakAt: 0, video: null, heavy: false };
	var reportedAt = 0;

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
				var trip = Date.now() - sent;
				// keep the quickest answer's clock; let it age so a changed network is learnt again
				if (m && m.now && (trip <= bestTrip * 1.25 || Date.now() - bestAt > 600000)) {
					skew = m.now - (sent + Date.now()) / 2;
					bestTrip = Math.min(trip, Date.now() - bestAt > 600000 ? trip : bestTrip);
					bestAt = Date.now();
				}
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
		call("start", { device: navigator.userAgent, kind: RADIO ? "Radio" : "Screen" }, function (m) {
			saved = { screen: m.screen, secret: m.secret };
			store(KEY, saved);
			showCode(m.code, m.qr);
			later(waitForPair, 3000);
		}, function () {
			offline(true);
			later(begin, 15000);
		});
	}

	// the code in large figures, drawn again only when it changes, so they rise once
	var shownCode = "";
	var shownQr = "";

	function showCode(code, qr) {
		text("pair-title", W.pair);
		text("pair-how", W.how);
		text("pair-where", W.where || "");
		text("pair-host", W.host || "");
		text("pair-scan", W.scan || "");
		if (qr && qr !== shownQr) {
			shownQr = qr;
			$("pair-qr").innerHTML = qr;
		}
		if (code && code !== shownCode) {
			shownCode = code;
			var figures = $("code");
			figures.innerHTML = "";
			for (var i = 0; i < code.length; i++) {
				// the six figures read as two groups of three
				if (i === 3) figures.appendChild(el("span", "gap"));
				var one = el("span");
				one.textContent = code.charAt(i);
				one.style.webkitAnimationDelay = one.style.animationDelay = 0.15 + i * 0.06 + "s";
				figures.appendChild(one);
			}
		}
		show("pair", true);
	}

	// paired: the code leaves, a tick and the screen's name arrive, and the
	// channel, loading behind them meanwhile, is uncovered
	function linked(m) {
		var pair = $("pair");
		text("pair-done", W.done || "");
		text("pair-what", [m.name, m.plays].filter(function (one) { return one; }).join(" · "));
		pair.className = "over linking";
		setTimeout(function () { pair.className = "over linking leaving"; }, 3400);
		setTimeout(function () {
			pair.className = "over";
			show("pair", false);
			shownCode = "";
		}, 4300);
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
				linked(m);
				return poll();
			}
			showCode(m.code, m.qr);
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
		call("state", { screen: saved.screen, token: saved.token, have: channel && channel.revision, report: report() }, function (m) {
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

	/* Once a minute a screen says what it is and what it holds, which the
	   Display Screen keeps and judges (screens._heard). */

	function report() {
		if (Date.now() - reportedAt < 60000) return null;
		reportedAt = Date.now();
		var memory = window.performance && performance.memory;
		var said = {
			boot: BOOT,
			why: why,
			w: window.innerWidth,
			h: window.innerHeight,
			dpr: window.devicePixelRatio || 1,
			mem: navigator.deviceMemory || 0,
			pictures: weight.pictures,
			video: weight.video,
			ua: navigator.userAgent
		};
		if (memory && memory.jsHeapSizeLimit) {
			said.heap = memory.usedJSHeapSize;
			said.limit = memory.jsHeapSizeLimit;
		}
		return JSON.stringify(said);
	}

	/* Brakes. A browser gives no warning before it runs out of memory, so a
	   page past most of its limit reloads at the next change of slide, and
	   every page reloads once a night at the channel's quiet hour. */

	function restart(reason) {
		try {
			window.localStorage.setItem(WHY, reason);
		} catch (e) {}
		window.location.reload();
	}

	function weigh() {
		var bytes = 0;
		var i;
		var pictures = document.getElementsByTagName("img");
		for (i = 0; i < pictures.length; i++) bytes += (pictures[i].naturalWidth || 0) * (pictures[i].naturalHeight || 0) * 4;
		// the most at once in the last half hour, so a light slide does not hide a heavy one
		if (bytes >= weight.pictures || Date.now() - weight.peakAt > 1800000) {
			weight.pictures = bytes;
			weight.peakAt = Date.now();
		}
		var videos = document.getElementsByTagName("video");
		for (i = 0; i < videos.length; i++) {
			var v = videos[i];
			if (v.videoWidth && (!weight.video || v.videoWidth * v.videoHeight > weight.video[0] * weight.video[1])) weight.video = [v.videoWidth, v.videoHeight];
		}
		if (PREVIEW || Date.now() - bornAt < 600000) return;
		var memory = window.performance && performance.memory;
		weight.heavy = !!(memory && memory.jsHeapSizeLimit && memory.usedJSHeapSize > memory.jsHeapSizeLimit * 0.8);
		var slides = channel && channel.slides && channel.slides.slides;
		// with no change of slide coming, now is as calm as it gets
		if (weight.heavy && !(slides && slides.length > 1 && channel.mode === "show")) return restart("memory");
		var at = channel && channel.reload_at;
		if (at == null || Date.now() - bornAt < 3600000) return;
		var minute = (((Math.floor(now() / 60000) + zone) % 1440) + 1440) % 1440;
		if (minute >= at && minute < at + 5) restart("nightly");
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
			restart("command");
			return;
		}
		lastCommand = command.at || "";
		zone = m.zone || 0;
		screen = m.screen || screen;
		soundZone = PREVIEW ? null : m.sounds || null;
		// a video's own sound plays where the screen and the slide both say so (play.js)
		if (window.onedesk && onedesk.play) onedesk.play.loud = !!(screen.plays_sound && !screen.muted && unlocked);
		announce((soundZone && soundZone.calls) || []);
		if (RADIO) drawRadio();
		brand = m.brand || {};
		today = m.today || today;
		dayParts = m.day || dayParts;
		var next = m.channel;
		if (next && next.light && channel && channel.revision === next.revision) {
			channel.mode = next.mode;
			channel.muted = next.muted;
			channel.ads = next.ads;
			var list = (channel.layout && channel.layout.widgets) || [];
			for (var i = 0; i < list.length; i++) {
				if (next.data.hasOwnProperty(list[i].id)) list[i].data = next.data[list[i].id];
			}
			if (next.backdrop && channel.layout) channel.layout.backdrop = next.backdrop;
		} else {
			channel = next || null;
			speaks(channel);
		}
		// Kept for a power cut with no connection: whenever the channel changes
		// shape, and its rows once a minute, which an old TV's storage can bear.
		if (!PREVIEW && (!(next && next.light) || Date.now() - storedAt > 60000)) {
			storedAt = Date.now();
			store(KEPT, { channel: channel, brand: brand, zone: zone, screen: screen, today: today, day: dayParts });
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
		// the clock in the workspace's time as soon as the zone is known, not at the next drift
		if (sleeping) text("saver-clock", hhmm(local(), false));
		show("saver", sleeping);
		show("frame", !sleeping);
		if (channel.revision !== built) build();
		update();
	}

	function size() {
		if (channel && channel.width > 0 && channel.height > 0) return { w: channel.width, h: channel.height };
		// a channel kept from before screens had sizes
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
		// shown on every screen; said by whatever plays a zone, so once in every zone
		if (message && message !== lastAlert && !screen.muted && soundZone) {
			sound({ chime: 3, text: message, lang: soundZone.language });
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
		$("frame").style.background = layout.background ? onedesk.play.background(layout.background) : brand.colour || "";
		// the words and pictures a screen's editor put behind the widgets (stage 7 of docs/ONESLIDE.md)
		behind = null;
		drawnBackdrop = "";
		if (layout.backdrop) {
			behind = el("div", "w");
			behind.style.left = behind.style.top = "0";
			behind.style.width = behind.style.height = "100%";
			behind.style.zIndex = 0;
			holder.appendChild(behind);
		}
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
			// a layout of its kind, or the kind as it first was (LAYOUTS)
			var make = (LAYOUTS[one.type] || {})[(one.settings || {}).layout] || KINDS[one.type];
			if (!make) continue;
			var inset = dress(box, (one.settings || {}).look, s.w / Math.round(s.w / 2));
			sizes(box, one);
			boxes[one.id] = make(box, one, (one.w * s.w) / 100 - inset, (one.h * s.h) / 100 - inset) || {};
		}
		slide = { index: -1, total: 0 };
		if (window.onedesk && onedesk.play) onedesk.play.release($("slides"));
		$("slides").innerHTML = "";
		music.index = -1;
	}

	/* A widget is bare: what surrounds its content is its element's look, set
	   in the screen's editor (one_display/widgets.py LOOK) in the editor's
	   units, `unit` of this frame's pixels each. Says how much of the box the
	   padding and border take, which the widget sizes itself without. */

	function dress(box, look, unit) {
		if (!look) return 0;
		var px = function (value) {
			return Math.max(0, Number(value) || 0) * unit;
		};
		var colour = window.onedesk && onedesk.play ? onedesk.play.colour : function (value) { return value; };
		if (look.fillColor) box.style.background = colour(look.fillColor);
		if (look.color) box.style.color = colour(look.color);
		if (look.fontFamily) box.style.fontFamily = '"' + String(look.fontFamily).replace(/"/g, "") + '", Inter, sans-serif';
		if (look.padding) box.style.padding = px(look.padding) + "px";
		if (look.borderRadius) box.style.borderRadius = px(look.borderRadius) + "px";
		var line = look.borderStyle && look.borderStyle !== "none" ? px(look.borderWidth || 1) : 0;
		if (line) box.style.border = line + "px " + look.borderStyle + " " + (look.borderColor ? colour(look.borderColor) : "currentColor");
		if (look.shadowColor && (Number(look.shadowBlur) || Number(look.shadowOffset))) {
			var size = box.offsetWidth || 100;
			var away = (Number(look.shadowOffset) / 100) * size;
			var angle = ((Number(look.shadowAngle) || 45) * Math.PI) / 180;
			box.style.boxShadow = Math.round(away * Math.cos(angle)) + "px " + Math.round(away * Math.sin(angle)) + "px " + Math.round((Number(look.shadowBlur) / 100) * size) + "px " + colour(look.shadowColor);
			box.style.overflow = "visible";
		}
		return 2 * (px(look.padding) + line);
	}

	function update() {
		var backdrop = channel.layout && channel.layout.backdrop;
		var said = backdrop ? JSON.stringify(backdrop.elements) : "";
		if (behind && said !== drawnBackdrop) {
			drawnBackdrop = said;
			onedesk.play.draw(backdrop, behind, true);
		}
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

	function joined(video, into, started) {
		video.muted = !(video.getAttribute("data-sound") && onedesk.play.loud);
		video.addEventListener("loadedmetadata", function () {
			try {
				video.currentTime = (into / 1000) % (video.duration || 1);
			} catch (e) {}
		});
		// kept to the shared clock by speed rather than jumps, so its sound runs on
		var keeping = setInterval(function () {
			if (!video.parentNode) return clearInterval(keeping);
			if (video.readyState < 2 || !video.duration) return;
			steer(video, ((now() - started) / 1000) % video.duration);
		}, 2000);
	}

	/* In step: a player a little off its place catches up or waits by
	   playing a few percent faster or slower; only one far off jumps. */

	function steer(media, want) {
		var off = want - media.currentTime;
		if (Math.abs(off) > 2) {
			try {
				media.currentTime = want;
			} catch (e) {}
			media.playbackRate = 1;
		} else if (Math.abs(off) > 0.05) {
			media.playbackRate = 1 + Math.max(-0.05, Math.min(0.05, off * 0.1));
		} else if (media.playbackRate !== 1) {
			media.playbackRate = 1;
		}
	}

	function playSlides() {
		if (!channel || !channel.slides || channel.mode !== "show") return;
		var items = channel.slides.slides || [];
		var at = where(items, now());
		if (!at || at.index === slide.index) return;
		if (weight.heavy) return restart("memory");
		slide.index = at.index;
		var holder = $("slides");
		var item = items[at.index];
		// a presentation's slide brings its own transition; a web page takes the playlist's
		var how = item.transition || channel.slides.transition || "fade";
		var ms = item.transition_ms || 800;
		var node = el("div", how === "fade" ? "out" : how === "slide" ? "ahead" : "");
		if (how !== "none") {
			node.style.webkitTransitionDuration = ms + "ms";
			node.style.transitionDuration = ms + "ms";
		}
		if (item.kind === "Slide" && window.onedesk && onedesk.play) {
			// A presentation's slide, drawn in the page from what the server
			// cleaned (public/js/one_slide/play.js); its videos join the
			// shared clock where the slide is.
			holder.appendChild(node);
			onedesk.play.draw(item.slide, node, true);
			// a slide of another shape: whole with bands, or filling the screen when its row says so
			if (item.fill) onedesk.play.fit(node, true);
			var videos = node.getElementsByTagName("video");
			for (var v = 0; v < videos.length; v++) joined(videos[v], at.into, now() - at.into);
		} else {
			var frame = el("iframe");
			frame.setAttribute("sandbox", "allow-scripts");
			frame.src = item.src;
			node.appendChild(frame);
			holder.appendChild(node);
		}
		function gone() {
			while (holder.firstChild && holder.firstChild !== node) {
				if (window.onedesk && onedesk.play) onedesk.play.release(holder.firstChild);
				holder.removeChild(holder.firstChild);
			}
		}
		if (how === "none") {
			gone();
		} else {
			setTimeout(function () {
				node.className = "";
			}, 30);
			setTimeout(gone, ms + 200);
		}
		var next = items[(at.index + 1) % items.length];
		var ahead = next && next.slide ? next.slide.elements || [] : [];
		for (var p = 0; p < ahead.length; p++) if (ahead[p].type === "image" && ahead[p].src) new Image().src = ahead[p].src;
	}

	/* Music: the same clock, so a lobby's two screens play the same bar. */

	var music = { index: -1 };

	function playMusic() {
		var audio = $("music");
		var list = soundZone && soundZone.music ? soundZone.music.tracks : [];
		var quiet = !soundZone || screen.muted || soundZone.muted || !list.length;
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
		} else if (audio.readyState > 0) {
			steer(audio, want);
		}
		// lower under a call or an ad, and under a video playing its own sound in the zone
		audio.volume = (soundZone.music.volume / 100) * (speaking ? 0.2 : ducked() ? 0.25 : 1);
		if (audio.paused) {
			var playing = audio.play();
			if (playing && playing.catch) playing.catch(function () {});
		}
	}

	/* Ads: each has its moment; play the ones whose moment has come. */

	var played = {};

	function playAds() {
		if (!soundZone || !soundZone.ads || screen.muted || soundZone.muted) return;
		var t = now();
		for (var i = 0; i < soundZone.ads.length; i++) {
			var ad = soundZone.ads[i];
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

	var unlocked = false;

	function unlock() {
		unlocked = true;
		if (window.onedesk && onedesk.play) onedesk.play.loud = !!(screen.plays_sound && !screen.muted);
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
			if (item.pieces && item.pieces.length) {
				strung(item.pieces, done);
			} else if (item.audio) {
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

	/* A voice pack's clips said end to end (packs.py). Each clip is fetched
	   and decoded once and kept, its silence at either end cut, so A, 1, 8
	   run on as one sentence; without Web Audio they play one after another. */
	var clips = {};
	var clipsHeld = 0;

	function clip(url, then) {
		var held = clips[url];
		if (held && held.buffer) return then && then(held.buffer);
		if (held) {
			if (then) held.waiting.push(then);
			return;
		}
		// a long day's clips are let go rather than kept in a TV's memory
		if (++clipsHeld > 300) {
			clips = {};
			clipsHeld = 1;
		}
		held = clips[url] = { waiting: then ? [then] : [] };
		var ctx = context();
		var settle = function (buffer) {
			held.buffer = buffer || "none";
			var waiting = held.waiting;
			held.waiting = [];
			for (var i = 0; i < waiting.length; i++) waiting[i](held.buffer);
		};
		if (!ctx || !window.XMLHttpRequest) return settle(null);
		var xhr = new XMLHttpRequest();
		xhr.open("GET", url, true);
		xhr.responseType = "arraybuffer";
		xhr.onload = function () {
			if (xhr.status !== 200) return settle(null);
			try {
				var decoding = ctx.decodeAudioData(xhr.response, function (buffer) {
					settle(trimmed(ctx, buffer));
				}, function () {
					settle(null);
				});
				if (decoding && decoding.catch) decoding.catch(function () {});
			} catch (e) {
				settle(null);
			}
		};
		xhr.onerror = function () {
			settle(null);
		};
		xhr.send();
	}

	function trimmed(ctx, buffer) {
		var data = buffer.getChannelData(0);
		var start = 0;
		var end = data.length - 1;
		while (start < end && Math.abs(data[start]) < 0.01) start++;
		while (end > start && Math.abs(data[end]) < 0.01) end--;
		var margin = Math.floor(buffer.sampleRate * 0.04);
		start = Math.max(0, start - margin);
		end = Math.min(data.length - 1, end + margin);
		var out = ctx.createBuffer(1, end - start + 1, buffer.sampleRate);
		out.getChannelData(0).set(data.subarray(start, end + 1));
		return out;
	}

	// whether every clip of a call is decoded, starting any that are not
	function strungReady(urls) {
		var ready = true;
		for (var i = 0; i < urls.length; i++) {
			clip(urls[i]);
			if (!clips[urls[i]].buffer) ready = false;
		}
		return ready;
	}

	function strung(urls, done) {
		var ctx = context();
		var buffers = [];
		for (var i = 0; i < urls.length; i++) {
			var held = clips[urls[i]];
			if (!ctx || !held || !held.buffer || held.buffer === "none") return oneByOne(urls, 0, done);
			buffers.push(held.buffer);
		}
		var t = ctx.currentTime + 0.05;
		for (var j = 0; j < buffers.length; j++) {
			var source = ctx.createBufferSource();
			source.buffer = buffers[j];
			source.connect(ctx.destination);
			source.start(t);
			t += buffers[j].duration;
		}
		setTimeout(done, (t - ctx.currentTime) * 1000);
	}

	function oneByOne(urls, at, done) {
		if (at >= urls.length) return done();
		var voice = new Audio(urls[at]);
		var on = function () {
			voice.onended = voice.onerror = null;
			oneByOne(urls, at + 1, done);
		};
		voice.onended = voice.onerror = on;
		var playing = voice.play();
		if (playing && playing.catch) playing.catch(on);
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
		box.style.fontSize = Math.max(Math.round(px * (box.textScale || 1)), 8) + "px";
	}

	// how large a widget's words are against what fits: all of them, then its
	// main figure, its labels and its details, each a percent (widgets.LOOK)
	function partsOf(one) {
		var look = ((one || {}).settings || {}).look || {};
		function part(key) {
			var value = Number(look[key]);
			return value > 0 ? value / 100 : 1;
		}
		return { text: part("textSize"), main: part("mainSize"), label: part("labelSize"), detail: part("detailSize") };
	}

	function sizes(box, one) {
		var parts = partsOf(one);
		box.textScale = parts.text;
		if (!box.style.setProperty) return;
		box.style.setProperty("--fs-main", parts.main);
		box.style.setProperty("--fs-label", parts.label);
		box.style.setProperty("--fs-detail", parts.detail);
	}

	// a widget's highlight: its look's, or the business's colour
	function accentOf(one) {
		return (((one || {}).settings || {}).look || {}).accentColor || brand.colour || "";
	}

	function accent(one) {
		var value = accentOf(one);
		if (!value) return "var(--accent)";
		return window.onedesk && onedesk.play ? onedesk.play.colour(value) : value;
	}

	// words on the highlight: dark on a light one, white on a dark one
	function inkOn(one) {
		var hex = /^#?([0-9a-f]{6})/i.exec(accentOf(one));
		if (!hex) return "var(--on-dark)";
		var n = parseInt(hex[1], 16);
		var light = (0.299 * (n >> 16) + 0.587 * ((n >> 8) & 255) + 0.114 * (n & 255)) / 255;
		return light > 0.62 ? "var(--on-light)" : "var(--on-dark)";
	}

	function highlight(node, one) {
		node.style.background = accent(one);
		node.style.color = inkOn(one);
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

	// how long an item has been as it is, from when it became so (boards.py)
	function lasted(since) {
		if (!since) return "";
		var minutes = Math.max(0, Math.floor((now() - since) / 60000));
		if (minutes < 60) return (W.minutes || "{0} min").replace("{0}", minutes);
		return (W.hours || "{0} h {1}").replace("{0}", Math.floor(minutes / 60)).replace("{1}", pad(minutes % 60));
	}

	// a board's items in a grid, each in its state's colour (the colour is the content)
	function boardTiles(box, one, w, h) {
		var grid = el("div", "tiles");
		box.appendChild(grid);
		var last = one;
		function draw() {
			var s = last.settings || {};
			var list = rows(last);
			var count = Math.max(list.length, 1);
			var columns = s.columns > 0 ? s.columns : Math.max(1, Math.round(Math.sqrt((count * w) / Math.max(h, 1))));
			var lines = Math.ceil(count / columns);
			sized(box, Math.min(w / columns / 9, h / lines / 4.4));
			grid.innerHTML = "";
			for (var i = 0; i < list.length; i++) {
				var item = list[i];
				var tile = el("div", "tile");
				tile.style.width = 100 / columns + "%";
				tile.style.height = 100 / lines + "%";
				var inside = el("div", "tile-in" + (item.over ? " fresh" : ""));
				if (item.colour) inside.style.background = item.colour;
				inside.appendChild(el("div", "t", item.item));
				inside.appendChild(el("div", "big", item.state || item.value || ""));
				var under = [];
				if (s.value && item.state && item.value) under.push(item.value);
				if (s.time && item.since) under.push(lasted(item.since));
				inside.appendChild(el("div", "c", under.join(" · ")));
				tile.appendChild(inside);
				grid.appendChild(tile);
			}
		}
		var timer = setInterval(draw, 20000);
		return {
			update: function (fresh) {
				last = fresh;
				draw();
			},
			drop: function () {
				clearInterval(timer);
			}
		};
	}

	// one item large: a board's, or what a queue's counter serves, flashing when it changes
	function boardItem(box, one, w, h) {
		var base = Math.min(h / 4.4, w / 6);
		sized(box, base);
		// the big word as large as the box takes it, by how many letters it has
		function fitted(words) {
			var letters = Math.max(String(words || "").length, 3);
			var parts = partsOf(one);
			big.style.fontSize = Math.min(2 * parts.main, (w * 0.92) / (letters * 0.6 * base * parts.text)) + "em";
		}
		var holder = el("div", "single");
		var name = el("div", "eyebrow");
		var big = el("div", "big");
		var under = el("div", "c");
		holder.appendChild(name);
		holder.appendChild(big);
		holder.appendChild(under);
		box.appendChild(holder);
		var last = one;
		var shown = null;
		function draw() {
			var s = last.settings || {};
			var whole = last.data && last.data.whole;
			var key = "";
			big.style.color = "";
			if (whole && whole.called) {
				var at = null;
				for (var c = 0; c < whole.called.length; c++) {
					if (String(whole.called[c].counter) === String(s.item)) {
						at = whole.called[c];
						break;
					}
				}
				text(name, word("counter") + " " + (s.item || ""));
				text(big, at ? at.ticket : s.idle || "");
				fitted(at ? at.ticket : s.idle);
				text(under, "");
				key = at ? at.id : "";
			} else {
				var list = rows(last);
				var item = list[0] || null;
				for (var i = 0; i < list.length; i++) if (list[i].item === s.item) item = list[i];
				if (!item) return;
				text(name, item.item);
				text(big, item.state || item.value || "");
				fitted(item.state || item.value);
				if (item.colour) big.style.color = item.colour;
				var said = [];
				if (item.state && item.value) said.push(item.value);
				if (s.time && item.since) said.push(lasted(item.since));
				text(under, said.join(" · "));
				key = item.state + "|" + item.value;
			}
			if (shown !== null && key !== shown) {
				big.className = "big fresh";
				setTimeout(function () {
					big.className = "big";
				}, 3200);
			}
			shown = key;
		}
		var timer = setInterval(draw, 20000);
		return {
			update: function (fresh) {
				last = fresh;
				draw();
			},
			drop: function () {
				clearInterval(timer);
			}
		};
	}

	var KINDS = {
		Board: boardTiles,
		"Board Item": boardItem,
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
							highlight(card, one);
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
				},
			};
		},

		// a tile a service, its letter large, in as many columns as the box suits
		Kiosk: function (box, one, w, h) {
			var panel = el("div", "wl-kiosk");
			var heading = el("div", "wl-k-head");
			var grid = el("div", "wl-k-grid");
			panel.appendChild(heading);
			panel.appendChild(grid);
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
					var count = Math.max(services.length, 1);
					var columns = Math.max(1, Math.min(count, Math.round(Math.sqrt((count * w) / Math.max(h * 0.8, 1)))));
					var lines = Math.ceil(count / columns);
					sized(box, Math.min((h * 0.8) / lines / 4.4, w / columns / 7, h / 7));
					grid.innerHTML = "";
					for (var i = 0; i < services.length; i++) {
						var cell = el("div", "wl-cell");
						cell.style.width = 100 / columns + "%";
						cell.style.height = 100 / lines + "%";
						var b = el("button", "wl-k-tile");
						highlight(b, one);
						b.appendChild(el("span", "wl-k-letter", services[i].prefix || services[i].service.charAt(0)));
						b.appendChild(el("span", "wl-k-name", services[i].service));
						b.setAttribute("data-service", services[i].service);
						b.onclick = function (e) {
							take(one.id, e.currentTarget.getAttribute("data-service"));
						};
						cell.appendChild(b);
						grid.appendChild(cell);
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
					text(node, (rows(one)[0] || {}).text || s.text || "");
				},
			};
		},

		Clock: function (box, one, w, h) {
			// the time alone takes the room a date would have had
			sized(box, Math.min(h / ((one.settings || {}).date ? 2.4 : 1.5), w / 3.4));
			var time = el("div", "big");
			time.style.fontSize = "calc(1em * var(--fs-main, 1))";
			var date = el("div");
			date.style.fontSize = "calc(0.32em * var(--fs-detail, 1))";
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

		// now on top, then the next days side by side
		Weather: function (box, one, w, h) {
			var panel = el("div", "panel weather");
			box.appendChild(panel);
			return {
				update: function (one) {
					var said = one.data && one.data.whole;
					show(box, !!said);
					if (!said) return;
					var list = (said.days || []).slice(1, 1 + Math.max((one.settings || {}).days || 3, 0));
					sized(box, Math.min(h / 11, w / Math.max(list.length * 3.4, 9)));
					panel.innerHTML = "";
					var top = el("div", "w-now");
					var i = el("span", "icon");
					i.innerHTML = icon(said.icon);
					top.appendChild(i);
					var now = el("div");
					now.appendChild(el("div", "temp", said.temperature));
					now.appendChild(el("div", "w-cond", said.condition));
					top.appendChild(now);
					panel.appendChild(top);
					var days = el("div", "days");
					for (var d = 0; d < list.length; d++) {
						var day = el("div");
						var di = el("div");
						di.innerHTML = icon(list[d].icon);
						day.appendChild(el("div", "w-name", dayName(list[d])));
						day.appendChild(di);
						day.appendChild(el("div", "w-hi", list[d].high));
						day.appendChild(el("div", "w-lo", list[d].low));
						days.appendChild(day);
					}
					panel.appendChild(days);
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

		// the code as large as fits, its caption on up to two lines beneath
		"QR Code": function (box, one, w, h) {
			var panel = el("div", "qr");
			var code = el("div", "qr-code");
			var caption = el("div", "qr-caption");
			panel.appendChild(code);
			panel.appendChild(caption);
			box.appendChild(panel);
			return {
				update: function (one) {
					var said = String((one.settings || {}).caption || "");
					var side = Math.min(w, said ? h * 0.76 : h);
					code.style.width = code.style.height = side + "px";
					sized(box, Math.min((h * 0.24) / 2.7, (2 * w) / Math.max(said.length * 0.56, 8), 64));
					code.innerHTML = (one.data && one.data.svg) || "";
					text(caption, said);
				},
			};
		},

		Custom: function (box, one) {
			var holder = el("div", "custom");
			holder.style.height = "100%";
			var frame = el("iframe");
			frame.setAttribute("sandbox", "allow-scripts");
			var data = JSON.stringify(one.data || {}).replace(/</g, "\\u003c");
			// its words wear the look's colour and font, which a frame does not inherit
			var worn = window.getComputedStyle ? window.getComputedStyle(box) : {};
			var page = "<style>html,body{margin:0;height:100%;overflow:hidden;background:transparent;color:" + (worn.color || "inherit") +
				";font-family:" + String(worn.fontFamily || "Inter, sans-serif").replace(/[<>]/g, "") + "}</style>";
			frame.setAttribute(
				"srcdoc",
				page + "<script>window.one_display_rows=" + data + ".rows||[];window.one_display_whole=" + data + ".whole||null;" +
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

	/* Layouts: one kind drawn another way, chosen by its Layout setting
	   (widgets.py LAYOUTS). The kind's first layout is its renderer in KINDS. */

	function settingsOf(one) {
		return one.settings || {};
	}

	function whole(one) {
		return (one.data && one.data.whole) || null;
	}

	// a word as large as its box allows, by how many letters it has
	// its main figure as set, but never wider than the box
	function fitWord(node, words, width, base, most, one) {
		var parts = partsOf(one);
		var letters = Math.max(String(words || "").length, 2);
		node.style.fontSize = Math.min(most * parts.main, (width * 0.9) / (letters * 0.6 * base * parts.text)) + "em";
	}

	// the newest call at each counter, the queue's counters in their order
	function byCounter(board) {
		var latest = {};
		var called = board.called || [];
		for (var i = called.length - 1; i >= 0; i--) latest[called[i].counter] = called[i];
		var names = (board.counters || []).slice();
		for (var c = 0; c < called.length; c++) if (names.indexOf(called[c].counter) < 0 && called[c].counter) names.push(called[c].counter);
		return names.map(function (name) {
			return { counter: name, call: latest[name] || null };
		});
	}

	function queueLatest(box, one, w, h) {
		var base = Math.min(h / 6, w / 7);
		sized(box, base);
		var holder = el("div", "wl-center");
		var eyebrow = el("div", "eyebrow");
		var ticket = el("div", "wl-huge");
		var where = el("div", "wl-sub");
		holder.appendChild(eyebrow);
		holder.appendChild(ticket);
		holder.appendChild(where);
		box.appendChild(holder);
		var shown = null;
		return {
			update: function (one) {
				var board = whole(one) || { called: [] };
				var first = (board.called || [])[0];
				text(eyebrow, settingsOf(one).heading || "");
				if ((first ? first.id : "") === shown) return;
				shown = first ? first.id : "";
				text(ticket, first ? first.ticket : "—");
				fitWord(ticket, ticket.textContent, w, base, 3.2, one);
				text(where, first ? word("counter") + " " + (first.counter || "") : word("nobody"));
				holder.className = "wl-center" + (first && heard && !heard[first.id] ? " fresh" : "");
			},
		};
	}

	// one counter: its name and the ticket it is serving, for above its desk
	function queueCounter(box, one, w, h) {
		var base = Math.min(h / 6.2, w / 6.5);
		sized(box, base);
		var holder = el("div", "wl-center");
		var name = el("div", "eyebrow");
		var ticket = el("div", "wl-huge");
		var said = el("div", "wl-sub");
		holder.appendChild(name);
		holder.appendChild(ticket);
		holder.appendChild(said);
		box.appendChild(holder);
		var shown = null;
		return {
			update: function (one) {
				var s = settingsOf(one);
				var counter = String(s.counter || "");
				var list = byCounter(whole(one) || { called: [] });
				var call = null;
				for (var i = 0; i < list.length; i++) if (String(list[i].counter) === counter) call = list[i].call;
				text(name, word("counter") + " " + counter);
				text(said, call ? s.heading || "" : word("nobody"));
				if ((call ? call.id : "") === shown) return;
				shown = call ? call.id : "";
				text(ticket, call ? call.ticket : "—");
				fitWord(ticket, ticket.textContent, w, base, 3.2, one);
				holder.className = "wl-center" + (call && heard && !heard[call.id] ? " fresh" : "");
			},
		};
	}

	function queueCounters(box, one, w, h) {
		var grid = el("div", "wl-grid");
		box.appendChild(grid);
		return {
			update: function (one) {
				var board = whole(one) || { called: [] };
				var list = byCounter(board);
				var count = Math.max(list.length, 1);
				var columns = Math.max(1, Math.round(Math.sqrt((count * w) / Math.max(h, 1))));
				var lines = Math.ceil(count / columns);
				sized(box, Math.min(w / columns / 6, h / lines / 3.6));
				var newest = (board.called || [])[0];
				grid.innerHTML = "";
				for (var i = 0; i < list.length; i++) {
					var cell = el("div", "wl-cell");
					cell.style.width = 100 / columns + "%";
					cell.style.height = 100 / lines + "%";
					var inside = el("div", "wl-cell-in");
					if (newest && list[i].call && list[i].call.id === newest.id) highlight(inside, one);
					inside.appendChild(el("div", "eyebrow", word("counter") + " " + list[i].counter));
					inside.appendChild(el("div", "wl-big", list[i].call ? list[i].call.ticket : "—"));
					cell.appendChild(inside);
					grid.appendChild(cell);
				}
			},
		};
	}

	function queueList(box, one, w, h) {
		var many = Math.max(settingsOf(one).rows || 6, 1);
		sized(box, h / (many * 1.9 + 2.2));
		var head = el("div", "eyebrow");
		var list = el("div", "wl-rows");
		box.appendChild(head);
		box.appendChild(list);
		return {
			update: function (one) {
				var s = settingsOf(one);
				var called = ((whole(one) || {}).called || []).slice(0, Math.max(s.rows || 6, 1));
				text(head, s.heading || "");
				list.innerHTML = "";
				if (!called.length) list.appendChild(el("div", "wl-row", word("nobody")));
				for (var i = 0; i < called.length; i++) {
					var row = el("div", "wl-row" + (i === 0 ? " first" : ""));
					var ticket = el("div", "wl-tk", called[i].ticket);
					if (i === 0) ticket.style.color = accent(one);
					row.appendChild(ticket);
					row.appendChild(el("div", "wl-arrow", "→"));
					row.appendChild(el("div", "wl-at", word("counter") + " " + (called[i].counter || "")));
					list.appendChild(row);
				}
			},
		};
	}

	function queueWaiting(box, one, w, h) {
		var head = el("div", "eyebrow");
		var list = el("div", "wl-rows");
		box.appendChild(head);
		box.appendChild(list);
		return {
			update: function (one) {
				var services = (whole(one) || {}).services || [];
				sized(box, Math.min(h / (Math.max(services.length, 1) * 2.9 + 2), w / 10));
				text(head, word("waiting"));
				list.innerHTML = "";
				for (var i = 0; i < services.length; i++) {
					var row = el("div", "wl-row");
					var pill = el("span", "pill", services[i].prefix);
					row.appendChild(pill);
					row.appendChild(el("div", "wl-name", services[i].service));
					row.appendChild(el("div", "wl-count", services[i].waiting));
					list.appendChild(row);
				}
			},
		};
	}

	// now: the sky, the temperature, today's high and low, wind and humidity
	function weatherToday(box, one, w, h) {
		sized(box, Math.min(h / 5.8, w / 12.5));
		var holder = el("div", "wl-today");
		box.appendChild(holder);
		return {
			update: function (one) {
				var said = whole(one);
				show(box, !!said);
				if (!said) return;
				holder.innerHTML = "";
				var mark = el("div", "wl-sky");
				mark.innerHTML = icon(said.icon);
				var words = el("div");
				words.appendChild(el("div", "wl-temp", said.temperature));
				words.appendChild(el("div", "wl-cond", said.condition));
				words.appendChild(highLow(said));
				words.appendChild(el("div", "wl-more", [said.wind, said.humidity].filter(function (one) { return one; }).join("  ·  ")));
				holder.appendChild(mark);
				holder.appendChild(words);
			},
		};
	}

	function weatherHours(box, one, w, h) {
		var count = Math.max(4, Math.min(8, Math.floor(w / (h * 0.42))));
		sized(box, Math.min(h / 6.2, w / count / 3));
		var top = el("div", "wl-now");
		var line = el("div", "wl-hours");
		box.appendChild(top);
		box.appendChild(line);
		return {
			update: function (one) {
				var said = whole(one);
				show(box, !!said);
				if (!said) return;
				text(top, said.temperature + "  " + said.condition);
				line.innerHTML = "";
				var hours = (said.hours || []).slice(0, count);
				for (var i = 0; i < hours.length; i++) {
					var cell = el("div", "wl-hour");
					cell.style.width = 100 / hours.length + "%";
					cell.appendChild(el("div", "wl-when", hours[i].label));
					var sky = el("div", "wl-sky-s");
					sky.innerHTML = icon(hours[i].icon);
					cell.appendChild(sky);
					cell.appendChild(el("div", "wl-t", hours[i].temperature));
					line.appendChild(cell);
				}
			},
		};
	}

	// each day a row: its name, its sky, and its low to high drawn to the week's scale
	function weatherList(box, one, w, h) {
		var list = el("div", "wl-days");
		box.appendChild(list);
		return {
			update: function (one) {
				var said = whole(one);
				show(box, !!said);
				if (!said) return;
				var days = (said.days || []).slice(0, Math.max((settingsOf(one).days || 5) + 1, 2));
				sized(box, Math.min(h / (days.length * 1.75), w / 15.5));
				var lo = 1e9, hi = -1e9;
				for (var d = 0; d < days.length; d++) {
					lo = Math.min(lo, Number(days[d].lo));
					hi = Math.max(hi, Number(days[d].hi));
				}
				var span = Math.max(hi - lo, 1);
				list.innerHTML = "";
				for (var i = 0; i < days.length; i++) {
					var row = el("div", "wl-day");
					row.appendChild(el("div", "wl-dname", dayName(days[i])));
					var sky = el("div", "wl-sky-s");
					sky.innerHTML = icon(days[i].icon);
					row.appendChild(sky);
					row.appendChild(el("div", "wl-lo", days[i].low));
					var track = el("div", "wl-track");
					var bar = el("i");
					var from = isNaN(Number(days[i].lo)) ? 0 : (Number(days[i].lo) - lo) / span;
					var to = isNaN(Number(days[i].hi)) ? 1 : (Number(days[i].hi) - lo) / span;
					bar.style.left = from * 100 + "%";
					bar.style.width = Math.max(to - from, 0.04) * 100 + "%";
					track.appendChild(bar);
					row.appendChild(track);
					row.appendChild(el("div", "wl-hi", days[i].high));
					list.appendChild(row);
				}
			},
		};
	}

	// today's high and low, each with its arrow
	function highLow(said) {
		var line = el("div", "wl-hl");
		line.appendChild(el("span", null, "↑ " + (said.high || "")));
		line.appendChild(el("span", null, "↓ " + (said.low || "")));
		return line;
	}

	function weatherCompact(box, one, w, h) {
		sized(box, Math.min(h / 1.9, w / 7));
		var line = el("div", "wl-compact");
		box.appendChild(line);
		return {
			update: function (one) {
				var said = whole(one);
				show(box, !!said);
				if (!said) return;
				line.innerHTML = "";
				var sky = el("span", "wl-sky-s");
				sky.innerHTML = icon(said.icon);
				line.appendChild(sky);
				line.appendChild(el("span", "wl-t", said.temperature));
				if (w > h * 4) line.appendChild(el("span", "wl-cond", said.condition));
			},
		};
	}

	function weatherBig(box, one, w, h) {
		sized(box, Math.min(h / 10.6, w / 7));
		var holder = el("div", "wl-center");
		box.appendChild(holder);
		return {
			update: function (one) {
				var said = whole(one);
				show(box, !!said);
				if (!said) return;
				holder.innerHTML = "";
				var sky = el("div", "wl-sky");
				sky.innerHTML = icon(said.icon);
				holder.appendChild(sky);
				holder.appendChild(el("div", "wl-giant", String(said.temperature).replace(/[CF]$/, "")));
				holder.appendChild(el("div", "wl-cond", said.condition));
				holder.appendChild(highLow(said));
			},
		};
	}

	// a face, its hands turned as the time is; the second hand steps
	function clockAnalog(box, one, w, h) {
		var side = Math.min(w, h);
		var ns = "http://www.w3.org/2000/svg";
		var face = document.createElementNS(ns, "svg");
		face.setAttribute("viewBox", "0 0 100 100");
		face.setAttribute("class", "wl-face");
		face.style.width = face.style.height = side + "px";
		var marks = "";
		for (var i = 0; i < 60; i++) {
			var big = i % 5 === 0;
			marks += '<line x1="50" y1="' + (big ? 4 : 5) + '" x2="50" y2="' + (big ? 11 : 7.5) + '" stroke="currentColor" stroke-width="' + (big ? 2.2 : 0.8) + '" stroke-linecap="round" opacity="' + (big ? 1 : 0.45) + '" transform="rotate(' + i * 6 + ' 50 50)"/>';
		}
		face.innerHTML = marks +
			'<line class="h" x1="50" y1="54" x2="50" y2="27" stroke="currentColor" stroke-width="4.4" stroke-linecap="round"/>' +
			'<line class="m" x1="50" y1="56" x2="50" y2="15" stroke="currentColor" stroke-width="3" stroke-linecap="round"/>' +
			'<line class="s" x1="50" y1="60" x2="50" y2="12" stroke-width="1.2" stroke-linecap="round"/>' +
			'<circle cx="50" cy="50" r="2.6" fill="currentColor"/>';
		var holder = el("div", "wl-center");
		holder.appendChild(face);
		box.appendChild(holder);
		var hands = { h: face.querySelector(".h"), m: face.querySelector(".m"), s: face.querySelector(".s") };
		hands.s.setAttribute("stroke", accent(one));
		function turn(node, degrees) {
			node.setAttribute("transform", "rotate(" + degrees + " 50 50)");
		}
		function tick() {
			var d = local();
			var seconds = d.getUTCSeconds();
			var minutes = d.getUTCMinutes() + seconds / 60;
			turn(hands.h, ((d.getUTCHours() % 12) + minutes / 60) * 30);
			turn(hands.m, minutes * 6);
			turn(hands.s, seconds * 6);
		}
		tick();
		var every = setInterval(tick, 1000);
		return {
			update: function (fresh) {
				hands.s.setAttribute("stroke", accent(fresh));
			},
			drop: function () {
				clearInterval(every);
			},
		};
	}

	// a page of a calendar: the weekday, the day large, the month
	function clockDate(box, one, w, h) {
		sized(box, Math.min(h / 7, w / 6));
		var holder = el("div", "wl-center");
		var weekday = el("div", "wl-wd wl-caps");
		var day = el("div", "wl-day-n");
		var month = el("div", "wl-sub");
		holder.appendChild(weekday);
		holder.appendChild(day);
		holder.appendChild(month);
		box.appendChild(holder);
		function draw() {
			var parts = dayParts || {};
			var d = local();
			text(weekday, parts.weekday || "");
			text(day, parts.day || d.getUTCDate());
			text(month, [parts.month, parts.year].filter(function (one) { return one; }).join(" "));
		}
		draw();
		var every = setInterval(draw, 60000);
		return { update: draw, drop: function () { clearInterval(every); } };
	}

	// the time large, the weekday and date beneath it, set to one side
	function clockStacked(box, one, w, h) {
		sized(box, Math.min(h / 6.2, w / 8.6));
		var holder = el("div", "wl-stack");
		var time = el("div", "wl-time");
		var day = el("div", "wl-wd");
		var date = el("div", "wl-sub");
		holder.appendChild(time);
		holder.appendChild(day);
		holder.appendChild(date);
		box.appendChild(holder);
		var s = settingsOf(one);
		function tick() {
			var parts = dayParts || {};
			text(time, hhmm(local(), s.hours === "12"));
			text(day, parts.weekday || "");
			text(date, [parts.day, parts.month].filter(function (one) { return one; }).join(" "));
		}
		tick();
		var every = setInterval(tick, 5000);
		return { update: function (fresh) { s = settingsOf(fresh); tick(); }, drop: function () { clearInterval(every); } };
	}

	function clockMinimal(box, one, w, h) {
		sized(box, Math.min(h / 1.3, w / 3.1));
		var time = el("div", "wl-thin");
		var holder = el("div", "wl-center");
		holder.appendChild(time);
		box.appendChild(holder);
		var s = settingsOf(one);
		function tick() {
			text(time, hhmm(local(), s.hours === "12"));
		}
		tick();
		var every = setInterval(tick, 5000);
		return { update: function (fresh) { s = settingsOf(fresh); tick(); }, drop: function () { clearInterval(every); } };
	}

	// one line at a time, each held a while and crossfaded to the next
	function tickerFade(box, one, w, h) {
		sized(box, h / 2.2);
		var line = el("div", "wl-fade");
		box.appendChild(line);
		var words = [];
		var at = 0;
		function next() {
			if (!words.length) return;
			line.style.opacity = 0;
			setTimeout(function () {
				text(line, words[at % words.length]);
				line.style.fontSize = "";
				if (line.scrollWidth > line.clientWidth) line.style.fontSize = (parseFloat(window.getComputedStyle(line).fontSize) * line.clientWidth) / line.scrollWidth + "px";
				line.style.opacity = 1;
				at++;
			}, 500);
		}
		var every = setInterval(next, 6000);
		return {
			update: function (one) {
				var s = settingsOf(one);
				var fresh = rows(one).map(function (r) { return r.text; }).filter(Boolean);
				if (s.text) fresh.unshift(s.text);
				var changed = fresh.join("|") !== words.join("|");
				words = fresh;
				if (changed) { at = 0; next(); }
			},
			drop: function () { clearInterval(every); },
		};
	}

	// a label in the brand's colour, and the line running beside it
	function tickerLabelled(box, one, w, h) {
		sized(box, h / 2.2);
		var band = el("div", "wl-labelled");
		var label = el("div", "wl-label");
		var rest = el("div", "wl-rest");
		band.appendChild(label);
		band.appendChild(rest);
		box.appendChild(band);
		var inner = null;
		return {
			update: function (one) {
				text(label, settingsOf(one).label || "");
				highlight(label, one);
				inner = inner || KINDS.Ticker(rest, one, rest.offsetWidth || w * 0.8, h);
				inner.update(one);
			},
		};
	}

	// a board as a list: each item, its state's colour, its state and for how long
	function boardList(box, one, w, h) {
		var list = el("div", "wl-rows");
		box.appendChild(list);
		var last = one;
		function draw() {
			var s = settingsOf(last);
			var items = rows(last);
			sized(box, Math.min(h / (Math.max(items.length, 1) * 1.8 + 0.4), w / 18));
			list.innerHTML = "";
			for (var i = 0; i < items.length; i++) {
				var row = el("div", "wl-row");
				var dot = el("span", "wl-dot");
				dot.style.background = items[i].colour || accent(last);
				row.appendChild(dot);
				row.appendChild(el("div", "wl-name", items[i].item));
				row.appendChild(el("div", "wl-state", items[i].state || items[i].value || ""));
				if (s.time) row.appendChild(el("div", "wl-since", lasted(items[i].since)));
				list.appendChild(row);
			}
		}
		var timer = setInterval(draw, 20000);
		return { update: function (fresh) { last = fresh; draw(); }, drop: function () { clearInterval(timer); } };
	}

	// how many items are in each state, in the state's colour
	function boardSummary(box, one, w, h) {
		var grid = el("div", "wl-grid");
		box.appendChild(grid);
		return {
			update: function (one) {
				var states = [];
				var counts = {};
				var colours = {};
				var items = rows(one);
				for (var i = 0; i < items.length; i++) {
					var state = items[i].state || items[i].value || "";
					if (!(state in counts)) { states.push(state); counts[state] = 0; colours[state] = items[i].colour; }
					counts[state]++;
				}
				var count = Math.max(states.length, 1);
				sized(box, Math.min(w / count / 4.6, h / 5.4));
				grid.innerHTML = "";
				for (var s = 0; s < states.length; s++) {
					var cell = el("div", "wl-cell");
					cell.style.width = 100 / count + "%";
					cell.style.height = "100%";
					var inside = el("div", "wl-cell-in");
					var figure = el("div", "wl-huge", counts[states[s]]);
					figure.style.color = colours[states[s]] || accent(one);
					inside.appendChild(figure);
					inside.appendChild(el("div", "wl-sub", states[s]));
					cell.appendChild(inside);
					grid.appendChild(cell);
				}
			},
		};
	}

	// the code beside its caption, for a wide band
	function qrSide(box, one, w, h) {
		sized(box, Math.min(h / 4, w / 12));
		var holder = el("div", "wl-side");
		var code = el("div", "wl-code");
		code.style.width = code.style.height = h + "px";
		var caption = el("div", "wl-caption");
		holder.appendChild(code);
		holder.appendChild(caption);
		box.appendChild(holder);
		return {
			update: function (one) {
				code.innerHTML = (one.data && one.data.svg) || "";
				text(caption, settingsOf(one).caption || "");
			},
		};
	}

	// a row a service: its letter, its name, how many are waiting
	function kioskList(box, one, w, h) {
		var panel = el("div", "wl-kiosk");
		var heading = el("div", "wl-k-head");
		var list = el("div", "wl-k-rows");
		panel.appendChild(heading);
		panel.appendChild(list);
		box.appendChild(panel);
		document.body.style.cursor = "default";
		return {
			update: function (one) {
				var services = (whole(one) || {}).services || [];
				sized(box, Math.min(h / (Math.max(services.length, 1) * 2.6 + 2.6), w / 17));
				text(heading, settingsOf(one).heading || "");
				list.innerHTML = "";
				for (var i = 0; i < services.length; i++) {
					var row = el("button", "wl-k-row");
					var letter = el("span", "wl-k-pre", services[i].prefix || services[i].service.charAt(0));
					highlight(letter, one);
					row.appendChild(letter);
					row.appendChild(el("span", "wl-name", services[i].service));
					row.appendChild(el("span", "wl-k-wait", services[i].waiting ? word("queued").replace("{0}", services[i].waiting) : ""));
					row.appendChild(el("span", "wl-k-go", document.documentElement.dir === "rtl" ? "‹" : "›"));
					row.setAttribute("data-service", services[i].service);
					row.onclick = function (e) {
						take(one.id, e.currentTarget.getAttribute("data-service"));
					};
					list.appendChild(row);
				}
			},
		};
	}

	// rows typed one a line, their parts split by "|"
	function lines(words) {
		var out = [];
		var all = String(words || "").split("\n");
		for (var i = 0; i < all.length; i++) {
			if (!all[i].replace(/\s/g, "")) continue;
			out.push(all[i].split("|").map(function (part) { return part.replace(/^\s+|\s+$/g, ""); }));
		}
		return out;
	}

	function minutesOf(words) {
		var found = /(\d{1,2})[:.](\d{2})/.exec(words || "");
		return found ? Number(found[1]) * 60 + Number(found[2]) : null;
	}

	function minutesNow() {
		var d = local();
		return d.getUTCHours() * 60 + d.getUTCMinutes();
	}

	// the session on now: the last that has started
	function onNow(rows) {
		var at = minutesNow();
		var current = -1;
		for (var i = 0; i < rows.length; i++) {
			var start = minutesOf(rows[i][0]);
			if (start !== null && start <= at) current = i;
		}
		return current;
	}

	// a day's sessions: what is on now marked, what is over faded, what is next said
	function scheduleList(box, one, w, h) {
		var list = el("div", "wl-sched");
		box.appendChild(list);
		var s = settingsOf(one);
		function draw() {
			var rows = lines(s.rows);
			sized(box, Math.min(h / (Math.max(rows.length, 1) * 2.4 + 0.4), w / 15));
			var current = onNow(rows);
			list.innerHTML = "";
			for (var i = 0; i < rows.length; i++) {
				var row = el("div", "wl-s-row" + (i < current ? " past" : ""));
				var time = el("div", "wl-s-time", rows[i][0]);
				time.style.color = accent(one);
				row.appendChild(time);
				var body = el("div", "wl-s-body");
				body.appendChild(el("div", "wl-s-what", rows[i][1] || ""));
				if (rows[i][2]) body.appendChild(el("div", "wl-s-where", rows[i][2]));
				row.appendChild(body);
				if (i === current || i === current + 1) {
					var tag = el("span", "wl-s-tag", word(i === current ? "now" : "next"));
					if (i === current) highlight(tag, one);
					row.appendChild(tag);
				}
				if (i === current) row.className += " now";
				list.appendChild(row);
			}
		}
		draw();
		var timer = setInterval(draw, 30000);
		return { update: function (fresh) { s = settingsOf(fresh); draw(); }, drop: function () { clearInterval(timer); } };
	}

	// only what is on now, large, and what comes after it
	function scheduleNext(box, one, w, h) {
		sized(box, Math.min(h / 7.6, w / 12));
		var holder = el("div", "wl-stack");
		box.appendChild(holder);
		var s = settingsOf(one);
		function part(label, row, large) {
			holder.appendChild(el("div", "eyebrow", label));
			holder.appendChild(el("div", large ? "wl-s-big" : "wl-s-what", row ? row[1] || "" : "—"));
			if (row) holder.appendChild(el("div", "wl-sub", [row[0], row[2]].filter(function (one) { return one; }).join("  ·  ")));
		}
		function draw() {
			var rows = lines(s.rows);
			var current = onNow(rows);
			holder.innerHTML = "";
			part(word("now"), rows[current] || null, true);
			var gap = el("div", "wl-s-gap");
			holder.appendChild(gap);
			part(word("next"), rows[current + 1] || null, false);
		}
		draw();
		var timer = setInterval(draw, 30000);
		return { update: function (fresh) { s = settingsOf(fresh); draw(); }, drop: function () { clearInterval(timer); } };
	}

	// whether a day's hours, such as "09:00 – 18:00", hold this minute
	function openAt(hours, at) {
		var times = String(hours || "").match(/\d{1,2}[:.]\d{2}/g) || [];
		if (times.length < 2) return false;
		var from = minutesOf(times[0]);
		var to = minutesOf(times[1]);
		return to > from ? at >= from && at < to : at >= from || at < to;
	}

	// the week's hours, Monday first, today marked, and whether it is open now
	function openingWeek(box, one, w, h) {
		var holder = el("div", "wl-open");
		box.appendChild(holder);
		var s = settingsOf(one);
		function draw() {
			var rows = lines(s.rows);
			sized(box, Math.min(h / (Math.max(rows.length, 1) * 1.7 + 2.6), w / 14));
			var today = (local().getUTCDay() + 6) % 7;
			var open = rows[today] && openAt(rows[today][1], minutesNow());
			holder.innerHTML = "";
			var state = el("span", "wl-o-state", word(open ? "open" : "closed"));
			if (open) highlight(state, one);
			holder.appendChild(state);
			for (var i = 0; i < rows.length; i++) {
				var row = el("div", "wl-o-row" + (i === today ? " today" : ""));
				row.appendChild(el("div", "wl-o-day", rows[i][0]));
				row.appendChild(el("div", "wl-o-time", rows[i][1] || ""));
				if (i === today) row.style.borderColor = accent(one);
				holder.appendChild(row);
			}
		}
		draw();
		var timer = setInterval(draw, 60000);
		return { update: function (fresh) { s = settingsOf(fresh); draw(); }, drop: function () { clearInterval(timer); } };
	}

	// only today: open or closed, large, and today's hours
	function openingToday(box, one, w, h) {
		sized(box, Math.min(h / 5, w / 8));
		var holder = el("div", "wl-center");
		box.appendChild(holder);
		var s = settingsOf(one);
		function draw() {
			var rows = lines(s.rows);
			var today = (local().getUTCDay() + 6) % 7;
			var row = rows[today] || [];
			var open = openAt(row[1], minutesNow());
			holder.innerHTML = "";
			var state = el("div", "wl-big", word(open ? "open" : "closed"));
			state.style.color = open ? accent(one) : "";
			holder.appendChild(state);
			holder.appendChild(el("div", "wl-sub", [row[0], row[1]].filter(function (one) { return one; }).join("  ·  ")));
		}
		draw();
		var timer = setInterval(draw, 60000);
		return { update: function (fresh) { s = settingsOf(fresh); draw(); }, drop: function () { clearInterval(timer); } };
	}

	// a code that joins the Wi-Fi, beside the network and its password
	// a code a phone joins the network from, the network and password beside it,
	// or under it in a box taller than it is wide
	function qrWifi(box, one, w, h) {
		var stacked = w < h * 1.3;
		var side = stacked ? Math.min(w * 0.8, h * 0.55) : Math.min(h, w * 0.42);
		sized(box, stacked ? Math.min((h - side) / 5.4, w / 10) : Math.min(h / 6.4, (w - side) / 13));
		var holder = el("div", stacked ? "wl-center" : "wl-side");
		var code = el("div", "wl-code");
		code.style.width = code.style.height = side + "px";
		code.style.webkitFlexShrink = code.style.flexShrink = "0";
		var words = el("div", stacked ? "wl-wifi top" : "wl-wifi");
		holder.appendChild(code);
		holder.appendChild(words);
		box.appendChild(holder);
		return {
			update: function (one) {
				var s = settingsOf(one);
				code.innerHTML = (one.data && one.data.svg) || "";
				words.innerHTML = "";
				words.appendChild(el("div", "eyebrow", word("network")));
				words.appendChild(el("div", "wl-w-value", s.network || ""));
				if (s.password) {
					words.appendChild(el("div", "eyebrow", word("password")));
					words.appendChild(el("div", "wl-w-value", s.password));
				}
			},
		};
	}

	KINDS.Schedule = scheduleList;
	KINDS["Opening Hours"] = openingWeek;

	var LAYOUTS = {
		"Queue Board": { latest: queueLatest, counter: queueCounter, counters: queueCounters, list: queueList, waiting: queueWaiting },
		Weather: { today: weatherToday, hours: weatherHours, list: weatherList, compact: weatherCompact, big: weatherBig },
		Clock: { analog: clockAnalog, date: clockDate, stacked: clockStacked, minimal: clockMinimal },
		Ticker: { fade: tickerFade, labelled: tickerLabelled },
		Board: { list: boardList, summary: boardSummary },
		"QR Code": { side: qrSide, wifi: qrWifi },
		Schedule: { next: scheduleNext },
		"Opening Hours": { today: openingToday },
		Kiosk: { list: kioskList },
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
		if (!soundZone || !soundZone.announce || screen.muted || soundZone.muted || PREVIEW) {
			pending = {};
			return;
		}
		for (i = 0; i < fresh.length; i++) {
			pending[fresh[i].id] = fresh[i].start || now();
			if (fresh[i].pieces && fresh[i].pieces.length) strungReady(fresh[i].pieces);
		}
		calling(called);
	}

	// every player in a zone starts a call at the one moment the server set,
	// with its recording if it has come, else in the player's own voice
	function calling(called) {
		var waits = false;
		for (var i = 0; i < called.length; i++) {
			var one = called[i];
			if (!pending[one.id]) continue;
			if (now() < pending[one.id]) {
				waits = true;
				continue;
			}
			var joined = one.pieces && one.pieces.length && strungReady(one.pieces);
			if (one.audio || joined || now() > pending[one.id] + 4000) {
				delete pending[one.id];
				sound({ chime: 1, audio: one.audio, pieces: joined ? one.pieces : null, text: one.say || one.ticket, lang: soundZone.language });
			} else {
				waits = true;
			}
		}
		if (waits) {
			clearTimeout(callTimer);
			callTimer = setTimeout(function () {
				calling((soundZone && soundZone.calls) || []);
			}, 250);
		}
	}

	/* A call waits a few seconds for OneAI's recording of it, which is made
	   the first time a screen shows the call, before the screen's own voice
	   says it instead. */
	var pending = {};
	var callTimer = null;

	// whether a screen in this zone is playing a video's own sound now, from
	// its playlist's fixed timing (programme.duck)
	function ducked() {
		var lists = (soundZone && soundZone.duck) || [];
		for (var i = 0; i < lists.length; i++) {
			var at = where(lists[i], now());
			if (at && lists[i][at.index].sound) return true;
		}
		return false;
	}

	// a radio shows only what it plays and where
	function drawRadio() {
		show("frame", false);
		show("radio", true);
		text("radio-zone", soundZone ? soundZone.name : "");
		var tracks = soundZone && soundZone.music ? soundZone.music.tracks : [];
		var at = tracks.length ? where(tracks, now()) : null;
		text("radio-now", at ? tracks[at.index].title || "" : W.silent || "");
		$("radio").className = "over" + (at && !soundZone.muted ? "" : " silent");
	}

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
			dayParts = kept.day || null;
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
	setInterval(weigh, 30000);
	saver();
	begin();
})();
