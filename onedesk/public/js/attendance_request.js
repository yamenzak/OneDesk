// Answering a request, which HRMS leaves as "whoever has the submit grant
// presses Submit". Approve is that same submit with a note attached; Reject is
// the half that did not exist — it leaves the draft where it is, signed, and
// the server refuses to submit it until somebody approves instead.
frappe.ui.form.on("Attendance Request", {
	refresh(frm) {
		frm.set_query("one_reason", () => ({ filters: { enabled: 1 } }));
		decision(frm);
		answer(frm);
	},
});

function decision(frm) {
	if (frm.doc.one_decision === "Rejected") {
		frm.dashboard.set_headline_alert(
			__("Turned down by {0}.", [frappe.utils.escape_html(frm.doc.one_decided_by || "")]),
			"red",
		);
	}
}

function answer(frm) {
	if (frm.is_new() || frm.doc.docstatus !== 0) return;
	if (!frappe.model.can_submit(frm.doctype)) return;

	frm.add_custom_button(__("Approve"), () =>
		note(frm, "approve", __("Approve"), __("These days will be marked as worked."), "green"),
	);
	frm.add_custom_button(__("Reject"), () =>
		note(frm, "reject", __("Reject"), __("Nothing will be written to attendance."), "red"),
	);
}

function note(frm, verb, title, what, colour) {
	const dialog = new frappe.ui.Dialog({
		title: title,
		fields: [
			{ fieldtype: "HTML", fieldname: "what" },
			{ fieldtype: "Small Text", fieldname: "note", label: __("Note"), description: __("Optional. The person who asked will see it.") },
		],
		primary_action_label: title,
		primary_action: ({ note }) => {
			dialog.hide();
			frappe
				.xcall(`onedesk.one_hr.request.${verb}`, { name: frm.doc.name, note: note || "" })
				.then(() => {
					frappe.show_alert({ message: __("Done"), indicator: colour });
					frm.reload_doc();
				});
		},
	});
	dialog.fields_dict.what.$wrapper.html(`<p class="text-muted">${frappe.utils.escape_html(what)}</p>`);
	dialog.show();
}
