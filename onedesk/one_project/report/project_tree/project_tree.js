// Every project as the tree it is (one_project/tree.py). frappe's own tree
// report: a row is indented under its parent and folds with it.
frappe.query_reports["Project Tree"] = {
	tree: true,
	name_field: "project",
	parent_field: "parent",
	initial_depth: 3,
	filters: [
		{
			fieldname: "closed",
			label: __("Include Completed"),
			fieldtype: "Check",
		},
	],
};
