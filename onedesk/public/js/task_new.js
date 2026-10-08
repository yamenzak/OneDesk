// New Task, OneTask's own dialog: what a task needs to start, in frappe's
// controls, the rest one click away in the full form. `values` fills it in
// (a project, a parent); `projects` narrows Project to a project's tree.
// Rough for now; one_task/README.md, New Task.
frappe.provide("onedesk.task");

onedesk.task.new = async ({ values = {}, projects = null, done = null } = {}) => {
	await frappe.model.with_doctype("Task");
	const meta = (fieldname) => frappe.meta.get_docfield("Task", fieldname) || {};
	const dialog = new frappe.ui.Dialog({
		title: __("New Task"),
		size: "large",
		fields: [
			{ fieldtype: "Data", fieldname: "subject", label: __("Task"), reqd: 1 },
			{
				fieldtype: "Link",
				fieldname: "project",
				options: "Project",
				label: __("Project"),
				default: values.project,
				get_query: () => ({ filters: projects ? { name: ["in", projects] } : { status: "Open" } }),
				onchange: () => {
					dialog.set_value("parent_task", null);
					joins();
				},
			},
			{
				fieldtype: "Link",
				fieldname: "parent_task",
				options: "Task",
				label: __("Part Of"),
				default: values.parent_task,
				get_query: () => ({ filters: { project: dialog.get_value("project") || undefined, status: ["!=", "Template"] } }),
			},
			{ fieldtype: "Column Break" },
			{ fieldtype: "Link", fieldname: "owner_user", options: "User", label: __("Owner"), default: values.owner_user, only_select: 1, onchange: () => joins() },
			{ fieldtype: "Select", fieldname: "priority", label: __("Priority"), options: meta("priority").options, default: values.priority || meta("priority").default || "Medium" },
			{ fieldtype: "Section Break" },
			{ fieldtype: "Date", fieldname: "exp_start_date", label: __("Starts"), default: values.exp_start_date },
			{ fieldtype: "Column Break" },
			{ fieldtype: "Date", fieldname: "exp_end_date", label: __("Due"), default: values.exp_end_date },
			{ fieldtype: "Column Break" },
			{ fieldtype: "Float", fieldname: "expected_time", label: __("Planned Hours"), default: values.expected_time },
			{ fieldtype: "Section Break" },
			{ fieldtype: "Small Text", fieldname: "description", label: __("Description") },
		],
		primary_action_label: __("Add Task"),
		primary_action: async ({ owner_user, ...picked }) => {
			dialog.disable_primary_action();
			try {
				// Whoever is named is given it as the task is made (one_task/capture.py task_made).
				const doc = await frappe.xcall("frappe.client.insert", { doc: { doctype: "Task", ...picked, one_for: owner_user || null } });
				dialog.hide();
				frappe.show_alert({ message: __("{0} added", [doc.subject]), indicator: "green" });
				done?.(doc);
			} catch {
				// frappe has said why.
			} finally {
				dialog.enable_primary_action();
			}
		},
		secondary_action_label: __("Edit Full Form"),
		secondary_action: () => {
			const { owner_user, ...picked } = dialog.get_values(true) || {};
			dialog.hide();
			frappe.new_doc("Task", picked);
		},
	});
	// Somebody given a task on a project they can't open joins it
	// (one_project/members.py `assigned`); the dialog says so beforehand.
	const joins = async () => {
		const { project, owner_user } = dialog.get_values(true) || {};
		const said = project && owner_user ? await frappe.xcall("onedesk.one_project.members.joins", { project, user: owner_user }) : false;
		dialog.set_df_property("owner_user", "description", said ? __("{0} will be added to the project.", [said]) : "");
	};
	dialog.show();
	return dialog;
};
