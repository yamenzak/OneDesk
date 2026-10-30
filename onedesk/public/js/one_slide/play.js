/* A slide of a presentation, drawn for a screen (docs/ONESLIDE.md, stage 5).

   The screen is a 2017 TV running Chromium 53, which cannot run the editor,
   so this draws Suite's stored slide again in ES5: no let, no arrow
   functions, no template strings, no 8-digit colours. `slide` answers the
   slide as HTML on a 960 by 540 stage, or the frame a screen's backdrop
   gives (stage 7); the caller scales it to the screen.

   What arrives was cleaned by the server (one_slide/play.py): text is
   sanitised HTML and free CSS holds only what css.json allows. Everything
   else - numbers, colours, addresses - is checked again here, and every
   attribute is escaped, so a slide can only ever draw itself. The shapes
   follow the editor's (frontend/src/slide/components/ShapeElement.vue and
   utils/shapeGeometry.js, Suite's with our star and block arrow). */
(function (root) {
	"use strict";

	var WIDE = 960;
	var HIGH = 540;
	var STYLE = "one-play-style";
	var HEX = /#([0-9a-fA-F]{8}|[0-9a-fA-F]{6}|[0-9a-fA-F]{4}|[0-9a-fA-F]{3})\b/g;
	var COLOUR = /^(#[0-9a-fA-F]{3,8}|transparent|rgba?\([\d\s.,%]+\))$/;
	var FADE = /^linear-gradient\((-?\d+)deg, ([^,]+), ([^,]+)\)$/;
	var SAFE = /^(\/files\/|\/assets\/|\/api\/method\/onedesk\.one_slide\.api\.shown\?|https:\/\/|data:image\/)/;
	var counter = 0;
	// one_slide/motion.json, which the editor reads too (a test keeps them one)
	var MOTION = /* motion */ {"in":{"Fade":{"opacity":0},"Fly In":{"fly":1},"Zoom":{"opacity":0,"scale":0.5},"Rise":{"opacity":0,"y":8}},"out":{"Fade":{"opacity":0},"Fly Out":{"fly":1},"Zoom":{"opacity":0,"scale":0.5},"Sink":{"opacity":0,"y":8}},"from":{"Left":[-100,0],"Right":[100,0],"Top":[0,-100],"Bottom":[0,100]},"start":["With the Slide","On Click"],"speed":0.6,"longest":600} /* end motion */;

	function esc(text) {
		return String(text == null ? "" : text)
			.replace(/&/g, "&amp;")
			.replace(/</g, "&lt;")
			.replace(/>/g, "&gt;")
			.replace(/"/g, "&quot;")
			.replace(/'/g, "&#39;");
	}

	function num(value, otherwise) {
		var said = Number(value);
		return isFinite(said) ? Math.round(said * 100) / 100 : otherwise || 0;
	}

	// #rrggbbaa and #rgba as rgba(), which an old browser reads
	function rgba(hex) {
		var digits = hex.charAt(0) === "#" ? hex.slice(1) : hex;
		if (digits.length === 3 || digits.length === 4) {
			digits = digits.replace(/(.)/g, "$1$1");
		}
		var r = parseInt(digits.slice(0, 2), 16);
		var g = parseInt(digits.slice(2, 4), 16);
		var b = parseInt(digits.slice(4, 6), 16);
		if (digits.length === 6) return "rgb(" + r + "," + g + "," + b + ")";
		return "rgba(" + r + "," + g + "," + b + "," + Math.round((parseInt(digits.slice(6, 8), 16) / 255) * 1000) / 1000 + ")";
	}

	function old(text) {
		return String(text || "").replace(HEX, function (found) {
			return rgba(found);
		});
	}

	function colour(value, otherwise) {
		var said = String(value || "").replace(/\s+/g, " ");
		return COLOUR.test(said) ? old(said) : otherwise || "transparent";
	}

	function source(value) {
		var said = String(value || "");
		return SAFE.test(said) && said.indexOf('"') < 0 ? said : "";
	}

	function background(value) {
		var said = String(value || "");
		var fade = FADE.exec(said);
		if (fade) return "linear-gradient(" + num(fade[1]) + "deg, " + colour(fade[2]) + ", " + colour(fade[3]) + ")";
		return colour(said, "#fff");
	}

	// the element's own box, its blur and its free CSS
	function box(element, turn) {
		var looks = [
			"position:absolute",
			"left:" + num(element.left) + "px",
			"top:" + num(element.top) + "px",
			"z-index:" + Math.max(1, Math.round(num(element.zIndex, 1)))
		];
		if (element.width != null) looks.push("width:" + num(element.width) + "px");
		if (element.height != null && element.type !== "text") looks.push("height:" + num(element.height) + "px");
		if (turn) looks.push(turn);
		var css = old(element.css || "").replace(/[<>"]/g, "");
		if (css) looks.push(css);
		var blur = num(element.blur);
		if (blur > 0) looks.push("-webkit-filter:blur(" + blur + "px)", "filter:blur(" + blur + "px)");
		return looks.join(";");
	}

	function rotated(element) {
		var rotation = num(element.rotation);
		return rotation ? "transform:rotate(" + rotation + "deg);transform-origin:center center" : "";
	}

	function shadow(element) {
		if (!element.shadowColor || !(num(element.shadowBlur) || num(element.shadowOffset))) return "";
		var size = num(element.width, 1);
		var distance = (num(element.shadowOffset) / 100) * size;
		var angle = (num(element.shadowAngle, 45) * Math.PI) / 180;
		var tint = colour(String(element.shadowColor).slice(0, 7), "rgb(0,0,0)").replace(/^rgb\((.*)\)$/, "rgba($1," + num(element.shadowOpacity, 100) / 100 + ")");
		return Math.round(distance * Math.cos(angle)) + "px " + Math.round(distance * Math.sin(angle)) + "px " + Math.round((num(element.shadowBlur) / 100) * size) + "px " + tint;
	}

	function text(element) {
		var transform = String(element.transform || "none");
		var origin = /^[\w\s.%-]*$/.test(element.transformOrigin || "") ? element.transformOrigin || "top left" : "top left";
		var turn = /^[\w\s(),.%-]*$/.test(transform) && transform !== "none" ? "transform:" + transform + ";-webkit-transform:" + transform + ";transform-origin:" + origin : "";
		var wrap = element.width != null ? "white-space:pre-wrap;word-wrap:break-word" : "white-space:pre";
		var line = num(element.lineHeight, 1.5);
		// a box set one way runs that way; else each paragraph runs the way its first letter does
		var dir = element.dir === "rtl" || element.dir === "ltr" ? ' dir="' + element.dir + '"' : "";
		return '<div class="one-text" style="' + esc(box(element, turn)) + ";opacity:" + num(element.opacity, 100) / 100 + '"' + dir + '><div style="' + wrap + ";line-height:" + line + '">' + old(element.content) + "</div></div>";
	}

	// Suite's regular polygons, and our star and block arrow, on the box
	var SIDES = { diamond: 4, triangle: 3, pentagon: 5 };
	var DRAWN = {
		star: (function () {
			var points = [];
			for (var k = 0; k < 10; k++) {
				var angle = -Math.PI / 2 + (k * Math.PI) / 5;
				var radius = k % 2 ? 0.4 : 1;
				points.push({ x: radius * Math.cos(angle), y: radius * Math.sin(angle) });
			}
			return points;
		})(),
		blockArrow: [
			{ x: 0, y: 0.3 }, { x: 0.6, y: 0.3 }, { x: 0.6, y: 0 }, { x: 1, y: 0.5 },
			{ x: 0.6, y: 1 }, { x: 0.6, y: 0.7 }, { x: 0, y: 0.7 }
		]
	};

	function vertices(kind, width, height, inset) {
		var unit = DRAWN[kind];
		var i;
		if (!unit) {
			unit = [];
			for (i = 0; i < SIDES[kind]; i++) {
				var angle = -Math.PI / 2 + (i * 2 * Math.PI) / SIDES[kind];
				unit.push({ x: Math.cos(angle), y: Math.sin(angle) });
			}
		}
		var xs = unit.map(function (v) { return v.x; });
		var ys = unit.map(function (v) { return v.y; });
		var x0 = Math.min.apply(null, xs);
		var x1 = Math.max.apply(null, xs);
		var y0 = Math.min.apply(null, ys);
		var y1 = Math.max.apply(null, ys);
		return unit
			.map(function (v) {
				return num(inset + ((v.x - x0) / (x1 - x0)) * (width - 2 * inset)) + "," + num(inset + ((v.y - y0) / (y1 - y0)) * (height - 2 * inset));
			})
			.join(" ");
	}

	function head(kind, size, at, back, ink) {
		if (!kind || kind === "none") return "";
		var h = size * 0.8;
		var dx = at.x - back.x;
		var dy = at.y - back.y;
		var turn = (Math.atan2(dy, dx) * 180) / Math.PI;
		var where = 'transform="translate(' + num(at.x) + "," + num(at.y) + ") rotate(" + num(turn) + ')"';
		if (kind === "arrow") return "<path " + where + ' d="M' + -size + "," + -h / 2 + " L0,0 L" + -size + "," + h / 2 + '" fill="none" stroke="' + ink + '" stroke-linecap="round" stroke-linejoin="round"/>';
		return "<path " + where + ' d="M' + -size + "," + -h / 2 + " L0,0 L" + -size + "," + h / 2 + ' Z" fill="' + ink + '"/>';
	}

	function shape(element) {
		var width = num(element.width, 1);
		var stroke = Math.max(0, num(element.strokeWidth));
		var height = element.shapeType === "line" && !element.points ? stroke : num(element.height, 1);
		var ink = esc(colour(element.strokeColor));
		var id = "f" + counter++;
		var fill = esc(colour(element.fillColor));
		var defs = "";
		if (element.fade && element.fade.to && element.shapeType !== "line") {
			var radians = ((num(element.fade.angle, 180) - 90) * Math.PI) / 180;
			var x = Math.cos(radians) / 2;
			var y = Math.sin(radians) / 2;
			defs = '<defs><linearGradient id="' + id + '" x1="' + num(0.5 - x) + '" y1="' + num(0.5 - y) + '" x2="' + num(0.5 + x) + '" y2="' + num(0.5 + y) + '"><stop offset="0" stop-color="' + fill + '"/><stop offset="1" stop-color="' + esc(colour(element.fade.to)) + '"/></linearGradient></defs>';
			fill = "url(#" + id + ")";
		}
		var dash = element.strokeStyle === "dashed" ? stroke * 3 + " " + stroke * 2 : element.strokeStyle === "dotted" ? stroke + " " + stroke * 1.5 : "";
		var lines = ' stroke="' + ink + '" stroke-width="' + stroke + '"' + (dash ? ' stroke-dasharray="' + dash + '"' : "") + (element.strokeStyle === "dotted" ? ' stroke-linecap="round"' : "");
		var drawn = "";
		var kind = element.shapeType;
		var size = 8 + stroke * 2.5;
		if (kind === "rectangle") {
			var r = num(element.borderRadius);
			drawn = '<rect x="' + stroke / 2 + '" y="' + stroke / 2 + '" width="' + Math.max(0, width - stroke) + '" height="' + Math.max(0, height - stroke) + '" rx="' + r + '" ry="' + r + '" fill="' + fill + '"' + lines + "/>";
		} else if (kind === "oval") {
			drawn = '<ellipse cx="' + width / 2 + '" cy="' + height / 2 + '" rx="' + Math.max(0, width / 2 - stroke / 2) + '" ry="' + Math.max(0, height / 2 - stroke / 2) + '" fill="' + fill + '"' + lines + "/>";
		} else if (SIDES[kind] || DRAWN[kind]) {
			drawn = '<polygon points="' + vertices(kind, width, height, stroke / 2) + '" fill="' + fill + '"' + lines + "/>";
		} else if (kind === "line" && element.points && element.points.length > 1) {
			var path = element.points.map(function (p, i) { return (i ? "L" : "M") + num(p.x) + " " + num(p.y); }).join(" ");
			var last = element.points.length - 1;
			drawn = '<path d="' + path + '" fill="none" stroke-linejoin="round"' + lines + "/>" +
				head(element.markerEnd, size, element.points[last], element.points[last - 1], ink) +
				head(element.markerStart, size, element.points[0], element.points[1], ink);
		} else if (kind === "line") {
			var mid = stroke / 2;
			drawn = '<line x1="0" y1="' + mid + '" x2="' + width + '" y2="' + mid + '"' + lines + "/>" +
				head(element.markerEnd, size, { x: width, y: mid }, { x: 0, y: mid }, ink) +
				head(element.markerStart, size, { x: 0, y: mid }, { x: width, y: mid }, ink);
		}
		var cast = shadow(element);
		var svg = '<svg xmlns="http://www.w3.org/2000/svg" width="' + width + '" height="' + height + '" style="overflow:visible;opacity:' + num(element.opacity, 100) / 100 + (cast ? ";-webkit-filter:drop-shadow(" + cast + ");filter:drop-shadow(" + cast + ")" : "") + '">' + defs + drawn + "</svg>";
		var words = element.content && kind !== "line" ? '<div class="one-shape-text">' + old(element.content) + "</div>" : "";
		return '<div style="' + esc(box(element, rotated(element))) + '">' + svg + words + "</div>";
	}

	function picture(element) {
		var src = source(element.src);
		if (!src) return "";
		var crop = element.crop;
		var place = "position:absolute;left:0;top:0;width:100%;height:100%;object-fit:cover";
		if (crop && num(crop.width) > 0 && num(crop.height) > 0) {
			var w = 100 / num(crop.width);
			var h = 100 / num(crop.height);
			place = "position:absolute;max-width:none;left:" + num(-num(crop.x) * w) + "%;top:" + num(-num(crop.y) * h) + "%;width:" + num(w) + "%;height:" + num(h) + "%";
		}
		var frame = [
			"position:relative;width:100%;height:100%;overflow:hidden",
			"opacity:" + num(element.opacity, 100) / 100,
			"border-radius:" + num(element.borderRadius) + "px",
			"border:" + num(element.borderWidth) + "px " + (/^(solid|dashed|dotted)$/.test(element.borderStyle) ? element.borderStyle : "none") + " " + colour(element.borderColor, "transparent"),
			"box-sizing:border-box"
		];
		var cast = shadow(element);
		if (cast) frame.push("box-shadow:" + cast);
		if (element.invertX === -1 || element.invertY === -1) frame.push("transform:scale(" + (element.invertX || 1) + "," + (element.invertY || 1) + ")");
		return '<div style="' + esc(box(element, rotated(element))) + '"><div style="' + esc(frame.join(";")) + '"><img src="' + esc(src) + '" style="' + place + '"></div></div>';
	}

	function video(element) {
		var src = source(element.src);
		if (!src) return "";
		var poster = source(element.poster);
		// a video that does not loop holds the slide for its length (play.py),
		// so it plays once; one whose length the editor never saw loops as before
		var loop = element.loop || !(num(element.length) > 0);
		// a video plays its own sound only when it says so and the page lets it (a screen's Plays Sound)
		var loud = element.sound && root.onedesk && root.onedesk.play && root.onedesk.play.loud;
		return '<div style="' + esc(box(element, rotated(element))) + '"><video src="' + esc(src) + '"' + (poster ? ' poster="' + esc(poster) + '"' : "") +
			(element.sound ? ' data-sound="1"' : "") + (loud ? "" : " muted") + ' autoplay' + (loop ? " loop" : "") + ' playsinline style="width:100%;height:100%;object-fit:cover;opacity:' + num(element.opacity, 100) / 100 + ";border-radius:" + num(element.borderRadius) + 'px"></video></div>';
	}

	function table(element) {
		// drawn to HTML by the server, which reads Suite's table (programme.py)
		return element.html ? '<div class="one-table" style="' + esc(box(element, "")) + '">' + old(element.html) + "</div>" : "";
	}

	var DRAW = { text: text, shape: shape, image: picture, video: video, table: table };

	/* How an element comes and goes (docs/ONESLIDE.md, an object comes and
	   goes): one keyframe track per element, on a box as large as the slide
	   that holds it, moved by transform and opacity only so a TV keeps up.
	   It waits, comes in, stays, goes, and with `again` starts over. */
	function state(effect, from) {
		if (!effect) return { o: 1, t: "none" };
		var at = effect.fly ? MOTION.from[from] || MOTION.from.Left : [0, effect.y || 0];
		var turn = "translate(" + at[0] + "%," + at[1] + "%)" + (effect.scale ? " scale(" + effect.scale + ")" : "");
		return { o: effect.opacity == null ? 1 : effect.opacity, t: turn };
	}

	function frame(at, look, ease) {
		return num(at) + "%{opacity:" + look.o + ";-webkit-transform:" + look.t + ";transform:" + look.t + (ease ? ";-webkit-animation-timing-function:" + ease + ";animation-timing-function:" + ease : "") + "}";
	}

	function motion(element, later, clicked) {
		var m = element.motion || {};
		var enter = MOTION["in"][m["in"]];
		var leave = num(m.stay) > 0 ? MOTION.out[m.out] : null;
		if (!enter && !leave) return null;
		var speed = num(m.speed, MOTION.speed) || MOTION.speed;
		var wait = num(m.wait);
		var shown = state(null);
		var inEnds = wait + (enter ? speed : 0);
		var outStarts = inEnds + num(m.stay);
		var total = Math.max(leave ? outStarts + speed : inEnds, 0.01);
		var pct = function (t) { return (t / total) * 100; };
		var first = state(enter, m.from);
		var name = "one-motion-" + counter++;
		var frames = [frame(0, first), frame(pct(wait), first, "ease-out"), frame(pct(inEnds), shown)];
		if (leave) frames.push(frame(pct(outStarts), shown, "ease-in"), frame(100, state(leave, m.from)));
		else frames.push(frame(100, shown));
		var run = name + " " + num(total) + "s linear " + num(later || 0) + "s " + (m.again && leave ? "infinite" : "1") + " both";
		var middle = num(num(element.left) + num(element.width) / 2) + "px " + num(num(element.top) + num(element.height) / 2) + "px";
		var look = [
			"position:absolute;left:0;top:0;width:100%;height:100%;pointer-events:none",
			"z-index:" + Math.max(1, Math.round(num(element.zIndex, 1))),
			"-webkit-transform-origin:" + middle + ";transform-origin:" + middle,
			"-webkit-animation:" + run + ";animation:" + run
		];
		if (clicked) look.push("-webkit-animation-play-state:paused;animation-play-state:paused");
		return {
			keys: "@-webkit-keyframes " + name + "{" + frames.join("") + "}@keyframes " + name + "{" + frames.join("") + "}",
			look: look.join(";"),
			speed: wait + speed
		};
	}

	// `auto`: nobody clicks (a screen, or a guest following the presenter),
	// so what comes on a click comes after the one before it
	function slide(said, auto) {
		var elements = (said && said.elements) || [];
		var drawn = [];
		var keys = [];
		var later = 0;
		for (var i = 0; i < elements.length; i++) {
			var element = elements[i];
			if (!element || element.hidden || !DRAW[element.type]) continue;
			var onClick = element.motion && element.motion.start === "On Click";
			var moves = motion(element, onClick && auto ? later + 1 : 0, onClick && !auto);
			if (!moves) {
				drawn.push(DRAW[element.type](element));
				continue;
			}
			if (onClick && auto) later += 1 + moves.speed;
			keys.push(moves.keys);
			drawn.push('<div class="one-motion"' + (onClick && !auto ? " data-click=\"1\"" : "") + ' style="' + esc(moves.look) + '">' + DRAW[element.type](element) + "</div>");
		}
		if (keys.length) drawn.unshift("<style>" + keys.join("") + "</style>");
		// a screen's backdrop gives its own frame and lets the screen's colour through
		var wide = (said && said.width) || WIDE;
		var high = (said && said.height) || HIGH;
		var ground = said && said.bare ? "transparent" : background(said && said.background);
		return '<div class="one-play" style="position:relative;overflow:hidden;width:' + wide + "px;height:" + high + "px;background:" + esc(ground) + '">' + drawn.join("") + "</div>";
	}

	// the stage scaled to its holder and centred: as large as fits whole, or
	// covering the holder and trimmed when `cover` (a screen's Fill the Screen)
	function fit(holder, cover) {
		var stage = holder.firstChild;
		if (!stage) return;
		var wide = stage.offsetWidth || WIDE;
		var high = stage.offsetHeight || HIGH;
		var scale = (cover ? Math.max : Math.min)(holder.clientWidth / wide, holder.clientHeight / high) || 1;
		stage.style.position = "absolute";
		stage.style.left = (holder.clientWidth - wide * scale) / 2 + "px";
		stage.style.top = (holder.clientHeight - high * scale) / 2 + "px";
		stage.style.transformOrigin = "0 0";
		stage.style.webkitTransformOrigin = "0 0";
		stage.style.transform = "scale(" + scale + ")";
		stage.style.webkitTransform = "scale(" + scale + ")";
	}

	function styled(document) {
		if (!document || document.getElementById(STYLE)) return;
		var style = document.createElement("style");
		style.id = STYLE;
		style.textContent =
			".one-play p{margin:0}.one-play ul,.one-play ol{margin:0;padding-left:1.2em;padding-inline-start:1.2em}" +
			".one-play .one-text p,.one-play .one-text li{unicode-bidi:plaintext}.one-play .one-text[dir] p,.one-play .one-text[dir] li{unicode-bidi:normal}" +
			".one-play .one-text{font-family:Inter,sans-serif;font-variant-ligatures:none}" +
			".one-play .one-shape-text{position:absolute;left:0;top:0;width:100%;height:100%;display:-webkit-flex;display:flex;" +
			"-webkit-flex-direction:column;flex-direction:column;-webkit-justify-content:center;justify-content:center;padding:8px;box-sizing:border-box;overflow:hidden}" +
			".one-play .one-motion>*{pointer-events:auto}.one-play table{border-collapse:collapse;width:100%}.one-play td,.one-play th{border:1px solid rgba(128,128,128,0.5);padding:4px 8px}";
		document.head.appendChild(style);
	}

	// a slide taken off: an old TV keeps a video's decoder until the video
	// is emptied, not merely removed
	function release(node) {
		var videos = node.getElementsByTagName("video");
		for (var i = videos.length - 1; i >= 0; i--) {
			try {
				videos[i].pause();
				videos[i].removeAttribute("src");
				videos[i].load();
			} catch (e) {}
		}
	}

	function draw(said, holder, auto) {
		if (holder.firstChild) release(holder);
		styled(holder.ownerDocument);
		holder.innerHTML = slide(said, auto);
		fit(holder);
	}

	// the next thing that comes on a click, if one is still waiting
	function step(holder) {
		var waiting = holder.querySelectorAll(".one-motion[data-click]");
		if (!waiting.length) return false;
		waiting[0].removeAttribute("data-click");
		waiting[0].style.webkitAnimationPlayState = "running";
		waiting[0].style.animationPlayState = "running";
		return true;
	}

	root.onedesk = root.onedesk || {};
	root.onedesk.play = { slide: slide, draw: draw, step: step, fit: fit, release: release, colour: colour, background: background };
})(typeof window !== "undefined" ? window : this);
