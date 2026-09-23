// A check report: each row is something that will fail on first use, whether
// it is Ready, To Do or Suggested, and a Fix where there is one. The Books
// Check and the Inventory Check are both this (one_book/ready.py,
// one_inventory/ready.py). `ask(key, call)` asks for what a fix needs and
// returns true, or returns false for a fix that needs nothing.
frappe.provide("onedesk.check");

onedesk.check.report = ({ method, ask }) => ({
	filters: [],
	formatter(value, row, column, data, default_formatter) {
		if (!data) return default_formatter(value, row, column, data);
		if (column.fieldname === "state") {
			const [label, theme] = {
				Ready: [__("Ready"), "green"],
				"To Do": [__("To Do"), "red"],
				Suggested: [__("Suggested"), "amber"],
			}[data.state];
			return frappe.ui.badge.html({ label, theme });
		}
		if (column.fieldname === "fix") {
			if (!data.fix) return "";
			return frappe.ui.button.html({ label: __("Fix"), size: "sm", attrs: { "data-one-fix": data.fix } });
		}
		return default_formatter(value, row, column, data);
	},
	onload(report) {
		report.page.wrapper.on("click", "[data-one-fix]", (e) => {
			const key = $(e.currentTarget).attr("data-one-fix");
			const call = (values) =>
				frappe.xcall(method, { key, ...values }).then(() => {
					frappe.ui.toast({ message: __("Fixed."), type: "success" });
					report.refresh();
				});
			if (!(ask && ask(key, call))) call({});
		});
	},
});
