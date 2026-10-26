frappe.ui.form.on("Reading Action", {
	refresh(frm) {
		const settle = (take) =>
			frappe.xcall("onedesk.one_ai.reading.act.settle", { action: frm.doc.name, take }).then(() => frm.reload_doc());
		if (frm.doc.level === "Proposed") {
			frm.add_custom_button(__("Apply"), () => settle(1));
			frm.change_custom_button_type(__("Apply"), null, "primary");
			frm.add_custom_button(__("Dismiss"), () => settle(0));
		}
		if (frm.doc.level === "Done") {
			frm.add_custom_button(__("Undo"), () =>
				frappe.xcall("onedesk.one_ai.reading.act.undo_one", { action: frm.doc.name }).then((said) => {
					if (said.why) frappe.msgprint(said.why);
					frm.reload_doc();
				})
			);
		}
	},
});
