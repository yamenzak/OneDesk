frappe.ui.form.on("Stock Reconciliation", {
	refresh(frm) {
		const grid = frm.fields_dict.items?.grid;
		if (!grid || grid.one_counted) return;
		grid.one_counted = true;
		grid.update_docfield_property("quantity_difference", "formatter", (value, df, options) => {
			if (value === undefined || value === null || value === "") return "";
			const shown = format_number(flt(value), null, flt(value) % 1 ? 2 : 0);
			return frappe.form.formatters._right(`${flt(value) > 0 ? "+" : ""}${shown}`, options);
		});
		grid.refresh();
	},
});
