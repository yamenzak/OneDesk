// Something OneAI did or proposed: Apply or Dismiss what waits, Undo what was done.
frappe.ui.form.on("Intake Action", {
	refresh(frm) {
		const settle = (take) =>
			frappe.xcall("onedesk.one_intake.act.settle", { action: frm.doc.name, take }).then(() => frm.reload_doc());
		if (frm.doc.level === "Proposed") {
			frm.add_custom_button(__("Apply"), () => settle(1)).addClass("btn-primary");
			frm.add_custom_button(__("Dismiss"), () => settle(0));
		}
		if (frm.doc.level === "Done") {
			frm.add_custom_button(__("Undo"), () =>
				frappe.xcall("onedesk.one_intake.act.undo_one", { action: frm.doc.name }).then((said) => {
					if (said.why) frappe.msgprint(said.why);
					frm.reload_doc();
				})
			);
		}
	},
});
