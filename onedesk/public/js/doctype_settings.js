// Frappe's Settings dialog for a doctype (frappe/public/js/frappe/form/doctype_settings/),
// opened for a workspace administrator from One's own menu item, beside Customize.
// docs/DESK-COVERAGE.md.
//
// Frappe offers its item only to whoever may create a Custom Field and a Property
// Setter, which a workspace administrator is never given (the Customize page writes
// those under its own guard), so the item here is ours and the dialog is frappe's.
// Each tab shows when its doctype can be read, which is frappe's own rule; the
// Permissions tab is frappe's own administrators' and stays theirs.
frappe.provide("onedesk.doctype_settings");

// Offered on a doctype a workspace may change: the modules the Customize page
// refuses are refused here too (one/customize.py), and whoever frappe gives its
// own item to (the same test frappe makes) keeps frappe's.
onedesk.doctype_settings.offered = (meta) =>
	!!meta &&
	!meta.istable &&
	!meta.issingle &&
	frappe.user.has_role("Workspace Administrator") &&
	!(frappe.model.can_create("Custom Field") && frappe.model.can_create("Property Setter")) &&
	!(frappe.boot.one_refused_modules || []).includes(meta.module);

// `tab` opens it on one of its tabs, as Workspace › Numbering opens it on Naming.
// The doctype's meta is loaded first: opened from Workspace › Numbering, no form of it
// has been, and the tabs ask it which apply.
onedesk.doctype_settings.open = (doctype, tab = null) =>
	frappe.require("doctype_settings.bundle.js", () =>
		frappe.model.with_doctype(doctype, () => {
			onedesk.doctype_settings.adapt();
			const opening = frappe.doctype_settings.open(doctype);
			opening && tab && opening.then((dialog) => dialog && dialog.activate(tab));
		})
	);

// The dialog's Notifications tab lists the workspace's own rules on the doctype
// and opens them in Workspace › Notifications, the one place a rule is written
// (one/rules.py). Frappe's tab opens frappe's Notification form, whose rail is
// frappe's; this is the same list, frappe's list panel, pointed at ours.
// The tabs a workspace administrator is given, as each is opened to workspaces
// (docs/DESK-COVERAGE.md). Frappe shows a tab to whoever can read its doctype, and
// reading an Email Template is everybody's; a tab is offered here once what it
// opens can be used, and the rail beside it is One's.
onedesk.doctype_settings.TABS = ["notifications", "naming", "print-format", "email-template", "workflow", "automations"];

