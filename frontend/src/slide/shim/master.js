// The presentation's master, drawn under every slide that does not hide it
// (one_slide/master.py), and whether the editor is open on a master itself.
// A text on the master may be a field, the slide's number or today's date,
// filled for each slide where it is drawn.
import { ref } from "vue";
import { date, today } from "../../kit/desk";

export const master = ref([]);
// the presentation this one is the master of, when the editor is open on a master
export const masterOf = ref("");

export function loadMaster(doc) {
	master.value = Array.isArray(doc?.master) ? doc.master : [];
	masterOf.value = doc?.master_of || "";
}

// a text's first run of words made `words`, the rest of them dropped, its look kept
const worded = (content, words) => {
	let done = false;
	const safe = String(words).replace(/[&<>]/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;" })[c]);
	const out = String(content || "").replace(/>[^<]+</g, () => {
		if (done) return "><";
		done = true;
		return `>${safe}<`;
	});
	return done ? out : `<p>${safe}</p>`;
};

// what the master draws under one slide: its own ids, so they never meet the slide's
export function underneath(slide, index) {
	if (!slide || slide.hideMaster || !master.value.length) return [];
	const number = index >= 0 ? String(index + 1) : "#";
	return master.value.map((one) => {
		const drawn = { ...one, id: `master-${one.id}`, locked: true };
		if (one.field === "number") drawn.content = worded(one.content, number);
		if (one.field === "date") drawn.content = worded(one.content, date(today()));
		return drawn;
	});
}

// a field to put on the master: a small text that becomes each slide's number, or the date
export function fieldElement(field, frameSize) {
	const word = field === "number" ? "#" : date(today());
	return {
		id: Math.random().toString(36).slice(2, 11),
		type: "text",
		field,
		left: field === "number" ? frameSize.w - 120 : 40,
		top: frameSize.h - 48,
		width: 80,
		zIndex: 1,
		content: `<p style="text-align: ${field === "number" ? "right" : "left"}"><span style="font-size: 14px">${word}</span></p>`,
	};
}
