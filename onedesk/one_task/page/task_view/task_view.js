// A task's page, opened at the task's own address (/desk/task/<name>;
// project_new.js hands the route here). Its body is the onedesk.task island
// (frontend/src/task); desk keeps the head (onedesk.island_page).

frappe.pages["task-view"].on_page_load = (wrapper) => {
	onedesk.island_page(wrapper, {
		island: "onedesk.task",
		title: __("Task"),
		parent: { label: __("Tasks"), route: "/desk/task" },
		// Edit Details and Repeat are the task panel's own (task_actions.js).
		requires: ["/assets/onedesk/js/project_actions.js", "/assets/onedesk/js/task_actions.js"],
		// No panel, as for any record: the place's name in the breadcrumb opens
		// OneTask's others.
		hide_sidebar: !frappe.is_mobile(),
		record: "Task",
		files: "files",
	});
};
