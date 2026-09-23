// A lead's or a deal's next step: marked done from the record, which asks what
// comes next in the same breath, and shown red on a list once it is overdue.
// See one_crm/next.py.
frappe.provide("onedesk.next_step");

onedesk.next_step.button = (frm) => {
	if (frm.is_new() || !frm.perm[0]?.write) return;
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
			__("{0} is marked done on the timeline. Leave empty if nothing comes next.", [
				frappe.utils.escape_html(frm.doc.one_next_step),
			]),
		);
	}
	dialog.show();
};

// Red once the time has passed, so an overdue step is seen without reading dates.
onedesk.next_step.formatters = {
	one_next_on(value) {
		if (!value) return "";
		const shown = frappe.datetime.str_to_user(value);
		return frappe.datetime.str_to_obj(value) < new Date()
			? `<span class="text-danger">${shown}</span>`
			: shown;
	},
};
