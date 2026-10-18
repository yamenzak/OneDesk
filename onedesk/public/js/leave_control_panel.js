frappe.ui.form.on("Leave Control Panel", {
	refresh: (frm) => onedesk.leave_panel.dates(frm),
	dates_based_on: (frm) => onedesk.leave_panel.dates(frm),
	leave_period: (frm) => onedesk.leave_panel.dates(frm),
	allocate_based_on_leave_policy: (frm) => onedesk.leave_panel.only_policy(frm),
	leave_policy: (frm) => onedesk.leave_panel.only_policy(frm),

	get_employees_datatable_columns() {
		return [
			{ name: "employee", id: "employee", content: __("Employee") },
			{ name: "employee_name", id: "employee_name", content: __("Name") },
			{ name: "department", id: "department", content: __("Department") },
		].map((column) => ({
			...column,
			editable: false,
			focusable: false,
			dropdown: false,
			align: "left",
		}));
	},
});

frappe.provide("onedesk.leave_panel");

onedesk.leave_panel.dates = (frm) => {
	if (frm.doc.dates_based_on !== "Leave Period" || !frm.doc.leave_period) return;
	frappe.db
		.get_value("Leave Period", frm.doc.leave_period, ["from_date", "to_date"])
		.then(({ message }) => {
			if (!message) return;
			if (frm.doc.from_date !== message.from_date) frm.set_value("from_date", message.from_date);
			if (frm.doc.to_date !== message.to_date) frm.set_value("to_date", message.to_date);
		});
	onedesk.leave_panel.only_policy(frm);
};

onedesk.leave_panel.only_policy = (frm) =>
	setTimeout(() => onedesk.leave_panel._only_policy(frm), 0);

onedesk.leave_panel._only_policy = (frm) => {
	if (frm.doc.leave_policy || !frm.doc.allocate_based_on_leave_policy) return;
	frappe.db
		.get_list("Leave Policy", { filters: { docstatus: 1 }, fields: ["name"], limit: 2 })
		.then((found) => {
			if (found.length === 1 && !frm.doc.leave_policy)
				frm.set_value("leave_policy", found[0].name);
		});
};
