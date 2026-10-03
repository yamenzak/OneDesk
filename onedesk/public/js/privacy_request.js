// A request to delete somebody's account (one/privacy.py): read here by a
// workspace administrator, decided with Approve and Delete or Hold, never by
// editing the record. frappe's own buttons are its System Manager's.
frappe.ui.form.on("Personal Data Deletion Request", {
	refresh(frm) {
		const who = frappe.user.full_name(frm.doc.email) || frm.doc.email;
		frm.set_intro(
			{
				"Pending Approval": __("{0} asked to delete their account. Approving signs them out and erases their data. Kept records are anonymised.", [who]),
				"On Hold": __("On hold. {0} was notified of the reason.", [who]),
				Deleted: __("Deleted. The account is disabled and its personal data erased."),
			}[frm.doc.status] || "",
			frm.doc.status === "Deleted" ? "green" : "blue"
		);
		if (!["Pending Approval", "On Hold"].includes(frm.doc.status) || !onedesk.privacy.decides()) return;
		frm.page.set_primary_action(__("Approve and Delete"), () =>
			frappe.confirm(__("Delete {0}'s account? This can't be undone.", [who]), async () => {
				await frappe.xcall("onedesk.one.privacy.approve", { name: frm.doc.name });
				frappe.show_alert({ message: __("{0} is signed out. Their data is being erased.", [who]), indicator: "green" });
				frm.reload_doc();
			})
		);
		if (frm.doc.status === "Pending Approval") {
			frm.add_custom_button(__("Hold"), () => {
				const dialog = new frappe.ui.Dialog({
					title: __("Hold Request"),
					fields: [
						{
							fieldname: "why",
							fieldtype: "Small Text",
							label: __("Reason"),
							reqd: 1,
							description: __("Sent to {0}. For example, payroll for the month has to close first.", [who]),
						},
					],
					primary_action_label: __("Hold"),
					primary_action: async ({ why }) => {
						await frappe.xcall("onedesk.one.privacy.hold", { name: frm.doc.name, why });
						dialog.hide();
						frm.reload_doc();
					},
				});
				dialog.show();
			});
		}
	},
});

frappe.provide("onedesk.privacy");
onedesk.privacy.decides = () => frappe.user.has_role("Workspace Administrator");
