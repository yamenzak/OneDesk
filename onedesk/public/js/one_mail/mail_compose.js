// A mailbox's signature is drawn with tables and inline styles, which the
// editor would flatten, so it stays out of the editor: it shows under it, as
// the mail client will show it, and goes in above the quoted mail as it is
// sent. Remove leaves it off this one mail.
(() => {
	const Composer = frappe.views && frappe.views.CommunicationComposer;
	if (!Composer || Composer.prototype.one_signed) return;
	const QUOTE = /<(?:div|p)(?:\s[^>]*)?>---<\/(?:div|p)>/i;
	// Signatures belong to the address, so there is none until one is chosen,
	// and frappe's own (the person's, or any mailbox's) is never put in.
	Composer.prototype.get_signature = async function (sender_email) {
		const email = (this.dialog && this.dialog.get_value("sender")) || sender_email || this.sender;
		this.one_show_signature(
			email ? await frappe.xcall("onedesk.one_mail.holders.signature_for", { email }) : null
		);
		return "";
	};
	Composer.prototype.one_show_signature = function (signature) {
		this.one_signature = signature || "";
		const content = this.dialog && this.dialog.fields_dict.content;
		if (!content) return;
		let $shown = content.$wrapper.siblings(".one-compose-signature");
		if (!$shown.length) {
			$shown = $(`<div class="one-compose-signature">
				<iframe sandbox="allow-same-origin" tabindex="-1" aria-hidden="true"></iframe>
				${frappe.ui.button.html({ label: __("Remove"), variant: "ghost", size: "xs" })}
			</div>`).insertAfter(content.$wrapper);
			$shown.find("button").on("click", () => {
				this.one_signature = "";
				$shown.addClass("hide");
			});
		}
		$shown.toggleClass("hide", !this.one_signature);
		if (!this.one_signature) return;
		$shown
			.find("iframe")
			.off("load")
			.on("load", function () {
				this.style.height = `${this.contentDocument.body.scrollHeight}px`;
			})
			.attr("srcdoc", `<style>body{margin:0;padding:8px 0;background:#fff}</style>${frappe.dom.remove_script_and_style(this.one_signature)}`);
	};
	const make = Composer.prototype.make;
	Composer.prototype.make = function () {
		const given = this.sender;
		const made = make.apply(this, arguments);
		const sender = this.dialog && this.dialog.fields_dict.sender;
		// New mail starts from the workspace's Default Outgoing when the writer
		// may send from it (one/boot.py `one_mail_sends_from`).
		const sends_from = frappe.boot.one_mail_sends_from;
		if (sender && !given && sends_from && (this.user_email_accounts || []).includes(sends_from)) {
			this.sender = sends_from;
			this.dialog.set_value("sender", sends_from);
		}
		if (sender) {
			const changed = sender.df.onchange;
			sender.df.onchange = (...args) => {
				if (changed) changed.apply(sender, args);
				this.get_signature(this.dialog.get_value("sender"));
			};
		}
		return made;
	};
	const send = Composer.prototype.send_email;
	Composer.prototype.send_email = function () {
		this.one_sending = true;
		try {
			return send.apply(this, arguments);
		} finally {
			this.one_sending = false;
		}
	};
	const content = Composer.prototype.get_email_content;
	Composer.prototype.get_email_content = function () {
		const said = content.call(this);
		if (!this.one_sending || !this.one_signature) return said;
		const signature = `<br>${this.one_signature}`;
		const at = said.search(QUOTE);
		return at < 0 ? said + signature : said.slice(0, at) + signature + said.slice(at);
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
	const pick = (box && box.sends && box) || sends.find((one) => one.sends_default) || sends[0];
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

// Writing to a colleague who is away says so above the message, and who
// covers for them, as their mailbox would answer (one_mail/rules.py
// who_is_away).
(() => {
	const Composer = frappe.views && frappe.views.CommunicationComposer;
	if (!Composer || Composer.prototype.one_warns_away) return;
	const make = Composer.prototype.make;
	Composer.prototype.make = function () {
		const made = make.apply(this, arguments);
		const dialog = this.dialog;
		if (!dialog || !dialog.fields_dict.content) return made;
		const $note = $(`<div class="one-compose-away hide"></div>`).insertBefore(dialog.fields_dict.content.$wrapper);
		let waiting = null;
		const check = () => {
			clearTimeout(waiting);
			waiting = setTimeout(async () => {
				const emails = ["recipients", "cc", "bcc"]
					.map((name) => dialog.get_value(name) || "")
					.join(",")
					.split(/[,;]/)
					.map((one) => one.trim())
					.filter(Boolean);
				const away = emails.length ? await frappe.xcall("onedesk.one_mail.rules.who_is_away", { emails }) : [];
				$note.toggleClass("hide", !away.length).html(
					away
						.map((one) => {
							const until = frappe.datetime.str_to_user(one.until);
							let said = one.until
								? one.leave
									? __("{0} is on leave until {1}.", [one.name, until])
									: __("{0} is away until {1}.", [one.name, until])
								: __("{0} is away.", [one.name]);
							if (one.covering) said += " " + __("{0} is covering.", [one.covering.name]);
							return `<div>${frappe.utils.icon("plane", "sm")}<span>${frappe.utils.escape_html(said)}</span></div>`;
						})
						.join("")
				);
			}, 400);
		};
		for (const name of ["recipients", "cc", "bcc"]) {
			const field = dialog.fields_dict[name];
			if (!field) continue;
			const changed = field.df.onchange;
			field.df.onchange = (...args) => {
				if (changed) changed.apply(field, args);
				check();
			};
			field.$wrapper.on("blur change", "input", check);
		}
		dialog.$wrapper.one("shown.bs.modal", check);
		return made;
	};
	Composer.prototype.one_warns_away = true;
})();

// A mail being written is kept on the server a moment after each change
// (one_mail/drafts.py), from any mailbox the writer holds, so closing the
// window or the tab loses nothing. Sending or Discard throws it away;
// closing it otherwise says it was kept.
(() => {
	const Composer = frappe.views && frappe.views.CommunicationComposer;
	if (!Composer || Composer.prototype.one_drafts) return;
	const DRAFTS = "onedesk.one_mail.drafts.";
	const WATCHED = ["sender", "recipients", "cc", "bcc", "subject", "content"];
	const make = Composer.prototype.make;
	Composer.prototype.make = function () {
		const made = make.apply(this, arguments);
		const dialog = this.dialog;
		if (!dialog) return made;
		let waiting = null;
		const later = () => {
			clearTimeout(waiting);
			waiting = setTimeout(() => this.one_keep(), 1500);
		};
		for (const name of WATCHED) {
			const field = dialog.fields_dict[name];
			if (!field) continue;
			const changed = field.df.onchange;
			field.df.onchange = (...args) => {
				if (changed) changed.apply(field, args);
				later();
			};
			field.$wrapper.on("input", later);
		}
		dialog.$wrapper.on("hidden.bs.modal", async () => {
			clearTimeout(waiting);
			if (this.one_gone) return;
			await this.one_keep();
			if (this.one_draft) frappe.show_alert({ message: __("Draft saved."), indicator: "green" });
		});
		return made;
	};
	Composer.prototype.one_keep = async function () {
		if (this.one_gone || !this.dialog) return;
		const values = this.dialog.get_values(true) || {};
		const content = this.dialog.get_value("content") || "";
		const typed = (values.recipients || values.subject || frappe.utils.html2text(content).trim());
		if (!values.sender || (!typed && !this.one_draft)) return;
		const record = this.doc || (this.frm && this.frm.doc) || {};
		const chosen = this.selected_attachments || new Set();
		const files = (this.get_available_attachments ? this.get_available_attachments() : []).filter((one) => chosen.has(one.name));
		this.one_saving = frappe
			.xcall(DRAFTS + "save", {
				sender: values.sender,
				name: this.one_draft || null,
				subject: values.subject || "",
				recipients: values.recipients || "",
				cc: values.cc || "",
				bcc: values.bcc || "",
				content,
				in_reply_to: (this.last_email && this.last_email.name) || null,
				kind: this.is_a_reply ? "Reply" : this.forward ? "Forward" : "New",
				reference_doctype: record.doctype || null,
				reference_name: record.name || null,
				send_after: values.send_after || null,
				attachments: JSON.stringify(files.map((one) => ({ name: one.name, file_name: one.file_name, file_url: one.file_url }))),
			})
			.then((name) => (this.one_draft = name || this.one_draft))
			.catch(() => null);
		return this.one_saving;
	};
	const clear = Composer.prototype.clear_cache;
	Composer.prototype.clear_cache = function () {
		this.one_gone = true;
		const done = clear.apply(this, arguments);
		Promise.resolve(this.one_saving).then(() => this.one_draft && frappe.xcall(DRAFTS + "discard", { name: this.one_draft }));
		return done;
	};
	Composer.prototype.one_drafts = true;
})();

// A draft opened again, where it was left.
onedesk.mail.open_draft = async (name) => {
	const said = await frappe.xcall("onedesk.one_mail.drafts.get", { name });
	const last_email = said.in_reply_to ? await frappe.xcall("onedesk.one_mail.drafts.replying_to", { name }) : null;
	const composer = new frappe.views.CommunicationComposer({
		sender: said.sender,
		recipients: said.recipients || "",
		cc: said.cc || "",
		bcc: said.bcc || "",
		subject: said.subject || "",
		message: said.content || "",
		doc: said.reference_doctype && said.reference_name ? { doctype: said.reference_doctype, name: said.reference_name } : undefined,
		is_a_reply: said.kind === "Reply",
		forward: said.kind === "Forward",
		...(last_email ? { last_email } : {}),
	});
	composer.one_draft = name;
	if (said.attachments.length) {
		composer.attachments = said.attachments;
		composer.selected_attachments = new Set(said.attachments.map((one) => one.name));
		composer.render_attachment_rows && composer.render_attachment_rows();
	}
	if (said.send_after) composer.dialog.set_value("send_after", said.send_after);
	return composer;
};
