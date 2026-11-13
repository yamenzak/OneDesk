// "Open in OneDoc" under every Text Editor field on a saved record: the
// text becomes a document filed on the record, and what is written there
// goes back into the field through the record's save (one_doc/field.py).
frappe.provide("onedesk.text_writer");

onedesk.text_writer.open = (frm, field) => {
	if (frm.is_dirty()) {
		frappe.msgprint(__("Save the record before opening its text in a document."));
		return;
	}
	frappe
		.call({ method: "onedesk.one_doc.field.open_field", args: { doctype: frm.doctype, name: frm.doc.name, field }, freeze: true })
		.then((r) => r.message && frappe.set_route("document", r.message));
};

frappe.ui.form.on("*", {
	refresh(frm) {
		if (frm.is_new() || frm.meta.istable || frm.meta.issingle) return;
		for (const df of frm.meta.fields) {
			const control = df.fieldtype === "Text Editor" && !df.read_only && !df.hidden && frm.fields_dict[df.fieldname];
			const $wrapper = control?.$wrapper;
			if (!$wrapper || $wrapper.find(".one-open-writer").length) continue;
			frappe.ui
				.button({ label: __("Open in {0}", [onedesk.names.of("one_doc")]), css_class: "mt-2 one-open-writer", onclick: () => onedesk.text_writer.open(frm, df.fieldname) })
				.appendTo($wrapper.find(".form-group").first());
		}
	},
});
