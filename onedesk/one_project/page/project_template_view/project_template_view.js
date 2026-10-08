// A project template's page, opened at the template's own address
// (/desk/project-template/<name>; project_new.js hands the route here). Its
// body is the onedesk.template island (frontend/src/template); desk keeps the
// head (onedesk.island_page).

frappe.pages["project-template-view"].on_page_load = (wrapper) => {
	onedesk.island_page(wrapper, {
		island: "onedesk.template",
		title: __("Project Template"),
		parent: { label: __("Templates"), route: "/desk/project-template" },
		// Edit Details is the project's own dialog (project_actions.js).
		requires: ["/assets/onedesk/js/project_actions.js"],
		// A record, as a project's page is: the panel is for the four places
		// (project_places.js).
		hide_sidebar: !frappe.is_mobile(),
		record: "Project Template",
	});
};
