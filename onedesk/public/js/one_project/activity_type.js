frappe.ui.form.on("Activity Type", {
	refresh(frm) {
		frm.remove_custom_button(__("Activity Cost per Employee"));
	},
});
