frappe.listview_settings["Workspace Server"] = {
	add_fields: ["status", "capacity", "tenant"],
	hide_name_column: true,

	get_indicator(doc) {
		const colour = { Up: "green", "Filling Up": "orange", Full: "orange", Down: "red" }[doc.status] || "gray";
		return [__(doc.status), colour, `status,=,${doc.status}`];
	},

	async primary_action() {
		const go = await onedesk.interface.ask({
			question: __("Order a server?"),
			effect: __("Takes about 25 minutes. $24 a month."),
			verb: __("Order Server"),
		});
		if (!go) return;
		await frappe.xcall("onedesk.one_admin.operator.order_server");
		frappe.show_alert({ message: __("Server ordered."), indicator: "green" });
	},
};
