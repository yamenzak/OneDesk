// A presentation's guides, and whether this person sees them and the rulers
// they are dragged from (shim/Rulers.vue); hidden, they snap nothing. A guide
// is an axis and a place in slide units, x a line down the slide and y one
// across it, kept on the presentation (one_slide/guides.py) and snapped to
// while moving or sizing (composables/useSnapping.js, a One: edit).
import { ref } from "vue";
import { call, userSettings } from "../../kit/desk";
import { frame } from "./frame.js";

export const guides = ref([]);
export const rulersShown = ref(false);

// the margin Add Margin Guides draws in from each edge
export const MARGIN = 40;
const MOST = 60;

let presentation = "";
let timer = null;
let asked = false;

export function readRulers() {
	if (asked) return;
	asked = true;
	userSettings
		.get("Presentation")
		.then((said) => (rulersShown.value = Boolean(said?.rulers)))
		.catch(() => {});
}

export function loadGuides(doc) {
	presentation = doc?.name || "";
	let kept = [];
	try {
		kept = JSON.parse(doc?.guides || "[]");
	} catch {
		kept = [];
	}
	guides.value = Array.isArray(kept) ? kept : [];
}

export function toggleRulers() {
	rulersShown.value = !rulersShown.value;
	userSettings.save("Presentation", "rulers", rulersShown.value);
}

// kept a moment after the last change, so a drag is one write
function keep() {
	clearTimeout(timer);
	if (!presentation) return;
	const name = presentation;
	timer = setTimeout(() => call("onedesk.one_slide.guides.keep", { name, guides: JSON.stringify(guides.value) }), 600);
}

const limit = (axis) => (axis === "x" ? frame.w : frame.h);
const newId = () => Math.random().toString(36).slice(2, 10);

export function addGuide(axis, at) {
	if (guides.value.length >= MOST) return null;
	const made = { id: newId(), axis, at: Math.round(at) };
	guides.value = [...guides.value, made];
	keep();
	return made.id;
}

// a guide dragged off the slide is gone
export function moveGuide(id, at, done = false) {
	const one = guides.value.find((guide) => guide.id === id);
	if (!one) return;
	const off = at < 0 || at > limit(one.axis);
	if (done && off) guides.value = guides.value.filter((guide) => guide.id !== id);
	else guides.value = guides.value.map((guide) => (guide.id === id ? { ...guide, at: Math.round(done ? Math.min(Math.max(at, 0), limit(one.axis)) : at) } : guide));
	if (done) keep();
}

export function addMarginGuides() {
	const wanted = [
		["x", MARGIN],
		["x", frame.w - MARGIN],
		["y", MARGIN],
		["y", frame.h - MARGIN],
	].filter(([axis, at]) => !guides.value.some((guide) => guide.axis === axis && guide.at === at));
	guides.value = [...guides.value, ...wanted.map(([axis, at]) => ({ id: newId(), axis, at }))].slice(0, MOST);
	rulersShown.value || toggleRulers();
	keep();
}

export function clearGuides() {
	guides.value = [];
	keep();
}
