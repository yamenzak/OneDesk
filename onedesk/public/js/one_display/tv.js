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
			var make = KINDS[one.type];
			if (!make) continue;
			var inset = dress(box, (one.settings || {}).look, s.w / Math.round(s.w / 2));
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
			onedesk.play.draw(backdrop, behind);
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
			onedesk.play.draw(item.slide, node);
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
			big.style.fontSize = Math.min(2, (w * 0.92) / (letters * 0.6 * base)) + "em";
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
		if (!soundZone || !soundZone.announce || screen.muted || soundZone.muted || PREVIEW) {
			pending = {};
			return;
		}
		for (i = 0; i < fresh.length; i++) pending[fresh[i].id] = fresh[i].start || now();
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
			if (one.audio || now() > pending[one.id] + 4000) {
				delete pending[one.id];
				sound({ chime: 1, audio: one.audio, text: one.say || one.ticket, lang: soundZone.language });
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
