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

onedesk.doctype_settings.open = (doctype) =>
	frappe.require("doctype_settings.bundle.js", () => {
		onedesk.doctype_settings.adapt();
		frappe.doctype_settings.open(doctype);
	});

// The dialog's Notifications tab lists the workspace's own rules on the doctype
// and opens them in Workspace › Notifications, the one place a rule is written
// (one/rules.py). Frappe's tab opens frappe's Notification form, whose rail is
// frappe's; this is the same list, frappe's list panel, pointed at ours.
// The tabs a workspace administrator is given, as each is opened to workspaces
// (docs/DESK-COVERAGE.md). Frappe shows a tab to whoever can read its doctype, and
// reading an Email Template is everybody's; a tab is offered here once what it
// opens can be used, and the rail beside it is One's.
onedesk.doctype_settings.TABS = ["general", "notifications"];

onedesk.doctype_settings.adapt = () => {
	if (onedesk.doctype_settings.adapted) return;
	onedesk.doctype_settings.adapted = true;
	for (const group of frappe.doctype_settings.groups) {
		for (const item of group.items) {
			const theirs = item.condition;
			item.condition = (doctype) => onedesk.doctype_settings.TABS.includes(item.id) && (theirs ? theirs(doctype) : true);
		}
	}
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
