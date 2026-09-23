// A project's board is the first thing somebody working in it wants, so it is
// a button of its own rather than the second entry under View. The board is
// ERPNext's own, made the way their button makes it (one_task/board.py shapes
// it as it is made). Calendar is OneCalendar narrowed to the project: its
// tasks by the day they are due, and the events about it.

frappe.ui.form.on("Project", {
	refresh(frm) {
		if (frm.is_new() || !frappe.model.can_read("Task")) return;
		frm.remove_custom_button(__("Kanban Board"), __("View"));
		frm.add_custom_button(__("Board"), async () => {
			await frappe.xcall("erpnext.projects.doctype.project.project.create_kanban_board_if_not_exists", {
				project: frm.doc.name,
			});
			frappe.set_route("List", "Task", "Kanban", frm.doc.project_name);
		});
		frm.add_custom_button(__("Calendar"), () =>
			frappe.set_route("onecalendar", { doctype: "Project", name: frm.doc.name })
		);
	},
});
