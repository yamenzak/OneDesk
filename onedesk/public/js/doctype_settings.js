frappe.provide("onedesk.doctype_settings");

onedesk.doctype_settings.offered = (meta) =>
	!!meta &&
	!meta.istable &&
	!meta.issingle &&
	frappe.user.has_role("Workspace Administrator") &&
	!(frappe.model.can_create("Custom Field") && frappe.model.can_create("Property Setter")) &&
	!(frappe.boot.one_refused_modules || []).includes(meta.module);

onedesk.doctype_settings.open = (doctype, tab = null, closed = null) =>
	frappe.require("doctype_settings.bundle.js", () =>
		frappe.model.with_doctype(doctype, () => {
			onedesk.doctype_settings.adapt();
			const opening = frappe.doctype_settings.open(doctype);
			opening &&
				opening.then((dialog) => {
					if (!dialog) return;
					tab && dialog.activate(tab);
					closed && dialog.$wrapper.one("hidden.bs.modal", closed);
				});
		})
	);

onedesk.doctype_settings.TABS = ["notifications", "naming", "print-format", "email-template", "workflow", "automations", "access"];

onedesk.doctype_settings.adapt = () => {
	if (onedesk.doctype_settings.adapted) return;
	onedesk.doctype_settings.adapted = true;
	delete frappe.doctype_settings.builders.general;
	const beside = frappe.doctype_settings.groups.find((group) => group.items.some((item) => item.id === "workflow"));
	beside &&
		beside.items.splice(beside.items.findIndex((item) => item.id === "workflow") + 1, 0, {
			id: "automations",
			label: __("Automations"),
			icon: "zap",
			condition: () => frappe.model.can_read("Automation Flow"),
		});
	beside && beside.items.push({ id: "access", label: __("Access"), icon: "shield-check" });
	for (const group of frappe.doctype_settings.groups) {
		for (const item of group.items) {
			const shown = item.condition;
			if (item.id === "naming") item.label = __("Numbering");
			if (item.id === "email-template") item.label = __("Mail Templates");
			if (item.id === "workflow") item.label = __("Approvals");
			if (item.id === "print-format") item.label = __("Printing");
			item.condition = (doctype) => onedesk.doctype_settings.TABS.includes(item.id) && (shown ? shown(doctype) : true);
		}
	}
	const print_formats = frappe.doctype_settings.builders["print-format"];
	print_formats &&
		frappe.doctype_settings.register("print-format", (panel, doctype) => {
			const set_view = panel.set_view.bind(panel);
			panel.set_view = (view) =>
				set_view({
					...view,
					actions: (view.actions || []).map((one) => (one.label === __("New") ? { ...one, click: () => onedesk.printing.new_format(panel, doctype) } : one)),
				});
			return print_formats(panel, doctype);
		});
	const get_list = frappe.doctype_settings.get_list;
	frappe.doctype_settings.get_list = (doctype, args = {}) =>
		get_list(doctype, doctype === "Print Format" ? { ...args, filters: { ...(args.filters || {}), disabled: 0 } } : args);
	const set_property = frappe.doctype_settings.set_property;
	frappe.doctype_settings.set_property = (doctype, property, value) =>
		property === "default_print_format"
			? frappe
					.xcall("onedesk.one.printing.set_default", { doctype, print_format: value })
					.then(() => frappe.show_alert({ message: __("Default updated"), indicator: "green" }))
			: set_property(doctype, property, value);
	const get_value = frappe.db.get_value;
	frappe.db.get_value = function (doctype, filters, fieldname, callback) {
		const setter = doctype === "Property Setter" && filters && filters.property === "default_print_format";
		const own = doctype === "DocType" && fieldname === "default_print_format";
		if ((!setter && !own) || frappe.model.can_read(doctype)) return get_value.apply(this, arguments);
		const answer = setter
			? frappe.xcall("onedesk.one.printing.default", { doctype: filters.doc_type }).then((value) => ({ message: { value } }))
			: Promise.resolve({ message: { default_print_format: null } });
		return answer.then((r) => {
			callback && callback(r.message);
			return r;
		});
	};
	const table = (panel, { title, description, add, load, columns, open, icon, empty, actions = [] }) => {
		let $into;
		const draw = async () => {
			const rows = await load();
			$into.empty();
			onedesk.shell.table($into, {
				rows,
				icon,
				empty,
				open: open && ((row) => open(row, draw)),
				columns: [
					...columns,
					...(actions.length
						? [{ type: "actions", actions: actions.map((one) => ({ ...one, action: (row) => one.action(row, draw) })) }]
						: []),
				],
			});
		};
		panel.set_view({
			title,
			description,
			actions: add ? [{ label: add.label, icon: "plus", click: () => add.click(draw) }] : [],
			render: (p) => {
				$into = $("<div></div>").appendTo(p.body.empty());
				draw();
			},
		});
	};
	const esc = frappe.utils.escape_html;
	const named = (label, badge) => esc(label) + (badge ? " " + frappe.ui.badge.html(badge) : "");
	frappe.doctype_settings.register("email-template", (panel, doctype) => {
		let current = null;
		const edit = (name, draw) => onedesk.mail_templates.edit(name, { doctype, done: draw });
		table(panel, {
			title: __("Mail Templates"),
			add: { label: __("New Template"), click: (draw) => edit(null, draw) },
			icon: "mail",
			empty: __("No mail templates"),
			load: () =>
				Promise.all([
					frappe.doctype_settings.get_list("Email Template", {
						filters: { reference_doctype: doctype },
						fields: ["name", "subject"],
						order_by: "name asc",
						limit: 0,
					}),
					frappe.xcall(onedesk.mail_templates.API + "default", { doctype }),
				]).then(([rows, value]) => {
					current = value;
					return rows;
				}),
			open: (row, draw) => edit(row.name, draw),
			columns: [
				{ label: __("Template"), render: (row) => named(row.name, row.name === current && { label: __("Default"), theme: "blue" }) },
				{ label: __("Subject"), fieldname: "subject" },
			],
			actions: [
				{
					label: __("Set as Default"),
					icon: "star",
					action: (row, draw) =>
						frappe.xcall(onedesk.mail_templates.API + "set_default", { doctype, template: row.name }).then(() => {
							frappe.show_alert({ message: __("Default updated"), indicator: "green" });
							draw();
						}),
				},
			],
		});
	});
	frappe.doctype_settings.register("workflow", (panel, doctype) => {
		const open = (name) => {
			panel.dialog.hide();
			frappe.set_route("workflow-builder", name);
		};
		table(panel, {
			title: __("Approvals"),
			add: {
				label: __("New Approval"),
				click: () => {
					panel.dialog.hide();
					onedesk.approvals.create(doctype);
				},
			},
			icon: "route",
			empty: __("No approvals"),
			load: () =>
				frappe.doctype_settings.get_list("Workflow", {
					filters: { document_type: doctype },
					fields: ["name", "workflow_name", "is_active"],
					order_by: "name asc",
					limit: 0,
				}),
			open: (row) => open(row.name),
			columns: [
				{
					label: __("Approval"),
					render: (row) => named(row.workflow_name || row.name, { label: row.is_active ? __("On") : __("Off"), theme: row.is_active ? "green" : "gray" }),
				},
			],
			actions: [
				{
					label: __("Turn On or Off"),
					icon: "power",
					action: (row, draw) => frappe.db.set_value("Workflow", row.name, { is_active: row.is_active ? 0 : 1 }).then(draw),
				},
			],
		});
	});
	frappe.doctype_settings.register("automations", (panel, doctype) => {
		const form = (name) => {
			panel.dialog.hide();
			frappe.app.sidebar && frappe.app.sidebar.select_module("One");
			name ? frappe.set_route("Form", "Automation Flow", name) : frappe.new_doc("Automation Flow", { document_type: doctype });
		};
		table(panel, {
			title: __("Automations"),
			add: { label: __("New Automation"), click: () => form(null) },
			icon: "zap",
			empty: __("No automations"),
			load: () =>
				frappe.doctype_settings.get_list("Automation Flow", {
					filters: { document_type: doctype },
					fields: ["name", "title", "trigger_type", "trigger_field", "to_value", "date_field", "date_offset", "date_direction", "enabled"],
					order_by: "title asc",
					limit: 0,
				}),
			open: (row) => form(row.name),
			columns: [
				{
					label: __("Automation"),
					render: (row) => named(row.title || row.name, { label: row.enabled ? __("On") : __("Off"), theme: row.enabled ? "green" : "gray" }),
				},
				{ label: __("When"), render: (row) => esc(onedesk.automations.when(row, doctype)) },
			],
			actions: [
				{
					label: __("Turn On or Off"),
					icon: "power",
					action: (row, draw) => frappe.db.set_value("Automation Flow", row.name, { enabled: row.enabled ? 0 : 1 }).then(draw),
				},
			],
		});
	});
	const go = (panel, args) => {
		panel.dialog.hide();
		frappe.app.sidebar && frappe.app.sidebar.select_module("One");
		frappe.set_route("workspace-settings", { section: "notification_types", ...args });
	};
	frappe.doctype_settings.register("notifications", (panel, doctype) =>
		table(panel, {
			title: __("Notifications"),
			add: { label: __("New Rule"), click: () => go(panel, { rule: "new", for: doctype }) },
			icon: "bell",
			empty: __("No rules"),
			load: () =>
				frappe.doctype_settings.get_list("Notification", {
					filters: { document_type: doctype, one_rule: 1 },
					fields: ["name", "event", "enabled"],
					order_by: "name asc",
					limit: 0,
				}),
			open: (row) => go(panel, { rule: row.name }),
			columns: [
				{ label: __("Rule"), render: (row) => named(row.name, !row.enabled && { label: __("Off"), theme: "gray" }) },
				{ label: __("When"), render: (row) => esc(row.event ? __(row.event) : "") },
			],
		})
	);
	frappe.doctype_settings.register("access", (panel, doctype) => {
		const said = (right) =>
			({ select: __("Select"), read: __("Read"), write: __("Edit"), create: __("Create"), delete: __("Delete"), submit: __("Submit"), cancel: __("Cancel"), export: __("Export") })[right];
		const level = (name) => {
			panel.dialog.hide();
			frappe.app.sidebar && frappe.app.sidebar.select_module("One");
			frappe.set_route("workspace-settings", name ? { section: "access", level: name } : { section: "access" });
		};
		table(panel, {
			title: __("Access"),
			add: { label: __("New Role"), click: () => level(null) },
			icon: "shield-check",
			empty: __("No roles"),
			load: () =>
				frappe
					.xcall("onedesk.one.access.doctype_levels", { doctype })
					.then((apps) => apps.flatMap((app) => app.rows.map((row) => ({ ...row, app: app.app })))),
			open: (row) => level(row.key),
			columns: [
				{ label: __("App"), render: (row) => esc(row.app) },
				{
					label: __("Role"),
					render: (row) => named(row.own ? row.level : __(row.level), row.own && { label: __("Custom"), theme: "purple" }),
				},
				{
					label: __("Permissions"),
					render: (row) => row.rights.map((right) => frappe.ui.badge.html({ label: said(right), theme: "gray" })).join(" "),
				},
			],
		});
	});
	frappe.doctype_settings.register("naming", (panel, doctype) => {
		let list;
		const head = (series) => ({
			title: __("Numbering"),
			actions: series ? [{ label: __("Add Series"), icon: "plus", click: () => onedesk.numbering.add(doctype, () => list.refresh()) }] : [],
		});
		panel.set_view({
			...head(true),
			render: (p) => {
				const $body = p.body.empty();
				const $by = $('<div class="one-numbering-by"></div>').appendTo($body);
				const $series = $('<div class="one-numbering-series"></div>').appendTo($body);
				list = onedesk.numbering.list($series, doctype);
				const series = (said) => (said ? said.series : !!frappe.meta.has_field(doctype, "naming_series"));
				const shown = (said) => {
					$series.toggle(series(said));
					panel.set_header(head(series(said)));
				};
				shown(null);
				onedesk.numbering.named_by($by, doctype, shown);
				onedesk.numbering.rules($('<div class="one-numbering-rules"></div>').appendTo($body), doctype);
			},
		});
	});
};

