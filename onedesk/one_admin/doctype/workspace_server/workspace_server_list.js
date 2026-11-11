frappe.listview_settings["Workspace Server"] = {
	add_fields: ["status", "capacity", "tenant"],
	hide_name_column: true,

	get_indicator(doc) {
		const colour = { Up: "green", "Filling Up": "orange", Full: "orange", Down: "red", Connecting: "blue" }[doc.status] || "gray";
		return [__(doc.status), colour, `status,=,${doc.status}`];
	},

	onload(listview) {
		listview.page.add_menu_item(__("Connect Server"), () => {
			frappe.prompt(
				[{ fieldname: "region", fieldtype: "Data", label: __("Region"), reqd: 1, default: "eu-frankfurt-1", description: __("Copies of a workspace are made in this region.") }],
				async ({ region }) => {
					const said = await frappe.xcall("onedesk.one_admin.operator.connect_server", { region });
					const shown = new frappe.ui.Dialog({
						title: __("Connect {0}", [said.server]),
						fields: [
							{ fieldname: "command", fieldtype: "Code", label: __("Command"), read_only: 1, default: said.command, description: __("Run once on the machine as root within an hour.") },
						],
						primary_action_label: __("Copy Command"),
						primary_action() {
							frappe.utils.copy_to_clipboard(said.command);
							shown.hide();
						},
					});
					shown.show();
				},
				__("Connect Server"),
				__("Get Command"),
			);
		});
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
