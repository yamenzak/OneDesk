// A log, so it is read and never opened: the workspace leads, then what
// happened, in words and in the operator's own language (one_admin/log.py),
// who did it, and when. The colour is the whole of what a row says at a
// glance: the two that cost a customer something are red, the warnings
// orange, and coming back green. A row opens its workspace, whose Activity
// holds its log too.
frappe.listview_settings["Tenant Event"] = {
	add_fields: ["kind", "by", "by_user", "tenant"],
	hide_name_column: true,
	hide_name_filter: true,

	get_form_link(doc) {
		return doc.tenant ? `/desk/tenant/${encodeURIComponent(doc.tenant)}` : `/desk/tenant-event/${encodeURIComponent(doc.name)}`;
	},

	formatters: {
		// What happened, as a badge: the colour is the whole of it at a glance.
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
		// A fixed phrase is stored in English and shown translated; a plan's
		// name or two sizes are data and pass through as they are.
		detail(value) {
			return value ? frappe.utils.escape_html(__(value)) : "";
		},
		by(value, df, doc) {
			if (value === "Operator" && doc.by_user) return frappe.utils.escape_html(frappe.user.full_name(doc.by_user));
			return value === "Customer" ? __("The customer") : __("One");
		},
	},
};
