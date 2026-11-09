frappe.ui.form.on("One Admin Settings", {
	refresh(frm) {
		frm.add_custom_button(__("Test Gateway"), () => onedesk.admin.tryGateway());
		frm.sidebar.sidebar.find(".form-shared").addClass("hidden");
		onedesk.admin.drawSetup(frm.fields_dict.cloudflare_setup_said.$wrapper, frm.doc.cloudflare_setup);
		onedesk.admin.drawOperators(frm.fields_dict.operators.$wrapper);
	},
	set_up_cloudflare(frm) {
		if (frm.is_dirty()) return frappe.msgprint(__("Save before setting up Cloudflare."));
		onedesk.admin.runSetup(frm.fields_dict.cloudflare_setup_said.$wrapper, () => frm.reload_doc());
	},
	sign_in_to_cloudflare(frm) {
		if (frm.is_dirty()) return frappe.msgprint(__("Save before signing in to Cloudflare."));
		frappe.xcall("onedesk.one_admin.cloudflare_signin.start").then((url) => (window.location.href = url));
	},
	create_aws_user(frm) {
		if (frm.is_dirty()) return frappe.msgprint(__("Save before creating the AWS user."));
		frappe.xcall("onedesk.one_admin.aws.link").then((url) => window.open(url, "_blank", "noopener"));
	},
});
