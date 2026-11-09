frappe.listview_settings["Workspace Error"] = {
	add_fields: ["status"],
	hide_name_column: true,

	get_indicator(doc) {
		const colour = doc.status === "Fixed" ? "green" : "red";
		return [__(doc.status), colour, `status,=,${doc.status}`];
	},
};
