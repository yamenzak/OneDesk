const FACTORY = "onedesk.one_factory.control.";

onedesk.centers.part("settings", onedesk.names.of("one_factory"), {
	sections: () => [
		{
			group: null,
			items: [
				{
					id: "workshop",
					label: __("Workshop"),
					icon: "hard-hat",
					title: __("Workshop"),
					description: __("Where workshop time is costed, and where a new work order works and puts what it makes."),
					async fields() {
						const said = await frappe.xcall(FACTORY + "workshop");
						const pick = (key) => said[key] || said.suggested[key] || "";
						const company = { company: said.company, is_group: 0 };
						const link = (fieldname, options, label) => ({
							fieldname,
							fieldtype: "Link",
							options,
							label,
							default: pick(fieldname),
							read_only: !said.may,
							get_query: () => ({ filters: company }),
						});
						return [
							link("default_operating_cost_account", "Account", __("Default Operating Cost Account")),
							link("default_wip_warehouse", "Warehouse", __("Default Work In Progress Warehouse")),
							link("default_fg_warehouse", "Warehouse", __("Default Finished Goods Warehouse")),
						];
					},
					save: (values) => frappe.xcall(FACTORY + "save_workshop", values),
				},
			],
		},
	],
});

$(document).on("page-change", () =>
	setTimeout(() => {
		const sidebar = frappe.app && frappe.app.sidebar;
		const win = onedesk.interface.current();
		if (!win || win.$foot_action || !sidebar || sidebar.current_module !== onedesk.names.sidebar("one_factory")) return;
		win.module_foot({ module: onedesk.names.of("one_factory"), settings: () => onedesk.centers.open("settings", { module: onedesk.names.of("one_factory") }) });
		onedesk.interface.nav.place();
	}, 0)
);
