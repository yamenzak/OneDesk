frappe.provide("onedesk.factory");
const FACTORY = "onedesk.one_factory.control.";

onedesk.factory.workshop = () => ({
	id: "workshop",
	label: __("Workshop"),
	icon: "hard-hat",
	title: __("Workshop"),
	description: __("Where workshop time is costed, and where a new work order works and puts what it makes."),
	actions: [
		{
			label: __("Save"),
			variant: "solid",
			class: "one-set-save",
			click: async (panel) => {
				await frappe.xcall(FACTORY + "save_workshop", panel.get_values() || {});
				frappe.show_alert({ message: __("Workshop saved."), indicator: "green" });
				panel.clean && panel.clean();
			},
		},
	],
	async render(panel) {
		const kit = onedesk.module_settings.kit;
		const said = await frappe.xcall(FACTORY + "workshop");
		const pick = (key) => said[key] || said.suggested[key] || "";
		const company = { company: said.company, is_group: 0 };
		panel.body.empty();
		panel.add_fields([
			{
				fieldname: "default_operating_cost_account",
				fieldtype: "Link",
				options: "Account",
				label: __("Default Operating Cost Account"),
				default: pick("default_operating_cost_account"),
				read_only: !said.may,
				get_query: () => ({ filters: company }),
			},
			{
				fieldname: "default_wip_warehouse",
				fieldtype: "Link",
				options: "Warehouse",
				label: __("Default Work In Progress Warehouse"),
				default: pick("default_wip_warehouse"),
				read_only: !said.may,
				get_query: () => ({ filters: company }),
			},
			{
				fieldname: "default_fg_warehouse",
				fieldtype: "Link",
				options: "Warehouse",
				label: __("Default Finished Goods Warehouse"),
				default: pick("default_fg_warehouse"),
				read_only: !said.may,
				get_query: () => ({ filters: company }),
			},
		]);
		if (said.may) kit.track(panel);
		else panel.$header.find(".one-set-save").addClass("hide");
	},
});

onedesk.factory.settings = ({ at = null } = {}) => {
	const tabs = [{ group: null, items: [onedesk.factory.workshop()] }];
	const dialog = onedesk.module_settings.open({ module: onedesk.names.of("one_factory"), tabs, default_tab: at });
	dialog.show();
	return dialog;
};

frappe.provide("onedesk.control_centers");
onedesk.control_centers.OneFactory = onedesk.factory.settings;

$(document).on("page-change", () =>
	setTimeout(() => {
		const sidebar = frappe.app && frappe.app.sidebar;
		const win = onedesk.interface.current();
		if (!win || win.$foot_action || !sidebar || sidebar.current_module !== onedesk.names.sidebar("one_factory")) return;
		win.module_foot({ module: onedesk.names.of("one_factory"), settings: () => onedesk.factory.settings() });
		onedesk.interface.nav.place();
	}, 0)
);
