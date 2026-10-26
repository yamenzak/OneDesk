// The Address Book (one/address_book.py): contacts and addresses as one screen.
frappe.pages["address-book"].on_page_load = (wrapper) => {
	onedesk.island_page(wrapper, {
		island: "onedesk.address_book",
		title: __("Address Book"),
	});
};
