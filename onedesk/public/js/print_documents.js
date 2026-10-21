// The record's print page, from page_js: under the letter head picker, the
// documents written on the record (one_doc/paper.py, on_record). Each prints
// as a PDF under the letter head chosen here, its fields filled from the
// record.
frappe.provide("onedesk.print_documents");

onedesk.print_documents.draw = (view) => {
	view.sidebar.find(".one-print-documents").remove();
	const frm = view.frm;
	if (!frm?.doctype || !frm.docname) return;
	frappe.xcall("onedesk.one_doc.paper.on_record", { doctype: frm.doctype, name: frm.docname }).then((found) => {
		if (!found?.length || view.frm !== frm) return;
		const $box = $(`<div class="one-print-documents form-group">
			<label class="control-label">${__("Documents")}</label>
			<div class="flex flex-col items-start gap-1"></div>
		</div>`).insertBefore(view.sidebar_dynamic_section);
		for (const one of found) {
			frappe.ui
				.button({ label: one.title, icon: "file-text", variant: "ghost", onclick: () => onedesk.print_documents.print(view, one.document) })
				.appendTo($box.find("div"));
		}
	});
};

onedesk.print_documents.print = (view, document) =>
	open_url_post("/api/method/onedesk.one_doc.paper.pdf", { name: document, letter_head: view.letterhead_selector.val() || "none" }, true);

if (frappe.ui.form.PrintView) {
	const show = frappe.ui.form.PrintView.prototype.show;
	frappe.ui.form.PrintView.prototype.show = function (frm) {
		const out = show.call(this, frm);
		onedesk.print_documents.draw(this);
		return out;
	};
}
