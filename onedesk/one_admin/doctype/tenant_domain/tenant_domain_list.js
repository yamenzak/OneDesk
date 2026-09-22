// Domains, where the only interesting rows are the ones that have not worked
// yet. Press decides the status and we keep its word for it, so these are its
// names rather than ours.
frappe.listview_settings["Tenant Domain"] = {
	add_fields: ["status"],

	get_indicator(doc) {
		const says = {
			Pending: ["orange", __("Waiting on DNS")],
			"In Progress": ["blue", __("Frappe Cloud is setting it up")],
			Active: ["green", __("Working")],
			Broken: ["red", __("Broken")],
			Gone: ["grey", __("Removed at Frappe Cloud")],
		};
		const [colour, word] = says[doc.status] || ["grey", doc.status];
		return [word, colour, `status,=,${doc.status}`];
	},
};
