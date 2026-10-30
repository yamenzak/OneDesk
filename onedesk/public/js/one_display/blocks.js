/* A designed slide drawn from its blocks (one_display/blocks.py says what a
   block may hold). The one drawing the screen plays and the designer edits
   on, so the two cannot disagree. ES5 on purpose, like tv.js: a 2017 TV
   runs Chromium 53, so no `inset`, no flex `gap`, no #rrggbbaa. Every value
   was checked by the server; text is escaped here all the same. */
(function (root) {
	"use strict";

	var FONTS = {
		sans: "'Inter','Noto Sans','Noto Sans Arabic',Tahoma,Arial,sans-serif",
		serif: "Georgia,'Noto Serif','Noto Naskh Arabic','Times New Roman',serif",
		mono: "'DejaVu Sans Mono',Menlo,Consolas,'Courier New',monospace",
		condensed: "'Roboto Condensed','Arial Narrow','Noto Sans','Noto Sans Arabic',sans-serif"
	};

	var POINTS = {
		triangle: "50,0 100,100 0,100",
		diamond: "50,0 100,50 50,100 0,50",
		star: "50,0 61.8,35.4 100,38.2 69.1,61.8 80.9,100 50,76.4 19.1,100 30.9,61.8 0,38.2 38.2,35.4",
		arrow: "0,35 62,35 62,8 100,50 62,92 62,65 0,65"
	};

	var CSS_NEVER = /url\s*\(|expression|javascript|@import|\\|["'<>{}]/i;

	function esc(text) {
		return String(text == null ? "" : text)
			.replace(/&/g, "&amp;")
			.replace(/</g, "&lt;")
			.replace(/>/g, "&gt;")
			.replace(/"/g, "&quot;");
	}

	function num(value, fallback) {
		var n = parseFloat(value);
		return isNaN(n) ? fallback : n;
	}

	/* A colour as Chromium 53 reads it: #rrggbbaa becomes rgba(). */
	function colour(hex) {
		hex = String(hex || "");
		if (!/^#(?:[0-9a-fA-F]{3}|[0-9a-fA-F]{6}|[0-9a-fA-F]{8})$/.test(hex)) return "";
		if (hex.length !== 9) return hex;
		var r = parseInt(hex.substr(1, 2), 16);
		var g = parseInt(hex.substr(3, 2), 16);
		var b = parseInt(hex.substr(5, 2), 16);
		var a = Math.round((parseInt(hex.substr(7, 2), 16) / 255) * 1000) / 1000;
		return "rgba(" + r + "," + g + "," + b + "," + a + ")";
	}

	function paint(one, from, to, angle) {
		var a = colour(one[from]);
		var b = colour(one[to]);
		if (!a) return "";
		return b ? "linear-gradient(" + num(one[angle], 180) + "deg," + a + "," + b + ")" : a;
	}

	function own(css) {
		var kept = [];
		var parts = String(css || "").split(";");
		for (var i = 0; i < parts.length; i++) {
			var at = parts[i].indexOf(":");
			if (at < 1) continue;
			var said = parts[i].substr(at + 1);
			if (CSS_NEVER.test(said)) continue;
			kept.push(parts[i].substr(0, at).trim() + ":" + said.trim());
		}
		return kept.length ? kept.join(";") + ";" : "";
	}

	function svgShape(one) {
		return one.kind === "shape" && one.shape !== "rectangle" && one.shape !== "ellipse";
	}

	/* The block's own box: where it is, how it is turned and what it wears. */
	function style(one) {
		var s =
			"position:absolute;box-sizing:border-box;left:" + num(one.x, 0) + "%;top:" + num(one.y, 0) + "%;width:" +
			num(one.w, 10) + "%;height:" + num(one.h, 10) + "%;";
		var turn = num(one.rotate, 0);
		if (turn) s += "-webkit-transform:rotate(" + turn + "deg);transform:rotate(" + turn + "deg);";
		if (num(one.opacity, 1) < 1) s += "opacity:" + num(one.opacity, 1) + ";";
		var shade = colour(one.shadow_colour);
		var filters = [];
		if (num(one.blur, 0)) filters.push("blur(" + num(one.blur, 0) + "px)");
		if (shade && svgShape(one))
			filters.push("drop-shadow(" + num(one.shadow_x, 0) + "px " + num(one.shadow_y, 0) + "px " + num(one.shadow_blur, 0) / 2 + "px " + shade + ")");
		if (filters.length) s += "-webkit-filter:" + filters.join(" ") + ";filter:" + filters.join(" ") + ";";
		if (!svgShape(one)) {
			var fill = one.kind === "text" || one.kind === "shape" ? paint(one, "fill", "fill2", "angle") : "";
			if (fill) s += "background:" + fill + ";";
			if (num(one.stroke, 0) > 0)
				s += "border:" + num(one.stroke, 0) + "px " + (one.stroke_style || "solid") + " " + (colour(one.stroke_colour) || "#fff") + ";";
			if (one.kind === "shape" && one.shape === "ellipse") s += "border-radius:50%;";
			else if (num(one.radius, 0)) s += "border-radius:" + num(one.radius, 0) + "px;";
			if (shade) s += "box-shadow:" + num(one.shadow_x, 0) + "px " + num(one.shadow_y, 0) + "px " + num(one.shadow_blur, 0) + "px " + shade + ";";
			if (one.kind !== "shape") s += "overflow:hidden;";
		}
		if (one.kind === "text") {
			var v = { top: "flex-start", middle: "center", bottom: "flex-end" }[one.valign] || "flex-start";
			s +=
				"display:-webkit-flex;display:flex;-webkit-flex-direction:column;flex-direction:column;-webkit-justify-content:" + v +
				";justify-content:" + v + ";padding:" + num(one.padding, 0) + "px;color:" + (colour(one.colour) || "#fff") +
				";font-family:" + (FONTS[one.font] || FONTS.sans) + ";font-size:" + num(one.size, 96) + "px;font-weight:" +
				num(one.weight, 700) + ";line-height:" + num(one.line, 1.15) + ";letter-spacing:" + num(one.spacing, 0) +
				"em;text-align:" + (one.align || "start") + ";";
			if (one.font === "condensed") s += "font-stretch:condensed;";
			if (one.italic) s += "font-style:italic;";
			if (one.underline) s += "text-decoration:underline;";
			if (one.upper) s += "text-transform:uppercase;";
		}
		return s + own(one.css);
	}

	function gradient(one, id) {
		var a = colour(one.fill);
		var b = colour(one.fill2);
		if (!a || !b) return "";
		var turn = ((num(one.angle, 180) - 90) * Math.PI) / 180;
		var x = Math.cos(turn) * 50;
		var y = Math.sin(turn) * 50;
		return (
			'<defs><linearGradient id="' + id + '" x1="' + (50 - x) + '%" y1="' + (50 - y) + '%" x2="' + (50 + x) + '%" y2="' +
			(50 + y) + '%"><stop offset="0" stop-color="' + a + '"/><stop offset="1" stop-color="' + b + '"/></linearGradient></defs>'
		);
	}

	/* What is inside the box. */
	function inner(one, qrs) {
		if (one.kind === "text")
			return '<div style="white-space:pre-wrap;word-wrap:break-word;width:100%">' + esc(one.text) + "</div>";
		if (one.kind === "image")
			return one.src
				? '<img src="' + esc(one.src) + '" style="width:100%;height:100%;display:block;object-fit:' +
						(one.fit === "contain" ? "contain" : "cover") + '">'
				: "";
		if (one.kind === "qr") {
			var code = (qrs || {})[one.link] || "";
			return code.replace("<svg ", '<svg width="100%" height="100%" style="display:block" ');
		}
		if (!svgShape(one)) return "";
		var id = "g" + String(one.id || "").replace(/[^\w-]/g, "");
		var defs = gradient(one, id);
		var fill = defs ? "url(#" + id + ")" : colour(one.fill) || "none";
		var width = num(one.stroke, 0);
		var line = colour(one.stroke_colour) || "#fff";
		var dash = one.stroke_style === "dashed" ? ' stroke-dasharray="' + width * 3 + " " + width * 2 + '"' : one.stroke_style === "dotted" ? ' stroke-dasharray="' + width + " " + width + '"' : "";
		var body;
		if (one.shape === "line")
			body =
				'<line x1="0" y1="50" x2="100" y2="50" stroke="' + (colour(one.fill) || line) + '" stroke-width="' + (width || 6) +
				'" vector-effect="non-scaling-stroke"' + dash + "/>";
		else
			body =
				'<polygon points="' + (POINTS[one.shape] || POINTS.triangle) + '" fill="' + fill + '"' +
				(width ? ' stroke="' + line + '" stroke-width="' + width + '" stroke-linejoin="round" vector-effect="non-scaling-stroke"' + dash : "") +
				"/>";
		return '<svg viewBox="0 0 100 100" preserveAspectRatio="none" width="100%" height="100%" style="display:block;overflow:visible">' + defs + body + "</svg>";
	}

	function block(one, qrs) {
		if (one.hidden) return "";
		return '<div data-block="' + esc(one.id) + '" style="' + esc(style(one)) + '">' + inner(one, qrs) + "</div>";
	}

	/* The whole slide, filling whatever box it is put in: 1920 × 1080 on a
	   screen, scaled down whole in the designer. */
	function slide(design, qrs) {
		design = design || {};
		var ground = paint(design, "background", "background2", "angle") || "#0e6e8c";
		var s = "position:absolute;top:0;left:0;width:100%;height:100%;overflow:hidden;background:" + ground + ";";
		var out = '<div style="' + esc(s) + '">';
		if (design.image)
			out +=
				'<div style="position:absolute;top:0;left:0;width:100%;height:100%;background-image:url(' + esc(design.image) +
				');background-size:cover;background-position:center"></div>';
		if (num(design.dim, 0) > 0)
			out += '<div style="position:absolute;top:0;left:0;width:100%;height:100%;background:rgba(0,0,0,' + num(design.dim, 0) + ')"></div>';
		var blocks = design.blocks || [];
		for (var i = 0; i < blocks.length; i++) out += block(blocks[i], qrs);
		return out + "</div>";
	}

	var api = { slide: slide, block: block, style: style, inner: inner, colour: colour, fonts: FONTS };
	root.onedesk = root.onedesk || {};
	root.onedesk.blocks = api;
})(typeof window !== "undefined" ? window : this);
