// The chart of accounts as One shows it. ERPNext's "View" menu holds places
// to go (cost centres, the opening invoice tool, the financial statements),
// not ways of looking at the tree, and sat beside the view toggles under the
// same word; it says "Go to". Only the words on the button change: frappe
// finds the group by the label ERPNext gave it, so that stays. The company
// filter is hidden, as everywhere: a workspace is one company.
(() => {
	const tree = frappe.treeview_settings["Account"] || (frappe.treeview_settings["Account"] = {});
	tree.filters = (tree.filters || []).map((one) => (one.fieldname === "company" ? { ...one, hidden: 1 } : one));
	const loaded = tree.onload;
	tree.onload = (treeview) => {
		loaded?.(treeview);
		treeview.page.inner_toolbar
			.find(`.inner-group-button[data-label="${encodeURIComponent(__("View"))}"] > .es-button .es-button__label`)
			.text(__("Go to"));
	};
})();
