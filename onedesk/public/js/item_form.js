frappe.ui.form.on("Item", {
	toggle_has_serial_batch_fields(frm) {
		if (!frm.doc.__onload?.stock_exists) return;
		["has_serial_no", "has_batch_no"].forEach((fieldname) => frm.set_df_property(fieldname, "read_only", 1));
	},
});
