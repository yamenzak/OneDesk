// Allocating leave to everybody, with the dates filled in and nobody asked
// which company.
//
// Three things about the panel as HRMS ships it:
//
//   * `set_leave_details` sets `dates_based_on: "Leave Period"` and a leave
//     period in the same breath as `from_date: today, to_date: null`. The dates
//     are meant to come from the period, but they arrive by `add_fetch`, which
//     fires when somebody *changes* the period — and nobody changes a field
//     that is already filled. So the panel opens saying it will allocate from
//     today until nothing.
//   * The employee table has a Company column, and it is the same company on
//     every row. The doctype's own Company field is hidden by `one/company.py`,
//     but this table is a datatable built in their form script, so it is not a
//     field and the sweep does not reach it.
//   * Leave Policy is mandatory and deliberately cleared, so the form opens
//     with a red box before anybody has done anything wrong.
frappe.ui.form.on("Leave Control Panel", {
	refresh: (frm) => onedesk.leave_panel.dates(frm),
	dates_based_on: (frm) => onedesk.leave_panel.dates(frm),
	leave_period: (frm) => onedesk.leave_panel.dates(frm),
	allocate_based_on_leave_policy: (frm) => onedesk.leave_panel.only_policy(frm),
	// Their own batch ends by clearing the policy, so filling it in is answered
	// by the clearing itself. Field handlers are a list rather than a slot, so
	// theirs still runs and still refreshes the employee table.
	leave_policy: (frm) => onedesk.leave_panel.only_policy(frm),

	// Replaces theirs rather than wrapping it: a form script's handlers are
	// merged onto `frm.events` and the last one registered wins, and this file
	// loads after the doctype's own.
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

//: One policy is not a choice. A workspace that has written a second one is
//: choosing between them and is left to. Deferred by a tick because their
//: `set_leave_details` fills the whole form in one `set_value`, clearing the
//: policy as it goes, and the triggers it fires run while that batch is still
//: being applied.
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