frappe.provide("onedesk.numbering");

onedesk.numbering.API = "onedesk.one.numbering.";

onedesk.numbering.list = ($wrapper, doctype) => {
	const esc = frappe.utils.escape_html;
	const draw = async () => {
		const rows = await frappe.xcall(onedesk.numbering.API + "series", { doctype });
		$wrapper.empty();
		onedesk.shell.table($wrapper, {
			rows,
			icon: "hash",
			empty: __("{0} is not named by a series.", [__(doctype)]),
			open: (row) => onedesk.numbering.edit(doctype, row, rows, draw),
			columns: [
				{
					label: __("Series"),
					render: (row) => esc(row.series) + (rows[0].series === row.series ? " " + frappe.ui.badge.html({ label: __("Default"), theme: "blue" }) : ""),
				},
				{ label: __("Next"), render: (row) => `<samp>${esc(row.next || "")}</samp>` },
			],
		});
	};
	draw();
	return { refresh: draw };
};

onedesk.numbering.add = (doctype, done) => {
	const dialog = new frappe.ui.Dialog({
		title: __("Add Series"),
		fields: [
			{
				fieldtype: "Data",
				fieldname: "series",
				label: __("New Series"),
				reqd: 1,
				description: __("For example {0}", ["INV-.YYYY.-.#####"]),
				onchange: () => onedesk.numbering.preview(doctype, dialog, "series", true),
			},
			{ fieldtype: "Check", fieldname: "first", label: __("Default"), description: __("A new record starts with this series.") },
			{ fieldtype: "Section Break", label: __("Series Format"), collapsible: 1 },
			{ fieldtype: "HTML", fieldname: "help", options: onedesk.numbering.help_html() },
		],
		primary_action_label: __("Add"),
		primary_action: async ({ series, first }) => {
			const rows = await frappe.xcall(onedesk.numbering.API + "series", { doctype });
			const kept = rows.map((one) => one.series);
			series = series.trim();
			await frappe.xcall(onedesk.numbering.API + "save", { doctype, options: first ? [series, ...kept] : [...kept, series] });
			dialog.hide();
			frappe.show_alert({ message: __("Series added"), indicator: "green" });
			done();
		},
	});
	dialog.fields_dict.series.$input.on("input", frappe.utils.debounce(() => onedesk.numbering.preview(doctype, dialog, "series", true), 300));
	dialog.show();
};

