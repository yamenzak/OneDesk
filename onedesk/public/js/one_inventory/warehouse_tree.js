(() => {
	const tree = frappe.treeview_settings["Warehouse"] || (frappe.treeview_settings["Warehouse"] = {});
	tree.filters = (tree.filters || []).map((one) => (one.fieldname === "company" ? { ...one, hidden: 1 } : one));
	let view = null;
	const loaded = tree.onload;
	tree.onload = (treeview) => {
		view = treeview;
		loaded?.(treeview);
	};
	const rendered = tree.on_node_render;
	tree.on_node_render = (node, deep) => {
		rendered?.(node, deep);
		if (node.is_root && !node.one_opened && view?.tree) {
			node.one_opened = true;
			view.tree.load_children(node, true);
		}
	};
})();
