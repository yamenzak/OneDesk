// Answering a request, which HRMS leaves as "whoever has the submit grant
// presses Submit". Approve is that same submit with a note attached; Reject is
// the half that did not exist — it leaves the draft where it is, signed, and
// the server refuses to submit it until somebody approves instead.
frappe.ui.form.on("Attendance Request", {
	refresh(frm) {
		frm.set_query("one_reason", () => ({ filters: { enabled: 1 } }));
		if (frm.doc.one_decision === "Rejected") {
			onedesk.decision.headline(
				frm,
				__("Turned down by {0}.", [frm.doc.one_decided_by || ""]),
				"red",
			);
		}
		onedesk.decision.buttons(frm, {
			approve: "onedesk.one_hr.request.approve",
			reject: "onedesk.one_hr.request.reject",
			approves: __("These days will be marked as worked."),
			rejects: __("Nothing will be written to attendance."),
		});
	},
});
