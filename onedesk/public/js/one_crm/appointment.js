// erpnext names its two buttons by the records' ids (CRM-LEAD-…, EV00009);
// they say what they open instead.
frappe.ui.form.on("Appointment", {
	refresh(frm) {
		if (frm.doc.lead) {
			frm.remove_custom_button(frm.doc.lead);
			frm.add_custom_button(__("Lead"), () => frappe.set_route("Form", "Lead", frm.doc.lead));
		}
		if (frm.doc.calendar_event) {
			frm.remove_custom_button(__(frm.doc.calendar_event));
			frm.add_custom_button(__("Calendar Event"), () => frappe.set_route("Form", "Event", frm.doc.calendar_event));
		}
	},
});
