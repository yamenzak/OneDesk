// Projects as a tree: frappe's Tree view of the Projects list, each project
// under its parent (one_project/tree.py `nodes`). A project opens its page;
// the tree's own add, move, rename and delete are left out, since a project
// is made with New Project and moved by its Parent Project.
frappe.treeview_settings["Project"] = {
	get_tree_nodes: "onedesk.one_project.tree.nodes",
	get_tree_root: false,
	root_label: __("All Projects"),
	title: __("Projects"),
	breadcrumb: "OneProject",
	disable_add_node: true,
	filters: [{ fieldname: "closed", fieldtype: "Check", label: __("Show Completed") }],
	get_label(node) {
		const data = node.data || {};
		if (node.is_root) return frappe.utils.escape_html(node.label);
		const late = ["At Risk", "Off Track"].includes(data.health);
		const health = late ? ` <span class="text-${data.health === "Off Track" ? "danger" : "warning"}">${__(data.health)}</span>` : "";
		const done = data.status === "Open" ? __("{0}% done", [Math.round(data.percent || 0)]) : __(data.status);
		return `${frappe.utils.escape_html(data.title || node.label)} <span class="text-muted">· ${done}</span>${health}`;
	},
	toolbar: [
		{
			label: __("Open"),
			icon: "arrow-up-right",
			inline: true,
			condition: (node) => !node.is_root,
			click: (node) => frappe.set_route("project", node.data.value),
		},
	],
	onload(tree) {
		if (frappe.model.can_create("Project")) {
			tree.page.set_primary_action(__("New Project"), () => frappe.new_doc("Project"), "plus");
		}
		tree.make_tree();
	},
};
