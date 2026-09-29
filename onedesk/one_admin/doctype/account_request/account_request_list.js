// Signups, in the words their Record Head says too (heads.REQUEST). A paid
// signup with no workspace is the row somebody has to act on, so it is
// orange or red and everything before it is a normal step.
frappe.listview_settings["Account Request"] = {
	add_fields: ["status", "offering"],
	hide_name_column: true,
	hide_name_filter: true,

	get_indicator(doc) {
		const says = {
			New: ["grey", __("Not paid")],
			Paying: ["orange", __("At checkout")],
			Paid: ["orange", __("Paid, not built")],
			Provisioning: ["blue", __("Being built")],
			Done: ["green", __("Built")],
			Failed: ["red", __("Paid, build failed")],
			Abandoned: ["grey", __("Abandoned")],
		};
		const [colour, word] = says[doc.status] || ["grey", doc.status];
		return [word, colour, `status,=,${doc.status}`];
	},
};
