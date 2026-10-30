// Widgets are placed on the layout page, where the screen is drawn; this
// form keeps the table for anybody who wants the numbers.
frappe.ui.form.on("Widget Collection", {
	refresh(frm) {
		if (frm.is_new()) return;
		frm.add_custom_button(__("Edit Layout"), () => frappe.set_route("display-layout", frm.doc.name));
		frm.change_custom_button_type(__("Edit Layout"), null, "primary");
	},
});
