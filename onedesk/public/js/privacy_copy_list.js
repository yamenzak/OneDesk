// Workspace › Data Copies (one/privacy_copy.py): who asked for a copy of their
// data, and where each stands. Reviewed and sent on the request itself.
frappe.listview_settings["Personal Data Download Request"] = {
	...frappe.listview_settings["Personal Data Download Request"],
	hide_name_column: true,
	add_fields: ["one_status", "user"],
	get_indicator: (doc) =>
		({
			Waiting: [__("Waiting for You"), "orange", "one_status,=,Waiting"],
			Gathering: [__("Being Gathered"), "blue", "one_status,=,Gathering"],
		})[doc.one_status] || [__("Sent"), "green", "one_status,=,Ready"],
	onload(list) {
		list.page.set_title(__("Data Copies"));
	},
};