onedesk.doctype_settings.adapt = () => {
	if (onedesk.doctype_settings.adapted) return;
	onedesk.doctype_settings.adapted = true;
	// General is held back: frappe's tab sets each control's value as it draws, and its
	// onchange compares with ===, so a value that comes back as another type is saved on
	// opening, twice, and the second meets the first as a conflict (tabs/settings_map.js).
	// It is added outside the groups, so it is taken out by its builder.
	delete frappe.doctype_settings.builders.general;
	// Automations is not one of frappe's tabs; it goes beside Approvals (one/automations.py).
	const beside = frappe.doctype_settings.groups.find((group) => group.items.some((item) => item.id === "workflow"));
	beside &&
		beside.items.push({ id: "automations", label: __("Automations"), icon: "zap", condition: () => frappe.model.can_read("Automation Flow") });
	for (const group of frappe.doctype_settings.groups) {
		for (const item of group.items) {
			// Frappe's own test for each tab; Naming's, read on Document Naming Rule, is
			// given with the rules (one/numbering.py GRANTS).
			const shown = item.condition;
			if (item.id === "naming") item.label = __("Numbering");
			if (item.id === "email-template") item.label = __("Mail Templates");
			if (item.id === "workflow") item.label = __("Approvals");
			item.condition = (doctype) => onedesk.doctype_settings.TABS.includes(item.id) && (shown ? shown(doctype) : true);
		}
	}
	// The Print Formats tab is frappe's own. Its star makes a format the default by
	// writing a Property Setter, which the workspace layer refuses, so that one property
	// goes through One's door (one/printing.py set_default), which is frappe's make_default.
	const set_property = frappe.doctype_settings.set_property;
	frappe.doctype_settings.set_property = (doctype, property, value) =>
		property === "default_print_format"
			? frappe
					.xcall("onedesk.one.printing.set_default", { doctype, print_format: value })
					.then(() => frappe.show_alert({ message: __("Default updated"), indicator: "green" }))
			: set_property(doctype, property, value);
	// The tab reads the current default from Property Setter and from DocType, which a
	// workspace administrator cannot read, so those two reads, and only those, are
	// answered by the same door: the Property Setter one with the doctype's default,
	// the DocType one with nothing, as frappe's own answer is the first it finds.
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
	// The dialog's Email Templates tab: frappe's list, with a template opened in One's
	// editor (onedesk.mail_templates.edit) rather than frappe's form, whose rail is
	// frappe's, and made the default through One's door (one/mail_templates.py).
	frappe.doctype_settings.register("email-template", (panel, doctype) => {
		let current = null;
		const edit = (name, list) => onedesk.mail_templates.edit(name, { doctype, done: () => list && list.reload() });
		const set_default = (name, list) =>
			frappe.xcall(onedesk.mail_templates.API + "set_default", { doctype, template: name }).then(() => {
				frappe.show_alert({ message: __("Default updated"), indicator: "green" });
				list.reload();
			});
		frappe.doctype_settings.render_list(panel, {
			title: __("Mail Templates"),
			description: __("Words to start a mail about a {0} with, picked in the composer.", [__(doctype)]),
			show_header: true,
			primary_action: { label: __("New"), icon: "plus", onclick: (list) => edit(null, list) },
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
			title_column: {
				label: __("Template"),
				primary: (row) => row.name,
				secondary: (row) => row.subject,
				onclick: (row, list) => edit(row.name, list),
				tags: (row) => (row.name === current ? [{ label: __("Default"), color: "green" }] : []),
			},
			actions: (row) => [
				...(row.name === current ? [] : [{ label: __("Set as Default"), icon: "star", onclick: (list) => set_default(row.name, list) }]),
				{ label: __("Edit"), icon: "pencil", onclick: (list) => edit(row.name, list) },
			],
			empty_state: {
				title: __("No mail templates yet"),
				description: __("A template is the words a mail about a {0} starts with.", [__(doctype)]),
				action: { label: __("New Template"), onclick: (list) => edit(null, list) },
			},
		});
	});
	// The dialog's Workflow tab, as frappe's, but a new one is made in frappe's workflow
	// builder, set to this doctype, rather than frappe's Workflow form (one/approvals.py).
	frappe.doctype_settings.register("workflow", (panel, doctype) => {
		const open = (name) => {
			panel.dialog.hide();
			frappe.set_route("workflow-builder", name);
		};
		const create = () => {
			panel.dialog.hide();
			onedesk.approvals.create(doctype);
		};
		frappe.doctype_settings.render_list(panel, {
			title: __("Approvals"),
			description: __("The states a {0} moves through, and who moves it.", [__(doctype)]),
			show_header: true,
			primary_action: { label: __("New"), icon: "plus", onclick: create },
			load: () =>
				frappe.doctype_settings.get_list("Workflow", {
					filters: { document_type: doctype },
					fields: ["name", "workflow_name", "is_active"],
					order_by: "name asc",
					limit: 0,
				}),
			title_column: {
				label: __("Approval"),
				primary: (row) => row.workflow_name || row.name,
				onclick: (row) => open(row.name),
				tags: (row) => (row.is_active ? [{ label: __("On"), color: "green" }] : []),
			},
			actions: (row) => [
				{
					label: row.is_active ? __("Turn Off") : __("Turn On"),
					icon: row.is_active ? "ban" : "circle-check",
					onclick: (list) =>
						frappe.db.set_value("Workflow", row.name, { is_active: row.is_active ? 0 : 1 }).then(() => list.reload()),
				},
				{ label: __("Edit"), icon: "pencil", onclick: () => open(row.name) },
			],
			empty_state: {
				title: __("No approvals yet"),
				description: __("An approval moves a {0} through states, each action taken by a role.", [__(doctype)]),
				action: { label: __("New Approval"), onclick: create },
			},
		});
	});
	// The Automations tab: the doctype's Automation Flows, each opened in frappe's own form,
	// which One's sidebar lists, so the rail stays One's.
	frappe.doctype_settings.register("automations", (panel, doctype) => {
		const form = (name) => {
			panel.dialog.hide();
			frappe.app.sidebar && frappe.app.sidebar.select_module("One");
			name ? frappe.set_route("Form", "Automation Flow", name) : frappe.new_doc("Automation Flow", { document_type: doctype });
		};
		frappe.doctype_settings.render_list(panel, {
			title: __("Automations"),
			description: __("What happens by itself when a {0} is made, changed or reaches a date.", [__(doctype)]),
			show_header: true,
			primary_action: { label: __("New"), icon: "plus", onclick: () => form(null) },
			load: () =>
				frappe.doctype_settings.get_list("Automation Flow", {
					filters: { document_type: doctype },
					fields: ["name", "title", "trigger_type", "enabled"],
					order_by: "title asc",
					limit: 0,
				}),
			title_column: {
				label: __("Automation"),
				primary: (row) => row.title || row.name,
				onclick: (row) => form(row.name),
				tags: (row) => (row.enabled ? [{ label: __("On"), color: "green" }] : []),
			},
			columns: [{ label: __("When"), badge: (row) => (row.trigger_type ? { label: __(row.trigger_type), color: "gray" } : null) }],
			actions: (row) => [
				{
					label: row.enabled ? __("Turn Off") : __("Turn On"),
					icon: row.enabled ? "ban" : "circle-check",
					onclick: (list) => frappe.db.set_value("Automation Flow", row.name, { enabled: row.enabled ? 0 : 1 }).then(() => list.reload()),
				},
				{ label: __("Edit"), icon: "pencil", onclick: () => form(row.name) },
			],
			empty_state: {
				title: __("No automations yet"),
				description: __("An automation sets a field, makes a record or tells somebody, by itself, when a {0} changes.", [__(doctype)]),
				action: { label: __("New Automation"), onclick: () => form(null) },
			},
		});
	});
	// Frappe keeps the sidebar on screen for a page of the same app, and every One sidebar is
	// one app, so the rule would open inside OneCRM's; One's is selected as a dock row would.
	const go = (panel, args) => {
		panel.dialog.hide();
		frappe.app.sidebar && frappe.app.sidebar.select_module("One");
		frappe.set_route("workspace-settings", { section: "notification_types", ...args });
	};
	frappe.doctype_settings.register("notifications", (panel, doctype) =>
		frappe.doctype_settings.render_list(panel, {
			title: __("Notifications"),
			description: __("The workspace's own rules on any {0}: when something happens to one, tell somebody.", [__(doctype)]),
			show_header: true,
			primary_action: { label: __("New Rule"), icon: "plus", onclick: () => go(panel, { rule: "new", for: doctype }) },
			load: () =>
				frappe.doctype_settings.get_list("Notification", {
					filters: { document_type: doctype, one_rule: 1 },
					fields: ["name", "event", "enabled"],
					order_by: "name asc",
					limit: 0,
				}),
			title_column: {
				label: __("Rule"),
				primary: (row) => row.name,
				onclick: (row) => go(panel, { rule: row.name }),
				tags: (row) => (row.enabled ? [] : [{ label: __("Off"), color: "gray" }]),
			},
			columns: [{ label: __("When"), badge: (row) => (row.event ? { label: __(row.event), color: "gray" } : null) }],
			empty_state: {
				title: __("No rules yet"),
				description: __("A rule tells somebody when something happens to a {0}.", [__(doctype)]),
				action: { label: __("New Rule"), onclick: () => go(panel, { rule: "new", for: doctype }) },
			},
		})
	);
	// The dialog's Naming tab: the doctype's series, through One's guarded doors
	// (one/numbering.py), since frappe's calls Document Naming Settings, which is not
	// given. The shell's table, which is frappe's EmbeddedList, and frappe's dialog. Rules
	// (Document Naming Rule) stay the framework's.
	frappe.doctype_settings.register("naming", (panel, doctype) => {
		let list;
		const head = (series) => ({
			title: __("Numbering"),
			description: series
				? __("How a new {0} is named. The first series is the one a new record starts with.", [__(doctype)])
				: __("How a new {0} is named.", [__(doctype)]),
			actions: series ? [{ label: __("Add Series"), icon: "plus", click: () => onedesk.numbering.add(doctype, () => list.refresh()) }] : [],
		});
		panel.set_view({
			...head(true),
			render: (p) => {
				const $body = p.body.empty();
				const $by = $('<div class="one-numbering-by"></div>').appendTo($body);
				const $series = $('<div class="one-numbering-series"></div>').appendTo($body);
				list = onedesk.numbering.list($series, doctype);
				// The series only while a new record takes its name from one; a kind that
				// names itself shows them wherever it has a series field.
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

// ------------------------------------------------------------------ numbering

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

// A new series, with the name it would give next shown as it is typed (or what is
// wrong with it, in frappe's words), and how a series is written beside it.
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
			{ fieldtype: "Section Break", label: __("How a Series Is Written"), collapsible: 1 },
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

// What a series being written would give next, under its field. `adding` says so when
// it is one the record already has.
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

// One series: its pattern, and the number it has reached, which only goes up.
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
				label: __("Reached"),
				default: row.current,
				description: row.last_name
					? __("The next name continues after this number. It can only go up, and not below {0}, the highest a {1} already has ({2}).", [row.used, __(doctype), row.last_name])
					: __("The next name continues after this number. It can only go up."),
			},
			{ fieldtype: "Section Break", label: __("How a Series Is Written"), collapsible: 1 },
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
	// A series is deleted from its own window; the last one is refused by the server.
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

// ------------------------------------------------------------------ mail templates

frappe.provide("onedesk.mail_templates");

onedesk.mail_templates.API = "onedesk.one.mail_templates.";

// A template in frappe's own dialog and controls, saved as a desk form saves: against
// the version it was opened at. What it may say is checked by one/mail_templates.py.
onedesk.mail_templates.edit = async (name, { doctype = null, done = null } = {}) => {
	const doc = name ? await frappe.db.get_doc("Email Template", name) : null;
	const dialog = new frappe.ui.Dialog({
		title: name || __("New Mail Template"),
		size: "large",
		fields: [
			{ fieldtype: "Data", fieldname: "template_name", label: __("Name"), reqd: name ? 0 : 1, hidden: name ? 1 : 0 },
			{ fieldtype: "Data", fieldname: "subject", label: __("Subject"), reqd: 1 },
			{
				fieldtype: "Link",
				fieldname: "reference_doctype",
				label: __("For"),
				options: "DocType",
				get_query: () => ({ query: "onedesk.one.rules.watchable" }),
				description: __("Empty offers it on any kind of record."),
			},
			{ fieldtype: "Check", fieldname: "use_html", label: __("Write in HTML") },
			{ fieldtype: "Text Editor", fieldname: "response", label: __("Message"), depends_on: "eval:!doc.use_html" },
			{ fieldtype: "Code", fieldname: "response_html", label: __("Message"), options: "HTML", depends_on: "eval:doc.use_html" },
			{
				fieldtype: "HTML",
				fieldname: "help",
				options: `<p class="text-muted small">${__("Name a field of the record in double braces, as {0}, and it is filled in when the mail is written.", ["<code>{{ customer_name }}</code>"])}</p>`,
			},
		],
		primary_action_label: name ? __("Update") : __("Create"),
		primary_action: async (values) => {
			const fields = {
				subject: values.subject,
				reference_doctype: values.reference_doctype || null,
				use_html: values.use_html ? 1 : 0,
				response: values.response || "",
				response_html: values.response_html || "",
			};
			if (doc) await frappe.xcall("frappe.client.save", { doc: { ...doc, ...fields } });
			else await frappe.db.insert({ doctype: "Email Template", name: values.template_name.trim(), ...fields });
			dialog.hide();
			frappe.show_alert({ message: name ? __("Template updated") : __("Template made"), indicator: "green" });
			done && done();
		},
	});
	if (doc) {
		dialog.set_values(doc);
		dialog.set_secondary_action_label(__("Delete"));
		dialog.set_secondary_action(() =>
			frappe.confirm(__("Delete template {0}?", [name]), async () => {
				await frappe.xcall("frappe.client.delete", { doctype: "Email Template", name });
				dialog.hide();
				done && done();
			})
		);
	}
	dialog.show();
	if (!doc && doctype) dialog.set_value("reference_doctype", doctype);
};

// ------------------------------------------------------------------ automations

// A flow the workspace writes runs as whoever wrote it and decides by its field rules
// (one/automations.py), so its form does not offer the code condition or who it runs as.
frappe.ui.form.on("Automation Flow", {
	refresh(frm) {
		if (frappe.model.can_create("Custom Field")) return;
		for (const fieldname of ["advanced_condition_section", "condition", "run_as", "automation_user"]) {
			frm.toggle_display(fieldname, false);
		}
	},
});

// ------------------------------------------------------------------ approvals

frappe.provide("onedesk.approvals");

// frappe's builder page asks for the doctype and a name when opened without a
// workflow, and makes it; route_options preselects the doctype.
onedesk.approvals.create = (doctype = null) => {
	frappe.route_options = doctype ? { doctype } : null;
	frappe.set_route("workflow-builder");
};

// How a series is written, in One's words: every part the series here accept.
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
			${part(".FY.", __("the fiscal year, and .TFY. its short form"))}
			${part(".ABBR.", __("the company's abbreviation"))}
			${part(".{fieldname}.", __("a field of the record, such as .{branch}."))}
			${part(".#####", __("the number, one # per digit; it starts again whenever the text before it changes"))}
		</ul>
		<p>${__("Only letters, digits, spaces and - / _ . # { } are allowed.")}</p>
		<p>${__("Examples: {0}, {1}, {2}", ["<code>INV-.YYYY.-.#####</code>", "<code>SO/.YY./.####</code>", "<code>INV-.YYYY.-.MM.-.####</code>"])}</p>
	</div>`;
};

// How a new record is named, with frappe's own choices: its series, one of its fields
// (made required and unique), an expression written as a series is, typed by whoever
// makes it, or random; or, for a kind that names itself (a Customer, an Item), its
// app's own choice. Changed through one/numbering.py set_naming_by. Nothing is drawn
// where there is no choice.
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
				description: __("Records already made keep their names."),
				change: () => group.get_value("by") !== EXPRESSION && apply(),
			},
			{ fieldtype: "Column Break" },
			{
				fieldtype: "Select",
				fieldname: "field",
				label: __("Field"),
				options: said.fields,
				depends_on: `eval:doc.by === "${FIELD}"`,
				description: __("It becomes required, and no two records may share its value."),
				change: () => apply(),
			},
			{
				fieldtype: "Data",
				fieldname: "pattern",
				label: __("Expression"),
				depends_on: `eval:doc.by === "${EXPRESSION}"`,
				placeholder: "PRJ-.YYYY.-.####",
				description: __("Written as a series is."),
				input_class: "font-mono",
			},
			{
				fieldtype: "Button",
				fieldname: "use",
				label: __("Use This Expression"),
				depends_on: `eval:doc.by === "${EXPRESSION}"`,
				click: () => apply(),
			},
			{ fieldtype: "Section Break", depends_on: `eval:doc.by === "${EXPRESSION}"` },
			{ fieldtype: "HTML", fieldname: "help" },
		],
	});
	group.make();
	group.get_field("help").$wrapper.html(onedesk.numbering.help_html());
	// The name it would give next, or what frappe says is wrong, as it is typed.
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
						? __("Next: {0}", [`<span class="font-mono">${frappe.utils.escape_html(row.next)}</span>`])
						: __("Written as a series is.")
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
			__("Name each new {0} by {1}? Records already made keep their names.", [__(doctype), frappe.utils.escape_html(label)]),
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

// Naming Rules: a record whose fields match is named by the rule's own prefix,
// before any series. frappe's Document Naming Rule, held by one/numbering.py
// validate_rule, in frappe's dialog and saved as a desk form saves.
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
			note: __("A record whose fields match a rule is named by the rule's own prefix, whatever it is named by above."),
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
				description: __("Every line must match. None means always."),
				cannot_add_rows: false,
				in_place_edit: true,
				fields: [
					{ fieldtype: "Select", fieldname: "field", label: __("Field"), options: fields, in_list_view: 1, reqd: 1 },
					{ fieldtype: "Select", fieldname: "condition", label: __("Is"), options: ["=", "!=", ">", "<", ">=", "<="], default: "=", in_list_view: 1, reqd: 1 },
					{ fieldtype: "Data", fieldname: "value", label: __("Value"), in_list_view: 1 },
				],
			},
			{ fieldtype: "Int", fieldname: "priority", label: __("Priority"), description: __("When two rules match, the higher one names the record.") },
			{ fieldtype: "Check", fieldname: "disabled", label: __("Off") },
			{ fieldtype: "Section Break", label: __("How a Series Is Written"), collapsible: 1 },
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
	if (doc) {
		dialog.set_values({ ...doc, conditions: doc.conditions });
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

// A list's menu carries it too. Frappe's list menu has no hook for an item, so
// get_menu_items is wrapped (docs/OVERRIDES.md).
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
