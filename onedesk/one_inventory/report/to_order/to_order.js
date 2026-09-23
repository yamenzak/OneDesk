// What to order, and Order: a draft purchase order per supplier from the rows
// ticked. See one_inventory/order.py.
frappe.query_reports["To Order"] = {
	filters: [],
	get_datatable_options(options) {
		return Object.assign(options, { checkboxColumn: true });
	},
	onload(report) {
		report.page.set_primary_action(__("Order"), () => {
			const picked = report.datatable.rowmanager.getCheckedRows().map((i) => report.data[Number(i)]);
			if (!picked.length) return frappe.msgprint(__("Tick the rows to order."));
			const call = (supplier) =>
				frappe.xcall("onedesk.one_inventory.order.order", { rows: picked, supplier }).then((made) => {
					frappe.ui.toast({ message: __("{0} purchase orders drafted.", [made.length]), type: "success" });
					report.refresh();
					if (made.length === 1) frappe.set_route("Form", "Purchase Order", made[0]);
					else frappe.set_route("List", "Purchase Order", { docstatus: 0 });
				});
			if (picked.every((row) => row.supplier)) return call(null);
			frappe.prompt(
				{
					fieldtype: "Link",
					fieldname: "supplier",
					label: __("Supplier"),
					options: "Supplier",
					description: __("For the rows that have no supplier of their own."),
				},
				({ supplier }) => call(supplier),
				__("Who Supplies the Rest?"),
				__("Order"),
			);
		});
	},
};
