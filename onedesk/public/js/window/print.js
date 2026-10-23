// A record's print on the window (docs/WINDOW.md): frappe's PrintView, which
// the print page defines when it first loads, so the adapter waits for the
// class. Print and the menu come from the page (page.js); Up goes back to
// the record.
onedesk.window.adapt("print", () => {
	onedesk.window.when(frappe.ui.form, "PrintView", (Print) => {
		if (Object.hasOwn(Print.prototype, "one_window")) return;
		Print.prototype.one_window = true;
		const show = Print.prototype.show;
		Print.prototype.show = function (...args) {
			const said = show.apply(this, args);
			const win = this.page && this.page.window;
			if (win) win.view({ kind: "print", up: () => this.go_to_form_view() });
			return said;
		};
	});
});
