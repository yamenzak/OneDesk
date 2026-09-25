// Intake: what OneAI did with what arrived, and what waits for you, as two
// boxes that work like a mailbox. The server decides what is in each and who
// has seen what (one_intake/inbox.py); this draws it.

frappe.pages["intake"].on_page_load = (wrapper) => {
	const page = onedesk.shell.page(wrapper, __("Intake"));
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
		// A mailbox: the documents in the shell's list pane, the one opened in
		// the pane beside it.
		const panes = onedesk.shell.panes(page.$shell, [{ key: "list", width: 380 }, { key: "read" }]);
		this.$n = $(`<span></span>`);
		this.tabs = new frappe.ui.TabButtons({
			label: __("Box"),
			options: [
				{ label: __("Waiting"), value: "waiting", suffix: this.$n[0] },
				{ label: __("Done"), value: "done" },
			],
			value: this.box,
			on_change: (box) => this.open_box(box),
		});
		onedesk.shell.pane_head(panes.list).append(this.tabs.el);
		this.$rows = $(`<div class="one-shell-list"></div>`).appendTo(panes.list);
		this.$more = $(`<div class="oi-inbox-more hide">${onedesk.shell.button(__("More"), {}, "ghost")}</div>`).appendTo(panes.list);
		this.$read = $(`<div class="one-shell-pane-body"></div>`).appendTo(panes.read).html(this.nothing_open());
		this.$more.find("button").on("click", () => this.load(this.items.length));
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

	nothing_open() {
		return onedesk.shell.empty(__("Pick a document to see what OneAI did with it."), null, { icon: "inbox" });
	}

	show() {
		const asked = frappe.utils.get_query_params();
		if (asked.box) this.box = asked.box === "done" ? "done" : "waiting";
		this.tabs.set_value(this.box, { silent: true });
		this.load().then(() => asked.reading && this.read(asked.reading));
	}

	open_box(box) {
		this.box = box;
		this.reading = null;
		this.load();
		this.$read.html(this.nothing_open());
		this.remember();
	}

	remember(reading) {
		const query = new URLSearchParams({ box: this.box, ...(reading ? { reading } : {}) });
		window.history.replaceState(null, "", `/app/intake?${query}`);
	}

	async load(start = 0) {
		const said = await frappe.xcall("onedesk.one_intake.inbox.listing", { box: this.box, everyone: this.everyone, start });
		this.items = start ? [...this.items, ...said.items] : said.items;
		this.$more.toggleClass("hide", !said.more);
		this.draw();
		this.counts();
	}

	async counts() {
		const said = await (onedesk.dock && onedesk.dock.intake ? onedesk.dock.intake() : frappe.xcall("onedesk.one_intake.inbox.counts"));
		this.$n.html(said.waiting ? frappe.ui.badge.html({ label: String(said.waiting), size: "sm", variant: "solid" }) : "");
	}

	draw() {
		const esc = frappe.utils.escape_html;
		if (!this.items.length) {
			this.$rows.html(
				this.box === "waiting"
					? onedesk.shell.empty(__("Nothing waits for you."), __("OneAI and its auditor dealt with everything."), { icon: "check-check" })
					: onedesk.shell.empty(__("Nothing yet."), null, { icon: "inbox" })
			);
			return;
		}
		const badge = (label, theme) => frappe.ui.badge.html({ label, theme, size: "sm" });
		this.$rows.html(
			this.items
				.map((one) =>
					onedesk.shell.row({
						title: esc(one.title || ""),
						meta: one.when ? esc(frappe.datetime.prettyDate(one.when, true)) : "",
						sub: [
							one.kind ? badge(one.kind, "blue") : "",
							one.waiting ? badge(__("{0} to decide", [one.waiting]), "orange") : "",
							one.done ? `<span class="one-shell-quiet">${esc(__("{0} done", [one.done]))}</span>` : "",
							one.person ? `<span class="one-shell-quiet">· ${esc(one.person)}</span>` : "",
						].join(""),
						quiet: one.summary ? esc(one.summary) : "",
						link: { "data-reading": one.name },
						active: one.name === this.reading,
						unread: one.unread,
					})
				)
				.join("")
		);
		this.$rows.find("[data-reading]").on("click", (event) => this.read($(event.currentTarget).attr("data-reading")));
		this.$rows.find("[data-reading]").on("keydown", (event) => event.key === "Enter" && this.read($(event.currentTarget).attr("data-reading")));
	}

	async read(reading) {
		this.reading = reading;
		this.remember(reading);
		this.$rows.find("[data-reading]").removeClass("is-active");
		this.$rows.find(`[data-reading="${CSS.escape(reading)}"]`).addClass("is-active").removeClass("is-unread");
		let said;
		try {
			said = await frappe.xcall("onedesk.one_intake.inbox.item", { name: reading });
		} catch (e) {
			this.$read.html(onedesk.shell.empty(__("That is no longer here."), null, { icon: "inbox" }));
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
				<div class="one-shell-quiet">${[said.kind ? esc(__(said.kind)) : "", said.person ? esc(__("for {0}", [said.person])) : "", open].filter(Boolean).join(" · ")}</div>
			</div>
			${said.summary ? `<div class="oi-summary">${esc(said.summary)}</div>` : ""}
			<div class="oi-title">${__("What OneAI did")}</div>
			<ul class="oi-acts">${(said.actions || []).map((act) => this.act(act, said.may_decide)).join("") || `<li class="one-shell-quiet">${__("Nothing.")}</li>`}</ul>
			<details class="oi-more"><summary>${__("Everything OneAI read")}</summary><div class="oi-more-body">${onedesk.intake.html(rest)}</div></details>
		</div>`;
	}

	act(act, may) {
		const esc = frappe.utils.escape_html;
		const link = act.record
			? ` · <a href="/desk/${frappe.router.slug(act.record[0])}/${encodeURIComponent(act.record[1])}">${__("Open")}</a>`
			: "";
		const doubted = act.level === "Done" && act.audit === "Wrong";
		const badge = (label, theme) => frappe.ui.badge.html({ label, theme, size: "sm" });
		const chip = doubted
			? badge(__("The auditor doubts this"), "red")
			: act.level === "Proposed"
				? badge(__("Needs a look"), "orange")
				: act.level === "Refused"
					? badge(__("Not allowed"), "gray")
					: act.by_auditor
						? badge(__("Approved by the auditor"), "green")
						: "";
		const change = (act.change || [])
			.map((it) => `<div class="oi-change">${esc(it.field)}: <s>${esc(String(it.from))}</s> → ${esc(String(it.to))}</div>`)
			.join("");
		const why = [act.level !== "Done" ? act.why : "", doubted || act.by_auditor || act.level === "Proposed" ? act.audit_why : ""]
			.filter(Boolean)
			.map((line) => `<div class="one-shell-quiet">${esc(line)}</div>`)
			.join("");
		// Espresso's buttons, as the rest of the page's; `attrs` says what one does.
		const button = (label, attrs, primary) => onedesk.shell.button(label, attrs, primary ? "solid" : "subtle");
		let buttons = "";
		if (may && act.level === "Proposed") {
			buttons = button(__("Apply"), { "data-settle": act.name, "data-take": "1" }, true) + button(__("Dismiss"), { "data-settle": act.name, "data-take": "0" });
		} else if (may && act.level === "Done") {
			buttons = (doubted ? button(__("Keep"), { "data-keep": act.name }, true) : "") + button(__("Undo"), { "data-undo-one": act.name });
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
