// Deliveries: the customer, where each stands, its date, its total and how
// much is billed, without ERPNext's number column taking the customer's room.
// The number is still on hover and in search.
frappe.listview_settings["Delivery Note"] = Object.assign(frappe.listview_settings["Delivery Note"] || {}, {
	hide_name_column: true,
});
