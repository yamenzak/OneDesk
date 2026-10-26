// TrustCenter (docs/READY.md, mechanism 13): the agreements, the laws they
// answer, the optional services a workspace turns on, every company that
// receives data, what is kept and how to leave, and what is changing. The
// docs dialog HelpCenter is: the whole of it from the bottom bar and the
// Agreements address, and a module's part from its foot. Its words are the
// agreements' own, in English; what is around them is translated.
frappe.provide("onedesk.trust");

onedesk.trust.open = async ({ module = null, at = null } = {}) => {
	const said = await frappe.xcall("onedesk.one_legal.reading.trust", { module: module || "" }, "GET");
	const kit = onedesk.module_settings.kit;
	const esc = frappe.utils.escape_html;
	const docs = onedesk.module_docs;

	// A document's sections get ids, so the tree and search can land on them.
	const anchored = (prefix, html) => {
		const $doc = $("<div></div>").html(html);
		$doc.find("h2").each((i, h2) => (h2.id = `${prefix}-${i}`));
		return $doc.html();
	};

	const pages = [];
	const page = (one) => (pages.push(one), one);

	// Opened in a module, only what is that module's: what it sends out and
	// to whom, then its own paragraphs of each agreement it writes into, and
	// the changes to those. The whole of TrustCenter is the bottom bar's.
	const mine = said.module ? said.module.documents.filter((doc) => doc.sections.length) : [];
	const keys = new Set(mine.map((doc) => doc.key));
	if (said.module) {
		page({
			id: "app",
			label: module,
			icon_html: frappe.utils.icon(module.toLowerCase(), "sm"),
			title: __("{0} and Your Data", [module]),
			description: __("What {0} can send out, and to whom.", [module]),
			html: "",
			after(panel) {
				const own = said.services.filter((one) => one.module === module);
				if (own.length) {
					panel.body.append(kit.heading(__("Optional Services"), __("Off until an administrator turns them on.")));
					services(panel.body, own);
				}
				const used = said.companies.filter((row) => row.uses.some((use) => use.module === module));
				if (used.length) {
					panel.body.append(kit.heading(__("Who It Sends Data To"), __("Struck through where your workspace doesn't use it.")));
					table(used, module).appendTo(panel.body);
				}
				if (!own.length && !used.length) panel.body.append(kit.empty(__("{0} sends nothing to another company.", [module])));
			},
		});
		for (const part of mine) {
			const doc = said.documents.find((one) => one.key === part.key);
			const html = part.sections
				.map(
					(section) =>
						`<h2>${esc(section.heading)}</h2>` +
						section.clauses.map((c) => (c.heading ? `<h3>${esc(c.heading)}</h3>` : "") + `<p>${esc(c.body)}</p>`).join(""),
				)
				.join("");
			page({
				id: `doc:${doc.key}`,
				group: "agreements",
				label: doc.title,
				icon: "file-text",
				title: doc.title,
				description: __("What {0} adds to it.", [module]),
				html: anchored(doc.key, html),
				before(panel) {
					standing(panel, doc, true);
				},
			});
		}
	} else {
		for (const doc of said.documents) {
			page({
				id: `doc:${doc.key}`,
				group: "agreements",
				label: doc.title,
				icon: "file-text",
				title: doc.title,
				description: doc.summary,
				html: anchored(doc.key, doc.html),
				before(panel) {
					standing(panel, doc);
				},
			});
		}
		page({
			id: "services",
			label: __("Optional Services"),
			icon: "toggle-right",
			title: __("Optional Services"),
			description: __("Sent to another company only once an administrator turns it on."),
			html: "",
			after(panel) {
				if (!said.services.length) panel.body.append(kit.empty(__("No optional services")));
				else services(panel.body, said.services);
			},
		});
		page({
			id: "companies",
			label: __("Companies"),
			icon: "building-2",
			title: __("Companies That Receive Data"),
			description: __("Every company that receives data, and whether yours uses it."),
			html: "",
			after(panel) {
				table(said.companies).appendTo(panel.body);
			},
		});
	}

	const paragraphs = (list) => list.map((one) => `<p>${esc(one)}</p>`).join("");
	// For administrators, under Your Data: who asked to have their account
	// deleted and who asked for a copy of their data, each opening its
	// request, where it is approved or held (one/privacy.py).
	const requests = async (panel) => {
		const asked = await frappe.xcall("onedesk.one.privacy.requests", {}, "GET");
		const go = (doctype, name) => (dialog.hide(), frappe.set_route("Form", doctype, name));
		const status = (one) => frappe.ui.badge.html({ label: __(one.status || "Pending"), theme: one.status === "Deleted" ? "gray" : ["Pending Approval", "Waiting"].includes(one.status) ? "orange" : "blue" });
		panel.body.append(kit.heading(__("Requests"), __("Requests to delete an account or copy its data, newest first.")));
		const $list = $(`<div class="one-set-list"></div>`).appendTo(panel.body);
		if (!asked.deletions.length && !asked.copies.length) $list.append(kit.empty(__("Nobody has asked yet.")));
		for (const one of asked.deletions) {
			kit.row({ lead: kit.glyph("user-x"), title: __("Delete {0}", [one.email]), sub: esc(frappe.datetime.prettyDate(one.creation)), end: status(one), open: () => go("Personal Data Deletion Request", one.name) }).appendTo($list);
		}
		for (const one of asked.copies) {
			kit.row({ lead: kit.glyph("download"), title: __("Data Copy for {0}", [one.user_name || one.user]), sub: esc(frappe.datetime.prettyDate(one.creation)), end: status({ status: one.one_status }), open: () => go("Personal Data Download Request", one.name) }).appendTo($list);
		}
	};
	if (!said.module) page({
		id: "data",
		label: __("Your Data"),
		icon: "database",
		title: __("Your Data"),
		description: __("What is kept and for how long, and how to take everything with you."),
		html: anchored(
			"data",
			`<h2>${esc(__("What Is Kept"))}</h2>${paragraphs(said.data.kept)}` +
				`<h2>${esc(__("Your Own Data"))}</h2>${paragraphs(said.data.yours)}` +
				`<h2>${esc(__("Taking It With You"))}</h2>${paragraphs(said.data.leaving)}`,
		),
		after: frappe.boot.one_administers ? requests : null,
	});

	page({
		id: "changes",
		label: __("Changes"),
		icon: "history",
		title: __("Changes"),
		description: __("What is changing in the agreements, and from when."),
		html: "",
		after(panel) {
			const changes = said.module ? said.changes.filter((one) => keys.has(one.document)) : said.changes;
			if (!changes.length) {
				panel.body.append(kit.empty(__("No changes")));
				return;
			}
			const $list = $(`<div class="one-set-list"></div>`).appendTo(panel.body);
			for (const one of changes) {
				const when = __("Published {0} · Takes effect {1}", [one.published, one.effective]);
				kit.row({
					lead: kit.glyph(one.coming ? "calendar-clock" : "circle-check"),
					title: `${one.title} ${one.revision}`,
					sub: `${esc(one.says)}<br>${esc(when)}`,
					end: one.coming ? frappe.ui.badge.html({ label: __("Coming"), theme: "orange" }) : "",
					open: () => dialog.activate(`doc:${one.document}`),
				}).appendTo($list);
			}
		},
	});

	// Where the reader and the workspace stand on an agreement, the change
	// coming to it, its earlier versions, and Print and Agree.
	function standing(panel, doc, part = false) {
		const $box = $(`<div class="one-trust-standing" data-tour="trust-standing"></div>`).appendTo(panel.body);
		const $list = $(`<div class="one-set-list"></div>`).appendTo($box);
		const sides = [
			[doc.you, __("You")],
			[doc.organisation, __("Your Organisation")],
		].filter(([side]) => side);
		if (!sides.length) kit.row({ lead: kit.glyph("book-open"), title: __("To Read"), sub: esc(__("Nobody has to agree to this.")) }).appendTo($list);
		for (const [side, label] of sides) {
			const sub = side.version
				? side.by
					? __("{0} agreed on {1}", [side.by, side.on])
					: __("Agreed on {0}", [side.on])
				: side === doc.organisation && !said.may_bind
					? __("Waiting for an administrator")
					: __("Not agreed yet");
			kit.row({ lead: kit.glyph(side.version ? "circle-check" : "circle"), title: label, sub: esc(sub) }).appendTo($list);
		}
		if (doc.effective) {
			kit.row({
				lead: kit.glyph("calendar-clock"),
				title: __("Changing on {0}", [frappe.datetime.str_to_user(doc.effective)]),
				sub: esc(doc.change || ""),
			}).appendTo($list);
		}
		const $buttons = kit.buttons($box);
		const owed = (doc.you && !doc.you.version) || (said.may_bind && doc.organisation && !doc.organisation.version);
		if (owed) {
			kit.button({ label: __("Agree"), variant: "solid" })
				.on("click", async () => {
					await frappe.xcall("onedesk.one_legal.gate.accept", { documents: [doc.key] });
					frappe.show_alert({ message: __("Agreed to {0}", [doc.title]), indicator: "green" });
					dialog.hide();
					onedesk.trust.open({ module, at: `doc:${doc.key}` });
				})
				.appendTo($buttons);
		}
		if (part) {
			kit.button({ label: __("Read in Full"), variant: "outline", icon: "book-open" })
				.on("click", () => {
					dialog.hide();
					onedesk.trust.open({ at: `doc:${doc.key}` });
				})
				.appendTo($buttons);
		}
		kit.button({ label: __("Print"), variant: "outline", icon: "printer" }).on("click", () => print(doc.title, doc.html)).appendTo($buttons);
		if (said.sees_acceptances) {
			kit.button({ label: __("Who Agreed"), variant: "ghost", icon: "users" })
				.on("click", async () => {
					const rows = await frappe.xcall("onedesk.one_legal.reading.acceptances", { key: doc.key }, "GET");
					kit.view(panel, { title: __("Who Agreed"), description: doc.title });
					const $list = $(`<div class="one-set-list"></div>`).appendTo(panel.body.empty());
					if (!rows.length) return $list.append(kit.empty(__("No one yet")));
					for (const one of rows) {
						kit.row({
							lead: kit.glyph(one.for === "organisation" ? "building-2" : "user"),
							title: esc(one.who),
							sub: esc(one.for === "organisation" ? __("For the organisation, version {0}", [one.version]) : __("For themselves, version {0}", [one.version])),
							end: `<span class="one-set-value">${esc(one.on)}</span>`,
						}).appendTo($list);
					}
				})
				.appendTo($buttons);
		}
		for (const old of doc.history.filter((one) => one.version !== doc.version).slice(0, 2)) {
			kit.button({ label: __("Version {0}", [old.version]), variant: "ghost", icon: "history" })
				.on("click", async () => {
					const read = await frappe.xcall("onedesk.one_legal.reading.document", { key: doc.key, version: old.version }, "GET");
					kit.view(panel, { title: doc.title, description: __("As agreed, version {0}.", [read.version]) });
					docs.page(panel.body.empty(), read.html.split("</h1>").pop());
				})
				.appendTo($buttons);
		}
	}

	// The optional services: what each does and sends, to whom, what happens
	// while it is off, and its switch, which only an administrator moves.
	function services($into, list) {
		const $list = $(`<div class="one-trust-services"></div>`).appendTo($into);
		for (const one of list) {
			const $card = $(`<div class="one-trust-service"></div>`).appendTo($list);
			const top = kit.heading_with(one.title, one.does);
			top.$row.appendTo($card);
			const control = frappe.ui.form.make_control({
				df: { fieldtype: "Switch", fieldname: "on", label: "" },
				parent: $(`<span class="one-set-switch"></span>`).appendTo(top.$end),
				render_input: true,
			});
			control.set_value(one.on ? 1 : 0);
			control.$input.attr("aria-label", one.title).prop("disabled", !said.may_bind);
			control.$input.on("change", () => turn(one, control));
			const facts = [
				[__("What It Sends"), one.sends],
				[__("To"), one.companies.map((c) => `${c.name} (${c.where})`).join(", ")],
				[__("While It Is Off"), one.off],
			];
			const $dl = $(`<dl class="one-trust-facts"></dl>`).appendTo($card);
			for (const [term, said_] of facts) $dl.append($(`<dt></dt>`).text(term), $(`<dd></dd>`).text(said_));
			const note = one.on
				? __("Turned on by {0} on {1}.", [one.agreed_by, one.agreed_on])
				: one.asks_again
					? __("It sends somewhere new, so it waits for an administrator to agree.")
					: !said.may_bind
						? __("Your role doesn't allow turning it on.")
						: "";
			if (note) $(`<div class="one-trust-note"></div>`).text(note).appendTo($card);
		}
	}

	async function turn(one, control) {
		const on = control.get_value() ? 1 : 0;
		if (on) {
			const yes = await new Promise((resolve) => {
				let answered = false;
				const ask = new frappe.ui.Dialog({
					title: __("Turn On {0}?", [one.title]),
					fields: [
						{
							fieldtype: "HTML",
							fieldname: "said",
							options: `<p>${esc(one.sends)}</p><p>${esc(__("Turning it on agrees to this for your whole workspace, and is recorded with your name."))}</p>`,
						},
					],
					primary_action_label: __("Turn On"),
					primary_action() {
						answered = true;
						ask.hide();
						resolve(true);
					},
					secondary_action_label: __("Cancel"),
					secondary_action: () => ask.hide(),
				});
				ask.onhide = () => answered || resolve(false);
				ask.show();
			});
			if (!yes) return control.set_value(0);
		}
		said.services = await frappe.xcall("onedesk.one_legal.services.switch", { key: one.key, on });
		frappe.show_alert({ message: on ? __("Turned on") : __("Turned off"), indicator: "green" });
		const fresh = await frappe.xcall("onedesk.one_legal.reading.trust", { module: module || "" }, "GET");
		Object.assign(said, fresh);
		dialog.get_panel(dialog.active_tab)?.refresh();
	}

	// The companies, with what each use is for; a use waiting on an optional
	// service this workspace hasn't turned on is struck through.
	function table(rows, only = null) {
		const $table = $(`<table class="one-trust-companies"><thead><tr></tr></thead><tbody></tbody></table>`);
		for (const word of [__("Company"), __("What For"), __("What They Receive"), __("Where"), __("Safeguard")]) {
			$(`<th></th>`).text(word).appendTo($table.find("thead tr"));
		}
		for (const row of rows) {
			for (const use of row.uses.filter((one) => !only || one.module === only)) {
				const $tr = $(`<tr></tr>`).toggleClass("one-trust-unused", !use.used).appendTo($table.find("tbody"));
				const $name = $(`<td></td>`).appendTo($tr);
				if (row.url) $(`<a target="_blank" rel="noopener"></a>`).attr("href", row.url).text(row.name).appendTo($name);
				else $name.text(row.name);
				const $for = $(`<td></td>`).text(use.purpose).appendTo($tr);
				if (use.service) {
					$for.append(
						" ",
						frappe.ui.badge.html({
							label: use.used ? use.service : __("Not Used by This Workspace"),
							theme: use.used ? "blue" : "gray",
						}),
					);
				}
				// A company One will need from the day a change takes effect.
				if (use.starts) $for.append(" ", frappe.ui.badge.html({ label: __("From {0}", [use.starts]), theme: "orange" }));
				for (const value of [use.data, use.where, row.safeguard]) $(`<td></td>`).text(value).appendTo($tr);
			}
		}
		return $(`<div class="one-doc-table"></div>`).append($table);
	}

	function print(title, html) {
		const win = window.open("", "_blank");
		if (!win) return;
		win.document.write(`<!doctype html><title>${esc(title)}</title><body style="font:14px/1.6 system-ui;max-width:46em;margin:2em auto"><h1>${esc(title)}</h1>${html}</body>`);
		win.document.close();
		win.print();
	}

	const items = pages.map((one) => ({
		id: one.id,
		label: one.label,
		icon: one.icon,
		icon_html: one.icon_html,
		title: one.title,
		description: one.description,
		render(panel) {
			panel.body.empty();
			if (one.before) one.before(panel);
			if (one.html) docs.page(panel.body, one.html);
			if (one.after) one.after(panel);
			panel.body.off("scroll.one-docs").on(
				"scroll.one-docs",
				frappe.utils.throttle(() => dialog.spy(one.id), 80),
			);
		},
	}));
	const sections = Object.fromEntries(pages.map((one) => [one.id, docs.sections(one.id, one.title, one.html)]));
	const node = (one) => ({
		id: one.id,
		label: one.label,
		icon: one.icon,
		icon_html: one.icon_html,
		children: sections[one.id]
			.filter((section) => section.anchor)
			.map((section) => ({ id: `${one.id}#${section.anchor}`, label: section.title, tab: false, click: () => dialog.go(one.id, section.anchor) })),
	});
	const agreements = pages.filter((one) => one.group === "agreements");
	const tree = [
		...pages.filter((one) => one.id === "app").map(node),
		{ id: "agreements", label: __("Agreements"), icon: "scale", tab: false, open: true, children: agreements.map(node) },
		...pages.filter((one) => !one.group && one.id !== "app").map(node),
	];

	const dialog = new onedesk.module_docs.Dialog({
		title: "TrustCenter",
		module,
		center: "trust",
		tabs: [{ items }],
		expand: module ? () => onedesk.trust.open() : null,
		tree,
		default_tab: (at && items.find((one) => one.id === at) ? at : null) || items[0]?.id,
	});
	dialog.$wrapper.addClass("one-set one-trust");
	dialog.index = Object.values(sections).flat();
	dialog.spy = (id) => {
		const panel = dialog.get_panel(id);
		if (!panel || dialog.query) return;
		let here = null;
		panel.body.find(".one-doc > h2").each((_i, h2) => {
			if ($(h2).position().top <= 32) here = h2.id;
		});
		dialog.$tree.find(".one-docs-row.here").removeClass("here");
		if (here) dialog.node(`${id}#${here}`).children(".one-docs-row").addClass("here");
	};
	dialog.on_page = (id) => {
		if (!dialog.query) {
			dialog.$tree.find(".one-docs-node").each((_i, el) => {
				if (el.querySelector(":scope > .one-docs-children .one-docs-row[data-tab-id]")) return;
				$(el).toggleClass("open", el.dataset.node === id);
			});
		}
		dialog.spy(id);
	};
	dialog.on_page(dialog.active_tab);
	dialog.show();
	// TrustCenter has no foot to start its tour from, so it starts here
	// the first time the agreements are open.
	if ((frappe.boot.one_tours_unseen || []).includes("OneLegal:agreements")) {
		setTimeout(async () => {
			const tour = await onedesk.tour.here("OneLegal");
			if (tour && dialog.display) onedesk.tour.run("OneLegal", tour);
		}, 600);
	}
	return dialog;
};
