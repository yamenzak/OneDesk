frappe.provide("onedesk.brand");

onedesk.brand.NAME = /\bOne(AI|Admin|Book|Calendar|Cloud|Code|CRM|DB|Desk|Display|Doc|Fit|Forms|Governance|HR|Intake|Inventory|Legal|Mail|Market|Mobility|Project|Scratchpad|Sheet|Signature|Slide|Studio|Study|Task|Ticket|Workbook|Writer)\b/g;

onedesk.brand.LEAVE = "input, textarea, select, option, script, style, code, pre, [contenteditable], .ql-editor, .CodeMirror, .ace_editor, [data-v-app], .one-name, title, svg";

onedesk.brand.wrap = (root) => {
	if (!root || !document.body.contains(root) && root !== document.body) return;
	if (root.nodeType === Node.TEXT_NODE) return onedesk.brand.text(root);
	if (root.nodeType !== Node.ELEMENT_NODE || root.closest(onedesk.brand.LEAVE)) return;
	if (!(root.textContent || "").includes("One")) return;
	const walker = document.createTreeWalker(root, NodeFilter.SHOW_TEXT, {
		acceptNode: (node) =>
			node.nodeValue.includes("One") && !node.parentElement.closest(onedesk.brand.LEAVE)
				? NodeFilter.FILTER_ACCEPT
				: NodeFilter.FILTER_REJECT,
	});
	const found = [];
	while (walker.nextNode()) found.push(walker.currentNode);
	found.forEach(onedesk.brand.text);
};

onedesk.brand.text = (node) => {
	const text = node.nodeValue;
	const parent = node.parentElement;
	if (!parent || parent.closest(onedesk.brand.LEAVE)) return;
	onedesk.brand.NAME.lastIndex = 0;
	if (!onedesk.brand.NAME.test(text)) return;
	onedesk.brand.NAME.lastIndex = 0;
	const into = document.createDocumentFragment();
	let at = 0;
	for (const match of text.matchAll(onedesk.brand.NAME)) {
		if (match.index > at) into.append(text.slice(at, match.index));
		const name = document.createElement("span");
		name.className = "one-name";
		const light = document.createElement("span");
		light.className = "one-light";
		light.textContent = "One";
		name.append(light, match[1]);
		into.append(name);
		at = match.index + match[0].length;
	}
	into.append(text.slice(at));
	parent.replaceChild(into, node);
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
