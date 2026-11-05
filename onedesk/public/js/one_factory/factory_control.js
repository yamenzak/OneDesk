frappe.provide("onedesk.factory");
onedesk.factory.settings = ({ at = null } = {}) => {
	const dialog = onedesk.module_settings.open({ module: "OneFactory", tabs: [], default_tab: at });
	dialog.show();
	return dialog;
};

frappe.provide("onedesk.control_centers");
onedesk.control_centers.OneFactory = onedesk.factory.settings;

$(document).on("page-change", () =>
	setTimeout(() => {
		const sidebar = frappe.app && frappe.app.sidebar;
		const win = onedesk.interface.current();
		if (!win || win.$foot_action || !sidebar || sidebar.current_module !== "OneFactory") return;
		win.module_foot({ module: "OneFactory", settings: () => onedesk.factory.settings() });
		onedesk.interface.nav.place();
	}, 0)
);