onedesk.numbering.preview = async (doctype, dialog, fieldname, adding = false) => {
	const field = dialog.fields_dict[fieldname];
	const one = (field.get_value() || "").trim();
	const said = one ? await frappe.xcall(onedesk.numbering.API + "preview", { doctype, one }) : {};
	if ((field.get_value() || "").trim() !== one) return;
	const esc = frappe.utils.escape_html;
	field.set_description(
		said.error || (adding && said.mine)
			? `<span class="text-danger">${esc(said.error || __("{0} is already one of its series.", [one]))}</span>`
			: said.next
			? __("Next: {0}", [`<samp>${esc(said.next)}</samp>`])
			: __("For example {0}", ["INV-.YYYY.-.#####"])
	);
};

onedesk.numbering.edit = (doctype, row, rows, done) => {
	const dialog = new frappe.ui.Dialog({
		title: __("Edit Series"),
		fields: [
			{
				fieldtype: "Data",
				fieldname: "series",
				label: __("Series"),
				reqd: 1,
				default: row.series,
				description: __("Next: {0}", [row.next]),
				onchange: () => onedesk.numbering.preview(doctype, dialog, "series"),
			},
			{
				fieldtype: "Check",
				fieldname: "first",
				label: __("Default"),
				default: rows[0].series === row.series ? 1 : 0,
				read_only: rows[0].series === row.series ? 1 : 0,
				description: __("A new record starts with this series."),
			},
			{
				fieldtype: "Int",
				fieldname: "current",
				label: __("Current Value"),
				default: row.current,
				description: row.last_name
					? __("Can only go up, and not below {0}, used by {1} {2}.", [row.used, __(doctype), row.last_name])
					: __("Can only go up."),
			},
			{ fieldtype: "Section Break", label: __("Series Format"), collapsible: 1 },
			{ fieldtype: "HTML", fieldname: "help", options: onedesk.numbering.help_html() },
		],
		primary_action_label: __("Update"),
		primary_action: async ({ series, current, first }) => {
			series = (series || "").trim();
			let options = rows.map((one) => (one.series === row.series ? series : one.series));
			if (first && rows[0].series !== row.series) options = [series, ...options.filter((one) => one !== series)];
			if (options.join("\n") !== rows.map((one) => one.series).join("\n")) {
				await frappe.xcall(onedesk.numbering.API + "save", { doctype, options });
			}
			if (cint(current) !== cint(row.current)) {
				await frappe.xcall(onedesk.numbering.API + "set_current", { doctype, one: series, current: cint(current) });
			}
			dialog.hide();
			frappe.show_alert({ message: __("Series updated"), indicator: "green" });
			done();
		},
	});
	dialog.fields_dict.series.$input.on("input", frappe.utils.debounce(() => onedesk.numbering.preview(doctype, dialog, "series"), 300));
	dialog.set_secondary_action_label(__("Delete"));
	dialog.set_secondary_action(() =>
		frappe.confirm(__("Delete series {0}?", [row.series]), async () => {
			await frappe.xcall(onedesk.numbering.API + "save", { doctype, options: rows.map((one) => one.series).filter((one) => one !== row.series) });
			dialog.hide();
			done();
		})
	);
	dialog.show();
};

