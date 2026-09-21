// Overtime is recorded on the day it was worked, so the day offers it.
frappe.ui.form.on("Attendance", {
	refresh(frm) {
		if (frm.doc.docstatus !== 1 || frm.doc.status !== "Present") return;
		if (!frappe.model.can_write("Attendance")) return;

		frm.add_custom_button(
			frm.doc.overtime_type ? __("Change the Overtime") : __("Record Overtime"),
			() =>
				onedesk.overtime.ask({
					employee: frm.doc.employee,
					date: frm.doc.attendance_date,
					after: () => frm.reload_doc(),
				}),
		);
	},
});
