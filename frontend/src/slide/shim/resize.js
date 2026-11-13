// Elements drawn for one frame, redrawn for another: a theme's layouts are
// 960 by 540, and a presentation may be any size. Every position and size
// follows its own axis; type, borders and corners follow the smaller of the
// two, so words never grow past their box. one_deck/resize.py is the same
// rule on the server.
import { frame } from "./frame.js";

const FONT = /(font-size|letter-spacing):\s*(-?[\d.]+)px/g;

export function scaled(elements, sx, sy) {
	const f = Math.min(sx, sy);
	const round = (n) => Math.round(n * 100) / 100;
	return (elements || []).map((one) => {
		const out = { ...one };
		for (const [key, by] of [["left", sx], ["top", sy], ["width", sx], ["height", sy]]) {
			if (typeof out[key] === "number") out[key] = round(out[key] * by);
		}
		for (const key of ["borderWidth", "strokeWidth", "borderRadius", "blur"]) {
			if (typeof out[key] === "number") out[key] = round(out[key] * f);
		}
		if (Array.isArray(out.points)) out.points = out.points.map((p) => ({ ...p, x: round(p.x * sx), y: round(p.y * sy) }));
		if (typeof out.content === "string" && out.type === "text") {
			out.content = out.content.replace(FONT, (_, prop, n) => `${prop}: ${round(Number(n) * f)}px`);
		}
		return out;
	});
}

// a layout from a template of another size, fitted to the presentation open now
export function fitted(elements, from) {
	const w = Number(from?.width) || 960;
	const h = Number(from?.height) || 540;
	if (w === frame.w && h === frame.h) return elements;
	return scaled(elements, frame.w / w, frame.h / h);
}