frappe.ui.form.on("Automation Flow", {
	refresh(frm) {
		onedesk.automations.offer(frm);
		if (frappe.model.can_create("Custom Field")) return;
		for (const fieldname of ["advanced_condition_section", "condition", "run_as", "automation_user"]) {
			frm.toggle_display(fieldname, false);
		}
	},
	document_type: (frm) => onedesk.automations.offer(frm),
	trigger_type: (frm) => onedesk.automations.offer(frm),
});

frappe.provide("onedesk.automations");

onedesk.automations.PLUMBING = ["step_key", "target", "output_alias", "step_condition", "related_condition", "parent_step", "branch"];

onedesk.automations.held = () => !frappe.model.can_create("Custom Field");

onedesk.automations.steps = (frm) => {
	const key = `${frm.doc.document_type || ""}|${frm.doc.trigger_type || ""}`;
	if (frm.one_steps?.key !== key) {
		const ready = frappe
			.xcall("onedesk.one.automations.steps", {
				doctype: frm.doc.document_type || null,
				trigger_type: frm.doc.trigger_type || null,
			})
			.catch(() => ({ actions: [], steps: ["Action"], events: [] }));
		frm.one_steps = { key, ready };
	}
	return frm.one_steps.ready;
};

onedesk.automations.STEP_LABELS = () => ({
	Action: __("Action"),
	Wait: __("Wait"),
	WaitForEvent: __("Wait for an Event"),
	If: __("If"),
});

onedesk.automations.when = (row, doctype) => {
	const label = (fieldname) => (fieldname && __(frappe.meta.get_label(doctype, fieldname) || fieldname, null, doctype)) || "";
	switch (row.trigger_type) {
		case "Doc Created":
			return __("When one is made");
		case "Doc Updated":
			return __("When one is saved");
		case "Doc Submitted":
			return __("When one is submitted");
		case "Doc Cancelled":
			return __("When one is cancelled");
		case "Doc Deleted":
			return __("When one is deleted");
		case "Field Value Changed":
			return row.to_value
				? __("When {0} changes to {1}", [label(row.trigger_field), __(row.to_value)])
				: __("When {0} changes", [label(row.trigger_field)]);
		case "Date Based":
			return row.date_direction === "Before"
				? __("{0} days before {1}", [row.date_offset || 0, label(row.date_field)])
				: __("{0} days after {1}", [row.date_offset || 0, label(row.date_field)]);
		case "Scheduled":
			return __("On a schedule");
		default:
			return row.trigger_type ? __(row.trigger_type) : "";
	}
};

