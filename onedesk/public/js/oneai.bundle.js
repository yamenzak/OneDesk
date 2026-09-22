// The OneAI panel, mounted once and never torn down.
//
// Fetched by `frappe.require("oneai.bundle.js")` the first time somebody opens
// the launcher, which is why Vue lives in here rather than in `app_include_js`:
// a page nobody asks a question on pays nothing for it.
//
// `onedesk.oneai.mount` is the whole of the contract with the launcher — it
// returns the two methods the launcher calls, `open` and `moved`, and nothing
// else crosses between them.

import { createApp, h, ref } from "vue";

import Panel from "./oneai/Panel.vue";

frappe.provide("onedesk.oneai");

onedesk.oneai.mount = function (where) {
	const root = document.createElement("div");
	root.className = "one-ai-root";
	where.appendChild(root);

	const showing = ref(false);
	const here = ref(onedesk.oneai.where());
	const panel = ref(null);

	createApp({
		render: () =>
			showing.value
				? h(Panel, {
						ref: panel,
						here: here.value,
						onClosed: () => (showing.value = false),
						onCounted: () => onedesk.oneai.count(),
				  })
				: null,
	}).mount(root);

	return {
		open(opening) {
			here.value = onedesk.oneai.where();
			showing.value = true;
			Promise.resolve().then(() => panel.value && panel.value.opened(opening));
		},
		moved(to) {
			here.value = to;
		},
	};
};
