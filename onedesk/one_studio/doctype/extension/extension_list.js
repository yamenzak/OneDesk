// The extensions, each with the word its head says: On, Off, Refused by Review,
// or Cannot Run Here where the bench does not run server scripts. The name is
// a random one, so it is neither a column nor a filter.
frappe.listview_settings["Extension"] = {
	add_fields: ["enabled", "review", "runs", "view", "event"],
	hide_name_column: true,
	hide_name_filter: true,
	get_indicator(doc) {
		if (doc.enabled) return [__("On"), "green", "enabled,=,1"];
		if (doc.review === "Refused") return [__("Refused by Review"), "red", "review,=,Refused"];
		if (doc.runs === "On Server" && frappe.boot.one_studio_server === false)
			return [__("Cannot Run Here"), "orange", "runs,=,On Server"];
		return [__("Off"), "gray", "enabled,=,0"];
	},
	formatters: {
		// When: the event on the server, the form or the list on the screen,
		// which also says where it runs. A screen one's event is frappe's
		// default and means nothing.
		event: (value, df, doc) => __(doc.runs === "On Screen" ? doc.view : value),
	},
};
