// Frappe's email composer, signed as the address it sends from.
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
