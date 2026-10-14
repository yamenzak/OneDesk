// Assets: the name with room for it, where each stands, where it is, what
// kind, who has it and what it is worth now. An asset in service said
// "Partially Depreciated", which is how ERPNext books it, not what a reader
// asks; it says In Use, and one written off to nothing says Written Off.
(() => {
	const settings = (frappe.listview_settings["Asset"] = frappe.listview_settings["Asset"] || {});
	settings.hide_name_column = true;
	const SAID = {
		"Partially Depreciated": () => [__("In Use"), "green"],
		Submitted: () => [__("In Use"), "green"],
		"Fully Depreciated": () => [__("Written Off"), "gray"],
		"Out of Order": () => [__("Out of Order"), "red"],
	};
	const theirs = settings.get_indicator;
	settings.get_indicator = function (doc) {
		const ours = doc.docstatus === 1 && SAID[doc.status];
		if (ours) return [...ours(), `status,=,${doc.status}`];
		return theirs ? theirs.call(this, doc) : undefined;
	};
})();
