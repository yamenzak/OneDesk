// A customer's or supplier's contact and the portal (one/portal_invite.py):
// where they stand, and Invite to Portal, Invite Again, Revoke Access or
// Restore Access for a workspace administrator or the party's manager.
// frappe's own Invite as User is only for somebody who may create users,
// and nobody on a workspace may.
frappe.ui.form.on("Contact", {
	async refresh(frm) {
		if (frm.is_new()) return;
		frm.remove_custom_button(__("Invite as User"));
		const method = (name) => `onedesk.one.portal_invite.${name}`;
		const state = await frappe.xcall(method("state"), { contact: frm.doc.name });
		const said = {
			invited: [__("Invited to the portal. Not signed in yet."), "blue"],
			active: [__("Signed in to the portal {0}.", [state.when]), "green"],
			revoked: [__("Portal access revoked."), "gray"],
		}[state.status];
		frm.set_intro(said ? said[0] : "", said ? said[1] : "");
		if (!state.may) return;
		const run = (name, done) => async () => {
			await frappe.xcall(method(name), { contact: frm.doc.name });
			frappe.show_alert({ message: done, indicator: "green" });
			frm.reload_doc();
		};
		const group = __("Portal");
		if (!state.status) {
			frm.add_custom_button(__("Invite to Portal"), run("invite_contact", __("Invitation sent")), group);
		}
		if (state.status === "invited") {
			frm.add_custom_button(__("Invite Again"), run("invite_again", __("Invitation sent")), group);
		}
		if (["invited", "active"].includes(state.status)) {
			frm.add_custom_button(
				__("Revoke Access"),
				() =>
					frappe.confirm(__("Turn off {0}'s portal access? They're signed out at once.", [frm.doc.full_name || frm.doc.email_id]), run("revoke", __("Access revoked"))),
				group
			);
		}
		if (state.status === "revoked") {
			frm.add_custom_button(__("Restore Access"), run("restore", __("Access restored")), group);
		}
	},
});
