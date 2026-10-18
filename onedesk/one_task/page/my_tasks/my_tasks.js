
frappe.pages["my-tasks"].on_page_load = (wrapper) => {
	onedesk.island_page(wrapper, { island: "onedesk.my_tasks", title: __("OneTask"), hide_sidebar: true, mark: "onetask" });
};
