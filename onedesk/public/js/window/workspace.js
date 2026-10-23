// A workspace on the window (docs/WINDOW.md): frappe's Workspace, an app's
// own home. Its Save (while it is edited) and its menu lead the command row.
onedesk.window.adapt("workspace", () => {
	const Workspace = frappe.views && frappe.views.Workspace;
	if (!Workspace || Object.hasOwn(Workspace.prototype, "one_window")) return;
	Workspace.prototype.one_window = true;
	const show = Workspace.prototype.show;
	Workspace.prototype.show = function (...args) {
		const said = show.apply(this, args);
		const win = this.page && this.page.window;
		if (win) {
			win.view({
				kind: "workspace",
				primary: this.page.btn_primary,
				menu: { $button: this.page.menu_btn_group, dropdown: this.page.menu_dropdown },
			});
		}
		return said;
	};
});
