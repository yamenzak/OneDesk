// Preview plays the channel as a paired screen would, now.
frappe.ui.form.on("Display Channel", {
	refresh(frm) {
		if (frm.is_new()) return;
		frm.add_custom_button(__("Preview"), () => window.open(`/tv?preview=${encodeURIComponent(frm.doc.name)}`, "_blank"));
		if (frm.doc.widget_collection) {
			frm.add_custom_button(__("Edit Layout"), () => frappe.set_route("display-layout", frm.doc.widget_collection));
		}
	},
});
