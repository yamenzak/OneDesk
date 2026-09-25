// Intake: what OneAI did with what arrived, and what waits for you, as two
// boxes that work like a mailbox. The server decides what is in each and who
// has seen what (one_intake/inbox.py); this draws it.

frappe.pages["intake"].on_page_load = (wrapper) => {
	const page = frappe.ui.make_app_page({ parent: wrapper, title: __("Intake"), single_column: true });
	wrapper.inbox = new onedesk.IntakeInbox(page);
};

frappe.pages["intake"].on_page_show = (wrapper) => wrapper.inbox && wrapper.inbox.show();

frappe.provide("onedesk");

onedesk.IntakeInbox = class IntakeInbox {
	constructor(page) {
		this.page = page;
		this.box = "waiting";
		this.everyone = 0;
		this.items = [];
		this.$body = $(`<div class="oi-inbox">
			<div class="oi-inbox-list">
				<div class="oi-inbox-tabs">
					<button class="oi-inbox-tab" data-box="waiting">${__("Waiting")} <span class="oi-inbox-n" data-n="waiting"></span></button>
					<button class="oi-inbox-tab" data-box="done">${__("Done")}</button>
				</div>
				<div class="oi-inbox-rows"></div>
				<div class="oi-inbox-more hide"><button class="btn btn-xs btn-default">${__("More")}</button></div>
			</div>
			<div class="oi-inbox-read"><div class="oi-empty">${__("Pick a document to see what OneAI did with it.")}</div></div>
		</div>`).appendTo(page.main);
		this.$rows = this.$body.find(".oi-inbox-rows");
		this.$read = this.$body.find(".oi-inbox-read");
		this.$body.find("[data-box]").on("click", (event) => this.open_box($(event.currentTarget).attr("data-box")));
		this.$body.find(".oi-inbox-more button").on("click", () => this.load(this.items.length));
		this.page.add_inner_button(__("Mark All as Read"), () => this.seen_all());
		if (frappe.user.has_role("Workspace Administrator")) {
			this.$everyone = this.page.add_field({
				fieldname: "everyone",
				fieldtype: "Check",
				label: __("Everybody's"),
				change: () => {
					this.everyone = this.$everyone.get_value() ? 1 : 0;
					this.load();
				},
			});
		}
		frappe.realtime.on("intake_inbox", () => this.load());
	}

	show() {
		const asked = frappe.utils.get_query_params();
		if (asked.box) this.box = asked.box === "done" ? "done" : "waiting";
		this.load().then(() => asked.reading && this.read(asked.reading));
	}

	open_box(box) {
		this.box = box;
		this.load();
		this.$read.html(`<div class="oi-empty">${__("Pick a document to see what OneAI did with it.")}</div>`);
		this.remember();
	}

	remember(reading) {
		const query = new URLSearchParams({ box: this.box, ...(reading ? { reading } : {}) });
		window.history.replaceState(null, "", `/app/intake?${query}`);
	}

	async load(start = 0) {
		this.$body.find("[data-box]").removeClass("active");
		this.$body.find(`[data-box="${this.box}"]`).addClass("active");
		const said = await frappe.xcall("onedesk.one_intake.inbox.listing", { box: this.box, everyone: this.everyone, start });
		this.items = start ? [...this.items, ...said.items] : said.items;
		this.$body.find(".oi-inbox-more").toggleClass("hide", !said.more);
		this.draw();
		this.counts();
	}

	async counts() {
		const said = await (onedesk.dock && onedesk.dock.intake ? onedesk.dock.intake() : frappe.xcall("onedesk.one_intake.inbox.counts"));
		this.$body.find('[data-n="waiting"]').text(said.waiting || "");
	}

	draw() {
		const esc = frappe.utils.escape_html;
		if (!this.items.length) {
			this.$rows.html(
				`<div class="oi-empty">${this.box === "waiting" ? __("Nothing waits for you. OneAI and its auditor dealt with everything.") : __("Nothing yet.")}</div>`
			);
			return;
		}
		this.$rows.html(
			this.items
				.map(
					(one) => `<button class="oi-inbox-row ${one.unread ? "unread" : ""} ${one.name === this.reading ? "active" : ""}" data-reading="${esc(one.name)}">
					<div class="oi-inbox-row-top">
						<span class="oi-inbox-title">${esc(one.title || "")}</span>
						<span class="oi-quiet oi-inbox-when">${one.when ? esc(frappe.datetime.prettyDate(one.when, true)) : ""}</span>
					</div>
					<div class="oi-inbox-row-sub">
						${one.kind ? `<span class="oi-chip">${esc(one.kind)}</span>` : ""}
						${one.waiting ? `<span class="oi-chip" data-tone="orange">${esc(__("{0} to decide", [one.waiting]))}</span>` : ""}
						${one.done ? `<span class="oi-quiet">${esc(__("{0} done", [one.done]))}</span>` : ""}
						${one.person ? `<span class="oi-quiet">· ${esc(one.person)}</span>` : ""}
					</div>
					${one.summary ? `<div class="oi-inbox-summary">${esc(one.summary)}</div>` : ""}
				</button>`
				)
				.join("")
		);
		this.$rows.find("[data-reading]").on("click", (event) => this.read($(event.currentTarget).attr("data-reading")));
	}

	async read(reading) {
		this.reading = reading;
		this.remember(reading);
		this.$rows.find("[data-reading]").removeClass("active");
		this.$rows.find(`[data-reading="${CSS.escape(reading)}"]`).addClass("active").removeClass("unread");
		let said;
		try {
			said = await frappe.xcall("onedesk.one_intake.inbox.item", { name: reading });
		} catch (e) {
			this.$read.html(`<div class="oi-empty">${__("That is no longer here.")}</div>`);
			return;
		}
		const one = this.items.find((row) => row.name === reading);
		if (one) one.unread = false;
		this.$read.html(this.pane(said));
		this.bind(said);
		this.counts();
	}

	pane(said) {
		const esc = frappe.utils.escape_html;
		const open = said.route ? `<a href="${esc(said.route)}">${__("Open the Document")}</a>` : "";
		const rest = { ...said, actions: [], may_decide: false };
		return `<div class="oi-read">
			<div class="oi-read-head">
				<div class="oi-read-title">${esc(said.title || "")}</div>
				<div class="oi-quiet">${[said.kind ? esc(__(said.kind)) : "", said.person ? esc(__("for {0}", [said.person])) : "", open].filter(Boolean).join(" · ")}</div>
			</div>
			${said.summary ? `<div class="oi-summary">${esc(said.summary)}</div>` : ""}
			<div class="oi-title">${__("What OneAI did")}</div>
			<ul class="oi-acts">${(said.actions || []).map((act) => this.act(act, said.may_decide)).join("") || `<li class="oi-quiet">${__("Nothing.")}</li>`}</ul>
			<details class="oi-more"><summary>${__("Everything OneAI read")}</summary><div class="oi-more-body">${onedesk.intake.html(rest)}</div></details>
		</div>`;
	}

	act(act, may) {
		const esc = frappe.utils.escape_html;
		const link = act.record
			? ` · <a href="/desk/${frappe.router.slug(act.record[0])}/${encodeURIComponent(act.record[1])}">${__("Open")}</a>`
			: "";
		const doubted = act.level === "Done" && act.audit === "Wrong";
		const chip = doubted
			? `<span class="oi-chip" data-tone="red">${__("The auditor doubts this")}</span>`
			: act.level === "Proposed"
				? `<span class="oi-chip" data-tone="orange">${__("Needs a look")}</span>`
				: act.level === "Refused"
					? `<span class="oi-chip" data-tone="gray">${__("Not allowed")}</span>`
					: act.by_auditor
						? `<span class="oi-chip" data-tone="green">${__("Approved by the auditor")}</span>`
						: "";
		const change = (act.change || [])
			.map((it) => `<div class="oi-change">${esc(it.field)}: <s>${esc(String(it.from))}</s> → ${esc(String(it.to))}</div>`)
			.join("");
		const why = [act.level !== "Done" ? act.why : "", doubted || act.by_auditor || act.level === "Proposed" ? act.audit_why : ""]
			.filter(Boolean)
			.map((line) => `<div class="oi-quiet">${esc(line)}</div>`)
			.join("");
		const button = (label, data, primary) =>
			`<button class="btn btn-xs ${primary ? "btn-primary" : "btn-default"}" ${data}>${label}</button>`;
		let buttons = "";
		if (may && act.level === "Proposed") {
			buttons = button(__("Apply"), `data-settle="${esc(act.name)}" data-take="1"`, true) + button(__("Dismiss"), `data-settle="${esc(act.name)}" data-take="0"`);
		} else if (may && act.level === "Done") {
			buttons = (doubted ? button(__("Keep"), `data-keep="${esc(act.name)}"`, true) : "") + button(__("Undo"), `data-undo-one="${esc(act.name)}"`);
		}
		return `<li class="oi-act">
			<div class="oi-act-line"><span>${chip} ${esc(act.said)}${link}</span>${buttons ? `<span class="oi-buttons">${buttons}</span>` : ""}</div>
			${change}${why}
		</li>`;
	}

	bind(said) {
		const again = () => this.read(said.name).then(() => this.load());
		this.$read.find("[data-settle]").on("click", async (event) => {
			const $button = $(event.currentTarget);
			$button.prop("disabled", true);
			await frappe.xcall("onedesk.one_intake.act.settle", { action: $button.attr("data-settle"), take: $button.attr("data-take") });
			again();
		});
		this.$read.find("[data-keep]").on("click", async (event) => {
			await frappe.xcall("onedesk.one_intake.inbox.keep", { action: $(event.currentTarget).attr("data-keep") });
			again();
		});
		this.$read.find("[data-undo-one]").on("click", (event) => {
			const action = $(event.currentTarget).attr("data-undo-one");
			frappe.confirm(__("Take this back?"), async () => {
				const done = await frappe.xcall("onedesk.one_intake.act.undo_one", { action });
				if (done.why) frappe.msgprint(done.why);
				else frappe.show_alert({ message: __("Undone."), indicator: "green" });
				again();
			});
		});
		onedesk.intake.bind(this.$read.find(".oi-more-body"), null, said.name);
	}

	async seen_all() {
		await frappe.xcall("onedesk.one_intake.inbox.seen_all", { box: this.box });
		this.load();
	}
};
