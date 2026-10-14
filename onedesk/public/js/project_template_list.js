// The Templates list (OneProject's rail): the workspace's own templates, and
// From the Library beside Add, which copies a preset in and opens it
// (one_project/library.py).
// Its counts read with what they count, as a phone shows them under the name.
frappe.listview_settings["Project Template"] = {
	formatters: {
		one_tasks: (value) => (Number(value) === 1 ? __("1 task") : __("{0} tasks", [value || 0])),
		one_days: (value) => (Number(value) === 1 ? __("1 day") : __("{0} days", [value || 0])),
		one_projects: (value) => (Number(value) === 1 ? __("1 project") : __("{0} projects", [value || 0])),
	},
	onload(listview) {
		if (!frappe.model.can_create("Project Template")) return;
		listview.page.add_inner_button(__("From the Library"), () => {
			const dialog = new frappe.ui.Dialog({
				title: __("From the Library"),
				fields: [{ fieldtype: "Autocomplete", fieldname: "library", label: __("Template"), reqd: 1 }],
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
