// Nothing on this record may be edited, and the grid still draws a selection
// box and a pencil per row. `editable_grid: 0` stops the typing, not the
// furniture, so the furniture is hidden in desk.css; and there is nothing to
// save, so no Save. The pill and the Accept and Reject that settle a flag are
// its Record Head (one_hr/heads.py).
frappe.ui.form.on("Clock Attempt", {
	refresh(frm) {
		frm.disable_save();
		frm.get_field("signals")?.$wrapper.addClass("one-static-grid");
	},
});
