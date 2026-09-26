// Reading attendance into a slip, without the slip saving itself first.
//
// HRMS's Fetch button calls a document method that ends in `self.save()`, so on
// a new form it inserted a record and left the person on the unsaved blank one.
// Ours asks the server for the rows, fills the grid, and leaves the document
// dirty so saving stays the person's decision.
frappe.ui.form.on("Overtime Slip", {
	onload(frm) {
		// The grid opens with one empty row, and Date and Overtime Type are
		// both mandatory on it, so the first Save fails on a row nobody added.
		if (frm.is_new()) frm.clear_table("overtime_details");
	},

	refresh(frm) {
		frm.remove_custom_button(__("Fetch Overtime Details"));
		if (frm.doc.docstatus === 0) {
			frm.add_custom_button(__("Read Attendance"), () => read(frm));
		}
	},

	// Replaces HRMS's, which called a document method that threw for anybody
	// without a salary structure — and named the date it was working out, so
	// the refusal read "for date None".
	set_frequency_and_dates(frm) {
		if (!frm.doc.employee || !frm.doc.posting_date) return;
		return frappe
			.xcall("onedesk.one_hr.overtime.dates", {
				employee: frm.doc.employee,
				posting_date: frm.doc.posting_date,
			})
			.then((when) => frm.set_value(when));
	},
});

function read(frm) {
	if (!frm.doc.employee || !frm.doc.start_date || !frm.doc.end_date) {
		frappe.msgprint(__("Choose an employee and a posting date first."));
		return;
	}

	frappe
		.xcall("onedesk.one_hr.overtime.collect", {
			employee: frm.doc.employee,
			start_date: frm.doc.start_date,
			end_date: frm.doc.end_date,
		})
		.then(({ rows, trimmed }) => {
			if (!rows.length) {
				frappe.msgprint(
					__("No overtime was recorded on any attendance between {0} and {1}.", [
						frappe.datetime.str_to_user(frm.doc.start_date),
						frappe.datetime.str_to_user(frm.doc.end_date),
					]),
				);
				return;
			}
			frm.clear_table("overtime_details");
			rows.forEach((row) => frm.add_child("overtime_details", row));
			frm.refresh_field("overtime_details");
			frm.set_value(
				"total_overtime_duration",
				rows.reduce((sum, row) => sum + row.overtime_duration, 0),
			);
			frappe.show_alert({
				message: __("{0} days read. Save to keep them.", [rows.length]),
				indicator: "green",
			});
			if (trimmed.length) told(trimmed);
		});
}

// A day worked beyond the type's daily maximum is paid up to it and no further.
// HRMS trimmed it on the way in and said nothing, which is a quiet pay cut.
function told(trimmed) {
	const rows = trimmed
		.map(
			(one) =>
				`<li>${frappe.datetime.str_to_user(one.date)} — ${__("{0} worked, {1} paid", [
					one.worked,
					one.paid,
				])}</li>`,
		)
		.join("");
	frappe.msgprint({
		title: __("Some Days Were Trimmed"),
		message: `<p>${__("These days go past the overtime type's daily maximum. Only the hours up to it are paid.")}</p><ul>${rows}</ul>`,
		indicator: "orange",
	});
}
