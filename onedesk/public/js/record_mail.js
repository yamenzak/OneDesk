// Mail on a record: a tab beside Files listing the conversations filed on it
// (one_mail/linking.py), and a way to write from it. Only the messages the
// reader may open are listed, since a link never grants read. A
// conversation opens in OneMail; writing uses the desk's own composer on
// the record, which files what is sent against it.
//
// Added to the layout, not to any doctype, as the Files tab is
// (record_files.js), and only on the records mail is about.
frappe.provide("onedesk.record_mail");

onedesk.record_mail.TAB = "__one_mail_tab";
onedesk.record_mail.FIELD = "__one_mail";

onedesk.record_mail.DOCTYPES = [
	"Customer", "Supplier", "Lead", "Contact", "Employee", "Opportunity", "Project", "Issue", "Job Applicant",
	"Quotation", "Sales Order", "Sales Invoice", "Purchase Order", "Purchase Invoice", "Supplier Quotation",
];

(() => {
	const Layout = frappe.ui.form.Layout;
	const fields_of = Layout.prototype.get_doctype_fields;
	Layout.prototype.get_doctype_fields = function () {
		const fields = fields_of.call(this);
		const frm = this.frm;
		if (!frm || this.is_child_table || this.doctype !== frm.doctype || !onedesk.record_mail.DOCTYPES.includes(frm.doctype)) return fields;
		const mail = [
			{ fieldtype: "Tab Break", fieldname: onedesk.record_mail.TAB, label: __("Mail") },
			{ fieldtype: "HTML", fieldname: onedesk.record_mail.FIELD },
		];
		// Beside Files, before it.
		const files = fields.findIndex((one) => one.fieldname === "__one_files_tab");
		files < 0 ? fields.push(...mail) : fields.splice(files, 0, ...mail);
		return fields;
	};
})();

onedesk.record_mail.tab = (frm) =>
	((frm.layout && frm.layout.tabs) || []).find((one) => one.df.fieldname === onedesk.record_mail.TAB);

onedesk.record_mail.open = async (frm) => {
	const field = frm.fields_dict[onedesk.record_mail.FIELD];
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
			return `<a class="om-row om-record-row" href="${esc(href)}">
				<div class="om-row-text">
					<div class="om-row-top"><span class="om-who">${esc(who || "")}</span>${row.count > 1 ? `<span class="om-thread-count">${row.count}</span>` : ""}
						<span class="om-when">${row.attachments ? frappe.utils.icon("paperclip", "xs") : ""}${esc(when(row.date))}</span></div>
					<div class="om-subject">${esc(row.subject || __("(no subject)"))}</div>
					<div class="om-snippet">${esc(row.snippet || "")}</div>
				</div>
			</a>`;
		})
		.join("");
	field.$wrapper.html(`<div class="om-record">
		<div class="om-record-head">
			<button class="es-button" data-variant="subtle" data-act="write">${frappe.utils.icon("pencil", "sm")}<span class="es-button__label">${__("Write")}</span></button>
		</div>
		${list || `<div class="om-none">${__("No mail is filed on this yet. Mail from its people is filed here as it arrives.")}</div>`}
	</div>`);
	field.$wrapper.find("[data-act=write]").on("click", () => {
		const composer = new frappe.views.CommunicationComposer({ frm, doc: frm.doc });
		composer.dialog.$wrapper.on("hidden.bs.modal", () => setTimeout(() => onedesk.record_mail.open(frm), 1500));
	});
	const tab = onedesk.record_mail.tab(frm);
	const $link = tab && tab.tab_link.find(".nav-link");
	if ($link) {
		$link.find(".one-files-count").remove();
		if (rows.length) $link.append(`<span class="one-files-count">${rows.length}</span>`);
	}
};

frappe.ui.form.on("*", {
	refresh(frm) {
		const tab = onedesk.record_mail.tab(frm);
		if (!tab) return;
		tab.df.hidden = frm.is_new() ? 1 : 0;
		frm.layout.refresh_tabs();
		if (frm.is_new()) return;
		const $link = tab.tab_link.find(".nav-link");
		if (!$link.data("one-mail")) $link.data("one-mail", 1).on("click", () => onedesk.record_mail.open(frm));
		if (tab.is_active && tab.is_active()) onedesk.record_mail.open(frm);
	},
});
