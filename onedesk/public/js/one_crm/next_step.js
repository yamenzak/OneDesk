frappe.provide("onedesk.next_step");

onedesk.next_step.OPEN = {
	Lead: ["Lead", "Open", "Replied", "Interested"],
	Opportunity: ["Open", "Quotation", "Replied"],
};

onedesk.next_step.button = (frm) => {
	if (frm.is_new() || !frm.perm[0]?.write) return;
	if (!onedesk.next_step.OPEN[frm.doctype]?.includes(frm.doc.status)) return;
	const label = frm.doc.one_next_step ? __("Next Step Done") : __("Set Next Step");
	frm.add_custom_button(label, () => onedesk.next_step.ask(frm));
};

onedesk.next_step.ask = (frm) => {
	const dialog = new frappe.ui.Dialog({
		title: frm.doc.one_next_step ? __("What Comes Next?") : __("Set Next Step"),
		fields: [
			{ fieldtype: "Data", fieldname: "next_step", label: __("Next Step") },
			{
				fieldtype: "Datetime",
				fieldname: "next_on",
				label: __("Next Step Due"),
				mandatory_depends_on: "eval:doc.next_step",
			},
		],
		primary_action_label: __("Save"),
		primary_action: async (values) => {
			await frappe.xcall("onedesk.one_crm.next.done", {
				doctype: frm.doctype,
				name: frm.doc.name,
				next_step: values.next_step,
				next_on: values.next_on,
			});
			dialog.hide();
			frm.reload_doc();
		},
	});
	if (frm.doc.one_next_step) {
		dialog.set_df_property(
			"next_step",
			"description",
			__("{0} is marked done. Leave empty if nothing comes next.", [
				frappe.utils.escape_html(frm.doc.one_next_step),
			]),
		);
	}
	dialog.show();
};

onedesk.next_step.late = (value) => !!value && value < frappe.datetime.system_datetime();

onedesk.next_step.formatters = {
	one_next_on(value, df, doc) {
		if (!value) return "";
		const shown = frappe.datetime.str_to_user(value);
		const open = Object.values(onedesk.next_step.OPEN).some((all) => all.includes(doc?.status));
		return open && onedesk.next_step.late(value) ? `<span class="text-danger">${shown}</span>` : shown;
	},
};
