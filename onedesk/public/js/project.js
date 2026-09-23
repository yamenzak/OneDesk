// A project's page: its board and calendar as buttons of their own, the
// overview in the band, and Group Under New Project.
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
		if (frm.perm[0] && frm.perm[0].write) {
			frm.add_custom_button(__("Group Under New Project"), () => onedesk.project.group(frm), __("Actions"));
		}
		onedesk.project.band(frm);
	},
});

frappe.provide("onedesk.project");

// What a project's page answers first (one_project/overview.py): how far it
// has got, whether it is on time, cost against budget, billed against what
// there is to bill, what is late and what comes next. The whole tree's, when
// the project has sub-projects.
onedesk.project.band = async (frm) => {
	const said = await frappe.xcall("onedesk.one_project.overview.overview", { project: frm.doc.name });
	if (frm.doc.name !== cur_frm?.doc?.name) return;
	const money = (value) => format_currency(value, said.currency, 0);
	const of = (part, whole) => (whole ? __("{0} of {1}", [money(part), money(whole)]) : money(part));
	const stat = onedesk.band.stat;
	const stats = [];
	if (said.projects > 1) stats.push(stat(__("Sub-projects"), said.projects - 1, "/desk/query-report/Project Tree"));
	stats.push(
		stat(
			__("Done"),
			said.tasks ? __("{0}% · {1} of {2} tasks", [said.share, said.done, said.tasks]) : `${said.share}%`,
		),
	);
	if (said.end) {
		const left = said.days_left;
		const when =
			left === null ? frappe.datetime.str_to_user(said.end)
			: left < 0 ? __("{0} days late", [-left])
			: left === 0 ? __("Today")
			: __("In {0} days", [left]);
		stats.push(stat(__("Due"), when, null, left !== null && left < 0 ? "alarm" : null));
	}
	stats.push(stat(__("Cost"), of(said.cost, said.estimated), null, said.estimated && said.cost > said.estimated ? "alarm" : null));
	if (said.to_bill || said.billed) stats.push(stat(__("Billed"), of(said.billed, said.to_bill)));
	if (said.billed || said.cost) stats.push(stat(__("Margin"), money(said.margin), null, said.margin < 0 ? "alarm" : null));
	if (said.late) {
		// The late ones, across the tree: the list, filtered the way the rail's
		// Inbox is, by route options.
		const route = (value) => encodeURIComponent(JSON.stringify(value));
		const late =
			`/desk/task?project=${route(["in", said.tree])}` +
			`&status=${route(["not in", ["Completed", "Cancelled", "Template"]])}` +
			`&exp_end_date=${route(["<", frappe.datetime.get_today()])}`;
		stats.push(stat(__("Overdue Tasks"), said.late, late, "alarm"));
	}
	if (said.milestone) {
		stats.push(
			stat(
				__("Next Milestone"),
				`${said.milestone.subject} · ${frappe.datetime.str_to_user(said.milestone.exp_end_date.split(" ")[0])}`,
				`/desk/task/${encodeURIComponent(said.milestone.name)}`,
			),
		);
	}
	onedesk.band.show(frm, stats);
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
