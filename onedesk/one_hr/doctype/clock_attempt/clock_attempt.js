frappe.ui.form.on("Clock Attempt", {
	refresh(frm) {
		frm.disable_save();
		frm.get_field("signals")?.$wrapper.addClass("one-static-grid");
	},
});
