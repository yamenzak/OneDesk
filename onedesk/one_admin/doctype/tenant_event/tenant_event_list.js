frappe.listview_settings["Tenant Event"] = {
	add_fields: ["kind", "by", "by_user", "tenant"],
	hide_name_column: true,
	hide_name_filter: true,

	get_form_link(doc) {
		return doc.tenant ? `/desk/tenant/${encodeURIComponent(doc.tenant)}` : `/desk/tenant-event/${encodeURIComponent(doc.name)}`;
	},

	formatters: {
		kind(value) {
			const says = {
				"Over Storage": "orange",
				Overdue: "orange",
				Suspended: "red",
				Dropped: "red",
				Restored: "green",
				"Plan Change Pending": "orange",
			};
			return value ? frappe.ui.badge.html({ label: __(value), theme: says[value] || "gray" }) : "";
		},
		tenant(value) {
			return (value && frappe.utils.get_link_title("Tenant", value)) || value;
		},
		detail(value) {
			return value ? frappe.utils.escape_html(__(value)) : "";
		},
		by(value, df, doc) {
			if (value === "Operator" && doc.by_user) return frappe.utils.escape_html(frappe.user.full_name(doc.by_user));
			return value === "Customer" ? __("Customer") : onedesk.names.of("one");
		},
	},
};
