frappe.ui.form.on("Offering", {
	refresh(frm) {
		frm.sidebar.sidebar.find(".form-shared").addClass("hidden");
		onedesk.offering.say(frm);
		if (frm.is_new()) return;
		if (frm.doc.kind !== "Plan") frm.dashboard.links_area && frm.dashboard.links_area.hide();
		if (frm.doc.kind === "Add-on") {
			frm.add_custom_button(__("View Workspaces"), () =>
				frappe.xcall("onedesk.one_admin.operator.sold", { offering: frm.doc.name }).then((sold) =>
					frappe.set_route("List", "Tenant", { name: ["in", sold.workspaces.length ? sold.workspaces : [""]] }),
				),
			);
		}
		if (frappe.model.can_read("Item")) {
			const item = `ONE-${frm.doc.name}`.toUpperCase();
			frm.add_custom_button(__("View Item"), () =>
				frappe.db.exists("Item", item).then((there) =>
					there ? frappe.set_route("Form", "Item", item) : frappe.show_alert(__("No item yet")),
				),
			);
		}
	},
});

frappe.provide("onedesk.offering");

onedesk.offering.say = (frm) => {
	const plan = frm.doc.kind === "Plan";
	const zero = plan ? __("Zero means unlimited.") : __("Set only what this add-on adds.");
	["storage_gb", "database_gb", "seats"].forEach((field) => frm.set_df_property(field, "description", zero));
};
