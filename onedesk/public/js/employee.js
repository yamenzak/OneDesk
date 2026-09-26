frappe.provide("onedesk.employee");

// A person's page: the two things you actually do to a person go in the
// sidebar, and HR's Reset Passkey when their phone changes. Where they are,
// their quarter and their numbers are the Employee's Record Head
// (one_hr/heads.py), drawn by head.js.

//: What you can do to a person from their own page, and the doctype that says
//: whether you may. Each one prefills `employee`, so it is self-service on your
//: own record and on somebody's behalf on theirs — which is the same control,
//: because a `User Permission` decides whose record you can open at all.
onedesk.employee.ACTIONS = [
	["Leave Application", __("Apply for Leave")],
	["Expense Claim", __("Claim an Expense")],
	// What somebody is paid is a Salary Structure Assignment, not the CTC field
	// on this record, and the only route to one was Connections. `can_create`
	// is the gate: an employee reading their own page does not have it.
	["Salary Structure Assignment", __("Assign a Salary Structure")],
];

// HR's one click when somebody's phone changes. Offered only where there is a
// credential to retire and only to somebody who may write one, so an ordinary
// reader of a colleague's record never sees it.
onedesk.employee.passkey = (frm, data) => {
	if (!data.passkey || !frappe.model.can_write("Clock Device")) return;
	frm.sidebar.add_user_action(__("Reset Passkey"), () => {
		frappe.confirm(
			__("{0} will register a new passkey on their next check-in. The old one is retired, not deleted.", [
				frm.doc.employee_name,
			]),
			() =>
				frappe
					.xcall("onedesk.one_hr.passkey.reset", { employee: frm.doc.name })
					.then(() => {
						frappe.show_alert({ message: __("Passkey reset"), indicator: "green" });
						frm.refresh();
					})
		);
	});
};

onedesk.employee.actions = (frm) => {
	frm.sidebar.clear_user_actions();
	// A person who has left is not applying for anything.
	if (frm.doc.status !== "Active") return;

	for (const [doctype, label] of onedesk.employee.ACTIONS) {
		if (!frappe.model.can_create(doctype)) continue;
		frm.sidebar.add_user_action(label, () => {
			frappe.new_doc(doctype, { employee: frm.doc.name });
		});
	}

	// Not a new doctype: overtime is written onto the day that was worked, so
	// the action opens the same dialog the Attendance record offers.
	if (frappe.model.can_write("Attendance")) {
		frm.sidebar.add_user_action(__("Record Overtime"), () =>
			onedesk.overtime.ask({ employee: frm.doc.name }),
		);
	}
};

frappe.ui.form.on("Employee", {
	refresh(frm) {
		if (!frm.doc.name || frm.is_new()) return;
		onedesk.employee.actions(frm);
		onedesk.record_calendar(frm);
		frappe.xcall("onedesk.one_hr.employee.passkey_of", { employee: frm.doc.name }).then((passkey) => {
			if (frm.doc.name === cur_frm?.doc?.name) onedesk.employee.passkey(frm, { passkey });
		});
	},
});
