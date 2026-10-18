frappe.ui.form.on("Delivery Trip", {
	refresh(frm) {
		const maps = !!frm.doc.__onload?.maps;
		frm.toggle_display(["calculate_arrival_time", "optimize_route", "total_distance"], maps);
	},
});
