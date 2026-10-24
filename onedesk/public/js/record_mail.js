frappe.provide("onedesk.record_mail");

onedesk.record_mail.doctypes = () =>
	(onedesk.record_tabs.declared().find((tab) => tab.name === "mail") || {}).doctypes || [];

onedesk.record_mail.tab = (frm) => onedesk.record_tabs.tab(frm, "mail");

onedesk.record_mail.open = async (frm, $into = null) => {
	const field = frm.fields_dict[onedesk.record_tabs.FIELD("mail")];
	const $wrapper = $into || (field && field.$wrapper);
	if (!$wrapper || !$wrapper.length || frm.is_new()) return;
	await frappe.require("/assets/onedesk/css/record_mail.css");
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
	$wrapper.html(`<div class="om-record">
		<div class="om-record-head">
			<button class="es-button" data-variant="subtle" data-act="write">${frappe.utils.icon("pencil", "sm")}<span class="es-button__label">${__("New Email")}</span></button>
		</div>
		${list ? onedesk.shell.list(list) : onedesk.shell.empty(__("No emails"), "", { icon: "mail" })}
	</div>`);
	$wrapper.find("[data-act=write]").on("click", () => {
		const composer = new frappe.views.CommunicationComposer({ frm, doc: frm.doc });
		composer.dialog.$wrapper.on("hidden.bs.modal", () => setTimeout(() => onedesk.record_mail.open(frm, $into), 1500));
	});
	onedesk.record_tabs.count(frm, "mail", rows.length);
};

onedesk.record_tabs.register("mail", {
	wanted: (frm) => !(onedesk.window.panelled && onedesk.window.panelled(frm)),
	open: (frm) => onedesk.record_mail.open(frm),
});
