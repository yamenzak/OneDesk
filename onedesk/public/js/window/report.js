// A query report on the window (docs/ONEINTERFACE.md): frappe's QueryReport, whose
// page frappe's report factory makes rather than its page loader, so it
// hands over its primary button and menu itself. Its filters stay the view
// row and its Refresh is frappe's (moved by the frame); it says how many rows
// it shows, with a tree's Expand All beside them. Its columns are wide
// enough for what they hold.
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

	// frappe sizes a column by its heading and its first row, so an amount
	// further down, a date, or the row number from 10 on was cut. A money
	// column is as wide as an amount in the millions, a date as a date, the
	// row number as the count of rows.
	const LEAST = { Currency: 150, Date: 110, Datetime: 150 };
	const columns = Report.prototype.prepare_columns;
	Report.prototype.prepare_columns = function (...args) {
		const prepared = columns.apply(this, args);
		if (this.page && this.page.window) {
			for (const column of prepared || []) {
				const least = LEAST[column.fieldtype];
				if (least && (column.width || 0) < least) column.width = least;
			}
		}
		return prepared;
	};

	const render = Report.prototype.render_datatable;
	Report.prototype.render_datatable = function (...args) {
		const said = render.apply(this, args);
		const table = this.datatable;
		const at = this.page && this.page.window && table && table.datamanager ? table.datamanager.getColumnIndexById("_rowIndex") : -1;
		if (at >= 0) {
			const width = 24 + 8 * String((this.data || []).length).length;
			if ((table.datamanager.getColumn(at).width || 0) < width) {
				table.datamanager.updateColumn(at, { width });
				table.columnmanager.setColumnHeaderWidth(at);
				table.columnmanager.setColumnWidth(at);
				table.style.refreshStickyColumns();
			}
		}
		return said;
	};

	// frappe's footer says how to type a filter and how long the query took;
	// the status row says how many rows there are, the total row aside, and
	// keeps only a tree's Expand All and Collapse All beside them.
	const footer = Report.prototype.show_footer_message;
	Report.prototype.show_footer_message = function (...args) {
		const said = footer.apply(this, args);
		const win = this.page && this.page.window;
		if (win) {
			this.$report_footer.children(":not(.tree-footer)").remove();
			const total = this.raw_data && this.raw_data.add_total_row && !(this.report_settings || {}).tree ? 1 : 0;
			const rows = Math.max((this.data || []).length - total, 0);
			win.view({ status: __("{0} rows", [rows]), more: this.$report_footer });
		}
		return said;
	};
});
