
frappe.pages["task-view"].on_page_load = (wrapper) => {
	onedesk.island_page(wrapper, {
		island: "onedesk.task",
		title: __("Task"),
		parent: { label: __("Tasks"), route: "/desk/task" },
		requires: ["/assets/onedesk/js/project_actions.js", "/assets/onedesk/js/task_actions.js"],
		record: "Task",
		files: "files",
	});
};
