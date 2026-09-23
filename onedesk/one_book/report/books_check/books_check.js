// What will fail the first time somebody invoices, is paid or pays, with the fix
// beside it (one_book/ready.py). A fix that needs a decision asks for it first.
frappe.query_reports["Books Check"] = {
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
		report.page.wrapper.on("click", "[data-one-fix]", (e) => onedesk.book.fix($(e.currentTarget).attr("data-one-fix"), report));
	},
};

frappe.provide("onedesk.book");

onedesk.book.fix = (key, report) => {
	const done = () => {
		frappe.ui.toast({ message: __("Fixed."), type: "success" });
		report.refresh();
	};
	const call = (values) => frappe.xcall("onedesk.one_book.ready.fix", { key, ...values }).then(done);
	if (key === "company") {
		frappe.set_route("Form", "Company", frappe.defaults.get_default("company"));
	} else if (key === "bank") {
		frappe.prompt(
			[
				{ fieldtype: "Data", fieldname: "bank", label: __("Bank"), reqd: 1 },
				{ fieldtype: "Data", fieldname: "account_name", label: __("Account Name"), reqd: 1, default: __("Current Account") },
				{ fieldtype: "Data", fieldname: "iban", label: __("IBAN") },
				{ fieldtype: "Data", fieldname: "bank_account_no", label: __("Account Number") },
			],
			call,
			__("Add Bank Account"),
			__("Add"),
		);
	} else if (key === "sales_tax" || key === "purchase_tax") {
		const doctype = key === "sales_tax" ? "Sales Taxes and Charges Template" : "Purchase Taxes and Charges Template";
		frappe.prompt(
			{ fieldtype: "Link", fieldname: "template", label: __("Default Template"), options: doctype, reqd: 1 },
			call,
			__("Choose the Tax Charged by Default"),
			__("Make Default"),
		);
	} else {
		call({});
	}
};
