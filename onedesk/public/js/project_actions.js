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
			{ fieldtype: "Percent", fieldname: "retention", label: __("Retention") },
			{
				fieldtype: "Date",
				fieldname: "retention_due",
				label: __("Retention Due"),
				depends_on: "eval:doc.retention",
				mandatory_depends_on: "eval:doc.retention",
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
// whose tasks it may be on; billable is ticked when the project has a customer.
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
			},
			{ fieldtype: "Section Break" },
			{ fieldtype: "Small Text", fieldname: "description", label: __("Description") },
			{ fieldtype: "Check", fieldname: "billable", label: __("Billable"), default: frm.doc.customer ? 1 : 0 },
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
		const money = (amount) => format_currency(amount, frappe.defaults.get_default("currency"));
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
