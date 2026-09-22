// The fourth request doctype gets the same two buttons as the other three.
//
// See `one_hr/expense.py`: HRMS's whole approval here is a Select the approver
// edits by hand, and an `on_submit` that throws if they forgot.
frappe.ui.form.on("Expense Claim", {
	refresh: (frm) => {
		onedesk.decision.buttons(frm, {
			approve: () => onedesk.expense.answer(frm, "approve"),
			reject: () => onedesk.expense.answer(frm, "reject"),
			approves: frm.doc.docstatus === 0,
			rejects: frm.doc.docstatus === 0,
		});
		onedesk.expense.say(frm);
	},
});

frappe.provide("onedesk.expense");

onedesk.expense.answer = (frm, verdict) => {
	onedesk.decision.ask(verdict, (note) =>
		frappe
			.xcall(`onedesk.one_hr.expense.${verdict}`, { name: frm.doc.name, note })
			.then(() => frm.reload_doc())
	);
};

onedesk.expense.say = (frm) => {
	if (frm.is_new() || frm.doc.docstatus !== 0) {
		frm.dashboard.clear_headline();
		return;
	}
	frappe.xcall("onedesk.one_hr.expense.about", { name: frm.doc.name }).then((about) => {
		const money = (amount) => format_currency(amount, about.currency);
		// One row does not need counting, and "1 expenses" reads badly.
		const lines = [
			about.rows > 1
				? __("Approving this pays {0} back {1}, across {2} expenses.", [
						about.employee_name,
						money(about.payable),
						about.rows,
				  ])
				: __("Approving this pays {0} back {1}.", [
						about.employee_name,
						money(about.payable),
				  ]),
		];
		if (about.advance) {
			lines.push(
				__("{0} of it is already covered by an advance.", [money(about.advance)])
			);
		}
		if (about.sanctioned !== about.claimed) {
			lines.push(
				__("They claimed {0} and {1} was sanctioned.", [
					money(about.claimed),
					money(about.sanctioned),
				])
			);
		}
		onedesk.decision.headline(frm, lines.join(" "), "blue");
	});
};
