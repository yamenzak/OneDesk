// Projects by Health (one_project/board.py), frappe's Kanban.
//
// The board leaves out an employee's onboarding or exit checklist as the list
// does (project_list.js), asked for with every load and never shown under
// Filters. frappe loads the board's code on first use, after this file, so
// the board is changed when it arrives.
(() => {
	const quiet = (Page) => {
		if (!Page || Page.prototype.one_boarding) return;
		Page.prototype.one_boarding = true;
		const effective = Page.prototype.get_effective_filters;
		Page.prototype.get_effective_filters = function (extra) {
			const filters = effective.call(this, extra);
			if (this.doctype !== "Project" || filters.some((one) => one[1] === "project_type")) return filters;
			return [...filters, ["Project", "project_type", "!=", "Employee Boarding"]];
		};
	};
	if (frappe.views.KanbanV2Page) return quiet(frappe.views.KanbanV2Page);
	let Page;
	Object.defineProperty(frappe.views, "KanbanV2Page", {
		configurable: true,
		enumerable: true,
		get: () => Page,
		set: (value) => {
			Page = value;
			quiet(value);
		},
	});
})();

// An internal project has no customer, so its card leaves the line out
// rather than ask for one.
frappe.kanban_v2.extend_settings("Project", {
	renderCard(card, el, ctx, page) {
		const fields = page.card_field_list;
		if (card.one_kind === "Internal") page.card_field_list = fields.filter((name) => name !== "customer");
		try {
			page.render_card(card, el);
		} finally {
			page.card_field_list = fields;
		}
	},
});
