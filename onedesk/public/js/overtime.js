// Recording overtime for one employee on one day. Offered from the Employee
// record and from the Attendance itself; both open the same dialog, because
// overtime is one person's extra hours on one date rather than something a
// list ever shares.

frappe.provide("onedesk.overtime");

onedesk.overtime.ask = (opts = {}) => {
	const dialog = new frappe.ui.Dialog({
		title: __("Record Overtime"),
		fields: [
			{
				fieldname: "employee",
				label: __("Employee"),
				fieldtype: "Link",
				options: "Employee",
				reqd: 1,
				default: opts.employee,
				read_only: opts.employee ? 1 : 0,
				get_query: () => ({ query: "erpnext.controllers.queries.employee_query" }),
				onchange: () => look(dialog),
			},
			{
				fieldname: "date",
				label: __("Date"),
				fieldtype: "Date",
				reqd: 1,
				default: opts.date || frappe.datetime.get_today(),
				onchange: () => look(dialog),
			},
			{ fieldtype: "Section Break", fieldname: "day_section" },
			{ fieldname: "day", fieldtype: "HTML" },
			{ fieldtype: "Section Break", fieldname: "overtime_section", hidden: 1 },
			{
				fieldname: "overtime_type",
				label: __("Overtime Type"),
				fieldtype: "Link",
				options: "Overtime Type",
				reqd: 1,
			},
			{ fieldtype: "Column Break" },
			{
				fieldname: "hours",
				label: __("Overtime Hours"),
				fieldtype: "Float",
				reqd: 1,
				description: __("Hours worked beyond the standard day."),
			},
		],
		primary_action_label: __("Record"),
		primary_action: (values) => {
			frappe
				.call({
					method: "onedesk.one_hr.overtime.record",
					args: {
						employee: values.employee,
						date: values.date,
						overtime_type: values.overtime_type,
						hours: values.hours,
					},
					freeze: true,
					freeze_message: __("Recording the overtime"),
				})
				.then((r) => {
					if (r.exc) return;
					dialog.hide();
					frappe.show_alert({
						message: __("Recorded on {0}", [r.message]),
						indicator: "green",
					});
					opts.after && opts.after(r.message);
				});
		},
	});

	dialog.show();
	look(dialog);
	return dialog;
};

// The day decides whether there is anything to write on. Asking the server
// first means the dialog says why rather than failing on submit.
function look(dialog) {
	const { employee, date } = dialog.get_values(true) || {};
	const $day = dialog.get_field("day").$wrapper;

	dialog.set_df_property("overtime_section", "hidden", 1);
	dialog.get_primary_btn().prop("disabled", true);
	$day.empty();

	if (!employee || !date) return;

	frappe
		.call({ method: "onedesk.one_hr.overtime.day", args: { employee, date } })
		.then(({ message }) => {
			if (!message) return;

			if (!message.ok) {
				$day.html(
					`<div class="text-muted">${frappe.utils.escape_html(message.why)}</div>`,
				);
				return;
			}

			$day.html(
				`<div class="text-muted">${__("Standard day: {0} hours. Anything beyond it is overtime.", [
					message.standard_hours,
				])}</div>`,
			);
			dialog.set_df_property("overtime_section", "hidden", 0);
			dialog.get_primary_btn().prop("disabled", false);
			if (message.overtime_type) {
				dialog.set_value("overtime_type", message.overtime_type);
				dialog.set_value("hours", message.hours);
			}
		});
}
