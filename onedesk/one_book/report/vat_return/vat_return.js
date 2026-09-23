// Tax charged against tax paid, for a period. See vat_return.py.
frappe.query_reports["VAT Return"] = {
	filters: [
		{
			fieldname: "from_date",
			label: __("From Date"),
			fieldtype: "Date",
			reqd: 1,
			default: frappe.datetime.quarter_start(),
		},
		{ fieldname: "to_date", label: __("To Date"), fieldtype: "Date", reqd: 1, default: frappe.datetime.get_today() },
	],
	onload(report) {
		report.page.add_inner_button(__("Lock Books"), () => onedesk.book.lock(report));
		onedesk.book.show_lock(report);
	},
	formatter(value, row, column, data, default_formatter) {
		// A heading or a total has no rate or amount of its own: blank, not nought.
		if (value === undefined || value === null) return "";
		const out = default_formatter(value, row, column, data);
		if (data && data.sub && column.fieldname === "line") return `<span style="padding-left: var(--padding-lg)">${out}</span>`;
		return data && data.bold ? `<strong>${out}</strong>` : out;
	},
};

frappe.provide("onedesk.book");

// Where the lock stands, beside the report's title. See one_book/closing.py.
onedesk.book.show_lock = (report) =>
	frappe.db.get_value("Company", frappe.defaults.get_default("company"), "accounts_frozen_till_date").then(({ message }) => {
		const until = message && message.accounts_frozen_till_date;
		if (until) report.page.set_indicator(__("Locked to {0}", [frappe.datetime.str_to_user(until)]), "gray");
		else report.page.clear_indicator();
		return until;
	});

onedesk.book.lock = (report) => {
	onedesk.book.show_lock(report).then((until) => {
		const call = (value) =>
			frappe.xcall("onedesk.one_book.closing.lock", { until: value }).then(() => {
				dialog.hide();
				frappe.ui.toast({ message: value ? __("Books locked.") : __("Books unlocked."), type: "success" });
				onedesk.book.show_lock(report);
			});
		const dialog = new frappe.ui.Dialog({
			title: __("Lock Books"),
			fields: [
				{
					fieldtype: "Date",
					fieldname: "until",
					label: __("Up To"),
					reqd: 1,
					default: report.get_filter_value("to_date"),
					description: __("Nothing dated on or before this day can then be entered, changed or cancelled, by anybody."),
				},
			],
			primary_action_label: __("Lock"),
			primary_action: ({ until: value }) => call(value),
			secondary_action_label: until ? __("Unlock") : null,
			secondary_action: until ? () => call(null) : null,
		});
		dialog.show();
	});
};