onedesk.automations.offer = (frm) =>
	onedesk.automations.steps(frm).then((said) => {
		const grid = frm.fields_dict.actions?.grid;
		if (!grid || grid.one_offered === frm.one_steps.key) return said;
		grid.one_offered = frm.one_steps.key;
		const kinds = onedesk.automations.STEP_LABELS();
		const labels = Object.fromEntries(said.actions.map((one) => [one.action_type, one.label]));
		grid.update_docfield_property("step_type", "fieldtype", "Select");
		grid.update_docfield_property(
			"step_type",
			"options",
			said.steps.map((kind) => ({ value: kind, label: kinds[kind] }))
		);
		grid.update_docfield_property("action_type", "options", [
			{ value: "", label: "" },
			...said.actions.map((one) => ({ value: one.action_type, label: labels[one.action_type] })),
		]);
		grid.set_column_disp_in_list_view("params", false);
		const map = frappe.meta.docfield_map["Automation Action"] || {};
		if (map.action_type) map.action_type.formatter = (value) => labels[value] || value;
		if (map.step_type) map.step_type.formatter = (value) => kinds[value] || value;
		grid.refresh();
		return said;
	});

onedesk.automations.waits = (said) => {
	const units = ["Minutes", "Hours", "Days"].map((unit) => ({ value: unit, label: __(unit) }));
	return {
		Wait: [
			{ fieldname: "value", label: __("How Long"), fieldtype: "Int", reqd: 1 },
			{ fieldname: "unit", label: __("Unit"), fieldtype: "Select", options: units, default: "Minutes" },
		],
		WaitForEvent: [
			{
				fieldname: "event_name",
				label: __("Event"),
				fieldtype: "Select",
				reqd: 1,
				options: said.events.map((one) => ({ value: one.name, label: __(one.label || one.name) })),
			},
			{ fieldname: "correlation_key", label: __("Matched By"), fieldtype: "Data", reqd: 1 },
			{ fieldname: "timeout_value", label: __("Give Up After"), fieldtype: "Int", reqd: 1 },
			{ fieldname: "timeout_unit", label: __("Unit"), fieldtype: "Select", options: units, default: "Days" },
		],
	};
};

onedesk.automations.field = async (one, frm, action_type) => {
	const df = {
		fieldname: one.fieldname,
		label: one.label,
		fieldtype: one.fieldtype,
		options: one.options,
		reqd: one.reqd,
		default: one.default,
	};
	if (one.control === "users") {
		const options = (txt) =>
			frappe
				.xcall("frappe.automation_engine.api.get_param_options", {
					action_type,
					fieldname: one.fieldname,
					doctype: frm.doc.document_type || "",
					search_text: txt || "",
				})
				.then((rows) =>
					rows.map((row) => ({ value: row.name, label: row.full_name || row.name, description: row.name }))
				);
		Object.assign(df, { fieldtype: "MultiSelectPills", get_data: options, one_options: await options() });
	} else if (one.options_source === "doc_fields") {
		const doctype = frm.doc.document_type;
		if (doctype) await frappe.model.with_doctype(doctype);
		const fields = doctype ? frappe.get_meta(doctype).fields : [];
		df.fieldtype = "Select";
		df.options = [
			{ value: "", label: "" },
			...fields
				.filter((field) => field.label && !frappe.model.no_value_type.includes(field.fieldtype))
				.map((field) => ({ value: field.fieldname, label: __(field.label, null, doctype) })),
		];
	} else if (one.fieldtype === "JSON") {
		Object.assign(df, { fieldtype: "Code", options: "JSON" });
	}
	if (one.link_filters) df.get_query = () => ({ filters: one.link_filters });
	if (one.options === "Email Template")
		df.get_query = () => ({
			query: "frappe.email.doctype.email_template.email_template.get_email_templates",
			filters: { reference_doctype: frm.doc.document_type || "" },
		});
	if (one.templatable) df.description = __("Can include a field of the record, such as {0}.", ["{{ doc.customer_name }}"]);
	return df;
};

