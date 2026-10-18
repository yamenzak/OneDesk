frappe.listview_settings["Tenant"] = {
	add_fields: ["status", "storage_bytes", "storage_limit", "domain", "is_house"],
	hide_name_column: true,
	hide_name_filter: true,

	get_indicator(doc) {
		if (doc.is_house) return [__("Internal"), "blue", "is_house,=,1"];
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
		storage_bytes(value, df, doc) {
			const held = Number(value || 0) ? onedesk.tenant.size(value) : "0";
			if (!doc.storage_limit) return held;
			const said = __("{0} of {1}", [held, onedesk.tenant.size(doc.storage_limit)]);
			const over = Number(value || 0) > Number(doc.storage_limit);
			return over ? `<span class="text-danger">${said}</span>` : said;
		},
	},
};
