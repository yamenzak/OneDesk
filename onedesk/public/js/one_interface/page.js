// A desk page on the window (onedesk/one_interface/AGENTS.md): any page frappe loads by name
// (a dashboard, print, a query report, a page of ours). What every page has
// is frappe's primary button and its menu, said once here when the page has
// loaded; a view that knows more says it in its own adapter.
onedesk.interface.adapt("page", () => {
	const Page = frappe.views && frappe.views.Page;
	if (!Page || Object.hasOwn(Page.prototype, "one_interface")) return;
	Page.prototype.one_interface = true;
	const trigger = Page.prototype.trigger_page_event;
	Page.prototype.trigger_page_event = function (event, ...args) {
		const said = trigger.call(this, event, ...args);
		const page = event === "on_page_load" && this.wrapper && this.wrapper.page;
		if (page && page.interface) {
			page.interface.view({
				primary: page.btn_primary,
				menu: { $button: page.menu_btn_group, dropdown: page.menu_dropdown },
			});
		}
		return said;
	};
});