onedesk.automations.draw = async (frm, cdn, changed = false) => {
	const row = locals["Automation Action"]?.[cdn];
	const form = frm.fields_dict.actions?.grid.grid_rows_by_docname[cdn]?.grid_form;
	if (!row || !form?.fields_dict.params) return;
	const said = await onedesk.automations.offer(frm);
	const kind = row.step_type || "Action";
	const action = kind === "Action" ? said.actions.find((one) => one.action_type === row.action_type) : null;
	const schema = action ? action.params_schema : onedesk.automations.waits(said)[kind];
	const fields = form.fields_dict;
	if (onedesk.automations.held())
		for (const fieldname of onedesk.automations.PLUMBING) fields[fieldname]?.$wrapper.toggle(false);
	fields.action_type?.$wrapper.toggle(kind === "Action");
	form.one_step?.$wrapper.remove();
	form.one_step = null;
	fields.params.$wrapper.toggle(!schema && !onedesk.automations.held());
	if (!schema) return;

	if (changed) await frappe.model.set_value(row.doctype, row.name, "params", "");
	let values = {};
	try {
		values = JSON.parse(row.params || "{}") || {};
	} catch {
		values = {};
	}

	const dfs = action ? await Promise.all(schema.map((one) => onedesk.automations.field(one, frm, row.action_type))) : schema;
	const $wrapper = $(`<div class="one-step-fields"></div>`).insertBefore(fields.params.$wrapper);
	if (action?.description) $(`<p class="text-muted small"></p>`).text(action.description).appendTo($wrapper);
	const group = new frappe.ui.FieldGroup({
		fields: dfs.map((df) => ({ ...df, onchange: () => group.one_ready && write() })),
		body: $("<div>").appendTo($wrapper),
	});
	group.make();
	const write = () => {
		const said = {};
		for (const df of dfs) {
			let value = group.get_value(df.fieldname);
			if (value == null || value === "" || (Array.isArray(value) && !value.length)) continue;
			if (df.fieldtype === "Text Editor" && !frappe.utils.html2text(value).trim()) continue;
			if (df.fieldtype === "Code") {
				try {
					value = JSON.parse(value);
				} catch {
				}
			}
			said[df.fieldname] = value;
		}
		frappe.model.set_value(row.doctype, row.name, "params", Object.keys(said).length ? JSON.stringify(said) : "");
	};
	for (const df of dfs) {
		const control = group.get_field(df.fieldname);
		if (df.one_options) control.set_data(df.one_options);
		let value = values[df.fieldname];
		if (value === undefined) continue;
		if (df.fieldtype === "Code" && typeof value !== "string") value = JSON.stringify(value, null, 2);
		await group.set_value(df.fieldname, value);
	}
	group.one_ready = true;
	if (changed) write();
	form.one_step = { $wrapper, group };
};

frappe.ui.form.on("Automation Action", {
	form_render: (frm, cdt, cdn) => onedesk.automations.draw(frm, cdn),
	step_type: (frm, cdt, cdn) => onedesk.automations.draw(frm, cdn, true),
	action_type: (frm, cdt, cdn) => onedesk.automations.draw(frm, cdn, true),
});

frappe.provide("onedesk.approvals");

onedesk.approvals.create = (doctype = null) => {
	frappe.route_options = doctype ? { doctype } : null;
	frappe.set_route("workflow-builder");
};

onedesk.numbering.help_html = () => {
	const part = (code, said) => `<li><code>${code}</code> ${said}</li>`;
	return `<div class="text-muted small">
		<p>${__("A series is parts joined by dots. Text stays as written, such as INV- or SO/.")}</p>
		<ul>
			${part(".YYYY.", __("the year, 2026"))}
			${part(".YY.", __("the year's last two digits, 26"))}
			${part(".MM.", __("the month"))}
			${part(".DD.", __("the day of the month"))}
			${part(".JJJ.", __("the day of the year"))}
			${part(".WW.", __("the week of the year"))}
			${part(".FY.", __("the fiscal year (.TFY. for the short form)"))}
			${part(".ABBR.", __("the company's abbreviation"))}
			${part(".{fieldname}.", __("a field of the record, such as .{branch}."))}
			${part(".#####", __("the counter, one # per digit. It restarts when the text before it changes"))}
		</ul>
		<p>${__("Only letters, digits, spaces and - / _ . # { } are allowed.")}</p>
		<p>${__("Examples: {0}, {1}, {2}", ["<code>INV-.YYYY.-.#####</code>", "<code>SO/.YY./.####</code>", "<code>INV-.YYYY.-.MM.-.####</code>"])}</p>
	</div>`;
};

frappe.provide("onedesk.printing");

onedesk.printing.new_format = async (panel, doctype) => {
	const starts = await frappe.xcall("onedesk.one.printing.new_format_starts", { doctype });
	const every = __("Every field of {0}", [__(doctype)]);
	const dialog = new frappe.ui.Dialog({
		title: __("New Print Format"),
		fields: [
			{ fieldtype: "Data", fieldname: "name", label: __("Name"), reqd: 1 },
			{
				fieldtype: "Select",
				fieldname: "start_from",
				label: __("Start From"),
				options: [...starts.map((one) => ({ label: one.name, value: one.name })), { label: every, value: "" }],
				default: starts.length ? starts[0].name : "",
				description: __("The format to copy. It opens in the builder.", [__(doctype)]),
			},
		],
		primary_action_label: __("Create"),
		primary_action: async ({ name, start_from }) => {
			const made = await frappe.xcall("onedesk.one.printing.new_format", { doctype, name, start_from: start_from || null });
			dialog.hide();
			panel.dialog.hide();
			frappe.set_route("print-format-builder", made);
		},
	});
	dialog.show();
};

