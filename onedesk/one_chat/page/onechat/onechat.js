frappe.pages["onechat"].on_page_load = (wrapper) => {
	onedesk.island_page(wrapper, {
		island: "onedesk.onechat",
		title: onedesk.names.of("one_chat"),
	});
};
