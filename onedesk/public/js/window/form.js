// A form on the window (docs/WINDOW.md): frappe's Form, saying what it has
// through `window.view`. Its Save, actions and tabs stay where frappe put
// them; the window gives it Refresh and Up.
onedesk.window.adapt("form", () => {
	const Form = frappe.ui.form && frappe.ui.form.Form;
	if (!Form || Object.hasOwn(Form.prototype, "one_window")) return;
	Form.prototype.one_window = true;
	const setup = Form.prototype.setup;
	Form.prototype.setup = function (...args) {
		const said = setup.apply(this, args);
		const win = this.page && this.page.window;
		if (win) {
			win.view({
				kind: "form",
				refresh: () => !this.is_new() && this.reload_doc(),
				up: () => frappe.set_route("List", this.doctype),
			});
		}
		return said;
	};
});
