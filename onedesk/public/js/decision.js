// The two buttons a request is answered with, and the note that goes with them.
// Two doctypes in the Time group are asked for and then answered by a person,
// and a product where one of them has Approve and Reject and the other has a
// Status dropdown is two products. This is the shape; what each verdict does
// stays on the server, where the two genuinely differ.
frappe.provide("onedesk.decision");

// `verbs` is { approve, reject } — the dotted paths to call — plus the two
// sentences that say what each one will do, which is the part a person needs
// before pressing and cannot get from the word "Approve".
onedesk.decision.buttons = (frm, verbs) => {
	if (frm.is_new() || frm.doc.docstatus !== 0) return;
	if (!frappe.model.can_submit(frm.doctype)) return;

	frm.add_custom_button(__("Approve"), () =>
		onedesk.decision.ask(frm, verbs.approve, __("Approve"), verbs.approves, "green"),
	);
	frm.add_custom_button(__("Reject"), () =>
		onedesk.decision.ask(frm, verbs.reject, __("Reject"), verbs.rejects, "red"),
	);
};

onedesk.decision.ask = (frm, method, title, what, colour) => {
	const dialog = new frappe.ui.Dialog({
		title: title,
		fields: [
			{ fieldtype: "HTML", fieldname: "what" },
			{
				fieldtype: "Small Text",
				fieldname: "note",
				label: __("Note"),
				description: __("Optional. The person who asked will see it."),
			},
		],
		primary_action_label: title,
		primary_action: ({ note }) => {
			dialog.hide();
			frappe.xcall(method, { name: frm.doc.name, note: note || "" }).then(() => {
				frappe.show_alert({ message: __("Done"), indicator: colour });
				frm.reload_doc();
			});
		},
	});
	dialog.fields_dict.what.$wrapper.html(
		`<p class="text-muted">${frappe.utils.escape_html(what || "")}</p>`,
	);
	dialog.show();
};

// The framework writes "Submit this document to confirm" into the message area
// from `show_submit_message`, which runs after the refresh trigger and stacks
// rather than replaces. Ours is that same sentence with the answer in it, so it
// clears the generic one and goes last.
// Called with no text to clear it, which is what a form with nothing to say yet
// needs: leaving the last sentence up is worse than leaving the strip empty.
onedesk.decision.headline = (frm, text, colour) => {
	setTimeout(() => {
		frm.dashboard.clear_headline();
		if (text) frm.dashboard.set_headline_alert(frappe.utils.escape_html(text), colour);
	}, 0);
};
