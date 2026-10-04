// A project's page, opened at the project's own address (/desk/project/<name>;
// project_new.js hands the route here). The page itself is
// public/js/project_page.js, loaded the first time it is opened.

frappe.pages["project-view"].on_page_load = (wrapper) => {
	const page = onedesk.shell.page(wrapper, __("Project"));
	wrapper.loading = frappe
		.require([
			"/assets/onedesk/css/project_page.css",
			"/assets/onedesk/js/project_actions.js",
			"/assets/onedesk/js/progress.js",
			"/assets/onedesk/js/project_page.js",
		])
		.then(() => {
			wrapper.project = new onedesk.ProjectPage(page);
		});
};

frappe.pages["project-view"].on_page_show = (wrapper) => {
	wrapper.loading && wrapper.loading.then(() => wrapper.project && wrapper.project.show(frappe.get_route()[1]));
};
