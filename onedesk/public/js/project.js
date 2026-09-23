// A project's page: its board and calendar as buttons of their own, its
// sub-projects' figures added up in the band, and Group Under New Project.
//
// The board is ERPNext's own, made the way their button makes it
// (one_project/board.py shapes it as it is made). Calendar is OneCalendar
// narrowed to the project. The figures are one_project/tree.py's.

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

// The whole tree's figures, when there is a tree under this project.
onedesk.project.band = async (frm) => {
	const said = await frappe.xcall("onedesk.one_project.tree.totals", { project: frm.doc.name });
	if (frm.doc.name !== cur_frm?.doc?.name) return;
	if (!said.under.length) return frm.dashboard.clear_headline();
	const money = (value) => format_currency(value, said.currency, 0);
	const stat = onedesk.band.stat;
	onedesk.band.show(frm, [
		stat(__("Sub-projects"), said.projects - 1, `/desk/query-report/Project Tree`),
		stat(__("Estimated Cost"), money(said.tree.estimated_costing)),
		stat(__("Total Costing Amount"), money(said.tree.total_costing_amount + said.tree.total_purchase_cost)),
		stat(__("Total Billed Amount"), money(said.tree.total_billed_amount)),
		stat(__("Gross Margin"), money(said.tree.gross_margin), null, said.tree.gross_margin < 0 ? "alarm" : null),
	]);
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
