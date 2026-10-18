frappe.listview_settings["Tenant Domain"] = {
	add_fields: ["status", "tenant", "problem", "is_main"],
	hide_name_column: true,
	hide_name_filter: true,

	get_indicator(doc) {
		const says = {
			Pending: ["orange", __("Waiting")],
			Active: ["green", __("Working")],
			Broken: ["red", __("Not working")],
			Gone: ["grey", __("Not at Cloudflare")],
		};
		const [colour, word] = says[doc.status] || ["grey", doc.status];
		return [word, colour, `status,=,${doc.status}`];
	},

	formatters: {
		is_main(value) {
			return value ? frappe.ui.badge.html({ label: __("Main"), theme: "blue" }) : "";
		},
		problem(value) {
			return value ? `<span class="text-muted small" title="${frappe.utils.escape_html(value)}">${frappe.utils.escape_html(value)}</span>` : "";
		},
	},
};
