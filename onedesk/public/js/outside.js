// What of frappe's own desk a workspace is not offered (one/outside.py). A menu
// item that ends on a screen only frappe's System Manager may open is left off,
// on frappe's own read check of that screen, so the platform's people keep it.
// The editors for frappe's own furniture (the sidebar, the dock) are left off
// for everyone on One's desk, whose sidebars are One's.

frappe.provide("onedesk.outside");

// `build` runs with `page.add_menu_item` skipping the given labels.
onedesk.outside.skipping = (page, labels, build) => {
	const add = page.add_menu_item;
	page.add_menu_item = function (label, ...rest) {
		return labels.includes(label) ? $() : add.call(this, label, ...rest);
	};
	try {
		return build();
	} finally {
		page.add_menu_item = add;
	}
};

// A dropdown's groups without the options named.
onedesk.outside.without = (groups, names) =>
	(groups || []).map((group) => ({
		...group,
		options: Array.isArray(group.options)
			? group.options.filter((one) => !names.includes(one.name))
			: group.options,
	}));

// A record's View Audit Trail opens frappe's Audit Trail, a System Manager's single.
(() => {
	const Toolbar = frappe.ui.form && frappe.ui.form.Toolbar;
	if (!Toolbar || Toolbar.prototype.one_outside) return;
	Toolbar.prototype.one_outside = true;
	const audit = Toolbar.prototype.add_audit_trail;
	Toolbar.prototype.add_audit_trail = function () {
		if (frappe.model.can_read("Audit Trail")) audit.call(this);
	};
})();

// A report view's Setup Auto Email opens Auto Email Report, the administrator's.
(() => {
	const Report = frappe.views && frappe.views.ReportView;
	if (!Report || Report.prototype.one_outside) return;
	Report.prototype.one_outside = true;
	const items = Report.prototype.report_menu_items;
	Report.prototype.report_menu_items = function () {
		const menu = items.call(this);
		return frappe.model.can_read("Auto Email Report")
			? menu
			: menu.filter((one) => one.label !== __("Setup Auto Email"));
	};
})();

// The print page's Print Settings opens frappe's form, which an administrator
// may only read and nobody else may open: it is left off One's desk. The page's
// class arrives with the page, so it is wrapped then.
(() => {
	const form = frappe.ui.form;
	if (!form || Object.getOwnPropertyDescriptor(form, "PrintView")?.set) return;
	let View = form.PrintView;
	Object.defineProperty(form, "PrintView", {
		configurable: true,
		get: () => View,
		set(value) {
			View = class OnePrintView extends value {
				setup_menu() {
					if (!frappe.boot.one_elsewhere) return super.setup_menu();
					return onedesk.outside.skipping(this.page, [__("Print Settings")], () => super.setup_menu());
				}
			};
		},
	});
})();

// Edit Sidebar and Manage Dock arrange frappe's sidebars and dock; One's desk
// has One's (one/outside.py). The user menu gains the theme, which frappe's
// own settings dialog held, and Help is One's.
if (frappe.boot.one_elsewhere && frappe.ui.SidebarHeader && frappe.ui.Sidebar) {
	frappe.ui.SidebarHeader = class OneSidebarHeader extends frappe.ui.SidebarHeader {
		menu_items() {
			// All apps opens frappe's apps screen, which One's desk sends Home; the rail is the switcher.
			return onedesk.outside.without(super.menu_items(), ["edit-sidebar", "all-apps"]);
		}

		// Help is One's: OneAI answers from each product's own docs. erpnext's
		// links to its documentation are left out; the site's own help rows stay.
		get_help_siblings() {
			const [, site] = super.get_help_siblings();
			const ask = {
				name: "ask-oneai",
				label: __("Ask OneAI"),
				icon: "sparkles",
				onclick: () => onedesk.oneai.open({ ask: __("How does this page work?") }),
			};
			return [{ group: "", options: [ask] }, site];
		}
	};
	frappe.ui.Sidebar = class OneUserMenuSidebar extends frappe.ui.Sidebar {
		create_user_menu(args) {
			const Dropdown = frappe.ui.Dropdown;
			frappe.ui.Dropdown = class extends Dropdown {
				constructor(opts) {
					const options = onedesk.outside.without(opts.options, ["workspace-selector"]);
					// The theme, which frappe's own settings dialog held, beside Reload.
					const group = options.find((one) => Array.isArray(one.options) && one.options.some((o) => o.name === "reload"));
					group?.options.splice(group.options.findIndex((o) => o.name === "reload"), 0, {
						name: "theme",
						label: __("Theme"),
						icon: "sun-moon",
						onclick: () => new frappe.ui.ThemeSwitcher().show(),
					});
					super({ ...opts, options });
				}
			};
			try {
				return super.create_user_menu(args);
			} finally {
				frappe.ui.Dropdown = Dropdown;
			}
		}
	};
}

