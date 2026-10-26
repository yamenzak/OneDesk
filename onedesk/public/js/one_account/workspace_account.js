frappe.ui.form.on("Workspace Account", {
	onload() {
		frappe.set_re_route("one", { center: "account", at: "plan" });
	},
});
