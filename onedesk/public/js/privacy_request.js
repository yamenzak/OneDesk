// A request to delete somebody's account (one/privacy.py): read here by a
// workspace administrator, decided with Approve and Delete or Hold, never by
// editing the record. frappe's own buttons are its System Manager's.
frappe.ui.form.on("Personal Data Deletion Request", {
	refresh(frm) {
		const who = frappe.user.full_name(frm.doc.email) || frm.doc.email;
		frm.set_intro(
			{
				"Pending Approval": __("{0} asked for their account to be deleted. Approving signs them out at once and erases what is only theirs; what the workspace keeps stays without their name and address.", [who]),
				"On Hold": __("Held. {0} was told why. Approve it when what the workspace has to keep is settled.", [who]),
				Deleted: __("Deleted. The account is turned off and renamed, and its name and address are gone from what the workspace kept."),
			}[frm.doc.status] || "",
			frm.doc.status === "Deleted" ? "green" : "blue"
		);
		if (!["Pending Approval", "On Hold"].includes(frm.doc.status) || !onedesk.privacy.decides()) return;
		frm.page.set_primary_action(__("Approve and Delete"), () =>
			frappe.confirm(__("Delete {0}'s account? This cannot be undone.", [who]), async () => {
				await frappe.xcall("onedesk.one.privacy.approve", { name: frm.doc.name });
				frappe.show_alert({ message: __("{0} is signed out; their data is being erased.", [who]), indicator: "green" });
				frm.reload_doc();
			})
		);
		if (frm.doc.status === "Pending Approval") {
			frm.add_custom_button(__("Hold"), () => {
				const dialog = new frappe.ui.Dialog({
					title: __("Hold the Request"),
					fields: [
						{
							fieldname: "why",
							fieldtype: "Small Text",
							label: __("Why"),
							reqd: 1,
							description: __("{0} is told this, for example that payroll for the month has to close first.", [who]),
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
