frappe.provide("onedesk.brand");

onedesk.brand.NAME = /\bOne(AI|Admin|Book|Calendar|Cloud|Code|CRM|DB|Desk|Display|Doc|Fit|Forms|Governance|HR|Inventory|Legal|Mail|Market|Mobility|Project|Scratchpad|Sheet|Signature|Slide|Studio|Study|Task|Ticket|Workbook|Writer)\b/g;


// One's centres (module_settings.js CENTERS), drawn as a product's name is:
// One's mark, the first word light and Center after it.
onedesk.brand.CENTER = /\b(Help|Control|Account|Update|Trust|Access|Notification|AI)Center\b/g;

onedesk.brand.VERBS = new Set(
	"opens added may can cannot keeps sends reads shows asks uses does doesn't is isn't will won't has hasn't holds makes gives tells writes stores checks knows works needs puts takes turns brings finds counts books bills pays says sees saves signs".split(" "),
);

onedesk.brand.solo = (text) => {
	const found = [];
	for (const match of (text || "").matchAll(/\bOne\b(?!-)/g)) {
		const before = text.slice(0, match.index).trimEnd();
		const after = text.slice(match.index + 3);
		if (/^\w/.test(after) && !/^'s\b/.test(after)) continue;
		const next = (after.match(/^\s+([\p{L}']+)/u) || [])[1] || "";
		const starts = !before || /[.!?:]$/.test(before);
		const product = /^['’]s\b/.test(after) || (starts ? onedesk.brand.VERBS.has(next) : !/^\p{Lu}/u.test(next));
		if (product && text.trim() !== "One") found.push(match.index);
	}
	return found;
};

onedesk.brand.parts = (text) => {
	const parts = [];
	let at = 0;
	for (const index of onedesk.brand.solo(text)) {
		if (index > at) parts.push(text.slice(at, index));
		parts.push({ one: true });
		at = index + 3;
	}
	if (at < (text || "").length) parts.push(text.slice(at));
	return parts;
};

onedesk.brand.LEAVE = "input, textarea, select, option, script, style, code, pre, [contenteditable], .ql-editor, .CodeMirror, .ace_editor, .one-json-body, [data-v-app], .one-name, title, svg";

// Where a label that is only a product's name has no icon beside it, so it
// draws the mark itself: a settings panel's title.
onedesk.brand.MARK_ALONE = ".settings-dialog-panel-title";

onedesk.brand.wrap = (root) => {
	if (!root || !document.body.contains(root) && root !== document.body) return;
	if (root.nodeType === Node.TEXT_NODE) return onedesk.brand.text(root);
	if (root.nodeType !== Node.ELEMENT_NODE || root.closest(onedesk.brand.LEAVE)) return;
	const named = (text) => (text || "").includes("One") || (text || "").includes("Center");
	if (!named(root.textContent)) return;
	const walker = document.createTreeWalker(root, NodeFilter.SHOW_TEXT, {
		acceptNode: (node) =>
			named(node.nodeValue) && !node.parentElement.closest(onedesk.brand.LEAVE)
				? NodeFilter.FILTER_ACCEPT
				: NodeFilter.FILTER_REJECT,
	});
	const found = [];
	while (walker.nextNode()) found.push(walker.currentNode);
	found.forEach((node) => onedesk.brand.text(node));
};

// `inside`: an island drawing its own text asks for it by name, which the
// observer, kept out of islands by LEAVE, never does.
onedesk.brand.text = (node, inside = false) => {
	const text = node.nodeValue;
	const parent = node.parentElement;
	if (!parent || (!inside && parent.closest(onedesk.brand.LEAVE))) return;
	const alone = parent.closest(onedesk.brand.MARK_ALONE) ? null : text.trim();
	const found = [
		...[...text.matchAll(onedesk.brand.NAME)].map((match) => ({ at: match.index, length: match[0].length, rest: match[1], marked: alone !== match[0] })),
		...[...text.matchAll(onedesk.brand.CENTER)].map((match) => ({ at: match.index, length: match[0].length, center: match[1], marked: !parent.closest(onedesk.brand.CENTER_ICONED) })),
		...onedesk.brand.solo(text).map((at) => ({ at, length: 3, rest: null })),
	].sort((a, b) => a.at - b.at);
	if (!found.length) return;
	const into = document.createDocumentFragment();
	let at = 0;
	for (const one of found) {
		if (one.at > at) into.append(text.slice(at, one.at));
		into.append(one.center ? onedesk.brand.center(one.center, one.marked) : one.rest === null ? onedesk.brand.mark() : onedesk.brand.named(one.rest, one.marked));
		at = one.at + one.length;
	}
	into.append(text.slice(at));
	parent.replaceChild(into, node);
};

/** The sprite's mark for a product: its name lowered, but for the three
 * whose id is older than their name (scripts/gen_brand.py, ALIAS). */
onedesk.brand.MARK_IDS = { Cloud: "onecloud", Writer: "onedoc", Workbook: "onesheet" };

onedesk.brand.mark_of = (rest) => {
	const id = onedesk.brand.MARK_IDS[rest] || `one${rest.toLowerCase()}`;
	return document.getElementById(`icon-${id}`) ? id : null;
};

/** A product's name: One light. In a sentence its mark goes before it, as
 * the lone One's does; a label that is only the name draws its own icon. */
onedesk.brand.named = (rest, marked = false) => {
	const name = document.createElement("span");
	name.className = "one-name";
	const id = marked && onedesk.brand.mark_of(rest);
	if (id) {
		name.className = "one-name one-solo";
		name.innerHTML = frappe.utils.icon(id, { width: "1.05em", height: "1.05em" }, "", "", "one-mark");
	}
	const light = document.createElement("span");
	light.className = "one-light";
	light.textContent = "One";
	if (!id) {
		name.append(light, rest);
		return name;
	}
	const word = document.createElement("span");
	word.append(light, rest);
	name.append(word);
	return name;
};

// Where a centre's name already has its own icon beside it: a rail row.
onedesk.brand.CENTER_ICONED = ".sidebar-item-label, .settings-dialog-tab-label";

/** A centre's name, such as HelpCenter: One's mark, the first word light
 * and Center after it, in a sentence and at the top of the centre alike;
 * on a rail row, beside the row's own icon, without the mark. */
onedesk.brand.center = (first, marked = true) => {
	const name = document.createElement("span");
	name.className = marked ? "one-name one-solo" : "one-name";
	if (marked) name.innerHTML = frappe.utils.icon("one", { width: "1.05em", height: "1.05em" }, "", "", "one-mark");
	const word = document.createElement("span");
	const light = document.createElement("span");
	light.className = "one-light";
	light.textContent = first;
	word.append(light, "Center");
	name.append(word);
	return name;
};

onedesk.brand.mark = () => {
	const name = document.createElement("span");
	name.className = "one-name one-solo";
	name.innerHTML = frappe.utils.icon("one", { width: "1.05em", height: "1.05em" }, "", "", "one-mark");
	const light = document.createElement("span");
	light.className = "one-light";
	light.textContent = "One";
	name.append(light);
	return name;
};

(() => {
	let waiting = [];
	let asked = false;
	const run = () => {
		asked = false;
		const nodes = waiting;
		waiting = [];
		for (const node of nodes) if (node.isConnected) onedesk.brand.wrap(node);
	};
	const observer = new MutationObserver((changes) => {
		for (const change of changes) {
			if (change.type === "characterData") waiting.push(change.target);
			else change.addedNodes.forEach((node) => waiting.push(node));
		}
		if (waiting.length && !asked) {
			asked = true;
			requestAnimationFrame(run);
		}
	});
	const start = () => {
		onedesk.brand.wrap(document.body);
		observer.observe(document.body, { childList: true, subtree: true, characterData: true });
	};
	if (document.body) start();
	else document.addEventListener("DOMContentLoaded", start);
})();
