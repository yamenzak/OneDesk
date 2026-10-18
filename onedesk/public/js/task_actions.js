frappe.provide("onedesk.task");

onedesk.task.GROUPS = [
	[__("Details"), ["type", "priority", "project", "parent_task", "is_group", "department", "issue", "color"]],
	[__("Schedule"), ["exp_start_date", "exp_end_date", "expected_time", "progress", "task_weight", "is_milestone", "one_bill_share"]],
	[__("Depends On"), ["depends_on"]],
	[__("Review"), ["review_date", "closing_date", "completed_on", "completed_by"]],
	[__("Template"), ["is_template", "start", "duration"]],
];
onedesk.task.ELSEWHERE = ["subject", "status", "description", "one_steps"];

onedesk.task.edit = async (task, modified, done, fieldnames = null) => {
	await frappe.model.with_doctype("Task");
	const doc = await frappe.db.get_doc("Task", task);
	for (const row of doc.depends_on || []) if (row.subject) frappe.utils.add_link_title("Task", row.task, row.subject);
	const groups = fieldnames || onedesk.project.about_fields("Task", onedesk.task.GROUPS, onedesk.task.ELSEWHERE);
	const fields = groups
		.flatMap((one) => (Array.isArray(one) ? [{ fieldtype: "Section Break", label: one[0] }, ...one[1]] : [one]))
		.map((fieldname) => (typeof fieldname === "string" ? onedesk.task.field(doc, fieldname) : fieldname))
		.filter(Boolean);
	const dialog = new frappe.ui.Dialog({
		title: fieldnames ? __("Edit {0}", [__(frappe.meta.get_label("Task", fieldnames[0]))]) : __("Edit Details"),
		size: "large",
		fields,
		primary_action_label: __("Save"),
		primary_action: async (values) => {
			dialog.disable_primary_action();
			try {
				const changed = { ...doc, ...values, modified };
				if ("depends_on" in values) changed.depends_on = (values.depends_on || []).filter((row) => row.task).map((row) => ({ task: row.task }));
				await frappe.xcall("frappe.client.save", { doc: changed });
				dialog.hide();
				done?.();
			} catch {
			} finally {
				dialog.enable_primary_action();
			}
		},
	});
	dialog.show();
};

onedesk.task.field = (doc, fieldname) => {
	const task = doc.name;
	if (fieldname === "depends_on") {
		return {
			fieldtype: "Table",
			fieldname: "depends_on",
			label: __("Depends On"),
			in_place_edit: true,
			data: (doc.depends_on || []).map((row) => ({ task: row.task })),
			fields: [
				{
					fieldtype: "Link",
					fieldname: "task",
					options: "Task",
					label: __("Task"),
					in_list_view: 1,
					reqd: 1,
					get_query: () => ({ filters: { name: ["!=", task], status: ["!=", "Template"] } }),
				},
			],
		};
	}
	const df = frappe.meta.get_docfield("Task", fieldname);
	if (!df) return null;
	const field = { ...df, default: doc[fieldname] };
	if (fieldname === "parent_task")
		field.get_query = () => ({ filters: { name: ["!=", task], project: doc.project || undefined, status: ["!=", "Template"] } });
	if (fieldname === "one_bill_share") field.depends_on = "eval:doc.is_milestone";
	if (["start", "duration"].includes(fieldname)) field.depends_on = "eval:doc.is_template";
	return field;
};

onedesk.task.log_time = (task, project, bills_hours, done) => {
	const dialog = new frappe.ui.Dialog({
		title: __("Log Time"),
		fields: [
			{ fieldtype: "Date", fieldname: "date", label: __("Date"), reqd: 1, default: frappe.datetime.get_today() },
			{ fieldtype: "Float", fieldname: "hours", label: __("Hours"), reqd: 1, precision: 2 },
			{ fieldtype: "Column Break" },
			{ fieldtype: "Link", fieldname: "activity_type", label: __("Activity"), options: "Activity Type", reqd: 1 },
			{ fieldtype: "Section Break" },
			{ fieldtype: "Small Text", fieldname: "description", label: __("Description") },
			{ fieldtype: "Check", fieldname: "billable", label: __("Billable"), default: bills_hours ? 1 : 0 },
		],
		primary_action_label: __("Log Time"),
		primary_action: async (values) => {
			await frappe.xcall("onedesk.one_project.hours.log", { project, task, ...values });
			dialog.hide();
			frappe.show_alert({ message: __("Time logged"), indicator: "green" });
			done?.();
		},
	});
	dialog.show();
};
