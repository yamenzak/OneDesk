// The two decisions on something the clock proposed. Status is read-only on
// the record, because rejecting an address is a decision rather than a value
// you pick out of a list — and because the learner treats a rejection as final.
frappe.ui.form.on("Clock Network", { refresh: settle });

function settle(frm) {
	if (frm.is_new() || !frappe.model.can_write(frm.doctype)) return;

	if (frm.doc.status === "Proposed") {
		frm.add_custom_button(__("Confirm"), () =>
			ask(frm, "confirm", __("Check-ins from {0} will be allowed.", [frm.doc.address || frm.doc.label])),
		);
	}

	if (["Proposed", "Confirmed"].includes(frm.doc.status)) {
		frm.add_custom_button(__("Reject"), () =>
			ask(
				frm,
				"reject",
				__("Check-ins from {0} will be refused, and it will not be proposed again.", [
					frm.doc.address || frm.doc.label,
				]),
			),
		);
	}
}

function ask(frm, verb, question) {
	frappe.confirm(question, () =>
		frappe
			.xcall(`onedesk.one_hr.learned.${verb}`, { doctype: frm.doctype, name: frm.doc.name })
			.then(() => {
				frappe.show_alert({ message: __("Done"), indicator: "green" });
				frm.reload_doc();
			}),
	);
}
