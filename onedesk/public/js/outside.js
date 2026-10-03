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

// The print page's Print Settings opens frappe's form, read only by an
// administrator. The page's class arrives with the page, so it is wrapped then.
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
					if (frappe.model.can_read("Print Settings")) return super.setup_menu();
					return onedesk.outside.skipping(this.page, [__("Print Settings")], () => super.setup_menu());
				}
			};
		},
	});
})();

// Edit Sidebar and Manage Dock arrange frappe's sidebars and dock; One's desk
// has One's (one/outside.py).
if (frappe.boot.one_elsewhere && frappe.ui.SidebarHeader && frappe.ui.Sidebar) {
	frappe.ui.SidebarHeader = class OneSidebarHeader extends frappe.ui.SidebarHeader {
		menu_items() {
			return onedesk.outside.without(super.menu_items(), ["edit-sidebar"]);
		}
	};
	frappe.ui.Sidebar = class OneUserMenuSidebar extends frappe.ui.Sidebar {
		create_user_menu(args) {
			const Dropdown = frappe.ui.Dropdown;
			frappe.ui.Dropdown = class extends Dropdown {
				constructor(opts) {
					super({ ...opts, options: onedesk.outside.without(opts.options, ["workspace-selector"]) });
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
