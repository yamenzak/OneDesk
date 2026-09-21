// Why the amount is nought, said on the record rather than at Submit.
//
// See `one_hr/encashment.py`: the rate lives in a field on the salary structure
// that nothing fills and nothing asks for, and the only sign of it missing is a
// throw after the form has been filled in.
frappe.ui.form.on("Leave Encashment", {
	refresh: (frm) => onedesk.encashment.say(frm),
	employee: (frm) => onedesk.encashment.say(frm),
	encashment_date: (frm) => onedesk.encashment.say(frm),
	encashment_days: (frm) => onedesk.encashment.say(frm),
	// The amount is worked out server-side on save, so the headline is redrawn
	// when it lands rather than only when somebody edits a field.
	encashment_amount: (frm) => onedesk.encashment.say(frm),
	after_save: (frm) => onedesk.encashment.say(frm),
});

frappe.provide("onedesk.encashment");

onedesk.encashment.say = (frm) => {
	if (frm.doc.docstatus !== 0 || !frm.doc.employee || !frm.doc.encashment_date) {
		frm.dashboard.clear_headline();
		return;
	}
	if (frm.doc.encashment_amount > 0) {
		onedesk.decision.headline(
			frm,
			__("Submitting this pays {0} {1} for {2} days of {3}.", [
				frm.doc.employee_name || frm.doc.employee,
				format_currency(frm.doc.encashment_amount, frm.doc.currency),
				// `frappe.format` would wrap a Float in a right-aligned div, which
				// is right in a cell and wrong in a sentence.
				flt(frm.doc.encashment_days, 2),
				frm.doc.leave_type,
			]),
			"blue"
		);
		return;
	}
	frappe.xcall("onedesk.one_hr.encashment.rate", {
		employee: frm.doc.employee,
		on: frm.doc.encashment_date,
	}).then(({ structure }) => {
		onedesk.decision.headline(
			frm,
			structure
				? __(
						"Nothing to pay yet: {0} has no Leave Encashment Amount Per Day, so a day is worth nought. Set it on the salary structure or on this person's assignment.",
						[structure]
				  )
				: __("Nothing to pay yet: this person has no salary structure on {0}.", [
						frappe.format(frm.doc.encashment_date, { fieldtype: "Date" }),
				  ]),
			"orange"
		);
	});
};
