// What a workspace needing this much would pay, every way it could.
// A workspace fills the four needs from what it has now.
frappe.query_reports["Plan Calculator"] = {
	filters: [
		{
			fieldname: "workspace",
			label: __("Workspace"),
			fieldtype: "Link",
			options: "Tenant",
			on_change(report) {
				const workspace = report.get_filter_value("workspace");
				if (!workspace) return report.refresh();
				frappe
					.xcall("onedesk.one_admin.report.plan_calculator.plan_calculator.needs_of", { workspace })
					.then((needs) => {
						// Setting a changed need refreshes; the same needs again would not.
						const changed = Object.keys(needs).some((key) => report.get_filter_value(key) != needs[key]);
						report.set_filter_value(needs);
						if (!changed) report.refresh(true);
					});
			},
		},
		{ fieldname: "seats", label: __("Seats"), fieldtype: "Int", default: 10 },
		{ fieldname: "storage_gb", label: __("Storage (GB)"), fieldtype: "Int", default: 50 },
		{ fieldname: "database_gb", label: __("Database (GB)"), fieldtype: "Int", default: 2 },
		{ fieldname: "credits_a_month", label: __("Credits a Month"), fieldtype: "Int", default: 2000 },
	],
	formatter(value, row, column, data, default_formatter) {
		const shown = default_formatter(value, row, column, data);
		if (!data) return shown;
		if (column.fieldname === "dearer_by" && data.cheapest) return `<span class="text-success">${shown}</span>`;
		if (column.fieldname === "dearer_by" && data.short) return `<span class="text-danger">${shown}</span>`;
		if (column.fieldname === "theirs" && value) return `<span class="indicator-pill blue">${shown}</span>`;
		return shown;
	},
};
