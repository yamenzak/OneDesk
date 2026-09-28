// An action's model and added instructions are changed where the actions are
// listed, OneAI › Actions, in a dialog there. The desk form sends its reader
// to that dialog, as the account's form sends its reader to Plan and Credits.
frappe.ui.form.on("AI Action Setting", {
	onload(frm) {
		frappe.set_re_route("workspace-settings", { section: "oneai", action: frm.doc.action || undefined });
	},
});
