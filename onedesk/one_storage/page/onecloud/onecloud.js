// The OneCloud page. The explorer itself is public/js/onecloud.js, shared
// with a record's Files tab, and loaded the first time either is opened.

frappe.pages["onecloud"].on_page_load = (wrapper) => {
	// The explorer is its own navigation: the rail's panel (Files, and Storage
	// Check under Setup) starts closed, and the tree takes its place.
	const page = onedesk.shell.page(wrapper, __("Files"), { hide_sidebar: true });
	wrapper.loading = frappe.require(["/assets/onedesk/css/onecloud.css", "/assets/onedesk/js/onecloud.js"]).then(() => {
		wrapper.onecloud = new onedesk.OneCloud(page);
	});
};

frappe.pages["onecloud"].on_page_show = (wrapper) => {
	wrapper.loading && wrapper.loading.then(() => wrapper.onecloud && wrapper.onecloud.show());
};
