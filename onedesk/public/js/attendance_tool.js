// Loaded after hrms's own employee_attendance_tool.js, so every handler here
// runs after theirs and has the last word.

frappe.ui.form.on("Employee Attendance Tool", {
	refresh(frm) {
		quiet(frm);
		frm.trigger("one_no_overtime");
	},

	date(frm) {
		quiet(frm);
	},

	status(frm) {
		frm.trigger("one_no_overtime");
	},

	// Overtime Slip only collects days marked Present, so anything else would
	// write a figure nothing reads.
	one_no_overtime(frm) {
		if (frm.doc.status !== "Present" && frm.doc.one_overtime_type) {
			frm.set_value("one_overtime_type", "");
			frm.set_value("one_overtime_hours", 0);
		}
	},

	one_from_checkins(frm) {
		const control = frm.get_field("unmarked_employees_multicheck");
		if (!control) return;

		frappe
			.call({
				method: "onedesk.one_hr.marking.clocked_in",
				args: { date: frm.doc.date },
				freeze: true,
				freeze_message: __("Reading the check-ins"),
			})
			.then((r) => {
				const listed = new Set(control.options.map((option) => option.value));
				const ticked = (r.message || []).filter((employee) => listed.has(employee));

				control.selected_options = ticked;
				control.select_options(ticked);

				if (!frm.doc.status) frm.set_value("status", "Present");

				frappe.show_alert({
					message: ticked.length
						? __("Ticked {0} of {1}", [ticked.length, listed.size])
						: __("Nobody on this list checked in"),
					indicator: ticked.length ? "green" : "orange",
				});
			});
	},

	// hrms sets the primary action once the employees are on screen. Ours
	// replaces it so the overtime fields reach the Attendance rows; the half
	// day list is still theirs to write.
	set_primary_action(frm) {
		frm.page.set_primary_action(__("Mark Attendance"), () => {
			const full_day = frm.get_field("unmarked_employees_multicheck")?.get_checked_options() || [];
			const half_day = frm.get_field("half_marked_employees_multicheck")?.get_checked_options() || [];

			if (!full_day.length && !half_day.length) {
				frappe.throw({
					message: __("Please select the employees you want to mark attendance for."),
					title: __("Mandatory"),
				});
			}
			if (full_day.length && !frm.doc.status) {
				frappe.throw({
					message: __("Please select the attendance status."),
					title: __("Mandatory"),
				});
			}
			if (half_day.length && !frm.doc.half_day_status) {
				frappe.throw({
					message: __("Please select half day attendance status."),
					title: __("Mandatory"),
				});
			}
			if (frm.doc.one_overtime_type && !frm.doc.one_overtime_hours) {
				frappe.throw({
					message: __("Please enter the overtime hours."),
					title: __("Mandatory"),
				});
			}

			mark(frm, full_day, half_day);
		});
	},
});

// The heading is the last breadcrumb, which for a Single is the doctype's own
// name; DocType has no label to set, so the crumb is replaced instead. The
// Single is never saved either, so the dirty badge it keeps is about nothing.
function quiet(frm) {
	frm.page.clear_indicator();
	frappe.after_ajax(() =>
		frappe.breadcrumbs.add({
			type: "Custom",
			label: __("Mark Attendance"),
			route: "/desk/employee-attendance-tool",
		}),
	);
}

function mark(frm, full_day, half_day) {
	const ours = full_day.length
		? frappe.call({
				method: "onedesk.one_hr.marking.mark",
				args: {
					employees: full_day,
					status: frm.doc.status,
					date: frm.doc.date,
					shift: frm.doc.shift,
					late_entry: frm.doc.late_entry,
					early_exit: frm.doc.early_exit,
					overtime_type: frm.doc.one_overtime_type,
					overtime_hours: frm.doc.one_overtime_hours,
				},
		  })
		: Promise.resolve({});

	ours.then((r) => {
		if (r.exc) return;
		if (!half_day.length) return done(frm);

		frappe
			.call({
				method: "hrms.hr.doctype.employee_attendance_tool.employee_attendance_tool.mark_employee_attendance",
				args: {
					employee_list: [],
					status: frm.doc.status,
					date: frm.doc.date,
					late_entry: frm.doc.late_entry,
					early_exit: frm.doc.early_exit,
					shift: frm.doc.shift,
					mark_half_day: true,
					half_day_status: frm.doc.half_day_status,
					half_day_employee_list: half_day,
				},
			})
			.then((r) => !r.exc && done(frm));
	});
}

function done(frm) {
	frappe.show_alert({ message: __("Attendance marked successfully"), indicator: "green" });
	frm.refresh();
}
