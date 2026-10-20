frappe.ui.form.on("Item", {
	setup(frm) {
		// A size is typed in a length: millimetres, centimetres, inches.
		frm.set_query("one_size_uom", () => ({ filters: { name: ["in", frappe.boot.one_measure?.lengths || []] } }));
	},
	toggle_has_serial_batch_fields(frm) {
		if (!frm.doc.__onload?.stock_exists) return;
		["has_serial_no", "has_batch_no"].forEach((fieldname) => frm.set_df_property(fieldname, "read_only", 1));
	},
});