// Frappe's own screens for what One has a screen of its own for. A list or form
// of these, reached from frappe's bell, a link or an address, opens One's, in
// place of it in the history so Back does not return to it.
onedesk.outside.instead = (sub_path) => {
	const [doctype, name] = (sub_path || "").split("/");
	const me = frappe.session.user;
	switch (doctype) {
		case "notification-settings":
			return ["settings", { section: "notifications" }];
		case "user":
			if (name && decodeURIComponent(name) === me) return ["settings", { section: "profile" }];
			return name && name !== "new" && !name.startsWith("new-")
				? ["workspace-settings", { section: "people", person: decodeURIComponent(name) }]
				: ["workspace-settings", { section: "people" }];
		case "file":
			return name ? null : ["onecloud"];
		case "todo":
			return name ? null : ["my-tasks"];
		case "print-settings":
			return ["workspace-settings", { section: "printing" }];
		case "print-format":
		case "letter-head":
			return name ? null : ["workspace-settings", { section: "printing" }];
		// frappe's mail client, the list and its Inbox view; a message's own form stays.
		case "communication":
			return !name || name === "view" ? ["onemail"] : null;
	}
	return null;
};

if (frappe.boot.one_elsewhere) {
	const own = frappe.router.re_route;
	frappe.router.re_route = function (sub_path) {
		const instead = onedesk.outside.instead(sub_path);
		if (!instead) return own.call(this, sub_path);
		frappe.route_flags.replace_route = true;
		frappe.set_route(...instead);
		return true;
	};
}

// Search offers the pages and reports of One's desk: those a One sidebar
// lists, and One's own. Frappe's and erpnext's others (point of sale, the sales
// funnel, stock balance) are left out; records of every kind are still found.
onedesk.outside.ours = (kind) => {
	const named = new Set();
	for (const sidebar of Object.values(frappe.boot.module_sidebars || {})) {
		for (const item of sidebar.items || []) if (item.link_type === kind && item.link_to) named.add(item.link_to);
	}
	return named;
};

if (frappe.boot.one_elsewhere && frappe.search?.utils) {
	const utils = frappe.search.utils;
	const app_of = (module) => (frappe.boot.module_app || {})[frappe.scrub(module || "")];
	const keep = (kind, info, found) => {
		const named = onedesk.outside.ours(kind);
		return found.filter((one) => {
			const name = (one.route || []).at(-1);
			return named.has(name) || app_of(info[name]?.module) === "onedesk";
		});
	};
	const pages = utils.get_pages;
	utils.get_pages = function (keywords) {
		// frappe's own Calendar entry opens its event calendar; OneCalendar is a page of One's.
		const found = pages.call(this, keywords).filter((one) => one.type !== "Calendar");
		return keep("Page", frappe.boot.page_info || {}, found);
	};
	const reports = utils.get_reports;
	utils.get_reports = function (keywords) {
		return keep("Report", frappe.boot.allowed_reports || {}, reports.call(this, keywords));
	};
}
