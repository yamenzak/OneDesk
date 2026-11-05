(() => {
	const settings = (frappe.listview_settings["Prospect"] ||= {});
	settings.hide_name_column = true;
})();
