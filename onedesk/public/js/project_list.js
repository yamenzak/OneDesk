// Projects: where each one stands, said as its status. ERPNext's list put
// "33%" in place of Open once a task was done, and Open in red otherwise;
// how far it has got is its own column. The manager reads as a name because
// every link to a person does (`show_title_field_in_link` on User).
frappe.listview_settings["Project"] = Object.assign(frappe.listview_settings["Project"] || {}, {
	hide_name_column: true,
	hide_name_filter: true,
	// Projects Settings has four ticks about time; it is opened from here by
	// whoever may change it, rather than taking a row in the rail.
	onload(listview) {
		if (frappe.model.can_write("Projects Settings")) {
			listview.page.add_menu_item(__("Projects Settings"), () => frappe.set_route("Form", "Projects Settings"));
		}
	},
	// A bar on the Timeline says how far along it is and when it ends.
	gantt_custom_popup_html(task, item) {
		const ends = item && item.expected_end_date ? frappe.datetime.str_to_user(item.expected_end_date) : "";
		const done = __("{0}% done", [Math.round((item && item.percent_complete) || 0)]);
		return `<div class="title">${frappe.utils.escape_html(task.name)}</div>
			<div class="subtitle">${[done, ends].filter(Boolean).join(" · ")}</div>`;
	},
	get_indicator(doc) {
		const colour = { Open: "blue", Completed: "green", Cancelled: "gray" }[doc.status] || "gray";
		return [__(doc.status), colour, `status,=,${doc.status}`];
	},
});

// The Timeline leaves out an employee's onboarding or exit checklist, as the
// rail's Projects and the Tree do (one_hr/lifecycle.py); it reads the type.
(frappe.listview_settings["Project"].add_fields = frappe.listview_settings["Project"].add_fields || []).push("project_type");
