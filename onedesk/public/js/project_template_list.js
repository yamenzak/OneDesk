// The Templates list (OneProject's rail): the workspace's own templates, and
// From the Library beside Add, which copies a preset in and opens it
// (one_project/library.py).
frappe.listview_settings["Project Template"] = {
	onload(listview) {
		if (!frappe.model.can_create("Project Template")) return;
		listview.page.add_inner_button(__("From the Library"), () => {
			const dialog = new frappe.ui.Dialog({
				title: __("From the Library"),
				fields: [{ fieldtype: "Select", fieldname: "library", label: __("Template"), reqd: 1 }],
				primary_action_label: __("Copy Template"),
				primary_action: async ({ library }) => {
					dialog.hide();
					const made = await frappe.xcall("onedesk.one_project.library.copy", { key: library });
					frappe.set_route("Form", "Project Template", made);
				},
			});
			onedesk.project.library(dialog.get_field("library"));
			dialog.show();
		});
	},
};
