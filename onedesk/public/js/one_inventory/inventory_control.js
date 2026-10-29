// OneInventory's settings (docs/READY.md, mechanism 5): what every module's finds,
// its lists, roles and notifications (module_settings.centers).
frappe.provide("onedesk.inventory");
onedesk.inventory.settings = ({ at = null } = {}) => {
	const dialog = onedesk.module_settings.open({ module: "OneInventory", tabs: [], default_tab: at });
	dialog.show();
	return dialog;
};

frappe.provide("onedesk.control_centers");
onedesk.control_centers.OneInventory = onedesk.inventory.settings;

// Its foot: Settings, the tour, Help and the version at the foot of its rail,
// drawn by the window under whichever of its screens is open (module_foot).
$(document).on("page-change", () =>
	setTimeout(() => {
		const sidebar = frappe.app && frappe.app.sidebar;
		const win = onedesk.window.current();
		if (!win || win.$foot_action || !sidebar || sidebar.current_module !== "OneInventory") return;
		win.module_foot({ module: "OneInventory", settings: () => onedesk.inventory.settings() });
		onedesk.window.nav.place();
	}, 0)
);
