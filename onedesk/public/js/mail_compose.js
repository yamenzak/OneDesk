// Frappe's email composer, signed as the address it sends from, and offered the
// templates for what it is about.
//
// Frappe signs with the writer's own User signature first and the address's
// only when they have none, so a reply from sales@ went out signed as the
// person rather than as sales@. A shared address signs the same whoever
// writes from it; the writer's own signature is for their own address. The
// server's second signature, added after the composer closed, is held off in
// one_mail/outbound.py `file_sent`.
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

// The composer's templates are the record's: frappe asks its form for the kind,
// and OneMail's composer has no form, so it was offered every template, the
// leave mails in a mail to a customer among them. It asks the record it is
// about instead, and with none, is offered the templates for any record.
// The template is filled in from the record by one/mail_templates.py.
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
