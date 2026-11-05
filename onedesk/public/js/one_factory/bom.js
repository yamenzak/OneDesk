frappe.ui.form.on("BOM", {
	refresh(frm) {
		if (frm.doc.__onload?.one_costs_hidden) frm.toggle_display("costing", false);
	},
});
