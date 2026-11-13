Object.assign(frappe.treeview_settings["Task"] || (frappe.treeview_settings["Task"] = {}), {
	get_tree_nodes: "onedesk.one_task.views.children",
	breadcrumb: onedesk.names.of("one_task"),
	get_label(node) {
		const data = node.data || {};
		if (node.is_root) return frappe.utils.escape_html(node.label);
		const state = data.status && data.status !== "Open" ? ` <span class="text-muted">· ${frappe.utils.escape_html(__(data.status))}</span>` : "";
		return `${frappe.utils.escape_html(data.title || node.label)}${state}`;
	},
});
