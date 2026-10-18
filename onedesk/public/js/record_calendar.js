frappe.provide("onedesk");

onedesk.record_calendar = (frm) => {
	if (frm.is_new()) return;
	frm.add_custom_button(__("Calendar"), () =>
		frappe.set_route("onecalendar", { doctype: frm.doctype, name: frm.doc.name })
	);
};
