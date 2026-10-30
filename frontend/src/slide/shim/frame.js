// The frame a slide is drawn on, in the editor's own units: the presentation's
// own size (Presentation.width and height, 960 by 540 unless it was made
// otherwise), or a screen's shape when the editor lays out a screen (stage 7
// of docs/ONESLIDE.md). Set it before the editor mounts.
import { reactive } from "vue";
import { __ } from "./words.js";

export const WIDE = { w: 960, h: 540 };
export const TALL = { w: 540, h: 960 };
export const frame = reactive({ ...WIDE });

// the sizes New Presentation and Slide Size offer, in the reader's language;
// one_slide/resize.py SIZES is the same list
export const sizes = () => [
	{ key: "wide", label: __("Wide (16:9)"), w: 960, h: 540 },
	{ key: "standard", label: __("Standard (4:3)"), w: 960, h: 720 },
	{ key: "a4", label: __("A4, Landscape"), w: 1123, h: 794 },
	{ key: "a4-portrait", label: __("A4, Portrait"), w: 794, h: 1123 },
	{ key: "square", label: __("Square"), w: 960, h: 960 },
	{ key: "tall", label: __("Standing (9:16)"), w: 540, h: 960 },
];

export function setFrame(w, h) {
	Object.assign(frame, w > 0 && h > 0 ? { w, h } : WIDE);
}

// what a loaded presentation is drawn on: a screen's shape, else its own size
export function frameOf(doc) {
	if (doc?.screen) return doc.screen.orientation === "Portrait" ? TALL : WIDE;
	return { w: Number(doc?.width) || WIDE.w, h: Number(doc?.height) || WIDE.h };
}

export const frameSize = () => ({ width: `${frame.w}px`, height: `${frame.h}px` });
