(() => {
	const settings = (frappe.listview_settings["Asset"] = frappe.listview_settings["Asset"] || {});
	settings.hide_name_column = true;
	const theirs = settings.get_indicator;
	settings.get_indicator = function (doc) {
		if (doc.docstatus === 1 && doc.status === "Out of Order") return [__("Out of Order"), "red", "status,=,Out of Order"];
		return theirs ? theirs.call(this, doc) : undefined;
	};
})();
