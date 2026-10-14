// Suppliers: the name with room for it, where each stands, its group and the
// money it bills in. The name is the record's own, so frappe's number column
// said it twice and cut it; whether it is a company or a person is on the
// supplier, as nearly every one is a company.
frappe.listview_settings["Supplier"] = Object.assign(frappe.listview_settings["Supplier"] || {}, {
	hide_name_column: true,
});
