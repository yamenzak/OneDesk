
frappe.ui.form.on("Clock Place", {
	refresh: draw,
	latitude: draw,
	longitude: draw,
	radius: draw,

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

function draw(frm) {
	const { latitude, longitude, radius } = frm.doc;
	if (!latitude && !longitude) return;

	const area = JSON.stringify({
		type: "FeatureCollection",
		features: [
			{
				type: "Feature",
				properties: { point_type: "circle", radius: radius || 0 },
				geometry: { type: "Point", coordinates: [longitude, latitude] },
			},
		],
	});
	if (area !== frm.doc.area) {
		frm.doc.area = area;
		frm.refresh_field("area");
	}
	fit(frm.get_field("area"));
}

function fit(control, tries = 10) {
	if (!control) return;

	setTimeout(() => {
		if (!control.map) return;
		const box = control.map.getContainer();
		if (!box.offsetWidth || !box.offsetHeight) {
			if (tries) fit(control, tries - 1);
			return;
		}
		control.map.invalidateSize();

		const drawn = control.editableLayers;
		const bounds = drawn && drawn.getLayers().length && drawn.getBounds();
		if (bounds && bounds.isValid()) {
			control.map.fitBounds(bounds, { maxZoom: 17, padding: [24, 24] });
		}
	}, 300);
}
