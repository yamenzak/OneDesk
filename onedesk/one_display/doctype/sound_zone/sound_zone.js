// A zone's schedule only plays music or stays quiet; a channel's only shows.
frappe.ui.form.on("Sound Zone", {
	refresh(frm) {
		const grid = frm.fields_dict.programme.grid;
		grid.update_docfield_property("plays", "options", "Music\nMuted");
		for (const field of ["slide_playlist", "widget_collection"]) grid.update_docfield_property(field, "hidden", 1);
		grid.reset_grid();
	},
});
