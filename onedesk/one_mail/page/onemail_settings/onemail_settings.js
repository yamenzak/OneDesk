// OneMail's settings: your mailboxes, and for a workspace administrator who
// reads and sends from the workspace's mailboxes and the mail templates. The
// sections are One's settings page (public/js/settings.js), group "onemail";
// the page sits at the foot of OneMail's rail.
frappe.pages["onemail-settings"].on_page_load = (wrapper) => {
	const page = onedesk.shell.page(wrapper, __("OneMail Settings"));
	wrapper.loading = frappe.require(["/assets/onedesk/css/settings.css", "/assets/onedesk/js/settings.js"]).then(() => {
		wrapper.settings = new onedesk.Settings(page, "onemail");
	});
};

frappe.pages["onemail-settings"].on_page_show = (wrapper) => {
	wrapper.loading && wrapper.loading.then(() => wrapper.settings && wrapper.settings.show());
};
