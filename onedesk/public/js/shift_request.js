// What the form knows and the person reading it does not: who may approve this,
// what the shift actually is, what an empty To Date means, and what pressing
// Submit will do. All four are on the screen now.
frappe.ui.form.on("Shift Request", {
	refresh(frm) {
		say(frm);
		onedesk.decision.buttons(frm, {
			approve: "onedesk.one_hr.shift.approve",
			reject: "onedesk.one_hr.shift.reject",
			approves: __("A Shift Assignment is created and the employee works this shift."),
			rejects: __("The request is closed and nobody is assigned anything."),
		});
	},

	employee: say,
	shift_type: say,
	from_date: say,
	to_date: say,
});

// The Approver is mandatory and HRMS filters it to the employee's own approver
// plus their department's. An employee with neither leaves the picker empty,
// which reads as a broken field rather than as missing setup — so where there
// is one obvious answer the form takes it, and where there is none it says so
// instead of leaving somebody guessing at a required field.
async function say(frm) {
	if (frm.doc.docstatus !== 0) return;
	if (!frm.doc.employee) return onedesk.decision.headline(frm);

	const who = await frappe.xcall("onedesk.one_hr.shift.approvers", {
		employee: frm.doc.employee,
	});
	if (who.length === 1 && !frm.doc.approver) frm.set_value("approver", who[0]);
	else if (!who.length && frm.is_dirty()) frm.set_value("approver", "");

	if (!who.length) {
		return onedesk.decision.headline(
			frm,
			__("Nobody can approve a shift request for {0}. Set a Shift Request Approver on their Employee record first.", [
				await name(frm),
			]),
			"red",
		);
	}

	if (!frm.doc.shift_type || !frm.doc.from_date) return onedesk.decision.headline(frm);

	const hours =
		frm.doc.one_when ||
		(await frappe.xcall("onedesk.one_hr.shift.hours", { shift_type: frm.doc.shift_type }));
	const shift = hours ? frm.doc.shift_type + " (" + hours + ")" : frm.doc.shift_type;
	const when = frm.doc.to_date
		? __("from {0} to {1}", [on(frm.doc.from_date), on(frm.doc.to_date)])
		: __("from {0}, with no end date", [on(frm.doc.from_date)]);
	onedesk.decision.headline(
		frm,
		__("Approving this puts {0} on {1} {2}.", [await name(frm), shift, when]),
		"blue",
	);
}

// `employee_name` is fetched from the Employee and is not there yet on the tick
// the employee is chosen, which is the tick this sentence is written on.
async function name(frm) {
	if (frm.doc.employee_name) return frm.doc.employee_name;
	const found = await frappe.db.get_value("Employee", frm.doc.employee, "employee_name");
	return found?.message?.employee_name || frm.doc.employee;
}

const on = (date) => frappe.datetime.str_to_user(date);
