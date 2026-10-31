// A place is found by its name (one/weather.py search), so nobody types
// coordinates; they stay on the form for a place no search finds.
frappe.ui.form.on("Weather Place", {
	refresh(frm) {
		if (!frm.perm[0]?.write) return;
		frm.add_custom_button(__("Find a Place"), () => find_place(frm));
		if (frm.is_new()) frm.change_custom_button_type(__("Find a Place"), null, "primary");
	},
});

function find_place(frm) {
	let asked = 0;
	const dialog = new frappe.ui.Dialog({
		title: __("Find a Place"),
		fields: [
			{ fieldname: "query", fieldtype: "Data", label: __("Town or City"), default: frm.doc.place_name || "" },
			{ fieldname: "found", fieldtype: "HTML" },
		],
	});
	const wrapper = dialog.get_field("found").$wrapper;
	const search = frappe.utils.debounce(async (query) => {
		const mine = ++asked;
		if ((query || "").trim().length < 2) return wrapper.empty();
		wrapper.html(`<p class="text-muted">${__("Searching…")}</p>`);
		const { message: places } = await frappe.call({ method: "onedesk.one.weather.search", args: { query } });
		if (mine !== asked) return;
		wrapper.empty();
		if (!places?.length) return wrapper.html(`<p class="text-muted">${__("No place by that name.")}</p>`);
		for (const place of places) {
			const where = [place.region, place.country].filter(Boolean).join(", ");
			const pick = () => {
				frm.set_value({
					place_name: frm.doc.place_name || place.name,
					region: place.region,
					country: place.country,
					latitude: place.latitude,
					longitude: place.longitude,
				});
				dialog.hide();
			};
			const label = where ? `${place.name} · ${where}` : place.name;
			wrapper.append(frappe.ui.button({ label, variant: "outline", css_class: "btn-block", onclick: pick }));
		}
	}, 400);
	dialog.fields_dict.query.$input.on("input", (event) => search(event.target.value));
	dialog.show();
	if (frm.doc.place_name) search(frm.doc.place_name);
}
