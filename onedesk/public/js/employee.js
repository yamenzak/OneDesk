frappe.provide("onedesk.employee");

onedesk.employee.ACTIONS = [
	["Leave Application", __("Apply for Leave")],
	["Expense Claim", __("Claim an Expense")],
	["Salary Structure Assignment", __("Assign a Salary Structure")],
];

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
	if (frm.doc.status !== "Active") return;

	for (const [doctype, label] of onedesk.employee.ACTIONS) {
		if (!frappe.model.can_create(doctype)) continue;
		frm.sidebar.add_user_action(label, () => {
			frappe.new_doc(doctype, { employee: frm.doc.name });
		});
	}

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
