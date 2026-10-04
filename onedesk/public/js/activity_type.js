// An activity's rates for a person are listed under it, with + to add one
// (one_project/rates.py), so ERPNext's button opening the same list goes.
frappe.ui.form.on("Activity Type", {
	refresh(frm) {
		frm.remove_custom_button(__("Activity Cost per Employee"));
	},
});
