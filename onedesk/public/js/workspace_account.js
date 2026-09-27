// The workspace's own account is Workspace › Plan and Credits and Domains in
// Settings, drawn from the same copy (one/account.py). The desk form was a
// second screen for one record, so it sends its reader there, replacing
// itself in the history so Back does not bounce.
frappe.ui.form.on("Workspace Account", {
	onload() {
		frappe.set_re_route("workspace-settings", { section: "plan" });
	},
});
