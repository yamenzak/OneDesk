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

// A reply and a forward of a conversation, written into frappe's composer:
// for OneMail and for OneAI's reply card, which approves a reply OneAI wrote.
frappe.provide("onedesk.mail");

onedesk.mail.sender = (boxes, box) => {
	const sends = boxes.filter((one) => one.sends);
	const pick = (box && box.sends && box) || sends.find((one) => one.workspace) || sends[0];
	return pick ? pick.email : null;
};

onedesk.mail.record_of = (messages) => {
	const record = messages.find((one) => one.reference_doctype && one.reference_name);
	return record ? { doctype: record.reference_doctype, name: record.reference_name } : undefined;
};

onedesk.mail.reply = (boxes, messages, sender, { all = false, text = "" } = {}) => {
	const message = messages[messages.length - 1];
	const subject = message.subject || "";
	const mine = boxes.map((one) => one.email.toLowerCase());
	const others = (list) =>
		(list || "")
			.split(",")
			.map((one) => one.trim())
			.filter((one) => one && !mine.some((me) => one.toLowerCase().includes(me)));
	const from_me = mine.includes((message.sender || "").toLowerCase());
	const recipients = from_me ? message.recipients : message.sender;
	const cc = all ? [...others(message.recipients), ...others(message.cc)].filter((one) => !recipients.includes(one)).join(", ") : "";
	const esc = frappe.utils.escape_html;
	const written = (text || "")
		.split(/\n{2,}/)
		.map((one) => `<p>${esc(one.trim()).replace(/\n/g, "<br>")}</p>`)
		.join("");
	return new frappe.views.CommunicationComposer({
		sender,
		doc: onedesk.mail.record_of(messages),
		subject: /^re:/i.test(subject) ? subject : `Re: ${subject}`,
		recipients,
		cc,
		is_a_reply: true,
		last_email: message,
		...(written ? { message: written } : {}),
	});
};

onedesk.mail.forward = (messages, sender, when) => {
	const message = messages[messages.length - 1];
	const subject = message.subject || "";
	const esc = frappe.utils.escape_html;
	const header = `<p><br></p><p>${__("Forwarded message")}<br>${__("From")}: ${esc(message.sender)}<br>${__("Date")}: ${esc(when)}<br>${__(
		"Subject"
	)}: ${esc(subject)}<br>${__("To")}: ${esc(message.recipients || "")}</p>`;
	return new frappe.views.CommunicationComposer({
		sender,
		doc: onedesk.mail.record_of(messages),
		subject: /^fwd?:/i.test(subject) ? subject : `Fwd: ${subject}`,
		forward: true,
		message: header + `<blockquote>${message.content || ""}</blockquote>`,
	});
};

onedesk.mail.reply_to = async (account, thread, { text = "" } = {}) => {
	const [boxes, said] = await Promise.all([
		frappe.xcall("onedesk.one_mail.api.mailboxes"),
		frappe.xcall("onedesk.one_mail.api.conversation", { account, thread }),
	]);
	const sender = onedesk.mail.sender(boxes, boxes.find((one) => one.name === account));
	if (!sender) return frappe.msgprint(__("None of your mailboxes can send email"));
	return onedesk.mail.reply(boxes, said.messages, sender, { text });
};
