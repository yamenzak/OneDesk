// Headlines: the title has the room, no ID column, and a Hidden pill on a
// headline nobody sees.
frappe.listview_settings["News Item"] = {
	hide_name_column: true,
	add_fields: ["hidden_item", "image"],
	get_indicator(doc) {
		if (doc.hidden_item) return [__("Hidden"), "gray", "hidden_item,=,1"];
	},
};
