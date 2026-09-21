// Loaded after hrms's own employee_attendance_tool.js, so every handler here
// runs after theirs and has the last word.
//
// The screen reads in three steps rather than one: the day, then who, then
// what to mark them as. hrms interleaves the three, so the checkboxes that
// qualify the status sat a screen above it and the filters nobody sets were
// the first thing on the page.

frappe.ui.form.on("Employee Attendance Tool", {
	refresh(frm) {
		quiet(frm);
		hide_field("one_mark_section");
	},

	date(frm) {
		quiet(frm);
		hide_field("one_mark_section");
	},

	onload_post_render(frm) {
		search(frm);
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

	// hrms triggers this once the employees are on screen, which is also the
	// moment there is something to mark them as.
	set_primary_action(frm) {
		unhide_field("one_mark_section");
		search(frm);
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

// A department of sixty is three columns of checkboxes with no way through it.
// The rows are hidden rather than removed, so a tick survives a search: the
// control's own selection is untouched by anything here.
function search(frm) {
	const field = frm.get_field("one_search");
	if (!field || !field.$input || field.$input.data("one-bound")) return;

	field.$input.data("one-bound", true).on("input", () => {
		const looking = (field.$input.val() || "").toLowerCase().trim();

		frm.$wrapper.find(".employee_wrapper .unit-checkbox").each(function () {
			const row = $(this);
			row.toggle(!looking || row.text().toLowerCase().includes(looking));
		});
	});
}
