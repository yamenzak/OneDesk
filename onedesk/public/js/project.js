// A project's form, under Edit Details on its page (project_page.js): its
// board, calendar and plan as buttons of their own, Group Under New Project,
// Save as Template, Invoice Time, Quote Extra Work and Post Update, from
// project_actions.js.
// What it says above its fields is its Record Head (one_project/heads.py).
//
// Calendar is OneCalendar narrowed to the project. The figures are one_project/overview.py's.

// The money (Customer, Cost, Forecast, Cost Types, Suppliers) is the page's
// Money and Suppliers views; the form keeps the fields behind them.

frappe.ui.form.on("Project", {
	refresh(frm) {
		if (frm.is_new()) return;
		if (frappe.model.can_read("Task")) {
			frm.remove_custom_button(__("Kanban Board"), __("View"));
			frm.add_custom_button(__("Board"), () => onedesk.project.board(frm));
		}
		onedesk.record_calendar(frm);
		if (frappe.model.can_read("Task")) {
			frm.remove_custom_button(__("Gantt Chart"), __("View"));
			frm.add_custom_button(__("Schedule"), () => onedesk.project.plan(frm));
		}
		if (frm.perm[0] && frm.perm[0].write) {
			frm.add_custom_button(__("Group Under New Project"), () => onedesk.project.group(frm), __("Actions"));
		}
		if (frm.doc.customer && frappe.model.can_create("Sales Invoice")) {
			frm.add_custom_button(__("Invoice Time"), () => onedesk.project.invoice_time(frm), __("Actions"));
		}
		// Extra work the customer asks for: a quotation that becomes a sub-project
		// when it's ordered (one_project/billing.py).
		if (frm.doc.customer && frappe.model.can_create("Quotation")) {
			frm.add_custom_button(
				__("Quote Extra Work"),
				() =>
					frappe.new_doc("Quotation", {
						project: frm.doc.name,
						one_extra_work: 1,
						quotation_to: "Customer",
						party_name: frm.doc.customer,
					}),
				__("Actions")
			);
		}
		if (frappe.model.can_create("Project Template")) {
			frm.add_custom_button(__("Save as Template"), () => onedesk.project.save_as(frm), __("Actions"));
		}
		onedesk.project.asked(frm);
		frappe.realtime.off("one_project_money");
		frappe.realtime.on("one_project_money", (data) => {
			// The head's figures come with the record, so an unchanged form is
			// read again; one being edited keeps its edits.
			if (cur_frm !== frm || data.project !== frm.doc.name || frm.is_dirty()) return;
			frm.reload_doc();
		});
	},
});

frappe.provide("onedesk.project");

// Post Update: the reader's note on how the project is going
// (one_project/updates.py). Always under Actions; a button of its own, and a
// line at the top, when today's ask is waiting on the reader.
onedesk.project.asked = async (frm) => {
	const waiting = await frappe.xcall("onedesk.one_project.updates.asked", { project: frm.doc.name });
	if (frm.doc.name !== cur_frm?.doc?.name) return;
	if (waiting) {
		frm.set_intro(__("Your update on this project is asked for today."), "blue");
		frm.add_custom_button(__("Post Update"), () => onedesk.project.post(frm));
	} else {
		frm.add_custom_button(__("Post Update"), () => onedesk.project.post(frm), __("Actions"));
	}
};
