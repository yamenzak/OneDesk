// Purchase Orders: the supplier with room for its name, where each stands,
// its dates, its total and how much is received and billed. The number is
// left off, as on Receipts; it is still on hover and in search.
frappe.listview_settings["Purchase Order"] = Object.assign(frappe.listview_settings["Purchase Order"] || {}, {
	hide_name_column: true,
});
