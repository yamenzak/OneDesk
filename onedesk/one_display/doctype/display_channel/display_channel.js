// Preview plays the channel as a paired screen would, now.
frappe.ui.form.on("Display Channel", {
	refresh(frm) {
		const grid = frm.fields_dict.programme.grid;
		grid.update_docfield_property("plays", "options", "Slides\nWidgets\nScreensaver\nScreen Off");
		grid.update_docfield_property("music_playlist", "hidden", 1);
		grid.reset_grid();
		if (frm.is_new()) return;
		frm.add_custom_button(__("Preview"), () => window.open(`/tv?preview=${encodeURIComponent(frm.doc.name)}`, "_blank"));
		// with no layout yet, one is made and opened on its templates
		const label = frm.doc.widget_collection ? __("Edit Layout") : __("Choose a Layout");
		frm.add_custom_button(label, () => frappe.xcall("onedesk.one_display.starters.for_channel", { channel: frm.doc.name }).then((made) => frappe.set_route("presentation", made.presentation)));
		if (!frm.doc.widget_collection) frm.change_custom_button_type(label, null, "primary");
	},
});
