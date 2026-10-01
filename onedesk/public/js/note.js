// An announcement (one/announcements.py). Written by an administrator, a
// new one is everybody's and shown when they sign in; anybody else's note
// is their own, and what would make it everybody's is not offered.
frappe.ui.form.on("Note", {
	onload(frm) {
		if (frm.is_new() && onedesk_note_announces()) {
			frm.set_value("public", 1);
			frm.set_value("notify_on_login", 1);
		}
	},
	refresh(frm) {
		if (onedesk_note_announces()) {
			frm.set_df_property("notify_on_login", "label", __("Show When People Sign In"));
			frm.set_df_property("notify_on_every_login", "label", __("Every Time They Sign In"));
			frm.set_df_property("expire_notification_on", "label", __("Show Until"));
			frm.set_df_property("seen_by_section", "label", __("Seen By"));
			return;
		}
		for (const field of ["public", "notify_on_login", "notify_on_every_login", "expire_notification_on"]) {
			frm.set_df_property(field, "hidden", 1);
		}
	},
});

function onedesk_note_announces() {
	return frappe.user.has_role("Workspace Administrator") || (frappe.boot.user.can_write || []).includes("Custom Field");
}
