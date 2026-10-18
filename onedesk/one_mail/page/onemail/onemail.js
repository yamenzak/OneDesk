
frappe.pages["onemail"].on_page_load = (wrapper) => {
	const page = onedesk.shell.page(wrapper, __("OneMail"), { hide_sidebar: true, mark: "onemail" });
	wrapper.loading = frappe.require(["/assets/onedesk/css/onemail.css", "/assets/onedesk/js/onemail.js"]).then(() => {
		wrapper.onemail = new onedesk.OneMail(page);
	});
};

frappe.pages["onemail"].on_page_show = (wrapper) => {
	wrapper.loading && wrapper.loading.then(() => wrapper.onemail && wrapper.onemail.show());
};
