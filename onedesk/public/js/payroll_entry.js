// What this run pays, on the tab it opens on.
//
// The Overview tab carries the posting date, the currency, the exchange rate,
// the payable account and two checkboxes. The two numbers anybody opens a
// payroll run for — how many people and how much — are on neither this tab nor
// any other: `number_of_employees` is a read-only field parked in the employee
// filter section, and the total is only in the slips.
frappe.ui.form.on("Payroll Entry", {
	refresh: (frm) => onedesk.run.say(frm),
	after_save: (frm) => onedesk.run.say(frm),
});

frappe.provide("onedesk.run");

onedesk.run.say = (frm) => {
	if (frm.is_new()) {
		frm.dashboard.clear_headline();
		return;
	}
	frappe.xcall("onedesk.one_hr.payroll.run", { name: frm.doc.name }).then((run) => {
		if (!run.people) {
			onedesk.decision.headline(
				frm,
				__("No salary slips yet for {0} to {1}.", [
					frappe.datetime.str_to_user(frm.doc.start_date),
					frappe.datetime.str_to_user(frm.doc.end_date),
				]),
				"orange"
			);
			return;
		}
		const money = format_currency(run.total, run.currency || frm.doc.currency);
		const period = `${frappe.datetime.str_to_user(frm.doc.start_date)} – ${frappe.datetime.str_to_user(
			frm.doc.end_date
		)}`;
		onedesk.decision.headline(
			frm,
			run.drafts
				? __("{0}: {1} people, {2}, in {3} slips still in draft.", [
						period,
						run.people,
						money,
						run.drafts,
				  ])
				: __("{0}: {1} people, {2}, all submitted.", [period, run.people, money]),
			run.drafts ? "blue" : "green"
		);
	});
};
