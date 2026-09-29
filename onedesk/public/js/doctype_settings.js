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
onedesk.doctype_settings.TABS = ["notifications", "naming", "print-format"];

onedesk.doctype_settings.adapt = () => {
	if (onedesk.doctype_settings.adapted) return;
	onedesk.doctype_settings.adapted = true;
	// General is held back: frappe's tab sets each control's value as it draws, and its
	// onchange compares with ===, so a value that comes back as another type is saved on
	// opening, twice, and the second meets the first as a conflict (tabs/settings_map.js).
	// It is added outside the groups, so it is taken out by its builder.
	delete frappe.doctype_settings.builders.general;
	for (const group of frappe.doctype_settings.groups) {
		for (const item of group.items) {
			const theirs = item.condition;
			// Naming is offered on a doctype named by a series, which is all the tab
			// below shows; frappe's asks for read on Document Naming Rule, which is not given.
			const shown = item.id === "naming" ? (doctype) => !!frappe.meta.get_docfield(doctype, "naming_series") : theirs;
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
		panel.set_view({
			title: __("Numbering"),
			description: __("How a new {0} is named. The first series is the one a new record starts with.", [__(doctype)]),
			actions: [{ label: __("Add Series"), icon: "plus", click: () => onedesk.numbering.add(doctype, () => list.refresh()) }],
			render: (p) => {
				list = onedesk.numbering.list(p.body.empty(), doctype);
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

onedesk.numbering.add = (doctype, done) =>
	frappe.prompt(
		{ fieldtype: "Data", label: __("New Series"), fieldname: "series", reqd: 1, description: __("For example {0}", ["INV-.YYYY.-.####"]) },
		async ({ series }) => {
			const rows = await frappe.xcall(onedesk.numbering.API + "series", { doctype });
			await frappe.xcall(onedesk.numbering.API + "save", { doctype, options: [...rows.map((one) => one.series), series.trim()] });
			frappe.show_alert({ message: __("Series added"), indicator: "green" });
			done();
		},
		__("Add Series"),
		__("Add")
	);

// One series: its pattern, and the number it has reached, which only goes up.
onedesk.numbering.edit = (doctype, row, rows, done) => {
	const dialog = new frappe.ui.Dialog({
		title: __("Edit Series"),
		fields: [
			{ fieldtype: "Data", fieldname: "series", label: __("Series"), reqd: 1, default: row.series, description: __("Next: {0}", [row.next]) },
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
				description: __("The next name continues after this number. It can only go up."),
			},
			{ fieldtype: "Section Break", label: __("How a Series Is Written"), collapsible: 1 },
			{ fieldtype: "HTML", fieldname: "help", options: frappe.ui.NamingSeriesDialog.help_html() },
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
