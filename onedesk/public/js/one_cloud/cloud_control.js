frappe.provide("onedesk.cloud");
onedesk.cloud.settings = ({ at = null } = {}) => {
	const dialog = onedesk.module_settings.open({ module: onedesk.names.of("one_cloud"), tabs: [], default_tab: at });
	dialog.show();
	return dialog;
};

frappe.provide("onedesk.control_centers");
onedesk.control_centers.OneCloud = onedesk.cloud.settings;
