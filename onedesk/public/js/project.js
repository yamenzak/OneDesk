// A project's page: its board, calendar and plan as buttons of their own,
// Group Under New Project, Save as Template, Invoice Time and Post Update.
// What it says above its fields is its Record Head (one_project/heads.py).
//
// The board is ERPNext's own, made the way their button makes it
// (one_project/board.py shapes it as it is made). Calendar is OneCalendar
// narrowed to the project. The figures are one_project/overview.py's.

frappe.ui.form.on("Project", {
	refresh(frm) {
		if (frm.is_new()) return;
		if (frappe.model.can_read("Task")) {
			frm.remove_custom_button(__("Kanban Board"), __("View"));
			frm.add_custom_button(__("Board"), async () => {
				await frappe.xcall("erpnext.projects.doctype.project.project.create_kanban_board_if_not_exists", {
					project: frm.doc.name,
				});
				frappe.set_route("List", "Task", "Kanban", frm.doc.project_name);
			});
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
		if (frappe.model.can_create("Project Template")) {
			frm.add_custom_button(__("Save as Template"), () => onedesk.project.save_as(frm), __("Actions"));
		}
		onedesk.project.asked(frm);
	},
});

frappe.provide("onedesk.project");

// The schedule: frappe's Gantt over the tasks of this project and everything under
// it, the ones still in play. See one_project/plan.py.
onedesk.project.plan = async (frm) => {
	const said = await frappe.xcall("onedesk.one_project.overview.overview", { project: frm.doc.name });
	frappe.route_options = {
		project: ["in", said.tree],
		status: ["not in", ["Cancelled", "Template"]],
	};
	frappe.set_route("List", "Task", "Gantt");
};

// A new project above this one, taking its place, with this one and the
// sub-projects ticked moved under it.
onedesk.project.group = async (frm) => {
	const said = await frappe.xcall("onedesk.one_project.tree.totals", { project: frm.doc.name });
	const dialog = new frappe.ui.Dialog({
		title: __("Group Under New Project"),
		fields: [
			{ fieldtype: "Data", fieldname: "title", label: __("Project Name"), reqd: 1 },
			{
				fieldtype: "MultiCheck",
				fieldname: "bring",
				label: __("Move These Beside It"),
				hidden: said.under.length ? 0 : 1,
				options: said.under.map((one) => ({ label: one.title || one.name, value: one.name })),
			},
		],
		primary_action_label: __("Create"),
		primary_action: async (values) => {
			const top = await frappe.xcall("onedesk.one_project.tree.group_under", {
				project: frm.doc.name,
				title: values.title,
				bring: values.bring || [],
			});
			dialog.hide();
			frappe.set_route("Form", "Project", top);
		},
	});
	dialog.show();
};

// A template made from this project's tasks (one_project/templates.py), for
// the next one like it.
onedesk.project.save_as = (frm) => {
	frappe.prompt(
		{ fieldtype: "Data", fieldname: "title", label: __("Template Name"), reqd: 1, default: frm.doc.project_name },
		async ({ title }) => {
			const made = await frappe.xcall("onedesk.one_project.templates.save_as", { project: frm.doc.name, title });
			frappe.ui.toast({
				message: __("{0} is a template.", [made]),
				type: "success",
				action: { label: __("Open"), onclick: () => frappe.set_route("Form", "Project Template", made) },
			});
		},
		__("Save as Template"),
		__("Save"),
	);
};

// A draft invoice for the project's billable time not yet invoiced, by
// activity (one_project/billing.py). It opens unsaved, to be read first.
onedesk.project.invoice_time = async (frm) => {
	const said = await frappe.xcall("onedesk.one_project.billing.unbilled", { project: frm.doc.name });
	if (!said.hours) {
		frappe.ui.toast({ message: __("No billable time on {0} is waiting to be invoiced.", [frm.doc.project_name]), type: "info" });
		return;
	}
	const dialog = new frappe.ui.Dialog({
		title: __("Invoice Time"),
		fields: [
			{
				fieldtype: "HTML",
				fieldname: "said",
				options: `<p class="text-muted">${__("{0} hours, {1}, not invoiced yet.", [
					format_number(said.hours, null, 2),
					format_currency(said.amount, said.currency),
				])}</p>`,
			},
			{
				fieldtype: "Link",
				fieldname: "item",
				label: __("Item"),
				options: "Item",
				reqd: 1,
				default: said.item,
				get_query: () => ({ filters: { is_sales_item: 1, disabled: 0 } }),
			},
		],
		primary_action_label: __("Create"),
		primary_action: ({ item }) => {
			dialog.hide();
			frappe.model.open_mapped_doc({
				method: "onedesk.one_project.billing.invoice_time",
				source_name: frm.doc.name,
				args: { item },
			});
		},
	});
	dialog.show();
};

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

onedesk.project.post = (frm) => {
	frappe.prompt(
		{
			fieldtype: "Small Text",
			fieldname: "note",
			label: __("Your Update"),
			reqd: 1,
			description: __("What was done, what comes next, and anything in the way."),
		},
		async ({ note }) => {
			await frappe.xcall("onedesk.one_project.updates.post", { project: frm.doc.name, note });
			frappe.ui.toast({ message: __("Your update is on the project."), type: "success" });
			frm.reload_doc();
		},
		__("Post Update"),
		__("Post"),
	);
};
