// A shift that takes check-ins and never turns them into attendance says
// nothing about it: hrms's job returns early and the Attendance list, every
// chart over it and the Overtime Slip are all just empty. The form says so,
// where the fix is.
frappe.ui.form.on("Shift Type", {
	refresh(frm) {
		if (frm.is_new()) return;

		const deaf =
			!frm.doc.enable_auto_attendance ||
			!frm.doc.process_attendance_after ||
			!frm.doc.last_sync_of_checkin;

		if (!deaf) return;

		frm.dashboard.clear_headline();
		frm.dashboard.set_headline(
			__("Check-ins on this shift are not becoming attendance."),
			"orange",
		);

		if (!frappe.model.can_write("Shift Type")) return;

		frm.add_custom_button(__("Read Check-ins"), () =>
			frappe.confirm(
				__("Attendance will be written from check-ins on this shift from today onwards."),
				() =>
					frappe.xcall("onedesk.one_hr.setup.start_reading", { shift: frm.doc.name }).then(() => {
						frappe.show_alert({ message: __("Done"), indicator: "green" });
						frm.reload_doc();
					}),
			),
		);
	},
});
