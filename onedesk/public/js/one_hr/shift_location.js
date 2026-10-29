// hrms hides a Shift Location's radius and position unless its own
// geolocation tracking is on. One's Check Location reads them either way
// (one_hr/gates.py), so they show whenever that gate is on.
frappe.ui.form.on("Shift Location", {
	refresh: async (frm) => {
		const gated = await frappe.db.get_single_value("HR Settings", "one_gate_place");
		if (!gated) return;
		for (const field of ["checkin_radius", "fetch_geolocation", "latitude", "longitude", "geolocation"]) {
			frm.toggle_display(field, true);
		}
	},
});
