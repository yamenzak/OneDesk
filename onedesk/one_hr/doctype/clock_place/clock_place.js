// A place is a circle on the earth, and two Floats and a radius do not say
// whether it covers the car park or the road. The map is drawn from the three
// fields rather than edited: it is a reading of them, refreshed whenever one
// changes, so there is no second place where the fence is defined.

frappe.ui.form.on("Clock Place", {
	refresh: draw,
	latitude: draw,
	longitude: draw,
	radius: draw,

	// The button had no handler at all, so it did nothing. It asks the browser
	// where it is, and asks the reader first on a place that already has one:
	// pressing it at a desk otherwise moves the fence to the desk.
	fetch_position(frm) {
		if (!navigator.geolocation) {
			frappe.msgprint({
				message: __("This browser will not give a location."),
				title: __("No Location"),
				indicator: "orange",
			});
			return;
		}

		const move = () =>
			navigator.geolocation.getCurrentPosition(
				({ coords }) => {
					frm.set_value("latitude", coords.latitude);
					frm.set_value("longitude", coords.longitude);
					frappe.show_alert({
						message: __("Accurate to about {0} metres.", [Math.round(coords.accuracy)]),
						indicator: "green",
					});
				},
				(error) =>
					frappe.msgprint({
						message: error.message || __("The browser would not say where it is."),
						title: __("No Location"),
						indicator: "orange",
					}),
				{ enableHighAccuracy: true, timeout: 15000 },
			);

		if (frm.is_new() || !(frm.doc.latitude || frm.doc.longitude)) return move();

		frappe.confirm(
			__("{0} will move to where this browser is. Everyone checking in there is measured from the new centre.", [
				frm.doc.label || frm.doc.name,
			]),
			move,
		);
	},
});

// Written onto the doc rather than through `set_value`, so opening a record
// does not mark it unsaved. Frappe's Geolocation control reads a circle as a
// Point carrying `point_type` and `radius`.
function draw(frm) {
	const { latitude, longitude, radius } = frm.doc;
	if (!latitude && !longitude) return;

	frm.doc.area = JSON.stringify({
		type: "FeatureCollection",
		features: [
			{
				type: "Feature",
				properties: { point_type: "circle", radius: radius || 0 },
				geometry: { type: "Point", coordinates: [longitude, latitude] },
			},
		],
	});
	frm.refresh_field("area");
	fit(frm.get_field("area"));
}

// Leaflet measures its container once, when the control is made, and the map
// has a row of its own that gets its width after that. Without this the circle
// is on the map and the map is a pixel wide.
function fit(control) {
	if (!control) return;

	setTimeout(() => {
		if (!control.map) return;
		control.map.invalidateSize();

		const drawn = control.editableLayers;
		if (drawn && drawn.getLayers().length) {
			control.map.fitBounds(drawn.getBounds(), { maxZoom: 17, padding: [24, 24] });
		}
	}, 300);
}
