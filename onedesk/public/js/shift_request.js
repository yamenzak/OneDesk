// The Approver is mandatory and HRMS filters it to the employee's own approver
// plus their department's. Where there is one obvious answer the form takes it.
// Where there is none, the head's sentence says so (one_hr/heads.py) instead of
// leaving somebody guessing at a required field.
frappe.ui.form.on("Shift Request", {
	refresh: approver,
	employee: approver,
});

async function approver(frm) {
	if (frm.doc.docstatus !== 0 || !frm.doc.employee) return;
	const who = await frappe.xcall("onedesk.one_hr.shift.approvers", { employee: frm.doc.employee });
	if (who.length === 1 && !frm.doc.approver) frm.set_value("approver", who[0]);
	else if (!who.length && frm.is_dirty()) frm.set_value("approver", "");
}
