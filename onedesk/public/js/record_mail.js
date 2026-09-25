// Mail on a record: a tab beside Files listing the conversations filed on it
// (one_mail/linking.py), and a way to write from it. Only the messages the
// reader may open are listed, since a link never grants read. A
// conversation opens in OneMail; writing uses the desk's own composer on
// the record, which files what is sent against it.
//
// Declared in one_mail/linking.py, with the records mail is about, and
// drawn here, as every record tab is (record_tabs.js).
frappe.provide("onedesk.record_mail");

// The records mail is about, as linking.py declares them.
onedesk.record_mail.doctypes = () =>
	(onedesk.record_tabs.declared().find((tab) => tab.name === "mail") || {}).doctypes || [];

onedesk.record_mail.tab = (frm) => onedesk.record_tabs.tab(frm, "mail");

onedesk.record_mail.open = async (frm) => {
	const field = frm.fields_dict[onedesk.record_tabs.FIELD("mail")];
	if (!field || frm.is_new()) return;
	await frappe.require("/assets/onedesk/css/onemail.css");
	const esc = frappe.utils.escape_html;
	const rows = await frappe.xcall("onedesk.one_mail.linking.record", { doctype: frm.doctype, name: frm.doc.name });
	const when = (value) =>
		value.slice(0, 10) === frappe.datetime.get_today()
			? frappe.datetime.str_to_user(value, true).replace(/(\d{1,2}:\d{2}):\d{2}/, "$1")
			: frappe.datetime.str_to_user(value.slice(0, 10));
	const list = rows
		.map((row) => {
			const who = row.sent ? __("To {0}", [(row.recipients || "").split(",")[0]]) : row.sender_name || row.sender;
			const href = `/app/onemail?box=${encodeURIComponent(row.account)}&thread=${encodeURIComponent(row.thread)}`;
			return onedesk.shell.row({
				href,
				title: `<span class="om-who">${esc(who || "")}</span>${row.count > 1 ? `<span class="om-thread-count">${row.count}</span>` : ""}<span class="om-when">${
					row.attachments ? frappe.utils.icon("paperclip", "xs") : ""
				}${esc(when(row.date))}</span>`,
				sub: `<span class="om-subject">${esc(row.subject || __("(no subject)"))}</span>`,
				quiet: esc(row.snippet || ""),
			});
		})
		.join("");
	field.$wrapper.html(`<div class="om-record">
		<div class="om-record-head">
			<button class="es-button" data-variant="subtle" data-act="write">${frappe.utils.icon("pencil", "sm")}<span class="es-button__label">${__("Write")}</span></button>
		</div>
		${list ? onedesk.shell.list(list) : onedesk.shell.empty(__("No mail is filed on this yet."), __("Mail from its people is filed here as it arrives."), { icon: "mail" })}
	</div>`);
	field.$wrapper.find("[data-act=write]").on("click", () => {
		const composer = new frappe.views.CommunicationComposer({ frm, doc: frm.doc });
		composer.dialog.$wrapper.on("hidden.bs.modal", () => setTimeout(() => onedesk.record_mail.open(frm), 1500));
	});
	onedesk.record_tabs.count(frm, "mail", rows.length);
};

onedesk.record_tabs.register("mail", { open: (frm) => onedesk.record_mail.open(frm) });
