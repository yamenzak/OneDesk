frappe.provide("onedesk.employee");

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

// Its shortcuts (Apply for Leave, Claim an Expense, Assign a Salary Structure) are declared in the
// registry and drawn by window/form.js, which clears the panel's actions first; what is left here
// is the one that opens a dialog.
onedesk.employee.actions = (frm) => {
	if (frm.doc.status !== "Active") return;
	if (frappe.model.can_write("Attendance")) {
		frm.sidebar.add_user_action(`${frappe.utils.icon("clock-plus", "sm")}<span>${__("Record Overtime")}</span>`, () =>
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
