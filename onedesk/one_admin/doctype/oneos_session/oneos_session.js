frappe.ui.form.on("OneOS Session", {
	refresh(frm) {
		if (frm.doc.state === "Stopped") return;
		frm.add_custom_button(__("Stop Session"), async () => {
			const go = await onedesk.interface.ask({
				question: __("Stop this session?"),
				effect: __("{0} closes in OneOS for {1}. Changes they saved are kept.", [frm.doc.file_name, frm.doc.user]),
				verb: __("Stop Session"),
				danger: true,
			});
			if (!go) return;
			await frappe.xcall("onedesk.one_admin.oneos.stop_session", { name: frm.doc.name });
			frappe.show_alert({ message: __("Session stopped."), indicator: "green" });
			frm.reload_doc();
		});
	},
});
