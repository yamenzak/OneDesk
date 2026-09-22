// A vehicle log says how far, on how much.
//
// The record carries Last Odometer 49,110 and Current Odometer 49,880 and not
// the 770 between them, which is the only reason anybody writes one down. The
// litres and the price are worse off still: they are behind a collapsed
// Refuelling Details section, on a record whose whole subject is a refuelling.
frappe.ui.form.on("Vehicle Log", {
	refresh: (frm) => onedesk.vehicle.say(frm),
	odometer: (frm) => onedesk.vehicle.say(frm),
	fuel_qty: (frm) => onedesk.vehicle.say(frm),
	price: (frm) => onedesk.vehicle.say(frm),
});

frappe.provide("onedesk.vehicle");

onedesk.vehicle.say = (frm) => {
	const went = flt(frm.doc.odometer) - flt(frm.doc.last_odometer);
	if (frm.is_new() || went <= 0) {
		frm.dashboard.clear_headline();
		return;
	}
	const litres = flt(frm.doc.fuel_qty);
	if (litres <= 0) {
		onedesk.decision.headline(
			frm,
			__("{0} on the odometer since the last log.", [format_number(went, null, 0)]),
			"blue"
		);
		return;
	}

	// Fuel is measured in whatever the vehicle is kept in, so the sentence asks
	// the vehicle rather than assuming litres.
	frappe.db.get_value("Vehicle", frm.doc.license_plate, "uom").then(({ message }) => {
		const unit = (message || {}).uom || __("units");
		const spent = litres * flt(frm.doc.price);
		onedesk.decision.headline(
			frm,
			__("{0} on the odometer since the last log, on {1} {2} costing {3} — {4} per {2}.", [
				format_number(went, null, 0),
				format_number(litres, null, 2),
				unit,
				format_currency(spent, frappe.defaults.get_default("currency")),
				flt(went / litres, 1),
			]),
			"blue"
		);
	});
};
