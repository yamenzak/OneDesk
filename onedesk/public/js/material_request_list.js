// Material Requests: what is asked for, where it stands, when it is wanted,
// for which project and how much is ordered. The title names the items and
// whether they are bought or made, so the number is left off, as on Receipts;
// it is still on hover and in search.
frappe.listview_settings["Material Request"] = Object.assign(frappe.listview_settings["Material Request"] || {}, {
	hide_name_column: true,
});
