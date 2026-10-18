(() => {
	const Composer = frappe.views && frappe.views.CommunicationComposer;
	if (!Composer || Composer.prototype.one_signed) return;
	const own = Composer.prototype.get_signature;
	Composer.prototype.get_signature = async function (sender_email) {
		if (sender_email) {
			let signature = await frappe.xcall("onedesk.one_mail.holders.signature_for", { email: sender_email });
			if (signature) {
				if (!frappe.utils.is_html(signature)) signature = signature.replace(/\n/g, "<br>");
				return "<br>" + signature;
			}
		}
		return own.call(this, sender_email);
	};
	Composer.prototype.one_signed = true;
})();

(() => {
	const Composer = frappe.views && frappe.views.CommunicationComposer;
	if (!Composer || Composer.prototype.one_templated) return;
	const fields = Composer.prototype.get_fields;
	Composer.prototype.get_fields = function () {
		const all = fields.call(this);
		const template = all.find((one) => one.fieldname === "email_template");
		if (template)
			template.get_query = () => ({
				query: "frappe.email.doctype.email_template.email_template.get_email_templates",
				filters: { reference_doctype: (this.frm && this.frm.doctype) || (this.doc && this.doc.doctype) || "" },
			});
		return all;
	};
	Composer.prototype.one_templated = true;
})();

(() => {
	const Composer = frappe.views && frappe.views.CommunicationComposer;
	if (!Composer || Composer.prototype.one_extended) return;
	const make = Composer.prototype.make;
	const FILLED = ["subject", "cc", "bcc"];
	Composer.prototype.make = function () {
		const made = make.apply(this, arguments);
		if (!onedesk.places) return made;
		const dialog = this.dialog;
		const doc = this.doc || (this.frm && this.frm.doc) || {};
		onedesk.places.emit(
			"onemail.compose",
			{
				recipients: this.recipients || "",
				cc: this.cc || "",
				subject: this.subject || "",
				reply: !!this.is_a_reply,
				reference_doctype: doc.doctype || null,
				reference_name: doc.name || null,
			},
			{
				note: (text, tone) => dialog.$body.prepend(onedesk.places.note(text, tone)),
				set: (field, value) => FILLED.includes(field) && dialog.set_value(field, String(value || "")),
			}
		);
		return made;
	};
	Composer.prototype.one_extended = true;
})();
