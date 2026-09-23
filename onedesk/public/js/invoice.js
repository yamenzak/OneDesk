// An invoice's and a bill's page says what is still owed and when it was due,
// and records a payment in one step. See one_book/paid.py.
frappe.provide("onedesk.invoice");

onedesk.invoice.band = (frm) => {
	const doc = frm.doc;
	if (doc.docstatus !== 1 || doc.is_return) return;
	const stat = onedesk.band.stat;
	const money = (value) => format_currency(value, doc.currency);
	const late = doc.outstanding_amount > 0 && doc.due_date && frappe.datetime.get_diff(frappe.datetime.get_today(), doc.due_date);
	const due = !doc.due_date
		? null
		: doc.outstanding_amount <= 0
			? stat(__("Was Due"), frappe.datetime.str_to_user(doc.due_date), null, "quiet")
			: late > 0
				? stat(__("Due"), __("{0} · {1} days late", [frappe.datetime.str_to_user(doc.due_date), late]), null, "alarm")
				: late === 0
					? stat(__("Due"), __("Today"), null, "waiting")
					: stat(__("Due"), __("{0} · in {1} days", [frappe.datetime.str_to_user(doc.due_date), -late]));
	const stats = [
		stat(__("Outstanding"), money(doc.outstanding_amount), null, doc.outstanding_amount > 0 ? (late > 0 ? "alarm" : null) : "quiet"),
		due,
		stat(__("Paid"), money(doc.grand_total - doc.outstanding_amount)),
		stat(__("Total"), money(doc.grand_total)),
	].filter(Boolean);
	onedesk.band.show(frm, stats);
	// A repeating invoice says how often, and when the next one is made.
	if (!doc.auto_repeat) return;
	frappe.db.get_value("Auto Repeat", doc.auto_repeat, ["frequency", "next_schedule_date", "status"]).then(({ message }) => {
		if (!message || frm.doc.name !== doc.name) return;
		const route = frappe.utils.get_form_link("Auto Repeat", doc.auto_repeat);
		const repeat = message.status === "Active" && message.next_schedule_date
			? stat(__("Repeats {0}", [__(message.frequency)]), __("Next on {0}", [frappe.datetime.str_to_user(message.next_schedule_date)]), route)
			: stat(__("Repeats"), __(message.status), route, "quiet");
		onedesk.band.show(frm, [...stats, repeat]);
	});
};

onedesk.invoice.record = (frm) => {
	const company = frm.doc.company;
	const bill = frm.doctype === "Purchase Invoice";
	frappe.db.get_value("Company", company, ["default_bank_account", "default_cash_account"]).then(({ message }) => {
		const dialog = new frappe.ui.Dialog({
			title: __("Record Payment"),
			fields: [
				{ fieldtype: "Currency", fieldname: "amount", label: __("Amount"), options: "currency", reqd: 1, default: frm.doc.outstanding_amount },
				{ fieldtype: "Date", fieldname: "on", label: __("Paid On"), reqd: 1, default: frappe.datetime.get_today() },
				{
					fieldtype: "Link",
					fieldname: "account",
					label: bill ? __("Paid From") : __("Paid Into"),
					options: "Account",
					reqd: 1,
					default: message.default_bank_account || message.default_cash_account,
					get_query: () => ({ filters: { company, is_group: 0, account_type: ["in", ["Bank", "Cash"]] } }),
				},
				{
					fieldtype: "Data",
					fieldname: "reference",
					label: __("Reference"),
					description: __("The cheque or transfer number. The invoice's number when left empty."),
				},
			],
			primary_action_label: __("Record"),
			primary_action(values) {
				dialog.disable_primary_action();
				frappe
					.xcall("onedesk.one_book.paid.settle", { doctype: frm.doctype, name: frm.doc.name, ...values })
					.then((entry) => {
						dialog.hide();
						frappe.ui.toast({ message: __("Payment {0} recorded.", [entry]), type: "success" });
						frm.reload_doc();
					})
					.finally(() => dialog.enable_primary_action());
			},
		});
		dialog.show();
	});
};

onedesk.invoice.refresh = (frm) => {
	onedesk.invoice.band(frm);
	if (frm.doc.docstatus === 1 && frm.doc.outstanding_amount > 0 && !frm.doc.is_return && frappe.model.can_create("Payment Entry")) {
		frm.add_custom_button(__("Record Payment"), () => onedesk.invoice.record(frm));
		frm.change_custom_button_type(__("Record Payment"), null, "primary");
	}
};

// ERPNext's refresh runs after ours and makes Create the primary group. While
// Record Payment is on the page it is the one dark button, and Create is not.
onedesk.invoice.setup = (frm) => {
	const primary = frm.page.set_inner_btn_group_as_primary.bind(frm.page);
	frm.page.set_inner_btn_group_as_primary = (label) =>
		label === __("Create") && frm.custom_buttons[__("Record Payment")] ? null : primary(label);
};

frappe.ui.form.on("Sales Invoice", { setup: onedesk.invoice.setup, refresh: onedesk.invoice.refresh });
frappe.ui.form.on("Purchase Invoice", { setup: onedesk.invoice.setup, refresh: onedesk.invoice.refresh });