onedesk.numbering.set_up = async (naming) => {
	const kinds = await frappe.xcall(onedesk.numbering.API + "kinds");
	const dialog = new frappe.ui.Dialog({
		title: __("Set Up Naming"),
		fields: [{ fieldtype: "Autocomplete", fieldname: "doctype", label: __("Record Type"), options: kinds, reqd: 1 }],
		primary_action_label: __("Open"),
		primary_action: ({ doctype }) => {
			dialog.hide();
			naming(doctype);
		},
	});
	dialog.show();
};

onedesk.numbering.named_by = async ($wrapper, doctype, shown = () => {}) => {
	const API = onedesk.numbering.API;
	let said = await frappe.xcall(API + "naming_by", { doctype });
	if (!said) return;
	const FIELD = "Field";
	const EXPRESSION = "Expression";
	let checked = null;
	const group = new frappe.ui.FieldGroup({
		body: $wrapper,
		fields: [
			{
				fieldtype: "Select",
				fieldname: "by",
				label: __("Name each new {0} by", [__(doctype)]),
				options: said.kinds,
				description: said.made
					? __("Existing records keep their names. Only required fields are listed.")
					: __("Existing records keep their names."),
				change: () => group.get_value("by") !== EXPRESSION && apply(),
			},
			{ fieldtype: "Column Break" },
			{
				fieldtype: "Select",
				fieldname: "field",
				label: __("Field"),
				options: said.fields,
				depends_on: `eval:doc.by === "${FIELD}"`,
				description: __("It becomes required and unique."),
				change: () => apply(),
			},
			{
				fieldtype: "Data",
				fieldname: "pattern",
				label: __("Expression"),
				depends_on: `eval:doc.by === "${EXPRESSION}"`,
				placeholder: "PRJ-.YYYY.-.####",
				description: __("Same format as a series."),
				input_class: "font-mono",
			},
			{
				fieldtype: "Button",
				fieldname: "use",
				label: __("Use Expression"),
				depends_on: `eval:doc.by === "${EXPRESSION}"`,
				click: () => apply(),
			},
			{ fieldtype: "Section Break", depends_on: `eval:doc.by === "${EXPRESSION}"` },
			{ fieldtype: "HTML", fieldname: "help" },
		],
	});
	group.make();
	group.get_field("help").$wrapper.html(onedesk.numbering.help_html());
	const $pattern = group.get_field("pattern");
	$pattern.$input.on(
		"input",
		frappe.utils.debounce(async () => {
			const pattern = ($pattern.get_input_value() || "").trim();
			const row = pattern ? await frappe.xcall(API + "preview_pattern", { doctype, pattern }) : {};
			checked = row.error ? null : pattern;
			$pattern.set_description(
				row.error
					? `<span class="text-danger">${frappe.utils.escape_html(row.error)}</span>`
					: row.next
						? __("Next: {0}", [`<samp>${frappe.utils.escape_html(row.next)}</samp>`])
						: __("Same format as a series.")
			);
		}, 300)
	);
	const load = () => {
		group.set_values({
			by: said.by,
			field: said.value.startsWith("field:") ? said.value : "",
			pattern: said.pattern || "",
		});
		checked = said.pattern || null;
		group.refresh_dependency();
		shown(said);
	};
	const apply = () => {
		const values = group.get_values(true) || {};
		const value =
			values.by === FIELD
				? values.field
				: values.by === EXPRESSION
					? checked && (values.pattern || "").trim() === checked && checked
					: values.by;
		if (!value || value === said.value) return;
		const label = [...said.kinds, ...said.fields].find((one) => one.value === value)?.label || value;
		frappe.confirm(
			__("Name each new {0} by {1}? Existing records keep their names.", [__(doctype), frappe.utils.escape_html(label)]),
			async () => {
				said = await frappe.xcall(API + "set_naming_by", { doctype, value });
				frappe.show_alert({ message: __("Naming updated"), indicator: "green" });
				load();
			},
			load
		);
	};
	load();
};

onedesk.numbering.rules = async ($wrapper, doctype) => {
	const esc = frappe.utils.escape_html;
	const draw = async () => {
		const rows = await frappe.xcall("frappe.client.get_list", {
			doctype: "Document Naming Rule",
			filters: { document_type: doctype },
			fields: ["name", "prefix", "prefix_digits", "priority", "disabled"],
			order_by: "priority desc",
			limit_page_length: 0,
		});
		const conditions = rows.length
			? await frappe.xcall("frappe.client.get_list", {
					doctype: "Document Naming Rule Condition",
					parent: "Document Naming Rule",
					filters: { parent: ["in", rows.map((one) => one.name)] },
					fields: ["parent", "field", "condition", "value"],
					limit_page_length: 0,
			  })
			: [];
		const when = (name) =>
			conditions
				.filter((one) => one.parent === name)
				.map((one) => `${__(frappe.meta.get_label(doctype, one.field))} ${one.condition} ${one.value}`)
				.join(", ");
		$wrapper.empty();
		const add = $(onedesk.shell.button(__("Add Rule"), {}, "subtle", "plus")).on("click", () => onedesk.numbering.rule(doctype, null, draw));
		onedesk.shell.table($wrapper, {
			title: __("Rules"),
			note: __("Rules override the naming above."),
			rows,
			icon: "list-filter",
			empty: __("No rules."),
			actions: add,
			open: (row) => onedesk.numbering.rule(doctype, row.name, draw),
			columns: [
				{
					label: __("Prefix"),
					render: (row) =>
						`<samp>${esc(row.prefix)}${"#".repeat(row.prefix_digits || 5)}</samp>` +
						(row.disabled ? " " + frappe.ui.badge.html({ label: __("Off"), theme: "gray" }) : ""),
				},
				{ label: __("When"), render: (row) => esc(when(row.name) || __("Always")) },
			],
		});
	};
	draw();
};

