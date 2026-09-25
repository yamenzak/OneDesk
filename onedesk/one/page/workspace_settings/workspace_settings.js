// The workspace's settings, for its administrators. The client is public/js/settings.js, shared with settings; the
// sections are entries in One's sidebar, so the page is the shell's column (docs/SHELL.md).

frappe.pages["workspace-settings"].on_page_load = (wrapper) => {
	const page = onedesk.shell.page(wrapper, __("Workspace Settings"));
	wrapper.loading = frappe.require(["/assets/onedesk/css/settings.css", "/assets/onedesk/js/settings.js"]).then(() => {
		wrapper.settings = new onedesk.Settings(page, "workspace");
	});
};

frappe.pages["workspace-settings"].on_page_show = (wrapper) => {
	wrapper.loading && wrapper.loading.then(() => wrapper.settings && wrapper.settings.show());
};
