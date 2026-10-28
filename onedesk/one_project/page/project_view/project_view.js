
frappe.pages["project-view"].on_page_load = (wrapper) => {
	onedesk.island_page(wrapper, {
		island: "onedesk.project",
		title: __("Project"),
		parent: { label: __("Projects"), route: "/desk/project" },
		requires: ["/assets/onedesk/js/project_actions.js", "/assets/onedesk/js/progress.js"],
		record: "Project",
		files: "files",
	});
};
