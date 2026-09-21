// A payslip says what somebody is paid, on the tab it opens on.
//
// The money lives on the third and fourth tabs. The one it opens on carries
// Department, Letter Head, Designation, Payroll Frequency, Salary Structure and
// the two dates — all correct, and none of them the question anybody came with.
// So the headline answers it, and says where the number came from when the
// month was not a whole month.
frappe.ui.form.on("Salary Slip", {
	refresh: (frm) => onedesk.slip.say(frm),
	net_pay: (frm) => onedesk.slip.say(frm),
	after_save: (frm) => onedesk.slip.say(frm),
});

frappe.provide("onedesk.slip");

onedesk.slip.say = (frm) => {
	if (frm.is_new() || !frm.doc.net_pay) {
		frm.dashboard.clear_headline();
		return;
	}
	const paid = format_currency(frm.doc.rounded_total || frm.doc.net_pay, frm.doc.currency);
	const month = `${frappe.datetime.str_to_user(frm.doc.start_date)} – ${frappe.datetime.str_to_user(
		frm.doc.end_date
	)}`;
	const whole = flt(frm.doc.payment_days) >= flt(frm.doc.total_working_days);
	onedesk.decision.headline(
		frm,
		whole
			? __("{0} for {1}, a whole month.", [paid, month])
			: __("{0} for {1}: {2} of {3} days paid.", [
					paid,
					month,
					flt(frm.doc.payment_days, 2),
					flt(frm.doc.total_working_days, 2),
			  ]),
		frm.doc.docstatus === 1 ? "green" : "blue"
	);
};
