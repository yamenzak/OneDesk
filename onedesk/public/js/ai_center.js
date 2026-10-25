// AICenter (docs/AICENTER.md): OneAI for the workspace (one_ai/center.py).
// For administrators: OneAI on or off and its tier, Knowledge, what each
// module has OneAI do on its own, which records get a summary, and what was
// used. For everybody: Yours, what OneAI keeps about them. From the bottom
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
		description: __("Whether OneAI answers in this workspace, and how carefully."),
		actions: [{ label: __("Add Credits"), icon: "plus", click: () => frappe.set_route("workspace-settings", { section: "plan" }) }],
		async render(panel) {
			const said = await frappe.xcall(C + "state", {}, "GET");
			const $body = panel.body.empty();
			const $list = $(`<div class="one-set-list"></div>`).appendTo($body);
			const $on = kit.row({ lead: kit.glyph("oneai"), title: __("OneAI"), sub: esc(__("When off, nobody can ask OneAI, and nothing it does on its own runs.")) }).appendTo($list);
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
				kit.row({ lead: kit.glyph("coins"), title: __("Left"), end: `<span class="one-set-value">${esc(credits(said.credits))}</span>` }).appendTo(
					$(`<div class="one-set-list"></div>`).appendTo($body)
				);
			}
		},
	};

	// What OneAI should know about the company, which it reads as facts.
	const knowledge_tab = {
		id: "knowledge",
		label: __("Knowledge"),
		icon: "book-open",
		title: __("Knowledge"),
		description: __("What OneAI should know about the company, such as its facts, its terms and how work is done here."),
		actions: [{ label: __("New Knowledge"), icon: "plus", click: () => frappe.new_doc("AI Knowledge") }],
		async render(panel) {
			const rows = await frappe.xcall(C + "knowledge", {}, "GET");
			const $list = $(`<div class="one-set-list"></div>`).appendTo(panel.body.empty());
			if (!rows.length) return $list.append(kit.empty(__("Nothing written down yet.")));
			for (const one of rows) {
				kit.row({ lead: kit.glyph("book-open"), title: one.title, sub: esc(one.applies_to ? __(one.applies_to) : __("Everything")), chevron: true })
					.toggleClass("one-set-off", !one.enabled)
					.on("click", () => frappe.set_route("Form", "AI Knowledge", one.name))
					.appendTo($list);
			}
		},
	};

	// A module's part: what OneAI does there on its own.
	const part_tab = (part) => ({
		id: `part:${part.module}`,
		label: part.module,
		icon_html: frappe.utils.icon(onedesk.brand.mark_of(part.module.replace(/^One/, "")) || "oneai", "sm"),
		title: part.module,
		description: part.mailboxes
			? __("What OneAI does with each mailbox's new mail. Each is set on the mailbox.")
			: __("What OneAI does in {0} on its own. Each uses credits.", [part.module]),
		render(panel) {
			const $list = $(`<div class="one-set-list"></div>`).appendTo(panel.body.empty());
			if (part.mailboxes) {
				if (!part.mailboxes.length) return $list.append(kit.empty(__("No mailboxes receive mail yet.")));
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
				const control = frappe.ui.form.make_control({
					df: { fieldtype: "Int", fieldname: job.key, label: "" },
					parent: $(`<span class="one-set-number"></span>`).appendTo($end),
					render_input: true,
				});
				control.set_value(job.value || 0);
				control.$input.attr("aria-label", job.label).on("change", async () => {
					await frappe.xcall(C + "set_job", { key: job.key, value: control.get_value() || 0 });
					kit.saved();
				});
			}
		},
	});

	// Which kinds of record carry a few sentences at the top.
	const summaries_tab = {
		id: "summaries",
		label: __("Summaries"),
		icon: "notebook-text",
		title: __("Summaries"),
		description: __("A few sentences at the top of each record, written again when something happens to it, at most once a day."),
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
		description: __("Credits each job used in the last thirty days."),
		actions: [{ label: __("Credit Usage"), icon: "external-link", click: () => frappe.set_route("query-report", "AI Credits", { by: "Job" }) }],
		async render(panel) {
			const said = await frappe.xcall(C + "usage", {}, "GET");
			const $list = $(`<div class="one-set-list"></div>`).appendTo(panel.body.empty());
			if (!said.reached) return $list.append(kit.empty(__("The account could not be reached just now.")));
			if (!said.jobs.length) return $list.append(kit.empty(__("Nothing used yet.")));
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
		description: __("What OneAI remembers about you. Only you can see it."),
		actions: [{ label: __("Add Memory"), icon: "plus", click: (panel) => remember(panel) }],
		async render(panel) {
			const said = await frappe.xcall(C + "yours", {}, "GET");
			const $body = panel.body.empty();
			const $list = $(`<div class="one-set-list"></div>`).appendTo($body);
			if (!said.facts.length) $list.append(kit.empty(__("OneAI remembers nothing about you yet.")));
			for (const one of said.facts) {
				const $row = kit
					.row({ lead: kit.glyph("brain"), title: one.fact, sub: esc([one.about_title, frappe.datetime.prettyDate(one.creation)].filter(Boolean).join(" · ")) })
					.appendTo($list);
				$row.find(".one-set-title").on("click", () => remember(panel, one));
				kit.remove(() => frappe.xcall("onedesk.one.settings.forget", { name: one.name }).then(() => panel.refresh())).appendTo($row.find(".one-set-end"));
			}
			if (said.knowledge.length) {
				$body.append(kit.heading(__("Workspace Knowledge")));
				const $known = $(`<div class="one-set-list"></div>`).appendTo($body);
				for (const one of said.knowledge) kit.row({ lead: kit.glyph("book-open"), title: one.title, sub: esc(one.applies_to || __("Everything")) }).appendTo($known);
			}
		},
	};

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
				await frappe.xcall("onedesk.one.settings.keep", { ...values, name: one ? one.name : null });
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
				{ group: null, items: module ? [] : [oneai_tab, knowledge_tab] },
				{ group: module ? null : __("Modules"), items: [...mine.map(part_tab), ...(module ? [] : [summaries_tab])] },
				{ group: null, items: module ? [] : [usage_tab, yours_tab] },
		  ]
		: [{ group: null, items: [yours_tab] }];
	const shown = tabs.filter((group) => group.items.length);
	const ids = shown.flatMap((group) => group.items.map((item) => item.id));
	const dialog = new onedesk.module_settings.Dialog({
		title: "AICenter",
		module,
		center: "ai",
		tabs: shown,
		default_tab: ids.includes(at) ? at : ids[0],
		expand: module
			? () => {
					dialog.hide();
					onedesk.ai_center.open();
			  }
			: null,
	});
	dialog.$wrapper.addClass("one-set one-ai-center");
	dialog.show();
	return dialog;
};
