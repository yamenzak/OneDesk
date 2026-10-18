frappe.ui.form.on("AI Action Setting", {
	onload(frm) {
		frappe.set_re_route("workspace-settings", { section: "oneai", action: frm.doc.action || undefined });
	},
});
