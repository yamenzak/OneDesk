// A project's page: its board, calendar and plan as buttons of their own,
// Group Under New Project, Save as Template, Invoice Time, Quote Extra Work and
// Post Update.
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
		onedesk.project.money(frm);
		onedesk.project.cost_types(frm);
		frappe.realtime.off("one_project_money");
		frappe.realtime.on("one_project_money", (data) => {
			// The head's figures come with the record, so an unchanged form is
			// read again; one being edited keeps its edits and redraws the tab.
			if (cur_frm !== frm || data.project !== frm.doc.name) return;
			if (frm.is_dirty()) {
				onedesk.project.money(frm);
				onedesk.project.cost_types(frm);
			} else {
				frm.reload_doc();
			}
		});
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
// The Costing tab: the customer's side, the cost side and the forecast, each
// figure opening the documents behind it (one_project/money.py).
onedesk.project.money = async (frm) => {
	const said = await frappe.xcall("onedesk.one_project.money.money", { project: frm.doc.name });
	if (frm.doc.name !== said.project) return;
	const money = (value) => format_currency(value, said.currency, 0);
	const row = (figures) =>
		`<div class="one-stats">${figures.map((one) => onedesk.band.stat(one.label, money(one.value), one.route, one.tone)).join("")}</div>`;
	const draw = (field, ...rows) => {
		frm.get_field(field).$wrapper.html(`<div class="one-figures">${rows.map(row).join("")}</div>`);
	};
	draw("one_customer", said.customer);
	// What suppliers were asked for, then what the team spent itself.
	draw("one_cost", said.cost, said.own);
	onedesk.project.suppliers(frm, said, money);
	draw("one_forecast", [
		{ label: __("Contract"), value: said.contract },
		{ label: __("Budget"), value: said.budget },
		{ label: __("Forecast Cost"), value: said.forecast_cost },
		{ label: __("Forecast Margin"), value: said.forecast_margin, tone: said.forecast_margin < 0 ? "alarm" : null },
		{ label: __("Margin So Far"), value: said.margin, tone: said.margin < 0 ? "alarm" : null },
	]);
};

// Each order from a supplier on the project, the subcontracts, as a table:
// what it's for, billed, left to bill, retention held, advance not yet set
// off, and paid. The supplier opens the order.
onedesk.project.suppliers = (frm, said, money) => {
	const rows = said.suppliers || [];
	frm.toggle_display("one_suppliers_section", rows.length > 0);
	if (!rows.length) return;
	const esc = frappe.utils.escape_html;
	const columns = [
		["ordered", __("Ordered")],
		["billed", __("Billed")],
		["left", __("Left to Bill")],
		["retention", __("Retention Held")],
		["advance", __("Advance Left")],
		["paid", __("Paid")],
	];
	const head = `<tr><th>${esc(__("Supplier"))}</th>${columns.map(([, label]) => `<th class="text-right">${esc(label)}</th>`).join("")}</tr>`;
	const body = rows
		.map(
			(row) =>
				`<tr><td><a href="${row.route}">${esc(row.supplier)}</a><div class="text-muted small">${esc(row.order)}</div></td>` +
				columns.map(([key]) => `<td class="text-right">${esc(money(row[key]))}</td>`).join("") +
				`</tr>`
		)
		.join("");
	frm.get_field("one_suppliers").$wrapper.html(
		`<div class="table-responsive one-suppliers"><table class="table table-sm"><thead>${head}</thead><tbody>${body}</tbody></table></div>`
	);
};

// The budget by cost type: ERPNext's own Budget against the project, one
// per expense account (one_project/budget.py). A row opens it to change.
onedesk.project.cost_types = async (frm, said) => {
	said = said || (await frappe.xcall("onedesk.one_project.budget.lines", { project: frm.doc.name }));
	if (frm.doc.name !== cur_frm?.doc?.name) return;
	const rows = said.lines;
	frm.toggle_display("one_budget_section", rows.length > 0 || said.can_set);
	// The project's Budget is the cost types added up once there are any.
	frm.set_df_property("estimated_costing", "read_only", rows.length ? 1 : 0);
	const $field = frm.get_field("one_budget").$wrapper;
	const esc = frappe.utils.escape_html;
	const money = (value) => format_currency(value, frappe.defaults.get_default("currency"), 0);
	const columns = [
		["budget", __("Budget")],
		["committed", __("Committed")],
		["spent", __("Spent")],
		["left", __("Left")],
	];
	const table = rows.length
		? `<div class="table-responsive one-suppliers"><table class="table table-sm"><thead><tr><th>${esc(__("Cost Type"))}</th>` +
			columns.map(([, label]) => `<th class="text-right">${esc(label)}</th>`).join("") +
			`</tr></thead><tbody>` +
			rows
				.map(
					(row, i) =>
						`<tr data-row="${i}"><td>${said.can_set ? `<a href="#" data-row="${i}">${esc(row.cost_type)}</a>` : esc(row.cost_type)}</td>` +
						columns
							.map(
								([key]) =>
									`<td class="text-right${key === "left" && row.left < 0 ? " text-danger" : ""}">${esc(onedesk.shell.ltr(money(row[key])))}</td>`
							)
							.join("") +
						`</tr>`
				)
				.join("") +
			`</tbody></table></div>`
		: `<p class="text-muted">${esc(__("No cost types"))}</p>`;
	$field.html(
		table + (said.can_set ? `<button class="btn btn-xs btn-default one-add" data-add>${esc(__("Add Cost Type"))}</button>` : "")
	);
	$field.find("a[data-row]").on("click", (e) => {
		e.preventDefault();
		onedesk.project.cost_type(frm, rows[Number(e.currentTarget.dataset.row)]);
	});
	$field.find("[data-add]").on("click", () => onedesk.project.cost_type(frm));
};

onedesk.project.cost_type = (frm, row) => {
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
				get_query: () => ({ filters: { root_type: "Expense", is_group: 0, company: frm.doc.company } }),
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
			onedesk.project.cost_types(frm, said);
			frm.reload_doc();
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
						onedesk.project.cost_types(frm, said);
					})
			: null,
	});
	dialog.show();
};

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
