frappe.ui.form.on("Reading Settings", {
	refresh(frm) {
		const said = (frm.doc.__onload || {}).measured;
		if (said) frm.set_intro(frappe.utils.escape_html(said), "blue");
	},
});
