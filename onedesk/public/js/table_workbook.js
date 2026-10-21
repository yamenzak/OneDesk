// "Open in a workbook" under every table on a saved record: the table becomes
// the first sheet of a workbook attached to the record (one_sheet/table.py).
frappe.provide("onedesk.table_workbook");

// The editor's page and the Workbook doctype share the slug "workbook", and the
// router takes a doctype the user may read over a page: a System Manager got
// the stored record instead of the editor. A workbook is only ever opened in
// the editor, so the doctype gives the slug up.
if (frappe.router?.setup) {
	const setup = frappe.router.setup;
	frappe.router.setup = function () {
		setup.call(this);
		delete this.routes.workbook;
	};
}

// Which template to start from, when there are any: the name, "" for none,
// or null when the person closed the dialog.
onedesk.table_workbook.pick = (templates, plain) =>
	new Promise((resolve) => {
		if (!templates?.length) return resolve("");
		let chosen = null;
		const dialog = new frappe.ui.Dialog({
			title: __("Start From"),
			fields: [
				{
					fieldtype: "Select",
					fieldname: "template",
					label: __("Template"),
					options: [{ label: plain, value: "" }, ...templates.map((one) => ({ label: one.title, value: one.name }))],
					default: templates.length === 1 ? templates[0].name : "",
				},
			],
			primary_action_label: __("Open"),
			primary_action: ({ template }) => {
				chosen = template || "";
				dialog.hide();
			},
			on_hide: () => resolve(chosen),
		});
		dialog.show();
	});

onedesk.table_workbook.open = async (frm, field) => {
	if (frm.is_dirty()) {
		frappe.msgprint(__("Save the record before opening its table in a workbook."));
		return;
	}
	const templates = await frappe.xcall("onedesk.one_sheet.templates.listed", { doctype: frm.doctype, field, name: frm.doc.name });
	const template = await onedesk.table_workbook.pick(templates, __("The table as it is"));
	if (template === null) return;
	frappe
		.call({
			method: "onedesk.one_sheet.table.open_table",
			args: { doctype: frm.doctype, name: frm.doc.name, field, template: template || null },
			freeze: true,
		})
		.then((r) => r.message && frappe.set_route("workbook", r.message));
};

frappe.ui.form.on("*", {
	refresh(frm) {
		if (frm.is_new() || frm.meta.istable || frm.meta.issingle) return;
		for (const df of frm.meta.fields) {
			const grid = df.fieldtype === "Table" && frm.fields_dict[df.fieldname]?.grid;
			if (!grid || grid.one_workbook) continue;
			grid.one_workbook = grid.add_custom_button(__("Open in Workbook"), () =>
				onedesk.table_workbook.open(frm, df.fieldname)
			);
		}
	},
});
