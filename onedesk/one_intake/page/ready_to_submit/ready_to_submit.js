// Ready to submit: every draft OneAI made that the reader may post, the ready
// ones with Submit all and the red ones apart with what is wrong. The server
// decides what is ready and submits as the reader (one_intake/drafts.py).

frappe.pages["ready-to-submit"].on_page_load = (wrapper) => {
	const page = onedesk.shell.page(wrapper, __("Ready to Submit"));
	wrapper.ready = new onedesk.ReadyToSubmit(page);
};

frappe.pages["ready-to-submit"].on_page_show = (wrapper) => wrapper.ready && wrapper.ready.load();

frappe.provide("onedesk");

onedesk.ReadyToSubmit = class ReadyToSubmit {
	constructor(page) {
		this.page = page;
		// Tables, so the shell's wide body.
		this.$body = onedesk.shell.body(page.$shell, { wide: true });
		this.page.set_primary_action(__("Submit All"), () => this.submit(), "check-check");
	}

	async load() {
		this.said = await frappe.xcall("onedesk.one_intake.drafts.listed");
		this.draw();
	}

	draw() {
		const esc = frappe.utils.escape_html;
		const { ready, red } = this.said;
		const row = (one, tone) => {
			const from = one.document && one.document.route ? `<a href="${esc(one.document.route)}">${esc(one.document.label || one.title || "")}</a>` : esc(one.title || "");
			const why = (one.red || []).map((line) => `<div class="oi-red-why">${esc(line)}</div>`).join("");
			return `<tr data-tone="${tone}">
				<td>${tone === "ready" ? `<input type="checkbox" checked data-doctype="${esc(one.doctype)}" data-name="${esc(one.name)}">` : ""}</td>
				<td><a href="/desk/${frappe.router.slug(one.doctype)}/${encodeURIComponent(one.name)}">${esc(__(one.doctype))} ${esc(one.name)}</a>${why}</td>
				<td>${esc(one.party || "")}</td>
				<td>${one.date ? frappe.datetime.str_to_user(one.date) : ""}</td>
				<td class="text-right">${format_currency(one.total, one.currency)}</td>
				<td>${from}</td>
			</tr>`;
		};
		const table = (rows, tone) =>
			`<table class="table oi-ready-table"><thead><tr><th></th><th>${__("Draft")}</th><th>${__("Party")}</th><th>${__("Date")}</th><th class="text-right">${__("Total")}</th><th>${__("Document")}</th></tr></thead>
			<tbody>${rows.map((one) => row(one, tone)).join("")}</tbody></table>`;
		const count = (n) => frappe.ui.badge.html({ label: String(n), size: "sm" });
		this.$body.html(
			onedesk.shell.section(
				__("Ready"),
				ready.length ? table(ready, "ready") : onedesk.shell.empty(__("Nothing is waiting to be submitted."), null, { icon: "check-check" }),
				__("Drafts OneAI made whose facts checked out, whose party is known and whose totals match the document, and the order and receipt where there are some."),
				ready.length ? count(ready.length) : ""
			) + (red.length ? onedesk.shell.section(__("Needs a Look First"), table(red, "red"), null, count(red.length)) : "")
		);
		this.page.btn_primary.prop("disabled", !ready.length);
	}

	submit() {
		const names = this.$body.find("input[data-name]:checked").map((_, el) => [[el.dataset.doctype, el.dataset.name]]).get();
		if (!names.length) return;
		frappe.confirm(__("Submit {0} drafts?", [names.length]), async () => {
			const said = await frappe.xcall("onedesk.one_intake.drafts.submit_all", { names });
			if (said.failed.length) {
				frappe.msgprint({
					title: __("Some were not submitted"),
					message: said.failed.map((one) => `<div>${frappe.utils.escape_html(one.name)}: ${frappe.utils.escape_html(one.why)}</div>`).join(""),
				});
			} else {
				frappe.show_alert({ message: __("{0} submitted.", [said.done.length]), indicator: "green" });
			}
			this.load();
		});
	}
};
