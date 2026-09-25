// The OneMail page. The client itself is public/js/onemail.js, loaded the
// first time the page is opened.

frappe.pages["onemail"].on_page_load = (wrapper) => {
	// The mailboxes are their own navigation: no rail panel beside them.
	const page = onedesk.shell.page(wrapper, __("Mail"), { hide_sidebar: true });
	wrapper.loading = frappe.require(["/assets/onedesk/css/onemail.css", "/assets/onedesk/js/onemail.js"]).then(() => {
		wrapper.onemail = new onedesk.OneMail(page);
	});
};

frappe.pages["onemail"].on_page_show = (wrapper) => {
	wrapper.loading && wrapper.loading.then(() => wrapper.onemail && wrapper.onemail.show());
};
