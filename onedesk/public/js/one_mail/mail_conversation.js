// A conversation's row opens where it is read: in OneMail, on the
// conversation (one_mail/team.py `opened`).
frappe.ui.form.on("Mail Conversation", {
	onload(frm) {
		if (frm.is_new()) return;
		frappe.xcall("onedesk.one_mail.team.opened", { name: frm.doc.name }).then((url) => url && window.location.assign(url));
	},
});
