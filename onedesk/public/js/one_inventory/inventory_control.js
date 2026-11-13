// OneInventory's settings (docs/READY.md, mechanism 5): what every module's finds,
// its lists, roles and notifications (onedesk.centers.found).
frappe.provide("onedesk.inventory");
onedesk.centers.part("settings", onedesk.names.of("one_inventory"));

// Its foot: Settings, the tour, Help and the version at the foot of its rail,
// drawn by the window under whichever of its screens is open (module_foot).
$(document).on("page-change", () =>
	setTimeout(() => {
		const sidebar = frappe.app && frappe.app.sidebar;
		const win = onedesk.interface.current();
		if (!win || win.$foot_action || !sidebar || sidebar.current_module !== onedesk.names.sidebar("one_inventory")) return;
		win.module_foot({ module: onedesk.names.of("one_inventory"), settings: () => onedesk.centers.open("settings", { module: onedesk.names.of("one_inventory") }) });
		onedesk.interface.nav.place();
	}, 0)
);
