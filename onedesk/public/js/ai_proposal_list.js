// What a model has suggested. The list is a queue, so the one thing it has to
// say per row is whether anybody still has to answer it.
frappe.listview_settings["AI Proposal"] = {
	hide_name_column: true,
	add_fields: ["state", "kind", "for_doctype"],

	get_indicator(doc) {
		const says = {
			Proposed: [__("Pending"), "orange"],
			Applied: [__("Applied"), "green"],
			Refused: [__("Refused"), "grey"],
			Stale: [__("Outdated"), "red"],
		};
		const [word, colour] = says[doc.state] || [doc.state, "grey"];
		return [word, colour, `state,=,${doc.state}`];
	},
};
