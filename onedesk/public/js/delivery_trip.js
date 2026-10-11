// A delivery trip: its route buttons and distance only where Google Maps can
// answer them (one_inventory/trips.py). Without a key in Google Settings,
// ERPNext's Calculate Estimated Arrival Times and Optimize Route only say they
// cannot, and the distance stays 0.
frappe.ui.form.on("Delivery Trip", {
	refresh(frm) {
		const maps = !!frm.doc.__onload?.maps;
		frm.toggle_display(["calculate_arrival_time", "optimize_route", "total_distance"], maps);
	},
});
