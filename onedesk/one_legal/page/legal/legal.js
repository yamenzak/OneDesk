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
	}

	// Drawn as a docview: "Agreements / Privacy Policy" in the breadcrumb,
	// its version in the pill, the text in the main column, and the other
	// documents in frappe's form sidebar.
	async show() {
		if (!this.catalogue) this.catalogue = await frappe.xcall("onedesk.one_legal.reading.catalogue", {}, "GET");
		const asked = frappe.utils.get_query_params();
		this.key = asked.document || this.catalogue.documents[0].key;
		const said = await frappe.xcall("onedesk.one_legal.reading.document", { key: this.key, version: asked.version || "" }, "GET");
		const esc = frappe.utils.escape_html;
		this.page.clear_inner_toolbar();
		const documents = this.catalogue.documents
			.map((one) =>
				one.key === this.key
					? `<div class="ol-here">${esc(__(one.title))}</div>`
					: `<a class="one-record-link ol-other" href="/desk/legal?document=${encodeURIComponent(one.key)}">${esc(__(one.title))}</a>`
			)
			.join("");
		const $main = onedesk.shell.record(onedesk.shell.body(this.page.$shell), {
			page: this.page,
			parent: __("Agreements"),
			route: "/desk/settings?section=agreements",
			title: said.title,
			status: said.historic ? { label: __("As Agreed, {0}", [said.version]), colour: "orange" } : { label: __("Version {0}", [said.version]), colour: "blue" },
			side: onedesk.shell.side({
				mark: "scale",
				title: said.title,
				sub: esc(`${said.party.legal_name} · ${said.party.email}`),
				groups: [{ label: __("Documents"), html: documents }],
				meta: [said.historic ? __("The text as it was agreed to") : __("The current text")],
			}),
		});
		// The breadcrumb names it, as a form's does: the text starts under it.
		$main.html(`<article class="ol-document">${said.html.replace(/<h1[^>]*>[\s\S]*?<\/h1>/, "")}</article>`);
	}
};
