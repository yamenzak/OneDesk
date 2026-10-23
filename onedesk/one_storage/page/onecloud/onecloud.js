
frappe.pages["onecloud"].on_page_load = (wrapper) => {
	const page = onedesk.shell.page(wrapper, __("OneCloud"), { mark: "onestorage", window: true, fit: true });
	wrapper.loading = frappe.require(["/assets/onedesk/css/onecloud.css", "/assets/onedesk/js/onecloud.js"]).then(() => {
		wrapper.onecloud = new onedesk.OneCloud(page);
	});
};

frappe.pages["onecloud"].on_page_show = (wrapper) => {
	wrapper.loading && wrapper.loading.then(() => wrapper.onecloud && wrapper.onecloud.show());
};
