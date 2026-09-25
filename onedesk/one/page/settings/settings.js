// A person's own settings. The client is public/js/settings.js, shared with workspace-settings; the
// sections are entries in One's sidebar, so the page is the shell's column (docs/SHELL.md).

frappe.pages["settings"].on_page_load = (wrapper) => {
	const page = onedesk.shell.page(wrapper, __("Settings"));
	wrapper.loading = frappe.require(["/assets/onedesk/css/settings.css", "/assets/onedesk/js/push.js", "/assets/onedesk/js/settings.js"]).then(() => {
		wrapper.settings = new onedesk.Settings(page, "you");
	});
};

frappe.pages["settings"].on_page_show = (wrapper) => {
	wrapper.loading && wrapper.loading.then(() => wrapper.settings && wrapper.settings.show());
};
