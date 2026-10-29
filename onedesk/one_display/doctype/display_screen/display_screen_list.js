// Screens: a TV opens /tv and shows a code; Pair a Screen takes the code here.
frappe.provide("onedesk.display");

onedesk.display.pair = (listview) => {
	const dialog = new frappe.ui.Dialog({
		title: __("Pair a Screen"),
		fields: [
			{
				fieldname: "code",
				fieldtype: "Data",
				label: __("Code"),
				reqd: 1,
				description: __("Open {0} on the screen. It shows this code.", [`${location.origin}/tv`]),
			},
			{ fieldname: "screen_name", fieldtype: "Data", label: __("Screen Name"), reqd: 1 },
			{ fieldname: "channel", fieldtype: "Link", options: "Display Channel", label: __("Channel"), reqd: 1 },
			{ fieldname: "mode", fieldtype: "Select", options: "Board\nKiosk", default: "Board", label: __("Mode") },
		],
		primary_action_label: __("Pair"),
		primary_action: (values) =>
			frappe.xcall("onedesk.one_display.screens.pair", values).then(() => {
				dialog.hide();
				frappe.show_alert({ message: __("Paired."), indicator: "green" });
				listview?.refresh();
			}),
	});
	dialog.show();
};

onedesk.display.alert = () => {
	const dialog = new frappe.ui.Dialog({
		title: __("Send an Emergency Alert"),
		fields: [
			{
				fieldname: "message",
				fieldtype: "Small Text",
				label: __("Message"),
				reqd: 1,
				description: __("Every screen shows it over everything else, and reads it out, until it is ended."),
			},
		],
		primary_action_label: __("Send to Every Screen"),
		primary_action: ({ message }) =>
			frappe.xcall("onedesk.one_display.screens.alert", { message }).then((said) => {
				dialog.hide();
				frappe.show_alert({ message: said, indicator: "red" });
			}),
	});
	dialog.show();
};

frappe.listview_settings["Display Screen"] = {
	add_fields: ["status", "last_seen", "dark", "muted"],
	hide_name_column: true,
	get_indicator(doc) {
		if (doc.status !== "Paired") return [__("Waiting to Pair"), "orange", "status,=,Waiting to Pair"];
		if (doc.dark) return [__("Off"), "gray", "dark,=,1"];
		const seen = doc.last_seen && moment().diff(frappe.datetime.convert_to_user_tz(doc.last_seen), "seconds") < 90;
		return seen ? [__("Online"), "green", "status,=,Paired"] : [__("Offline"), "red", "status,=,Paired"];
	},
	// Adding a screen is pairing one: a screen record only comes from a TV.
	primary_action() {
		onedesk.display.pair(cur_list);
	},
	onload(listview) {
		listview.page.add_menu_item(__("Send an Emergency Alert"), () => onedesk.display.alert());
		listview.page.add_menu_item(__("End the Alert"), () =>
			frappe.xcall("onedesk.one_display.screens.alert", { message: "" }).then((said) =>
				frappe.show_alert({ message: said, indicator: "green" })
			)
		);
	},
};
