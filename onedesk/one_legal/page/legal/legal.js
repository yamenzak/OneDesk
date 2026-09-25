// The agreements, to read: the current text of each, or the exact text of a
// version somebody agreed to (?document=terms&version=1.4ca1a130). Open to
// everybody signed in, and never behind the agreement dialog, because a person
// asked to agree to something has to be able to read it first.

frappe.pages["legal"].on_page_load = (wrapper) => {
	const page = onedesk.shell.page(wrapper, __("Agreements"));
	wrapper.reader = new onedesk.legal.Reader(page);
};

frappe.pages["legal"].on_page_show = (wrapper) => wrapper.reader && wrapper.reader.show();

onedesk.legal.Reader = class Reader {
	constructor(page) {
		this.page = page;
		// The text is read in the shell's column, as a record is.
		this.$body = $(`<article class="ol-document"></article>`).appendTo(onedesk.shell.body(page.$shell).empty());
		this.picker = page.add_field({
			fieldname: "document",
			fieldtype: "Select",
			label: __("Document"),
			change: () => {
				const key = this.picker.get_value();
				if (key && key !== this.key) frappe.set_route("legal", { document: key });
			},
		});
	}

	async show() {
		if (!this.catalogue) this.catalogue = await frappe.xcall("onedesk.one_legal.reading.catalogue", {}, "GET");
		const asked = frappe.utils.get_query_params();
		this.key = asked.document || this.catalogue.documents[0].key;
		this.picker.df.options = this.catalogue.documents.map((one) => ({ value: one.key, label: __(one.title) }));
		this.picker.refresh();
		this.picker.set_value(this.key);
		const said = await frappe.xcall("onedesk.one_legal.reading.document", { key: this.key, version: asked.version || "" }, "GET");
		onedesk.shell.name(said.title);
		const esc = frappe.utils.escape_html;
		// The version goes under the title: which text this is, before any of it.
		const meta = `<div class="ol-meta">${esc(__("Version {0}", [said.version]))}${
			said.historic ? ` · ${esc(__("the text as it was agreed to"))}` : ""
		}</div>`;
		this.$body.html(`${said.html.replace("</h1>", `</h1>${meta}`)}<p class="ol-party">${esc(said.party.legal_name)} · ${esc(said.party.email)}</p>`);
	}
};
