// A form, customized by the workspace. The client is public/js/customize.js;
// the page is the shell's, since what it edits is saved like a record
// (docs/SHELL.md, decision 6).

frappe.pages["customize"].on_page_load = (wrapper) => {
	const page = onedesk.shell.page(wrapper, __("Customize"));
	wrapper.loading = frappe.require("/assets/onedesk/js/customize.js").then(() => {
		wrapper.customize = new onedesk.Customize(page);
	});
};

frappe.pages["customize"].on_page_show = (wrapper) => {
	wrapper.loading && wrapper.loading.then(() => wrapper.customize && wrapper.customize.show());
};
