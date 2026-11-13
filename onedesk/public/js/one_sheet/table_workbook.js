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
// or null when the person closed the dialog. With `sizes` (a presentation's),
// the dialog always shows and also asks the size: `{template, width, height}`.
onedesk.table_workbook.pick = (templates, plain, sizes) =>
	new Promise((resolve) => {
		if (!templates?.length && !sizes) return resolve("");
		let chosen = null;
		const fields = [];
		if (templates?.length) {
			fields.push({
				fieldtype: "Select",
				fieldname: "template",
				label: __("Template"),
				options: [{ label: plain, value: "" }, ...templates.map((one) => ({ label: one.title, value: one.name }))],
				default: templates.length === 1 ? templates[0].name : "",
			});
		}
		if (sizes) {
			fields.push(
				{
					fieldtype: "Select",
					fieldname: "size",
					label: __("Size"),
					// a template keeps the size it was made at unless another is chosen
					options: [
						...(templates?.length ? [{ label: __("As It Was Made"), value: "own" }] : []),
						...sizes.map((one) => ({ label: one.label, value: one.key })),
						{ label: __("Custom"), value: "custom" },
					],
					default: templates?.length ? "own" : sizes[0].key,
				},
				{ fieldtype: "Int", fieldname: "width", label: __("Width"), default: 960, depends_on: "eval:doc.size=='custom'" },
				{ fieldtype: "Int", fieldname: "height", label: __("Height"), default: 540, depends_on: "eval:doc.size=='custom'" }
			);
		}
		const dialog = new frappe.ui.Dialog({
			title: __("Start From"),
			fields,
			primary_action_label: __("Open"),
			primary_action: (values) => {
				if (!sizes) {
					chosen = values.template || "";
				} else {
					const preset = sizes.find((one) => one.key === values.size);
					const own = values.size === "own";
					chosen = {
						template: values.template || "",
						width: own ? null : preset ? preset.w : values.width,
						height: own ? null : preset ? preset.h : values.height,
					};
				}
				dialog.hide();
			},
			on_hide: () => resolve(chosen),
		});
		dialog.show();
	});

// The table as it is; a template's sheets, and the formulas it puts under
// the table, are added from inside the workbook (Add Sheets From a Template).
onedesk.table_workbook.open = (frm, field) => {
	if (frm.is_dirty()) {
		frappe.msgprint(__("Save the record before opening its table in a workbook."));
		return;
	}
	frappe
		.call({
			method: "onedesk.one_sheet.table.open_table",
			args: { doctype: frm.doctype, name: frm.doc.name, field },
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
			grid.one_workbook = grid.add_custom_button(__("Open in OneSheet"), () =>
				onedesk.table_workbook.open(frm, df.fieldname)
			);
		}
	},
});
