// The workspace list.
//
// Every rung gets its own colour, because the question somebody scans this list
// to answer is "is anything wrong", and a column of identical grey pills does
// not answer it. Frappe's default colours a Select by position in the options,
// which put Live and Dropped in the same family.
frappe.listview_settings["Tenant"] = {
	add_fields: ["status", "storage_bytes", "storage_limit", "domain"],
	hide_name_column: true,

	get_indicator(doc) {
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
		// The field is bytes, which nobody reads. Over the limit is red, because
		// that is the row somebody is looking for.
		storage_bytes(value, df, doc) {
			const held = onedesk.tenant.size(value);
			if (!doc.storage_limit) return held;
			const over = Number(value || 0) > Number(doc.storage_limit);
			return over ? `<span class="text-danger">${held}</span>` : held;
		},
	},
};
