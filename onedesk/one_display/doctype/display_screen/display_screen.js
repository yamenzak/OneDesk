// A screen is told what to do from here; it hears it within a few seconds.
const SCREEN_COMMANDS = [
	["reload", __("Reload")],
	["mute", __("Mute"), (doc) => !doc.muted],
	["unmute", __("Unmute"), (doc) => doc.muted],
	["off", __("Turn Off"), (doc) => !doc.dark],
	["on", __("Turn On"), (doc) => doc.dark],
];

frappe.ui.form.on("Display Screen", {
	refresh(frm) {
		if (frm.is_new() || frm.doc.status !== "Paired") return;
		for (const [command, label, shown] of SCREEN_COMMANDS) {
			if (shown && !shown(frm.doc)) continue;
			frm.add_custom_button(
				label,
				() =>
					frappe
						.xcall("onedesk.one_display.screens.control", { screen: frm.doc.name, command })
						.then((said) => {
							frappe.show_alert({ message: said, indicator: "green" });
							frm.reload_doc();
						}),
				__("Screen")
			);
		}
	},
});
