// OneCRM's settings (docs/READY.md, mechanism 5): what every module's finds,
// its lists, roles and notifications (module_settings.centers).
frappe.provide("onedesk.crm");
onedesk.crm.settings = ({ at = null } = {}) => {
	const dialog = onedesk.module_settings.open({ module: "OneCRM", tabs: [], default_tab: at });
	dialog.show();
	return dialog;
};

frappe.provide("onedesk.control_centers");
onedesk.control_centers.OneCRM = onedesk.crm.settings;

// Its foot: Settings, the tour, Help and the version at the foot of its rail,
// drawn by the window under whichever of its screens is open (module_foot).
$(document).on("page-change", () =>
	setTimeout(() => {
		const sidebar = frappe.app && frappe.app.sidebar;
		const win = onedesk.window.current();
		if (!win || win.$foot_action || !sidebar || sidebar.current_module !== "OneCRM") return;
		win.module_foot({ module: "OneCRM", settings: () => onedesk.crm.settings() });
		onedesk.window.nav.place();
	}, 0)
);
