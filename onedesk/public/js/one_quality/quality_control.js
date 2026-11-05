frappe.provide("onedesk.quality");
onedesk.quality.settings = ({ at = null } = {}) => {
	const dialog = onedesk.module_settings.open({ module: "OneQuality", tabs: [], default_tab: at });
	dialog.show();
	return dialog;
};

frappe.provide("onedesk.control_centers");
onedesk.control_centers.OneQuality = onedesk.quality.settings;

$(document).on("page-change", () =>
	setTimeout(() => {
		const sidebar = frappe.app && frappe.app.sidebar;
		const win = onedesk.interface.current();
		if (!win || win.$foot_action || !sidebar || sidebar.current_module !== "OneQuality") return;
		win.module_foot({ module: "OneQuality", settings: () => onedesk.quality.settings() });
		onedesk.interface.nav.place();
	}, 0)
);
