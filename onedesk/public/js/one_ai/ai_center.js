// AICenter (docs/AICENTER.md): OneAI for the workspace (one_ai/center.py).
// For administrators: OneAI on or off and its tier, reading what arrives,
// Knowledge, what each module has OneAI do on its own, which records get a
// summary, and what was used. For everybody: Yours, what OneAI keeps about them. From the bottom
// bar, OneAI in a module's ControlCenter (on that module), and Settings.
frappe.provide("onedesk.ai_center");

onedesk.ai_center.open = async ({ module = null, at = null } = {}) => {
	const C = "onedesk.one_ai.center.";
	const kit = onedesk.module_settings.kit;
	const esc = frappe.utils.escape_html;
	const admin = !!frappe.boot.one_administers;
	const credits = (value) => __("{0} credits", [format_number(value, null, value < 10 ? 2 : 0)]);

	// A switch at a row's end, saved as it changes; put back if refused.
	const toggle = ($end, { value, label, change }) => {
		const control = frappe.ui.form.make_control({
			df: { fieldtype: "Switch", fieldname: "on", label: "" },
			parent: $(`<span class="one-set-switch"></span>`).appendTo($end),
			render_input: true,
		});
		control.set_value(value ? 1 : 0);
		control.$input.attr("aria-label", label);
		control.$input.on("change", async () => {
			const on = control.get_value() ? 1 : 0;
			try {
				await change(on);
				kit.saved();
			} catch (e) {
				control.set_value(on ? 0 : 1);
			}
		});
		return control;
	};

	// OneAI on or off, the tier with what an answer costs at each, and the
	// credits left.
	const oneai_tab = {
		id: "oneai",
		label: __("OneAI"),
		icon: "oneai",
		title: __("OneAI"),
		description: __("The tier sets which models answer and what each answer costs."),
		actions: [{ label: __("Add Credits"), icon: "plus", click: (panel) => (panel.dialog.hide(), onedesk.account_center.open({ at: "plan" })) }],
		async render(panel) {
			const said = await frappe.xcall(C + "state", {}, "GET");
			const $body = panel.body.empty();
			const $list = $(`<div class="one-set-list"></div>`).appendTo($body);
			const $on = kit.row({ lead: kit.glyph("oneai"), title: __("OneAI"), sub: esc(__("If off, nobody can ask OneAI and none of its jobs run.")) }).appendTo($list);
			toggle($on.find(".one-set-end"), {
				value: said.on,
				label: __("OneAI"),
				change: async (on) => {
					await frappe.xcall(C + "set_on", { on });
					frappe.boot.one_hidden = frappe.boot.one_hidden || {};
					panel.refresh();
				},
			});
			if (!said.on) return;
			$body.append(kit.heading(__("Tier")));
			const $tiers = $(`<div class="one-set-list" role="radiogroup" aria-label="${esc(__("Tier"))}"></div>`).appendTo($body);
			for (const one of said.tiers) {
				const end = one.credits != null ? `<span class="one-set-value">${esc(__("About {0} an answer", [credits(one.credits)]))}</span>` : "";
				const $row = kit
					.row({ lead: kit.glyph(one.tier === said.tier ? "circle-dot" : "circle"), title: one.label, sub: esc(one.about), end })
					.attr({ role: "radio", tabindex: 0, "aria-checked": one.tier === said.tier ? "true" : "false" })
					.addClass("one-set-pick")
					.appendTo($tiers);
				$row.on("click keydown", async (event) => {
					if (event.type === "keydown" && !["Enter", " "].includes(event.key)) return;
					if (one.tier === said.tier) return;
					await frappe.xcall(C + "set_tier", { tier: one.tier });
					kit.saved();
					panel.refresh();
				});
			}
			if (said.credits != null) {
				$body.append(kit.heading(__("Credits")));
				kit.row({ lead: kit.glyph("coins"), title: __("Balance"), end: `<span class="one-set-value">${esc(credits(said.credits))}</span>` }).appendTo(
					$(`<div class="one-set-list"></div>`).appendTo($body)
				);
			}
		},
	};

	// A number at a row's end, saved as it changes.
	const number = ($end, { value, label, change }) => {
		const control = frappe.ui.form.make_control({
			df: { fieldtype: "Int", fieldname: "value", label: "" },
			parent: $(`<span class="one-set-number"></span>`).appendTo($end),
			render_input: true,
		});
		control.set_value(value || 0);
		control.$input.attr("aria-label", label).on("change", async () => {
			await change(control.get_value() || 0);
			kit.saved();
		});
		return control;
	};

	// Reading what arrives: on or off, this month, what OneAI may do with it,
	// and the mailboxes and folders it reads (one_ai/reading/).
	const reading_tab = {
		id: "reading",
		label: __("Reading"),
		icon: "oneintake",
		title: __("Reading"),
		description: __("Mail and files read as they arrive, and filed on their record."),
		actions: [{ label: __("Add Folder"), icon: "plus", click: (panel) => add_folder(panel) }],
		async render(panel) {
			const said = await frappe.xcall(C + "reading", {}, "GET");
			const $body = panel.body.empty();
			const $on = kit.row({ lead: kit.glyph("oneintake"), title: __("Reading"), sub: esc(__("If off, nothing new is read and Documents keeps what it holds.")) }).appendTo(
				$(`<div class="one-set-list"></div>`).appendTo($body)
			);
			toggle($on.find(".one-set-end"), { value: said.on, label: __("Reading"), change: (on) => frappe.xcall(C + "set_reading_on", { on }).then(() => panel.refresh()) });
			if (!said.on) return;
			const month = said.month || {};
			const inbox = (box) => () => {
				dialog.hide();
				frappe.set_route("intake", { box, everyone: 1 });
			};
			$body.append(kit.heading(__("This Month")));
			const $month = $(`<div class="one-set-list"></div>`).appendTo($body);
			for (const [value, label, box] of [
				[month.arrived, __("Received"), "done"],
				[month.handled, __("Handled by OneAI"), "done"],
				[month.needed, __("Needed Review"), "waiting"],
				[month.waiting, __("Waiting"), "waiting"],
				[month.undone, __("Undone"), "done"],
			]) {
				kit.row({ lead: kit.glyph("file-text"), title: label, end: `<span class="one-set-value">${esc(format_number(value || 0, null, 0))}</span>`, open: inbox(box) }).appendTo($month);
			}
			$body.append(kit.heading(__("Settings")));
			const $settings = $(`<div class="one-set-list"></div>`).appendTo($body);
			for (const one of said.settings) {
				const $end = kit.row({ lead: kit.glyph("oneai"), title: one.label, sub: esc(one.about || "") }).appendTo($settings).find(".one-set-end");
				const change = (value) => frappe.xcall(C + "set_reading", { key: one.key, value });
				if (one.kind === "switch") toggle($end, { value: one.value, label: one.label, change });
				else number($end, { value: one.value, label: one.label, change });
			}
			$body.append(kit.heading(__("Mailboxes")));
			const $boxes = $(`<div class="one-set-list"></div>`).appendTo($body);
			if (!said.mailboxes.length) $boxes.append(kit.empty(__("No mailboxes")));
			for (const one of said.mailboxes) {
				const sub = one.on ? __("Read on behalf of {0}", [one.for || ""]) : __("Not read");
				const $end = kit.row({ lead: kit.glyph("mail"), title: one.email, sub: esc(sub) }).appendTo($boxes).find(".one-set-end");
				toggle($end, {
					value: one.on,
					label: one.email,
					change: (on) => frappe.xcall("onedesk.one_ai.reading.switches.set_mailbox", { account: one.name, on }).then(() => panel.refresh()),
				});
			}
			$body.append(kit.heading(__("Folders")));
			const $folders = $(`<div class="one-set-list"></div>`).appendTo($body);
			if (!said.folders.length) $folders.append(kit.empty(__("No folders")));
			for (const one of said.folders) {
				const $end = kit
					.row({ lead: kit.glyph("folder"), title: one.path.replace(/^Home\//, ""), sub: esc(__("Read on behalf of {0}", [one.for || ""])) })
					.appendTo($folders)
					.find(".one-set-end");
				toggle($end, {
					value: 1,
					label: one.path,
					change: (on) => frappe.xcall("onedesk.one_ai.reading.switches.set_folder", { folder: one.name, on }).then(() => panel.refresh()),
				});
			}
		},
	};

	const add_folder = (panel) => {
		const asked = new frappe.ui.Dialog({
			title: __("Add Folder"),
			fields: [
				{ fieldname: "folder", fieldtype: "Link", options: "File", label: __("Folder"), reqd: 1, get_query: () => ({ filters: { is_folder: 1, one_intake: 0 } }) },
				{
					fieldname: "said",
					fieldtype: "HTML",
					options: `<div class="one-shell-quiet">${esc(__("New files in this folder and its subfolders are read and filed, using credits."))}</div>`,
				},
			],
			primary_action_label: __("Add"),
			primary_action: async (values) => {
				await frappe.xcall("onedesk.one_ai.reading.switches.set_folder", { folder: values.folder, on: 1 });
				asked.hide();
				panel.refresh();
			},
		});
		asked.show();
	};

	// What OneAI should know about the company, which it reads as facts.
	const knowledge_tab = {
		id: "knowledge",
		label: __("Knowledge"),
		icon: "book-open",
		title: __("Knowledge"),
		description: __("Facts, terms and policies OneAI reads with every answer."),
		actions: [{ label: __("New Knowledge"), icon: "plus", click: (panel) => write_knowledge(null, panel) }],
		async render(panel) {
			const rows = await frappe.xcall(C + "knowledge", {}, "GET");
			const $list = $(`<div class="one-set-list"></div>`).appendTo(panel.body.empty());
			if (!rows.length) return $list.append(kit.empty(__("No knowledge")));
			for (const one of rows) {
				kit.row({ lead: kit.glyph("book-open"), title: one.title, sub: esc(one.applies_to ? __(one.applies_to) : __("Everything")), chevron: true })
					.toggleClass("one-set-off", !one.enabled)
					.on("click", () => write_knowledge(one.name, panel))
					.appendTo($list);
			}
		},
	};

	// Knowledge is written here, by whoever holds Knowledge, rather than on
	// its record type's form, which only an administrator may open.
	const write_knowledge = async (name, panel) => {
		const one = name ? await frappe.xcall(C + "knowledge_of", { name }, "GET") : { enabled: 1 };
		const asked = new frappe.ui.Dialog({
			title: name ? one.title : __("New Knowledge"),
			size: "large",
			fields: [
				{ fieldtype: "Data", fieldname: "title", label: __("Title"), reqd: 1, default: one.title },
				{ fieldtype: "Link", fieldname: "applies_to", label: __("Applies To"), options: "DocType", default: one.applies_to, description: __("Empty for everything.") },
				{ fieldtype: "Check", fieldname: "enabled", label: __("Enabled"), default: one.enabled },
				{ fieldtype: "Text Editor", fieldname: "body", label: __("Knowledge"), reqd: 1, default: one.body },
			],
			primary_action_label: name ? __("Save") : __("Add"),
			primary_action: async (values) => {
				await frappe.xcall(C + "keep_knowledge", { ...values, name: name || "" });
				asked.hide();
				panel && panel.refresh();
			},
			secondary_action_label: name ? __("Delete") : null,
			secondary_action: name
				? () =>
						frappe.confirm(__("Delete {0}?", [one.title]), async () => {
							await frappe.xcall(C + "drop_knowledge", { name });
							asked.hide();
							panel && panel.refresh();
						})
				: null,
		});
		asked.show();
	};

	// A module's part: what OneAI does there on its own.
	const part_tab = (part) => ({
		id: `part:${part.module}`,
		label: part.module,
		icon_html: frappe.utils.icon(onedesk.brand.mark_of(part.module.replace(/^One/, "")) || "oneai", "sm"),
		title: part.module,
		description: part.mailboxes
			? __("How far OneAI reads each mailbox's new mail.")
			: __("Jobs OneAI runs in {0} by itself, each using credits.", [part.module]),
		render(panel) {
			const $list = $(`<div class="one-set-list"></div>`).appendTo(panel.body.empty());
			if (part.mailboxes) {
				if (!part.mailboxes.length) return $list.append(kit.empty(__("No mailboxes")));
				for (const box of part.mailboxes) {
					kit.row({
						lead: kit.glyph("mail"),
						title: box.email,
						sub: esc(box.reads ? box.level : __("Not read")),
						chevron: true,
					})
						.on("click", () => {
							dialog.hide();
							onedesk.mail.settings(`mailbox:${box.name}:oneai`);
						})
						.appendTo($list);
				}
				return;
			}
			for (const job of part.jobs) {
				const $row = kit.row({ lead: kit.glyph("oneai"), title: job.label, sub: esc(job.about || "") }).appendTo($list);
				const $end = $row.find(".one-set-end");
				if (job.kind === "switch") {
					toggle($end, { value: job.value, label: job.label, change: (on) => frappe.xcall(C + "set_job", { key: job.key, value: on }) });
					continue;
				}
				number($end, { value: job.value, label: job.label, change: (value) => frappe.xcall(C + "set_job", { key: job.key, value }) });
			}
		},
	});

	// Which kinds of record carry a few sentences at the top.
	const summaries_tab = {
		id: "summaries",
		label: __("Summaries"),
		icon: "notebook-text",
		title: __("Summaries"),
		description: __("Kept at the top of a record and rewritten at most once a day."),
		async render(panel) {
			const rows = await frappe.xcall(C + "summaries", {}, "GET");
			const $list = $(`<div class="one-set-list"></div>`).appendTo(panel.body.empty());
			for (const one of rows) {
				const written = one.written === 1 ? __("1 record") : one.written ? __("{0} records", [format_number(one.written, null, 0)]) : __("None yet");
				const $row = kit.row({ lead: kit.glyph("notebook-text"), title: one.label, sub: esc(written) }).appendTo($list);
				toggle($row.find(".one-set-end"), {
					value: one.on,
					label: one.label,
					change: (on) => frappe.xcall("onedesk.one_ai.brief.switch", { doctype: one.doctype, on }),
				});
			}
		},
	};

	// What each job used in the last thirty days.
	const usage_tab = {
		id: "usage",
		label: __("Usage"),
		icon: "chart-column",
		title: __("Usage"),
		description: __("Credits each job used in the last 30 days."),
		actions: admin ? [{ label: __("Credit Usage"), icon: "external-link", click: () => frappe.set_route("query-report", "AI Credits", { by: "Job" }) }] : [],
		async render(panel) {
			const said = await frappe.xcall(C + "usage", {}, "GET");
			const $list = $(`<div class="one-set-list"></div>`).appendTo(panel.body.empty());
			if (!said.reached) return $list.append(kit.empty(said.linked === false ? __("Not Connected Yet") : __("The account could not be reached.")));
			if (!said.jobs.length) return $list.append(kit.empty(__("No usage")));
			for (const one of said.jobs) {
				kit.row({
					lead: kit.glyph("oneai"),
					title: one.what,
					sub: esc(one.calls === 1 ? __("1 call") : __("{0} calls", [format_number(one.calls, null, 0)])),
					end: `<span class="one-set-value">${esc(credits(one.credits))}</span>`,
				}).appendTo($list);
			}
		},
	};

	// What OneAI keeps about the reader, and the workspace's Knowledge it
	// reads as well. Only the reader sees their memories.
	const yours_tab = {
		id: "yours",
		label: __("Yours"),
		icon: "user",
		title: __("Yours"),
		description: __("What OneAI remembers about you, which only you can see."),
		actions: [{ label: __("Add Memory"), icon: "plus", click: (panel) => remember(panel) }],
		async render(panel) {
			const said = await frappe.xcall(C + "yours", {}, "GET");
			const $body = panel.body.empty();
			const $list = $(`<div class="one-set-list"></div>`).appendTo($body);
			if (!said.facts.length) $list.append(kit.empty(__("No memories")));
			for (const one of said.facts) {
				const $row = kit
					.row({ lead: kit.glyph("brain"), title: one.fact, sub: esc([one.about_title, frappe.datetime.prettyDate(one.creation)].filter(Boolean).join(" · ")) })
					.appendTo($list);
				$row.find(".one-set-title").on("click", () => remember(panel, one));
				kit.remove(() => frappe.xcall("onedesk.one_ai.yours.forget", { name: one.name }).then(() => panel.refresh())).appendTo($row.find(".one-set-end"));
			}
			if (said.knowledge.length) {
				$body.append(kit.heading(__("Workspace Knowledge")));
				const $known = $(`<div class="one-set-list"></div>`).appendTo($body);
				for (const one of said.knowledge) kit.row({ lead: kit.glyph("book-open"), title: one.title, sub: esc(one.applies_to || __("Everything")) }).appendTo($known);
			}
		},
	};

	// The mailboxes and folders reading goes through that are the reader's
	// to switch (one_ai/yours.py `_reads`).
	const reads_tab = onedesk.center_section.tab(onedesk.ReadsSection, {
		id: "reads",
		label: __("What OneAI Reads"),
		icon: "oneintake",
		about: __("Your mailboxes and folders that OneAI reads, files and acts on as you."),
	});

	const remember = (panel, one = null) => {
		const asked = new frappe.ui.Dialog({
			title: one ? __("Edit Memory") : __("Add Memory"),
			fields: [
				{ fieldname: "fact", fieldtype: "Small Text", label: __("Memory"), reqd: 1, default: one ? one.fact : "" },
				{ fieldname: "about_doctype", fieldtype: "Link", options: "DocType", label: __("Record Type"), default: one ? one.about_doctype : "" },
				{ fieldname: "about_name", fieldtype: "Dynamic Link", options: "about_doctype", label: __("Record"), depends_on: "about_doctype", default: one ? one.about_name : "" },
			],
			primary_action_label: one ? __("Save") : __("Add"),
			primary_action: async (values) => {
				await frappe.xcall("onedesk.one_ai.yours.keep", { ...values, name: one ? one.name : null });
				asked.hide();
				panel.refresh();
			},
		});
		asked.show();
	};

	const parts = admin ? await frappe.xcall(C + "parts", {}, "GET") : [];
	const mine = module ? parts.filter((part) => part.module === module) : parts;
	const tabs = admin
		? [
				{ group: null, items: module ? [] : [oneai_tab, reading_tab, knowledge_tab] },
				{ group: module ? null : __("Modules"), items: [...mine.map(part_tab), ...(module ? [] : [summaries_tab])] },
				{ group: null, items: module ? [] : [usage_tab, yours_tab, reads_tab] },
		  ]
		: [
				{
					group: null,
					items: [
						...((frappe.boot.one_ai_may || {}).knowledge ? [knowledge_tab] : []),
						...((frappe.boot.one_ai_may || {}).usage ? [usage_tab] : []),
						yours_tab,
						reads_tab,
					],
				},
		  ];
	const shown = tabs.filter((group) => group.items.length);
	const ids = shown.flatMap((group) => group.items.map((item) => item.id));
	// For the whole workspace AICenter is OneAI's own settings, with its
	// mark, Help and the other centres; for one module, that module's part.
	const dialog = module
		? new onedesk.module_settings.Dialog({
				title: "AICenter",
				module,
				center: "ai",
				tabs: shown,
				default_tab: ids.includes(at) ? at : ids[0],
				expand: () => {
					dialog.hide();
					onedesk.ai_center.open();
				},
		  })
		: onedesk.module_settings.open({ module: "OneAI", tabs: shown, default_tab: at, title: "AICenter", center: "ai" });
	dialog.$wrapper.addClass("one-set one-ai-center");
	dialog.show();
	return dialog;
};

// What OneAI Reads: a CenterSection, so its tables and switches are drawn
// as the other centres' sections are.
onedesk.ReadsSection = class ReadsSection extends onedesk.CenterSection {
	static API = "onedesk.one_ai.yours.";
	static HERE = "ai";
	static LABEL = "AICenter";

	static read_switch(on) {
		return `<span class="switch-control one-read-switch" aria-hidden="true"><span class="input-area"><input type="checkbox" tabindex="-1" ${
			on ? "checked" : ""
		}></span><span class="switch-visual"><span class="switch-thumb"></span></span></span>`;
	}

	draw_reads(data) {
		const esc = frappe.utils.escape_html;
		if (data.off) {
			this.$content.append(onedesk.shell.section("", `<p class="one-shell-quiet">${esc(__("Reading is turned off for this workspace."))}</p>`));
			return;
		}
		const marks = data.marks || {};
		const reading = (one) =>
			!one.on ? __("Not read") : one.for && one.for !== frappe.session.user_fullname ? __("Read on behalf of {0}", [one.for]) : __("Read as you");
		const none = (text) => `<p class="one-shell-quiet">${esc(text)}</p>`;
		const mailboxes = data.mailboxes || [];
		const folders = data.folders || [];
		this.$content.append(
			onedesk.shell.section(
				__("Mailboxes"),
				mailboxes.length ? '<div data-list="mailboxes"></div>' : none(__("You don't hold a mailbox.")),
				__("New mail and its attachments are read, filed and acted on as you.")
			),
			onedesk.shell.section(
				__("Folders"),
				folders.length ? '<div data-list="folders"></div>' : none(__("OneAI has no access to any of your folders.")),
				__("New files in the folder and the folders inside it are read, filed and acted on as you."),
				onedesk.shell.button(__("Add Folder"), { "data-add-folder": "1" }, "subtle", "plus")
			)
		);
		if (mailboxes.length)
			onedesk.shell.table(this.$content.find('[data-list="mailboxes"]'), {
				mark: marks.OneMail,
				rows: mailboxes,
				columns: [
					{ label: __("Mailbox"), fieldname: "email" },
					{ label: __("Read by OneAI"), render: (one) => esc(reading(one)) },
					{ label: "", render: (one) => ReadsSection.read_switch(one.on) },
				],
				open: (one) => this.switch_mailbox(one),
			});
		if (folders.length)
			onedesk.shell.table(this.$content.find('[data-list="folders"]'), {
				mark: marks.OneCloud,
				rows: folders,
				columns: [
					{ label: __("Folder"), render: (one) => esc(one.path.replace(/^Home\//, "")) },
					{ label: __("Read by OneAI"), render: (one) => esc(reading({ on: true, for: one.for })) },
					{ label: "", render: () => ReadsSection.read_switch(true) },
				],
				open: (one) => this.stop_folder(one),
			});
		this.$content.on("click", "[data-add-folder]", () => this.add_folder());
	}

	switch_mailbox(one) {
		const esc = frappe.utils.escape_html;
		const set = async (on) => {
			await frappe.xcall("onedesk.one_ai.reading.switches.set_mailbox", { account: one.name, on });
			this.refresh();
		};
		if (one.on) return frappe.confirm(__("Stop OneAI reading new mail in {0}?", [esc(one.email)]), () => set(0));
		if (!one.mine) return frappe.msgprint(__("Only the owner of {0} can turn this on, because OneAI acts on their behalf.", [esc(one.email)]));
		frappe.confirm(
			__("OneAI will read new mail in {0} and its attachments, file them and act on them on your behalf. Scans and photos are read with OneAI credits.", [`<b>${esc(one.email)}</b>`]),
			() => set(1)
		);
	}

	stop_folder(one) {
		frappe.confirm(__("Stop OneAI reading new files in {0} and the folders inside it?", [frappe.utils.escape_html(one.path)]), async () => {
			await frappe.xcall("onedesk.one_ai.reading.switches.set_folder", { folder: one.name, on: 0 });
			this.refresh();
		});
	}

	add_folder() {
		const dialog = new frappe.ui.Dialog({
			title: __("Add Folder"),
			fields: [
				{
					fieldname: "folder",
					fieldtype: "Link",
					options: "File",
					label: __("Folder"),
					reqd: 1,
					get_query: () => ({ filters: { is_folder: 1, one_intake: 0 } }),
				},
				{
					fieldname: "said",
					fieldtype: "HTML",
					options: `<div class="one-shell-quiet">${frappe.utils.escape_html(
						__("New files in this folder and its subfolders are read and filed, using credits.")
					)}</div>`,
				},
			],
			primary_action_label: __("Add"),
			primary_action: async (values) => {
				await frappe.xcall("onedesk.one_ai.reading.switches.set_folder", { folder: values.folder, on: 1 });
				dialog.hide();
				this.refresh();
			},
		});
		dialog.show();
	}
};
