frappe.provide("onedesk");

// The rail is five marks and never needs to be words: every entry is a product,
// and the panel beside it is where the reading happens. Frappe keeps the choice
// in localStorage and offers a toggle; One takes the choice away and gives the
// width to the panel.
frappe.ui.Dock = class OneDock extends frappe.ui.Dock {
	constructor(...args) {
		super(...args);
		this.collapsed = true;
		this.apply_collapsed();
	}

	toggle_collapsed() {}
};
