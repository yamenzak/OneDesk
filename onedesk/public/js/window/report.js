// A query report on the window (docs/WINDOW.md): frappe's QueryReport, whose
// page frappe's report factory makes rather than its page loader, so it
// hands over its primary button and menu itself. Its filters stay the view
// row and its Refresh is frappe's (moved by the frame); it says how many rows
// it shows, with frappe's own footer (the filter hint, the time it took, a
// tree's Expand All) beside them.
onedesk.window.adapt("report", () => {
	const Report = frappe.views && frappe.views.QueryReport;
	if (!Report || Object.hasOwn(Report.prototype, "one_window")) return;
	Report.prototype.one_window = true;

	const wrapper = Report.prototype.setup_report_wrapper;
	Report.prototype.setup_report_wrapper = function (...args) {
		const said = wrapper.apply(this, args);
		const win = this.page && this.page.window;
		if (win) {
			win.view({
				kind: "query-report",
				primary: this.page.btn_primary,
				menu: { $button: this.page.menu_btn_group, dropdown: this.page.menu_dropdown },
				up: onedesk.window.home,
			});
		}
		return said;
	};

	const footer = Report.prototype.show_footer_message;
	Report.prototype.show_footer_message = function (...args) {
		const said = footer.apply(this, args);
		const win = this.page && this.page.window;
		if (win) win.view({ status: __("{0} rows", [(this.data || []).length]), more: this.$report_footer });
		return said;
	};
});
