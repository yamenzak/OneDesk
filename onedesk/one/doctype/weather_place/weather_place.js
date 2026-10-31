// The Place field is an autocomplete over the place search (one/weather.py
// suggest): typing lists the towns that answer to it, and choosing one
// fills in its region, country and coordinates, which are never typed and
// show, read only, once the place is saved. The
// location button beside it asks the server where the request came from
// (weather.located), so the browser asks the person nothing.
frappe.ui.form.on("Weather Place", {
	setup(frm) {
		frm.set_query("place_name", () => ({ query: "onedesk.one.weather.suggest" }));
	},
	refresh(frm) {
		const field = frm.fields_dict.place_name;
		const $input = field?.$input;
		frm._one_named = frm.doc.place_name;
		if (!$input || $input.data("one-place")) return;
		$input.data("one-place", true);
		// A place no search finds keeps the name typed for it.
		field.df.ignore_validation = 1;
		// The chosen row carries the whole place; the field's own value is only its name.
		$input.on("awesomplete-select", (e) => {
			frm._one_place = $(e.originalEvent?.origin).data("item.autocomplete") || null;
		});
		// Drawn as frappe draws a Link field's open arrow: an icon in the field.
		const $locate = $(`<span class="link-btn" style="display: inline-flex">
				<a title="${__("Use Where I Am")}">${frappe.utils.icon("locate-fixed", "sm")}</a></span>`)
			.on("click", () => {
				frappe.call({ method: "onedesk.one.weather.located", freeze: true }).then(({ message: place }) => {
					if (!place?.name) {
						frappe.show_alert({ message: __("Where you are could not be found. Type the place instead."), indicator: "orange" });
						return;
					}
					frm._one_place = null;
					frm._one_named = place.name;
					frm.set_value({
						place_name: place.name,
						region: place.region || "",
						country: place.country || "",
						latitude: place.latitude,
						longitude: place.longitude,
					});
				});
			});
		$input.css("padding-inline-end", "var(--padding-xl)");
		$input.parent().css("position", "relative").append($locate);
		$locate.find("a").css("cursor", "pointer");
	},
	place_name(frm) {
		const place = frm._one_place;
		frm._one_place = null;
		if (frm.doc.place_name === frm._one_named) return;
		if (!place || place.value !== frm.doc.place_name || place.latitude == null) {
			// A name typed rather than chosen is somewhere no one has said yet.
			frm.set_value({ region: "", country: "", latitude: 0, longitude: 0 });
			return;
		}
		frm._one_named = place.name;
		frm.set_value({
			place_name: place.name,
			region: place.region || "",
			country: place.country || "",
			latitude: place.latitude,
			longitude: place.longitude,
		});
	},
});
