frappe.provide("onedesk.quality");
onedesk.centers.part("settings", onedesk.names.of("one_quality"));

$(document).on("page-change", () =>
	setTimeout(() => {
		const sidebar = frappe.app && frappe.app.sidebar;
		const win = onedesk.interface.current();
		if (!win || win.$foot_action || !sidebar || sidebar.current_module !== onedesk.names.sidebar("one_quality")) return;
		win.module_foot({ module: onedesk.names.of("one_quality"), settings: () => onedesk.centers.open("settings", { module: onedesk.names.of("one_quality") }) });
		onedesk.interface.nav.place();
	}, 0)
);
