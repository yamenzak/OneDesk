frappe.ui.form.on("Private App", {
	refresh(frm) {
		if (frm.is_new()) return;
		frm.add_custom_button(__("New Code"), () => {
			frappe.prompt(
				{ fieldname: "tenant", fieldtype: "Link", options: "Tenant", label: __("Workspace"), reqd: 1 },
				async ({ tenant }) => {
					const code = await frappe.xcall("onedesk.one_admin.private.new_code", { app: frm.doc.name, tenant });
					frappe.msgprint({
						title: __("Code for {0}", [tenant]),
						message: `<p>${__("Send this to the workspace. It's shown once.")}</p><p class="text-lg"><b>${frappe.utils.escape_html(code)}</b></p>`,
					});
					frm.reload_doc();
				},
				__("New Code"),
				__("Make Code")
			);
		});
	},
});
