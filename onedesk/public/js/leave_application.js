// The third request doctype, answered the way the other two are.
//
// HRMS stacks two headlines here — frappe's "Submit this document to confirm"
// and its own "Submit this Leave Application to confirm." — and neither says
// what approving does. The one below says how many days of what, for whom, and
// what it leaves them with, because the table above the form does not: it reads
// Available Leaves 21 beside Leaves Pending Approval 3, and the 3 is this.
frappe.ui.form.on("Leave Application", {
	refresh(frm) {
		onedesk.decision.buttons(frm, {
			approve: "onedesk.one_hr.leave.approve",
			reject: "onedesk.one_hr.leave.reject",
			approves: __("The days are spent and the attendance is marked."),
			rejects: __("Nothing is spent and no attendance is marked."),
		});
		say(frm);
	},
});

async function say(frm) {
	if (frm.is_new() || frm.doc.docstatus !== 0) return;

	const it = await frappe.xcall("onedesk.one_hr.leave.about", { name: frm.doc.name });
	if (!it.days) return onedesk.decision.headline(frm);

	const when =
		it.from_date === it.to_date
			? on(it.from_date)
			: __("{0} to {1}", [on(it.from_date), on(it.to_date)]);

	onedesk.decision.headline(
		frm,
		__("Approving this books {0} days of {1} for {2}, {3}, leaving them {4}.", [
			it.days,
			it.leave_type,
			it.employee_name,
			when,
			it.after,
		]),
		"blue",
	);
}

const on = (date) => frappe.datetime.str_to_user(date);
