// A project's page, opened at the project's own address (/desk/project/<name>;
// project_new.js hands the route here). Its body is the onedesk.project island
// (frontend/src/project); desk keeps the head (onedesk.island_page).

frappe.pages["project-view"].on_page_load = (wrapper) => {
	onedesk.island_page(wrapper, {
		island: "onedesk.project",
		title: __("Project"),
		parent: { label: __("Projects"), route: "/desk/project" },
		requires: ["/assets/onedesk/js/project_actions.js", "/assets/onedesk/js/progress.js"],
		// No panel, as for any record: the project's name in the breadcrumb
		// opens the others (project_places.js).
		hide_sidebar: !frappe.is_mobile(),
		menu: () => onedesk.project.picker(frappe.get_route()[1]),
	});
};
