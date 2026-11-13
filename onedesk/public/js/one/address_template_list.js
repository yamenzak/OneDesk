// The name of an address template is its country, so the title column already
// says it and an ID box beside the Country filter is the same search twice.
frappe.listview_settings["Address Template"] = {
	...frappe.listview_settings["Address Template"],
	hide_name_filter: true,
};
