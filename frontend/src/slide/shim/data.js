// Words on a slide that come from records (one_deck/data.py). The
// presentation's sources, and what each chip says to whoever is looking:
// filled where a text is drawn (TextElement, TableElement, a One: edit), and
// asked for again when a record it read changes.
import { ref } from "vue";
import { call, follow } from "../../kit/desk";

export const sources = ref([]);
export const values = ref({});

const CHIP = /\{([a-z][a-z0-9_]{0,29})\.([a-z0-9_.]{1,80})\}/g;

let presentation = "";
let heard = [];
let timer = null;
// chips drawn that the last answer did not cover: put on since the last save
const asked = new Set();

const parsed = (text) => {
	try {
		const kept = JSON.parse(text || "[]");
		return Array.isArray(kept) ? kept : [];
	} catch {
		return [];
	}
};

const listen = (watch) => {
	heard.forEach((stop) => stop());
	heard = (watch || []).map(([doctype, name]) => follow(doctype, name, () => soon()));
};

export function loadData(doc) {
	presentation = doc?.name || "";
	sources.value = parsed(doc?.sources);
	values.value = doc?.data?.values || {};
	listen(doc?.data?.watch);
}

export async function refresh() {
	if (!presentation || !sources.value.length) return;
	const said = await call("onedesk.one_deck.data.values", { name: presentation, asked: [...asked] });
	values.value = said.values || {};
	listen(said.watch);
}

// a record changes in bursts as it is saved, and chips go on one after another; ask once they settle
function soon() {
	clearTimeout(timer);
	timer = setTimeout(refresh, 600);
}

export async function saveSources(next) {
	sources.value = await call("onedesk.one_deck.data.save_sources", { name: presentation, sources: next });
	await refresh();
}

const escaped = (text) => String(text).replace(/[&<>"]/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;" })[c]);

// a text with each chip put in; `keep` leaves a chip with nothing to say as it
// is, so the person writing the slide can still see what it is
export function fill(html, keep = false) {
	const said = values.value;
	if (!html || typeof html !== "string" || !html.includes("{") || !sources.value.length) return html;
	const keys = new Set(sources.value.map((one) => one.key));
	return html.replace(CHIP, (chip, key, rest) => {
		const one = said[`${key}.${rest}`];
		if (!keys.has(key)) return chip;
		if (one === undefined && !asked.has(chip)) {
			asked.add(chip);
			soon();
		}
		if (!one) return keep ? chip : "";
		return escaped(one);
	});
}

export const chip = (key, field) => `{${key}.${field}}`;

const ROW = /<tr\b[^>]*>[\s\S]*?<\/tr>/g;
const words = (html) => html.replace(/<[^>]*>/g, "").replace(/[\s\u200b]|&nbsp;/g, "");

// a table filled, and when presenting, without the rows of a list that ran
// out: a list of three under a table of ten shows three
export function fillTable(html, keep = false) {
	const filled = fill(html, keep);
	if (keep || filled === html) return filled;
	return html.replace(ROW, (row) => {
		const done = fill(row, false);
		return row.match(CHIP) && !words(done) ? "" : done;
	});
}
