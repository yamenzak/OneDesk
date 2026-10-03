// Workspace › Account Deletions (one/privacy.py): who asked for their account
// to be deleted, and where each stands. Decided on the request itself.
frappe.listview_settings["Personal Data Deletion Request"] = {
	...frappe.listview_settings["Personal Data Deletion Request"],
	hide_name_column: true,
	add_fields: ["email", "status"],
	get_indicator: (doc) =>
		({
			"Pending Verification": [__("Unconfirmed"), "gray", "status,=,Pending Verification"],
			"Pending Approval": [__("Waiting for You"), "orange", "status,=,Pending Approval"],
			"On Hold": [__("On Hold"), "blue", "status,=,On Hold"],
			Deleted: [__("Deleted"), "gray", "status,=,Deleted"],
		})[doc.status] || [__(doc.status), "gray", `status,=,${doc.status}`],
	onload(list) {
		list.page.set_title(__("Account Deletions"));
	},
};
