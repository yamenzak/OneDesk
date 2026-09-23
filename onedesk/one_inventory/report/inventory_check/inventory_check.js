// What will fail the first time somebody receives stock, counts it or
// registers an asset, with the fix beside it (one_inventory/ready.py).
frappe.query_reports["Inventory Check"] = onedesk.check.report({
	method: "onedesk.one_inventory.ready.fix",
	ask(key, call) {
		if (key === "company") {
			frappe.set_route("Form", "Company", frappe.defaults.get_default("company"));
		} else if (key === "location") {
			frappe.prompt(
				{
					fieldtype: "Data",
					fieldname: "location_name",
					label: __("Location"),
					reqd: 1,
					default: __("Head Office"),
					description: __("Where the company's equipment is kept. Add more later under Setup › Locations."),
				},
				call,
				__("Add a Location"),
				__("Add"),
			);
		} else {
			return false;
		}
		return true;
	},
});
