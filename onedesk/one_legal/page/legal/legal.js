frappe.pages["legal"].on_page_load = (wrapper) => {
	const page = onedesk.shell.page(wrapper, __("Agreements"));
	wrapper.reader = new onedesk.legal.Reader(page);
};

frappe.pages["legal"].on_page_show = (wrapper) => wrapper.reader && wrapper.reader.show();

// Three panes, as OneCloud and OneMail are: the documents and where each
// stands, the one open, and who agreed to it and when.
onedesk.legal.Reader = class Reader {
	constructor(page) {
		this.page = page;
		const panes = onedesk.shell.panes(page.$shell, [{ key: "list", width: 280 }, { key: "text" }, { key: "about", width: 300 }]);
		this.$list = $(`<nav class="ol-list" aria-label="${__("Documents")}"></nav>`).appendTo(panes.list);
		this.$head = onedesk.shell.pane_head(panes.text);
		this.$text = $(`<article class="ol-document"></article>`).appendTo(panes.text);
		this.$about = $(`<div class="ol-about"></div>`).appendTo(panes.about.addClass("ol-about-pane"));
		this.$list.on("click", "[data-key]", (e) => {
			e.preventDefault();
			frappe.set_route("legal", { document: $(e.currentTarget).attr("data-key") });
		});
		$(document).on("legal-agreed", () => this.page.wrapper.is(":visible") && this.show(true));
	}

	async show(fresh = false) {
		if (!this.said || fresh) this.said = await frappe.xcall("onedesk.one_legal.reading.overview", {}, "GET");
		const asked = frappe.utils.get_query_params();
		const docs = this.said.documents;
		this.doc = docs.find((one) => one.key === asked.document) || docs.find((one) => this.owed(one)) || docs[0];
		this.version = asked.version || "";
		this.draw_list();
		const read = await frappe.xcall("onedesk.one_legal.reading.document", { key: this.doc.key, version: this.version }, "GET");
		const history = await frappe.xcall("onedesk.one_legal.reading.history", { key: this.doc.key }, "GET");
		onedesk.shell.trail(__("Agreements"), "/desk/legal", read.title, [], null, this.page);
		this.draw_head(read);
		this.$text.html(read.html.replace(/<h1[^>]*>[\s\S]*?<\/h1>/, ""));
		this.$text.parent().scrollTop(0);
		this.draw_about(read, history);
	}

	owed(doc) {
		return Boolean((doc.you && doc.you.owed) || (this.said.may_bind && doc.organisation && doc.organisation.owed));
	}

	state(doc) {
		const sides = [doc.you, this.said.may_bind || this.said.admin ? doc.organisation : null].filter(Boolean);
		if (!sides.length) return null;
		if (sides.some((one) => one.owed && one.version)) return { label: __("Updated"), theme: "orange" };
		if (this.owed(doc)) return { label: __("To Agree"), theme: "orange" };
		if (sides.some((one) => one.owed)) return { label: __("Waiting"), theme: "gray" };
		return { label: __("Agreed"), theme: "green" };
	}

	draw_list() {
		const esc = frappe.utils.escape_html;
		const docs = this.said.documents;
		const groups = [
			[__("For You"), docs.filter((one) => one.you)],
			[__("For Your Organisation"), docs.filter((one) => !one.you && one.organisation)],
			[__("To Read"), docs.filter((one) => !one.you && !one.organisation)],
		].filter(([, rows]) => rows.length);
		this.$list.html(
			groups
				.map(
					([label, rows]) =>
						`<div class="ol-list-group">${esc(label)}</div>` +
						onedesk.shell.list(
							rows
								.map((one) => {
									const state = this.state(one);
									return onedesk.shell.row({
										title: esc(one.title),
										meta: state ? frappe.ui.badge.html(state) : "",
										href: `/desk/legal?document=${encodeURIComponent(one.key)}`,
										attrs: { "data-key": one.key },
										active: one.key === this.doc.key,
									});
								})
								.join("")
						)
				)
				.join("")
		);
	}

	draw_head(read) {
		const esc = frappe.utils.escape_html;
		const version = read.historic
			? frappe.ui.badge.html({ label: __("As Agreed, {0}", [read.version]), theme: "orange" })
			: frappe.ui.badge.html({ label: __("Version {0}", [read.version]), theme: "gray" });
		this.$head.html(`<div class="ol-head-title"><span>${esc(read.title)}</span>${version}</div><div class="ol-head-actions"></div>`);
		const $actions = this.$head.find(".ol-head-actions");
		if (read.historic) {
			frappe.ui
				.button({ label: __("Current Version"), variant: "subtle", onclick: () => frappe.set_route("legal", { document: this.doc.key }) })
				.appendTo($actions);
		} else if (this.owed(this.doc)) {
			frappe.ui.button({ label: __("Agree"), variant: "solid", onclick: () => this.agree() }).appendTo($actions);
		}
	}

	async agree() {
		const next = await frappe.xcall("onedesk.one_legal.gate.accept", { documents: [this.doc.key] });
		frappe.show_alert({ message: __("Agreed to {0}", [__(this.doc.title)]), indicator: "green" });
		if (next.ok && onedesk.legal.dialog) {
			onedesk.legal.dialog.hide();
			onedesk.legal.dialog = null;
		}
		$(document).trigger("legal-agreed");
	}

	draw_about(read, history) {
		const esc = frappe.utils.escape_html;
		const doc = this.doc;
		const line = (side, whose) => {
			if (!side) return "";
			const label = whose === "organisation" ? __("Your Organisation") : __("You");
			let said;
			if (!side.version) said = side.owed && whose === "organisation" && !this.said.may_bind ? __("Waiting for an administrator") : __("Not agreed yet");
			else if (whose === "organisation") said = __("{0} agreed on {1}", [side.by, side.on]);
			else said = __("Agreed on {0}", [side.on]);
			const earlier = side.version && side.version !== side.current
				? `<a class="ol-earlier" href="/desk/legal?document=${encodeURIComponent(doc.key)}&version=${encodeURIComponent(side.version)}">${esc(__("Read version {0}", [side.version]))}</a>`
				: "";
			return `<div class="ol-fact"><div class="ol-fact-label">${esc(label)}</div><div>${esc(said)}</div>${earlier}</div>`;
		};
		const versions = (history || [])
			.filter((one) => one.version !== doc.version)
			.map(
				(one) =>
					`<a class="ol-earlier${one.version === this.version ? " is-active" : ""}" href="/desk/legal?document=${encodeURIComponent(doc.key)}&version=${encodeURIComponent(one.version)}">${esc(
						__("Version {0}", [one.version])
					)}</a>`
			)
			.join("");
		const party = this.said.party || {};
		this.$about.html(
			`<div class="ol-about-mark">${frappe.utils.icon("scale", "xl")}</div>
			<div class="ol-about-title">${esc(read.title)}</div>
			${doc.you || doc.organisation ? `<div class="ol-about-section">${line(doc.you, "you")}${line(doc.organisation, "organisation")}</div>` : `<div class="ol-about-section one-shell-quiet">${esc(__("Nobody has to agree to this. It is here to read."))}</div>`}
			${versions ? `<div class="ol-about-section"><div class="ol-fact-label">${esc(__("Earlier Versions"))}</div>${versions}</div>` : ""}
			<div class="ol-about-section"><div class="ol-fact-label">${esc(__("From"))}</div><div>${esc(party.legal_name || "")}</div><a href="mailto:${esc(party.email || "")}">${esc(party.email || "")}</a></div>
			${this.said.admin ? `<div class="ol-about-section"><a class="ol-earlier" href="/desk/legal-acceptance">${esc(__("Everyone's Agreements"))}</a></div>` : ""}`
		);
	}
};
