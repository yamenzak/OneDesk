// A declaration says what was declared, on the tab it opens on.
//
// Both of these open on a Details tab carrying the employee, the payroll
// period, the department and the currency — and put the table and the two
// totals on a second tab. The number somebody came for is the total, and
// whether all of it is allowed: a category has a `max_amount`, so a person can
// declare thirty and be allowed twenty, and nothing on the first screen says
// which happened.
frappe.ui.form.on("Employee Tax Exemption Declaration", {
	refresh: (frm) => onedesk.exemption.say(frm, "total_declared_amount", "total_exemption_amount"),
	total_exemption_amount: (frm) =>
		onedesk.exemption.say(frm, "total_declared_amount", "total_exemption_amount"),
});

frappe.ui.form.on("Employee Tax Exemption Proof Submission", {
	refresh: (frm) => onedesk.exemption.say(frm, "total_actual_amount", "exemption_amount"),
	exemption_amount: (frm) => onedesk.exemption.say(frm, "total_actual_amount", "exemption_amount"),
});

frappe.provide("onedesk.exemption");

onedesk.exemption.say = (frm, claimed_field, allowed_field) => {
	const claimed = flt(frm.doc[claimed_field]);
	if (frm.is_new() || !claimed) {
		frm.dashboard.clear_headline();
		return;
	}
	const allowed = flt(frm.doc[allowed_field]);
	const who = frm.doc.employee_name || frm.doc.employee;
	const period = frm.doc.payroll_period;
	onedesk.decision.headline(
		frm,
		allowed >= claimed
			? __("{0} claimed {1} for {2}, and all of it is allowed.", [
					who,
					format_currency(claimed, frm.doc.currency),
					period,
			  ])
			: __("{0} claimed {1} for {2}, of which {3} is allowed — the rest is over a category limit.", [
					who,
					format_currency(claimed, frm.doc.currency),
					period,
					format_currency(allowed, frm.doc.currency),
			  ]),
		allowed >= claimed ? "blue" : "orange"
	);
};
