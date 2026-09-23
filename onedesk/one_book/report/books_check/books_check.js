// What will fail the first time somebody invoices, is paid or pays, with the fix
// beside it (one_book/ready.py). A fix that needs a decision asks for it first.
frappe.query_reports["Books Check"] = onedesk.check.report({
	method: "onedesk.one_book.ready.fix",
	ask(key, call) {
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
		} else if (key === "trn") {
			frappe.prompt(
				{ fieldtype: "Data", fieldname: "trn", label: __("TRN"), reqd: 1, description: __("The 15-digit Tax Registration Number on the VAT certificate.") },
				call,
				__("The Company's TRN"),
				__("Save"),
			);
		} else if (key === "emirate") {
			frappe.prompt(
				[
					{
						fieldtype: "Select",
						fieldname: "emirate",
						label: __("Emirate"),
						reqd: 1,
						options: ["", "Abu Dhabi", "Ajman", "Dubai", "Fujairah", "Ras Al Khaimah", "Sharjah", "Umm Al Quwain"],
					},
					{ fieldtype: "Data", fieldname: "address_line1", label: __("Street Address"), reqd: 1 },
					{ fieldtype: "Data", fieldname: "city", label: __("City") },
				],
				call,
				__("The Company's Address"),
				__("Save"),
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
			return false;
		}
		return true;
	},
});
