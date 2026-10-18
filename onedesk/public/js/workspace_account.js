frappe.ui.form.on("Workspace Account", {
	onload() {
		frappe.set_re_route("workspace-settings", { section: "plan" });
	},
});
