// What can be done to a project, from its page (one_project/page/project_view)
// and its form alike: the schedule, grouping it under a new project, saving it
// as a template, invoicing its time and posting an update, the board, and its
// budget and cost types. Each takes the
// project as `frm`, whose `doc` names it; the page passes its own.
frappe.provide("onedesk.project");

// The board: ERPNext's own, made the way their button makes it
// (one_project/board.py shapes it as it is made).
onedesk.project.board = async (frm) => {
	await frappe.xcall("erpnext.projects.doctype.project.project.create_kanban_board_if_not_exists", {
		project: frm.doc.name,
	});
	frappe.set_route("List", "Task", "Kanban", frm.doc.project_name);
};

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

// A template's tasks added to a running project, dated from the day chosen
// (one_project/templates.py `add`).
onedesk.project.add_template = (project, done) => {
	frappe.prompt(
		[
			{ fieldtype: "Link", fieldname: "template", label: __("Template"), options: "Project Template", reqd: 1 },
			{ fieldtype: "Date", fieldname: "starts", label: __("Starts"), default: frappe.datetime.get_today(), reqd: 1 },
		],
		async ({ template, starts }) => {
			const made = await frappe.xcall("onedesk.one_project.templates.add", { project, template, starts });
			frappe.ui.toast({ message: made === 1 ? __("Added 1 task") : __("Added {0} tasks", [made]), type: "success" });
			done?.();
		},
		__("Add from Template"),
		__("Add Tasks"),
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

// Add Contract: a Fixed Price project's contract, made after the project,
// as the New Project dialog makes it (one_project/kinds.py `add_contract`).
onedesk.project.add_contract = async (frm) => {
	const said = await frappe.xcall("onedesk.one_project.kinds.defaults", { customer: frm.doc.customer });
	const dialog = new frappe.ui.Dialog({
		title: __("Add Contract"),
		fields: [
			// In what the customer is billed in, which the order is made in.
			{ fieldtype: "Link", fieldname: "currency", options: "Currency", hidden: 1, default: said.currency },
			{ fieldtype: "Currency", fieldname: "contract", label: __("Contract Value"), reqd: 1, options: "currency" },
			{
				fieldtype: "Link",
				fieldname: "item",
				label: __("Bill As"),
				options: "Item",
				reqd: 1,
				default: said.item,
				get_query: () => ({ filters: { is_sales_item: 1, disabled: 0, is_stock_item: 0 } }),
			},
			{ fieldtype: "Column Break" },
			{ fieldtype: "Percent", fieldname: "retention", label: __("Retention"), hidden: !frappe.boot.one_retention },
			{
				fieldtype: "Date",
				fieldname: "retention_due",
				label: __("Retention Due"),
				depends_on: "eval:doc.retention",
				mandatory_depends_on: "eval:doc.retention",
			},
			{
				fieldtype: "Percent",
				fieldname: "retention_handover",
				label: __("Released at Handover"),
				description: __("Share of the retention"),
				depends_on: "eval:doc.retention",
			},
		],
		primary_action_label: __("Add Contract"),
		primary_action: async (values) => {
			const { currency, ...asked } = values;
			await frappe.xcall("onedesk.one_project.kinds.add_contract", { project: frm.doc.name, ...asked });
			dialog.hide();
			frm.reload_doc();
		},
	});
	dialog.show();
};

// Make Order: the quotation the customer accepted becomes the sales order,
// as ERPNext's Create › Sales Order makes it. A quotation with alternative
// items opens instead, where ERPNext asks which to take.
onedesk.project.order_quote = (quote) => {
	if (quote.alternatives) return frappe.set_route("Form", "Quotation", quote.name);
	frappe.model.open_mapped_doc({
		method: "erpnext.selling.doctype.quotation.mapper.make_sales_order",
		source_name: quote.name,
	});
};

// Post Update: the reader's note on how the project is going
// (one_project/updates.py).
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

// The budget: what the whole project is expected to cost, ERPNext's
// estimated_costing. Once it has cost types, it is their total and not set here.
onedesk.project.budget = async (frm, done) => {
	const own = (await frappe.db.get_value("Project", frm.doc.name, "estimated_costing")).message?.estimated_costing;
	const dialog = new frappe.ui.Dialog({
		title: __("Budget"),
		fields: [{ fieldtype: "Currency", fieldname: "amount", label: __("Budget"), reqd: 1, default: own }],
		primary_action_label: __("Save"),
		primary_action: async ({ amount }) => {
			await frappe.xcall("frappe.client.set_value", {
				doctype: "Project",
				name: frm.doc.name,
				fieldname: "estimated_costing",
				value: amount,
			});
			dialog.hide();
			done && done();
		},
	});
	dialog.show();
};

// A cost type: ERPNext's own Budget against the project, one per expense
// account (one_project/budget.py). Without a row it adds one; with one it
// changes its budget or removes it.
onedesk.project.cost_type = async (frm, row, done) => {
	const company = frm.doc.company || (await frappe.db.get_value("Project", frm.doc.name, "company")).message?.company;
	const dialog = new frappe.ui.Dialog({
		title: row ? row.cost_type : __("Add Cost Type"),
		fields: [
			{
				fieldtype: "Link",
				fieldname: "account",
				label: __("Cost Type"),
				options: "Account",
				reqd: 1,
				default: row && row.account,
				read_only: row ? 1 : 0,
				get_query: () => ({ filters: { root_type: "Expense", is_group: 0, company } }),
			},
			{ fieldtype: "Currency", fieldname: "amount", label: __("Budget"), reqd: 1, default: row && row.budget },
			{
				fieldtype: "Select",
				fieldname: "action",
				label: __("Over Budget"),
				options: [
					{ value: "Warn", label: __("Warn") },
					{ value: "Stop", label: __("Stop") },
				],
				default: (row && row.action) || "Warn",
			},
		],
		primary_action_label: __("Save"),
		primary_action: async (values) => {
			const said = await frappe.xcall("onedesk.one_project.budget.set_budget", { project: frm.doc.name, ...values });
			dialog.hide();
			done && done(said);
		},
		secondary_action_label: row ? __("Remove") : null,
		secondary_action: row
			? () =>
					frappe.confirm(__("Remove {0}?", [row.cost_type]), async () => {
						const said = await frappe.xcall("onedesk.one_project.budget.remove_budget", {
							project: frm.doc.name,
							account: row.account,
						});
						dialog.hide();
						done && done(said);
					})
			: null,
	});
	dialog.show();
};

// Log Time: an entry in the reader's draft timesheet for the week, the one the
// task timer writes into (one_project/hours.py). `frm.tree` names the projects
// it may be on; billable is ticked when the project's kind bills hours
// (`frm.bills_hours`).
onedesk.project.log_time = (frm, done) => {
	const tree = frm.tree || [frm.doc.name];
	const dialog = new frappe.ui.Dialog({
		title: __("Log Time"),
		fields: [
			{ fieldtype: "Date", fieldname: "date", label: __("Date"), reqd: 1, default: frappe.datetime.get_today() },
			{ fieldtype: "Float", fieldname: "hours", label: __("Hours"), reqd: 1, precision: 2 },
			{ fieldtype: "Column Break" },
			{ fieldtype: "Link", fieldname: "activity_type", label: __("Activity"), options: "Activity Type", reqd: 1 },
			{
				fieldtype: "Link",
				fieldname: "task",
				label: __("Task"),
				options: "Task",
				get_query: () => ({ filters: { project: ["in", tree], status: ["not in", ["Cancelled", "Template"]] } }),
				// The time goes on the task's project.
				onchange: () => {
					const task = dialog.get_value("task");
					if (task && tree.length > 1) frappe.db.get_value("Task", task, "project").then(({ message }) => message && dialog.set_value("on", message.project));
				},
			},
			// Where the time was, on a project with sub-projects (one_project/hours.py `log`).
			{
				fieldtype: "Link",
				fieldname: "on",
				label: __("Project"),
				options: "Project",
				default: frm.doc.name,
				hidden: tree.length < 2,
				get_query: () => ({ filters: { name: ["in", tree] } }),
				// Billable when that project's kind bills hours.
				onchange: () => {
					const on = dialog.get_value("on");
					if (!on) return;
					frappe.db.get_value("Project", on, ["one_kind", "customer"]).then(({ message }) => {
						const bills = Boolean(message?.customer) && ["Time and Materials", "Retainer"].includes(message?.one_kind);
						dialog.set_value("billable", bills ? 1 : 0);
					});
				},
			},
			{ fieldtype: "Section Break" },
			{ fieldtype: "Small Text", fieldname: "description", label: __("Description") },
			// Billable when the project's kind bills hours; cost only otherwise.
			{ fieldtype: "Check", fieldname: "billable", label: __("Billable"), default: frm.bills_hours ? 1 : 0 },
		],
		primary_action_label: __("Log Time"),
		primary_action: async (values) => {
			await frappe.xcall("onedesk.one_project.hours.log", { project: frm.doc.name, ...values });
			dialog.hide();
			frappe.show_alert({ message: __("Time logged"), indicator: "green" });
			done && done();
		},
	});
	dialog.show();
};

// Add Member: somebody joins the project's Members (one_project/team.py).
onedesk.project.add_member = (frm, done) => {
	const dialog = new frappe.ui.Dialog({
		title: __("Add Member"),
		fields: [
			{
				fieldtype: "Link",
				fieldname: "user",
				label: __("User"),
				options: "User",
				reqd: 1,
				get_query: () => ({ filters: { enabled: 1, name: ["not in", ["Administrator", "Guest"]] } }),
			},
		],
		primary_action_label: __("Add Member"),
		primary_action: async ({ user }) => {
			const said = await frappe.xcall("onedesk.one_project.team.add", { project: frm.doc.name, user });
			dialog.hide();
			done && done(said);
		},
	});
	dialog.show();
};

// Invoice Month: a retainer's month as a draft invoice, the fee and any hours
// over the allowance (one_project/retainer.py). It opens unsaved, to be read
// first. `month` is the month to start on; the dialog offers every month not
// invoiced yet.
onedesk.project.invoice_month = async (frm, month) => {
	const said = await frappe.xcall("onedesk.one_project.retainer.months", { project: frm.doc.name });
	const open = said.months.filter((one) => !one.invoice);
	if (!open.length) {
		frappe.ui.toast({ message: __("Every month of {0} is invoiced.", [frm.doc.project_name]), type: "info" });
		return;
	}
	const named = (value) => moment(value).format("MMMM YYYY");
	const ended = open.filter((one) => !one.current);
	const first = month || (ended.length ? ended[ended.length - 1] : open[0]).month;
	const dialog = new frappe.ui.Dialog({
		title: __("Invoice Month"),
		fields: [
			{
				fieldtype: "Select",
				fieldname: "month",
				label: __("Month"),
				reqd: 1,
				options: open.map((one) => ({ value: one.month, label: named(one.month) })),
				default: first,
				change: () => show(dialog.get_value("month")),
			},
			{
				fieldtype: "Link",
				fieldname: "item",
				label: __("Item"),
				options: "Item",
				reqd: 1,
				get_query: () => ({ filters: { is_sales_item: 1, disabled: 0 } }),
			},
			{ fieldtype: "HTML", fieldname: "said" },
			{ fieldtype: "Check", fieldname: "overage", label: __("Bill the hours over"), default: 1, hidden: 1 },
		],
		primary_action_label: __("Create"),
		primary_action: ({ month, item, overage }) => {
			dialog.hide();
			frappe.model.open_mapped_doc({
				method: "onedesk.one_project.retainer.invoice_month",
				source_name: frm.doc.name,
				args: { month, item, overage: overage ? 1 : 0 },
			});
		},
	});
	const show = async (value) => {
		const asked = await frappe.xcall("onedesk.one_project.retainer.asked", { project: frm.doc.name, month: value });
		if (!dialog.get_value("item") && asked.item) dialog.set_value("item", asked.item);
		const money = (amount) => format_currency(amount, asked.currency);
		const hours = (value) => format_number(value, null, value % 1 ? 1 : 0);
		const lines = [__("{0} h used of {1} h.", [hours(asked.hours), hours(said.allowance)])];
		if (asked.drafts) lines.push(__("{0} h are on timesheets not submitted yet.", [hours(asked.drafts)]));
		dialog.get_field("said").$wrapper.html(lines.map((line) => `<p class="text-muted">${frappe.utils.escape_html(line)}</p>`).join(""));
		dialog.set_df_property("overage", "hidden", asked.over && asked.over_amount ? 0 : 1);
		dialog.set_df_property(
			"overage",
			"label",
			__("Bill the {0} h over, {1}", [hours(asked.over), money(asked.over_amount)])
		);
	};
	dialog.show();
	show(first);
};

// Bill Progress on a project with more than one order asks which, each with
// what's left to bill; with one, it bills that one (progress.js).
// A project billed by milestones starts from the share they come to.
onedesk.project.bill_progress = (orders, contract, currency, share) => {
	const open = (orders || []).filter((one) => one.billable && one.billed < 100);
	// The milestones' share is the page's own, so an order under it starts
	// from what it has billed.
	const bill = (name) => {
		const one = open.find((order) => order.name === name);
		onedesk.progress.ask({ doctype: "Sales Order", doc: { name } }, !one || one.own ? share : null);
	};
	if (open.length <= 1) return bill(open.length ? open[0].name : contract);
	const dialog = new frappe.ui.Dialog({
		title: __("Bill Progress"),
		fields: [
			{
				fieldtype: "Select",
				fieldname: "order",
				label: __("Order"),
				reqd: 1,
				options: open.map((one) => ({
					value: one.name,
					label: [one.name, one.where, __("{0} left", [format_currency(one.left, currency)])].filter(Boolean).join(" · "),
				})),
				default: open[0].name,
			},
		],
		primary_action_label: __("Next"),
		primary_action: ({ order }) => {
			dialog.hide();
			bill(order);
		},
	});
	dialog.show();
};

// A milestone: a task marked Is Milestone, on the project or one under it,
// billed on completion when it carries a share of the contract. See
// one_project/milestones.py.
onedesk.project.add_milestone = (projects, billed, done) => {
	const dialog = new frappe.ui.Dialog({
		title: __("Add Milestone"),
		fields: [
			{ fieldtype: "Data", fieldname: "subject", label: __("Milestone"), reqd: 1 },
			{
				fieldtype: "Select",
				fieldname: "project",
				label: __("Project"),
				reqd: 1,
				options: projects,
				default: projects[0]?.value,
				hidden: projects.length < 2,
			},
			{ fieldtype: "Date", fieldname: "exp_end_date", label: __("Due Date"), reqd: 1 },
			{
				fieldtype: "Percent",
				fieldname: "one_bill_share",
				label: __("Bill on Completion"),
				description: __("Share of the contract"),
				hidden: !billed,
			},
		],
		primary_action_label: __("Add Milestone"),
		primary_action: async (values) => {
			dialog.disable_primary_action();
			try {
				await frappe.xcall("frappe.client.insert", {
					doc: { doctype: "Task", is_milestone: 1, ...values },
				});
				dialog.hide();
				done?.();
			} finally {
				dialog.enable_primary_action();
			}
		},
	});
	dialog.show();
};

// Ask for Updates: ERPNext's own Collect Progress fields on the project, how
// often and when the team is asked, saved against the project as it was
// loaded. See one_project/updates.py.
onedesk.project.ASKING = [
	"collect_progress",
	"frequency",
	"daily_time_to_send",
	"first_email",
	"second_email",
	"day_to_send",
	"weekly_time_to_send",
	"holiday_list",
	"subject",
	"message",
];

onedesk.project.ask_updates = async (project, done) => {
	await frappe.model.with_doctype("Project");
	const doc = await frappe.db.get_doc("Project", project);
	const dialog = new frappe.ui.Dialog({
		title: __("Ask for Updates"),
		fields: onedesk.project.ASKING.map((fieldname) => frappe.meta.get_docfield("Project", fieldname))
			.filter(Boolean)
			.map((df) => ({ ...df, default: doc[df.fieldname] })),
		primary_action_label: __("Save"),
		primary_action: async (values) => {
			dialog.disable_primary_action();
			try {
				await frappe.xcall("frappe.client.save", { doc: { ...doc, ...values } });
				dialog.hide();
				done?.();
			} finally {
				dialog.enable_primary_action();
			}
		},
	});
	dialog.show();
};

// About on a project's Overview, changed in place: ERPNext's own Project
// fields, saved against the project as the page loaded it, so a change made
// meanwhile is refused as a form's would be. % Complete is typed only when
// progress is Manual.
onedesk.project.ABOUT = ["one_manager", "expected_start_date", "expected_end_date", "percent_complete_method", "percent_complete", "priority", "one_time", "one_site"];

onedesk.project.edit = async (project, modified, fieldnames, title, done) => {
	await frappe.model.with_doctype("Project");
	const doc = await frappe.db.get_doc("Project", project);
	const fields = fieldnames
		.map((fieldname) => frappe.meta.get_docfield("Project", fieldname))
		.filter(Boolean)
		.map((df) => {
			const field = { ...df, default: doc[df.fieldname] };
			if (df.fieldname === "percent_complete") {
				Object.assign(field, { read_only: 0, depends_on: "eval:doc.percent_complete_method == 'Manual'" });
			}
			// Named as About names them; the Brief is the dialog's whole.
			if (df.fieldname === "percent_complete_method") field.label = __("Progress");
			if (df.fieldname === "notes") field.label = "";
			return field;
		});
	const dialog = new frappe.ui.Dialog({
		title,
		size: fieldnames.includes("notes") ? "large" : undefined,
		fields,
		primary_action_label: __("Save"),
		primary_action: async (values) => {
			dialog.disable_primary_action();
			try {
				await frappe.xcall("frappe.client.save", { doc: { ...doc, ...values, modified } });
				dialog.hide();
				done?.();
			} catch {
				// frappe has said why, as a changed record's "Please refresh".
			} finally {
				dialog.enable_primary_action();
			}
		},
	});
	dialog.show();
};

onedesk.project.edit_about = (project, modified, done) =>
	onedesk.project.edit(project, modified, onedesk.project.ABOUT, __("Edit About"), done);

onedesk.project.edit_brief = (project, modified, done) =>
	onedesk.project.edit(project, modified, ["notes"], __("Brief"), done);

// A task's details, changed from the project's task panel: ERPNext's own
// Task fields in frappe's controls, Depends On as frappe's table, saved
// against the task as the panel loaded it. One_task/README.md has what each
// is for.
onedesk.project.task_details = async (task, modified, done) => {
	await frappe.model.with_doctype("Task");
	const doc = await frappe.db.get_doc("Task", task);
	// The table names each task by its subject, as Task links do.
	for (const row of doc.depends_on || []) if (row.subject) frappe.utils.add_link_title("Task", row.task, row.subject);
	const field = (fieldname, extra = {}) => ({ ...frappe.meta.get_docfield("Task", fieldname), default: doc[fieldname], ...extra });
	const fields = [
		field("type"),
		field("expected_time"),
		field("parent_task", {
			get_query: () => ({ filters: { name: ["!=", task], project: doc.project || undefined, status: ["!=", "Template"] } }),
		}),
		doc.is_milestone && frappe.meta.get_docfield("Task", "one_bill_share") ? field("one_bill_share") : null,
		{
			fieldtype: "Table",
			fieldname: "depends_on",
			label: __("Waits On"),
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
		},
		field("description", { label: __("Description") }),
	].filter(Boolean);
	const dialog = new frappe.ui.Dialog({
		title: __("Edit Details"),
		size: "large",
		fields,
		primary_action_label: __("Save"),
		primary_action: async (values) => {
			dialog.disable_primary_action();
			try {
				const depends_on = (values.depends_on || []).filter((row) => row.task).map((row) => ({ task: row.task }));
				await frappe.xcall("frappe.client.save", { doc: { ...doc, ...values, depends_on, modified } });
				dialog.hide();
				done?.();
			} catch {
				// frappe has said why, as a changed task's "Please refresh".
			} finally {
				dialog.enable_primary_action();
			}
		},
	});
	dialog.show();
};

// Repeat, as the task's form offers it: frappe's own Auto Repeat prompt.
onedesk.project.repeat_task = (task, done) =>
	frappe.utils.new_auto_repeat_prompt({ doc: { doctype: "Task", name: task }, reload_doc: () => done?.() });

onedesk.project.stop_repeat = async (repeat, done) => {
	await frappe.xcall("frappe.client.set_value", { doctype: "Auto Repeat", name: repeat, fieldname: "disabled", value: 1 });
	done?.();
};
