
import { createApp, h, ref } from "vue";

import Panel from "./panel/Panel.vue";

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
						onClosed: () => {
							showing.value = false;
							onedesk.oneai.beside(false);
						},
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
