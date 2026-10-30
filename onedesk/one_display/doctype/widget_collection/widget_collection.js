// Widgets are placed in OneSlide's editor, where the screen is drawn
// (one_display/screen.py); this form keeps the table for anybody who wants
// the numbers.
frappe.ui.form.on("Widget Collection", {
	refresh(frm) {
		if (frm.is_new()) return;
		frm.add_custom_button(__("Edit Layout"), () => onedesk.display_layout(frm.doc.name));
		frm.change_custom_button_type(__("Edit Layout"), null, "primary");
	},
});

// The collection's backdrop presentation, made the first time, opened in the editor.
onedesk.display_layout = async (collection) => {
	const made = await frappe.xcall("onedesk.one_display.screen.backdrop", { collection });
	frappe.set_route("presentation", made.presentation);
};
