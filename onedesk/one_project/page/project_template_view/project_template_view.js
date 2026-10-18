
frappe.pages["project-template-view"].on_page_load = (wrapper) => {
	onedesk.island_page(wrapper, {
		island: "onedesk.template",
		title: __("Project Template"),
		parent: { label: __("Templates"), route: "/desk/project-template" },
		requires: ["/assets/onedesk/js/project_actions.js"],
		hide_sidebar: !frappe.is_mobile(),
		record: "Project Template",
	});
};
