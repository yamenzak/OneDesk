// An item with stock keeps Batches and Serial Numbers locked, as ERPNext's
// own refresh locks them. Its toggle_has_serial_batch_fields, triggered after
// that, turns both back on whenever lots are on in Stock Settings; the server
// refuses the change anyway (Item.cant_change), so the switch only looked open.
frappe.ui.form.on("Item", {
	toggle_has_serial_batch_fields(frm) {
		if (!frm.doc.__onload?.stock_exists) return;
		["has_serial_no", "has_batch_no"].forEach((fieldname) => frm.set_df_property(fieldname, "read_only", 1));
	},
});
