// The contact's Portal column (Contact.one_portal, one_portal/gate.py) says
// where their login stands; the Portal button opens the dialog where they are
// invited, revoked or restored. Neither while OnePortal is turned off.
frappe.ui.form.on("Contact", {
	async refresh(frm) {
		frm.remove_custom_button(__("Invite as User"));
		if (frm.is_new() || !onedesk.portal.on()) return;
		const state = await frappe.xcall("onedesk.one_portal.invite.state", { contact: frm.doc.name });
		if (!state.may) return;
		onedesk.portal.button(frm, () => onedesk.portal.open("Contact", frm.doc.name, () => frm.reload_doc()));
	},
});
