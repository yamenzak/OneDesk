// Projects: where each one stands, said as its status. ERPNext's list put
// "33%" in place of Open once a task was done, and Open in red otherwise;
// how far it has got is its own column. The manager reads as a name because
// every link to a person does (`show_title_field_in_link` on User).
frappe.listview_settings["Project"] = Object.assign(frappe.listview_settings["Project"] || {}, {
	hide_name_column: true,
	hide_name_filter: true,
	get_indicator(doc) {
		const colour = { Open: "blue", Completed: "green", Cancelled: "gray" }[doc.status] || "gray";
		return [__(doc.status), colour, `status,=,${doc.status}`];
	},
});
