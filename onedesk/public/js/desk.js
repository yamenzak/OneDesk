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

// The panel is a column, not a flyout. `panel_can_close` is the single hinge:
// frappe asks it both for where the panel starts and for whether it may close,
// and answers yes whenever there is a rail, on the reasoning that a rail is the
// way back to a panel you dismissed. One is a product people work inside all
// day rather than a desk they dip into, so the panel stays out and the rail is
// for moving between products.
frappe.ui.Sidebar = class OneSidebar extends frappe.ui.Sidebar {
	panel_can_close() {
		return false;
	}
};
