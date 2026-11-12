frappe.listview_settings["OneOS Session"] = {
	add_fields: ["state", "stop_reason"],
	hide_name_column: true,

	get_indicator(doc) {
		const colour = { Starting: "blue", Running: "green", Stopped: "gray" }[doc.state] || "gray";
		return [__(doc.state), colour, `state,=,${doc.state}`];
	},
};
