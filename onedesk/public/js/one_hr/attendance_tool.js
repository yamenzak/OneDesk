
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

	set_primary_action(frm) {
		unhide_field("one_mark_section");
		search(frm);
	},
});

function quiet(frm) {
	frm.page.clear_indicator();
	frappe.after_ajax(() => frm.page.set_breadcrumbs([{ label: __("Mark Attendance") }]));
}

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
