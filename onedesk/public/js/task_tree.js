// Tasks as a tree: ERPNext's (task_tree.js), read through one_task/views.py
// `children`, which leaves a template's tasks out. Each task is its subject
// and where it stands; frappe's own label added its number after it.
Object.assign(frappe.treeview_settings["Task"] || (frappe.treeview_settings["Task"] = {}), {
	get_tree_nodes: "onedesk.one_task.views.children",
	breadcrumb: "OneTask",
	get_label(node) {
		const data = node.data || {};
		if (node.is_root) return frappe.utils.escape_html(node.label);
		const state = data.status && data.status !== "Open" ? ` <span class="text-muted">· ${frappe.utils.escape_html(__(data.status))}</span>` : "";
		return `${frappe.utils.escape_html(data.title || node.label)}${state}`;
	},
});
