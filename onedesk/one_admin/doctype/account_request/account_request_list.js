// Signups. Failed is the row somebody has to act on — a person paid and has no
// workspace — so it is red and everything before it is a normal step.
frappe.listview_settings["Account Request"] = {
	add_fields: ["status", "offering"],

	get_indicator(doc) {
		const says = {
			New: ["grey", __("Not paid")],
			Paying: ["orange", __("At Stripe")],
			Paid: ["blue", __("Paid")],
			Provisioning: ["blue", __("Being built")],
			Done: ["green", __("Done")],
			Failed: ["red", __("Paid and not built")],
		};
		const [colour, word] = says[doc.status] || ["grey", doc.status];
		return [word, colour, `status,=,${doc.status}`];
	},
};
