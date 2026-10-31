// A source fetches on its own schedule (one/news); Fetch Now asks at once,
// and the last problem, if there was one, is said above the form.
frappe.ui.form.on("News Source", {
	refresh(frm) {
		if (frm.is_new()) return;
		if (frm.doc.kind === "Written") {
			frm.add_custom_button(__("Write an Item"), () => frappe.new_doc("News Item", { source: frm.doc.name }));
		} else if (frm.perm[0]?.write) {
			frm.add_custom_button(__("Fetch Now"), () =>
				frappe.xcall("onedesk.one.news.fetching.fetch_now", { name: frm.doc.name }).then(() =>
					frappe.show_alert({ message: __("Fetching. Its items arrive in a moment."), indicator: "blue" })
				)
			);
		}
		frm.add_custom_button(__("Its Items"), () => frappe.set_route("List", "News Item", { source: frm.doc.name }));
		if (frm.doc.last_error) frm.dashboard.set_headline_alert(frappe.utils.escape_html(frm.doc.last_error), "orange");
	},
});
