// A count's line says what was counted, what the books held and the
// difference. ERPNext keeps the difference as text ("-3.0"), so it is printed
// here as the number it is, signed and right-aligned like the rest.
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