onedesk.numbering.rule = async (doctype, name, done) => {
	const doc = name ? await frappe.db.get_doc("Document Naming Rule", name) : null;
	const fields = frappe.meta
		.get_docfields(doctype)
		.filter((df) => !frappe.model.no_value_type.includes(df.fieldtype) && !df.permlevel && df.label)
		.map((df) => ({ label: __(df.label), value: df.fieldname }));
	const dialog = new frappe.ui.Dialog({
		title: name ? __("Edit Rule") : __("Add Rule"),
		fields: [
			{
				fieldtype: "Data",
				fieldname: "prefix",
				label: __("Prefix"),
				reqd: 1,
				description: __("The text before the number, such as {0}", ["RET-.YYYY.-"]),
			},
			{ fieldtype: "Int", fieldname: "prefix_digits", label: __("Digits"), default: 5 },
			{
				fieldtype: "Table",
				fieldname: "conditions",
				label: __("When"),
				description: __("All conditions must match. Leave empty to always apply."),
				cannot_add_rows: false,
				in_place_edit: true,
				fields: [
					{ fieldtype: "Select", fieldname: "field", label: __("Field"), options: fields, in_list_view: 1, reqd: 1 },
					{ fieldtype: "Select", fieldname: "condition", label: __("Is"), options: ["=", "!=", ">", "<", ">=", "<="], default: "=", in_list_view: 1, reqd: 1 },
					{ fieldtype: "Data", fieldname: "value", label: __("Value"), in_list_view: 1 },
				],
			},
			{ fieldtype: "Int", fieldname: "priority", label: __("Priority"), description: __("If two rules match, the higher priority wins.") },
			{ fieldtype: "Check", fieldname: "disabled", label: __("Disabled") },
			{ fieldtype: "Section Break", label: __("Series Format"), collapsible: 1 },
			{ fieldtype: "HTML", fieldname: "help", options: onedesk.numbering.help_html() },
		],
		primary_action_label: name ? __("Update") : __("Add"),
		primary_action: async (values) => {
			const fields_of = {
				prefix: values.prefix.trim(),
				prefix_digits: values.prefix_digits || 5,
				priority: values.priority || 0,
				disabled: values.disabled ? 1 : 0,
				conditions: (values.conditions || []).map(({ field, condition, value }) => ({ field, condition, value })),
			};
			if (doc) await frappe.xcall("frappe.client.save", { doc: { ...doc, ...fields_of } });
			else await frappe.db.insert({ doctype: "Document Naming Rule", document_type: doctype, ...fields_of });
			dialog.hide();
			frappe.show_alert({ message: name ? __("Rule updated") : __("Rule added"), indicator: "green" });
			done();
		},
	});
	const prefix = dialog.get_field("prefix");
	const said = prefix.df.description;
	const next = frappe.utils.debounce(async () => {
		const value = (prefix.get_input_value() || "").trim();
		const digits = dialog.get_value("prefix_digits") || 5;
		const row = value ? await frappe.xcall(onedesk.numbering.API + "preview_rule", { doctype, prefix: value, digits }) : {};
		prefix.set_description(
			row.error
				? `<span class="text-danger">${frappe.utils.escape_html(row.error)}</span>`
				: row.next
					? __("Next: {0}", [`<samp>${frappe.utils.escape_html(row.next)}</samp>`])
					: said
		);
	}, 300);
	prefix.$input.on("input", next);
	dialog.get_field("prefix_digits").$input.on("input change", next);
	if (doc) {
		dialog.set_values({ ...doc, conditions: doc.conditions });
		next();
		dialog.set_secondary_action_label(__("Delete"));
		dialog.set_secondary_action(() =>
			frappe.confirm(__("Delete this rule?"), async () => {
				await frappe.xcall("frappe.client.delete", { doctype: "Document Naming Rule", name });
				dialog.hide();
				done();
			})
		);
	}
	dialog.show();
};

(() => {
	const List = frappe.views && frappe.views.ListView;
	if (!List || List.prototype.one_settings_item) return;
	List.prototype.one_settings_item = true;
	const items = List.prototype.get_menu_items;
	List.prototype.get_menu_items = function () {
		const menu = items.call(this);
		if (onedesk.doctype_settings.offered(this.meta)) {
			menu.push({ label: __("Settings"), action: () => onedesk.doctype_settings.open(this.doctype), standard: true });
		}
		return menu;
	};
})();
