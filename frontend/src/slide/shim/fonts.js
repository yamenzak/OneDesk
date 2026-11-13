// The workspace's fonts as the font picker offers them (one_deck/fonts.py):
// the ones One ships, by group, and the workspace's own. Their faces are the
// page's: slide/fonts.css and the workspace's stylesheet, loaded once.
import { computed, ref } from "vue";
import { call } from "../../kit/desk";
import { __ } from "./words.js";

export const SHIPPED_CSS = "/assets/onedesk/slide/fonts.css";
export const OWN_CSS = "/api/method/onedesk.one_deck.fonts.css";

export const library = ref({ shipped: [], yours: [], may_add: false, google: false });

const GROUPS = () => ({
	arabic: __("Arabic"),
	sans: __("Sans Serif"),
	serif: __("Serif"),
	display: __("Display"),
	mono: __("Monospace"),
});

// a few letters to show an Arabic face in, beside its name
export const ARABIC_SAMPLE = "أبجد";

export async function loadFonts() {
	library.value = await call("onedesk.one_deck.fonts.library");
}

// the workspace's stylesheet again, after a font is added, so the new face draws at once
export function refreshFaces(doc) {
	const link = doc.head.querySelector(`link[data-one-fonts]`);
	if (link) link.href = `${OWN_CSS}?at=${Date.now()}`;
}

export function pageFonts(doc) {
	if (!doc.head.querySelector(`link[href="${SHIPPED_CSS}"]`)) {
		const link = doc.createElement("link");
		link.rel = "stylesheet";
		link.href = SHIPPED_CSS;
		doc.head.appendChild(link);
	}
	if (!doc.head.querySelector("link[data-one-fonts]")) {
		const link = doc.createElement("link");
		link.rel = "stylesheet";
		link.href = OWN_CSS;
		link.dataset.oneFonts = "1";
		doc.head.appendChild(link);
	}
}

// the picker's options: the workspace's own first, then One's by group
export const fontOptions = computed(() => {
	const named = GROUPS();
	const out = [];
	if (library.value.yours.length)
		out.push({ group: __("Your Fonts"), options: library.value.yours.map((one) => ({ label: one.family, value: one.family })) });
	for (const [key, label] of Object.entries(named)) {
		const options = library.value.shipped.filter((one) => one.group === key).map((one) => ({ label: one.family, value: one.family, arabic: key === "arabic" }));
		if (options.length) out.push({ group: label, options });
	}
	return out;
});
