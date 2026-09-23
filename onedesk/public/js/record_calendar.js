// Calendar on a record: OneCalendar narrowed to it, with the layers that can
// draw that doctype's (one_calendar/layers.py, `about`) — a project's tasks, a
// deal's or a lead's next step, an employee's leave, and every event about it.
frappe.provide("onedesk");

onedesk.record_calendar = (frm) => {
	if (frm.is_new()) return;
	frm.add_custom_button(__("Calendar"), () =>
		frappe.set_route("onecalendar", { doctype: frm.doctype, name: frm.doc.name })
	);
};
