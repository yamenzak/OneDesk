// A webhook written by a workspace administrator (one/webhooks.py): what
// the server would refuse is not offered. Somebody frappe lets customize
// keeps frappe's whole form.
frappe.ui.form.on("Webhook", {
	refresh(frm) {
		if ((frappe.boot.user.can_write || []).includes("Custom Field")) return;
		for (const field of ["condition", "html_condition", "is_dynamic_url", "background_jobs_queue"]) {
			frm.set_df_property(field, "hidden", 1);
		}
		frm.set_df_property(
			"request_url",
			"description",
			__("A public HTTPS URL. To filter records, use an automation with a Call Webhook step.")
		);
	},
});
