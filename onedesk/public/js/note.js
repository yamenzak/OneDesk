// An announcement runs along the top bar until its Show Until, so frappe's
// sign-in pop-up and its switches are hidden (one/custom/note.json); who
// doesn't announce keeps a private note.
frappe.ui.form.on("Note", {
	onload(frm) {
		if (frm.is_new() && onedesk_note_announces()) frm.set_value("public", 1);
	},
	refresh(frm) {
		if (onedesk_note_announces()) {
			const until = frm.doc.expire_notification_on;
			if (frm.doc.public && !frm.is_new() && (!until || frappe.datetime.str_to_obj(until) > new Date())) {
				frm.add_custom_button(__("Stop Showing"), () =>
					frappe.xcall("onedesk.one.announcements.stop", { name: frm.doc.name }).then(() => frm.reload_doc())
				);
			}
			return;
		}
		for (const field of ["public", "expire_notification_on"]) frm.set_df_property(field, "hidden", 1);
	},
});

function onedesk_note_announces() {
	return frappe.user.has_role("Workspace Administrator") || (frappe.boot.user.can_write || []).includes("Custom Field");
}
