// Receipts: the supplier, where each stands, its date, its total and how much
// is billed, without ERPNext's number column taking the supplier's room. The
// number is still on hover and in search.
frappe.listview_settings["Purchase Receipt"] = Object.assign(frappe.listview_settings["Purchase Receipt"] || {}, {
	hide_name_column: true,
});
