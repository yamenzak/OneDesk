// Status is the only decision on this record, so it is made by a verb rather
// than by a dropdown: read-only on the form, and changed through the two
// functions that also decide what happens next. Reset lets the employee
// register another passkey; Block does not.
frappe.ui.form.on("Clock Device", {
	refresh(frm) {
		if (frm.is_new() || !frappe.model.can_write("Clock Device")) return;

		if (frm.doc.status !== "Reset") {
			frm.add_custom_button(__("Reset"), () =>
				ask(
					frm,
					"onedesk.one_hr.passkey.reset",
					__("{0} will register a new passkey on their next check-in. The old one is retired, not deleted.", [
						frm.doc.employee_name,
					]),
				),
			);
		}

		if (frm.doc.status !== "Blocked") {
			frm.add_custom_button(__("Block"), () =>
				ask(
					frm,
					"onedesk.one_hr.passkey.retire",
					__("{0} will not be able to check in or register another passkey.", [frm.doc.employee_name]),
				),
			);
		}
	},
});

function ask(frm, method, question) {
	frappe.confirm(question, () =>
		frappe.xcall(method, { employee: frm.doc.employee }).then(() => {
			frappe.show_alert({ message: __("Done"), indicator: "green" });
			frm.reload_doc();
		}),
	);
}
