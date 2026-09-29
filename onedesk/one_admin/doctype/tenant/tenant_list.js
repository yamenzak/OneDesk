// The workspace list.
//
// Every rung gets its own colour, because the question somebody scans this list
// to answer is "is anything wrong", and a column of identical grey pills does
// not answer it. Frappe's default colours a Select by position in the options,
// which put Live and Dropped in the same family.
//
// The name is the workspace's own, with its slug after it: two companies can
// be called Probe Ltd, and the slug is what tells them apart. The slug is
// searched as the workspace is, so the ID filter goes.
frappe.listview_settings["Tenant"] = {
	add_fields: ["status", "storage_bytes", "storage_limit", "domain", "is_house"],
	hide_name_column: true,
	hide_name_filter: true,

	get_indicator(doc) {
		// Our own workspace (house.py): nobody bills it, so it has no standing.
		if (doc.is_house) return [__("Ours"), "blue", "is_house,=,1"];
		const says = {
			Requested: ["orange", __("Waiting to be built")],
			Provisioning: ["blue", __("Being built")],
			Live: ["green", __("Live")],
			Overdue: ["orange", __("Payment overdue")],
			Suspended: ["red", __("Suspended")],
			Archived: ["grey", __("Archived")],
			Dropped: ["grey", __("Dropped")],
			Failed: ["red", __("Provisioning failed")],
		};
		const [colour, word] = says[doc.status] || ["grey", doc.status];
		return [word, colour, `status,=,${doc.status}`];
	},

	formatters: {
		workspace_name(value, df, doc) {
			return value && value !== doc.name ? `${value} · ${doc.name}` : doc.name;
		},
		// The field is bytes, which nobody reads, so it says what is held
		// against what the plan allows. Over the limit is red, because that is
		// the row somebody is looking for.
		storage_bytes(value, df, doc) {
			const held = Number(value || 0) ? onedesk.tenant.size(value) : "0";
			if (!doc.storage_limit) return held;
			const said = __("{0} of {1}", [held, onedesk.tenant.size(doc.storage_limit)]);
			const over = Number(value || 0) > Number(doc.storage_limit);
			return over ? `<span class="text-danger">${said}</span>` : said;
		},
	},
};
