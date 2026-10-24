frappe.provide("onedesk.rules");

// A mail rule as steps, top to bottom (one_mail/flow.py), drawn so it
// reads as sentences: each step is one line on a timeline, "If the sender is
// a Customer and it arrives after hours", "Move it to Archive", and every
// part that can change is a chip. A choice opens frappe's menu, a short
// blank is typed in place, and long words (a reply) open a small dialog.
// Branches hang under their step as timelines of their own. The rule is
// one object kept here and saved whole.
onedesk.rules.builder = ($into, rule, context) => {
	const esc = frappe.utils.escape_html;
	const id = () => Math.random().toString(36).slice(2, 8);
	const state = { title: rule.title || "", steps: JSON.parse(JSON.stringify(rule.steps || [])) };

	const TEXT = [
		["from", __("the sender's name or address")],
		["to", __("To or Cc")],
		["subject", __("the subject")],
		["text", __("the subject or text")],
		["domain", __("the sender's domain")],
	];
	const OPS = [
		["contains", __("contains")],
		["not_contains", __("doesn't contain")],
		["is", __("is")],
		["is_not", __("isn't")],
		["starts_with", __("starts with")],
		["ends_with", __("ends with")],
	];
	const FLAGS = [
		["outside", __("it's from outside the workspace"), __("it's from inside the workspace")],
		["starts", __("it starts a conversation"), __("it's a reply")],
		["attachment", __("it has an attachment"), __("it has no attachment")],
		["after_hours", __("it arrives after hours"), __("it arrives in working hours")],
		["holiday", __("it arrives on a holiday"), __("it doesn't arrive on a holiday")],
	];
	const KINDS = ["Customer", "Supplier", "Lead", "Contact", "Employee"];
	const ACTIONS = [
		{ type: "move", icon: "folder-input", label: __("Move to Folder") },
		{ type: "read", icon: "mail-open", label: __("Mark as Read") },
		{ type: "star", icon: "star", label: __("Star") },
		{ type: "junk", icon: "shield-alert", label: __("Move to Junk") },
		{ type: "reply", icon: "reply", label: __("Reply") },
		{ type: "forward", icon: "forward", label: __("Forward") },
		{ type: "assign", icon: "user-check", label: __("Assign") },
		{ type: "notify", icon: "bell", label: __("Tell Someone") },
		{ type: "link", icon: "link", label: __("Link to Their Record") },
		{ type: "create", icon: "file-plus", label: __("Create a Record") },
		{ type: "stop", icon: "octagon", label: __("Stop Here") },
	];
	const ONCE = [
		["conversation", __("once per conversation")],
		["day", __("once a day to each sender")],
		["week", __("once a week to each sender")],
		["month", __("once a month to each sender")],
	];
	const CREATES = [
		["Lead", __("lead")],
		["Issue", __("issue")],
		["Task", __("task")],
	];

	// ── The pieces a sentence is made of ────────────────────────────────
	const words = (text) => $(`<span class="rb-words"></span>`).text(text);
	// A choice: the chip says the value, clicking opens frappe's menu.
	const chip = (options, value, change) => {
		const said = options.find(([v]) => v === value) || options[0] || ["", ""];
		const $chip = $(`<button type="button" class="rb-chip"></button>`).html(
			`<span>${esc(said[1] || "…")}</span>${frappe.utils.icon("chevron-down", "xs")}`
		);
		new frappe.ui.Dropdown({
			trigger: $chip,
			options: options.map(([v, l]) => ({ label: l, onclick: () => change(v) })),
		});
		return $chip;
	};
	// A short blank, typed in place, as wide as what is in it.
	const blank = (value, change, placeholder) => {
		const $input = $(`<input type="text" class="rb-blank">`).attr("placeholder", placeholder || "").val(value || "");
		const fit = () => $input.attr("size", Math.max(($input.val() || placeholder || "").length, 4) + 1);
		fit();
		return $input.on("input", function () {
			change(this.value);
			fit();
		});
	};
	// Long words: the chip quotes the start, clicking opens a dialog.
	const quote = (text, empty, open) =>
		$(`<button type="button" class="rb-chip rb-quote"></button>`)
			.text(text ? `“${text.length > 48 ? text.slice(0, 48) + "…" : text}”` : empty)
			.toggleClass("rb-chip-empty", !text)
			.on("click", open);
	const line = (...parts) => $(`<div class="rb-line"></div>`).append(parts.filter(Boolean));

	// ── A step on the timeline: its dot, its sentence, its tools ─────────
	const node = (list, step, icon, $line, tone = "") => {
		const $node = $(`<div class="rb-node"></div>`).addClass(tone);
		$node.append(`<span class="rb-dot">${frappe.utils.icon(icon, "sm")}</span>`);
		const $body = $(`<div class="rb-node-body"></div>`).appendTo($node);
		const at = list.indexOf(step);
		const $tools = $(`<span class="rb-tools"></span>`);
		const tool = (icon_, title, click) =>
			$(frappe.ui.button.html({ variant: "ghost", size: "xs", icon: icon_, title, attrs: { "aria-label": title } })).on("click", click);
		if (at > 0) $tools.append(tool("arrow-up", __("Move Up"), () => (list.splice(at - 1, 0, list.splice(at, 1)[0]), draw())));
		if (at < list.length - 1) $tools.append(tool("arrow-down", __("Move Down"), () => (list.splice(at + 1, 0, list.splice(at, 1)[0]), draw())));
		$tools.append(tool("x", __("Remove Step"), () => (list.splice(at, 1), draw())));
		$body.append($(`<div class="rb-head"></div>`).append($line, $tools));
		return { $node, $body };
	};

	const branch = ($body, label, list) =>
		$body.append($(`<div class="rb-branch"></div>`).append(`<div class="rb-branch-label">${esc(label)}</div>`, timeline(list)));

	// ── If: one sentence per condition, joined by and / or ──────────────
	const condition = (group, one) => {
		const remove = $(`<button type="button" class="rb-x"></button>`)
			.attr({ title: __("Remove"), "aria-label": __("Remove") })
			.html(frappe.utils.icon("x", "xs"))
			.on("click", () => (group.items.splice(group.items.indexOf(one), 1), draw()));
		const what = [
			...TEXT,
			["sender_is", __("the sender")],
			...FLAGS.flatMap(([field, yes, no]) => [
				[`${field}:1`, yes],
				[`${field}:0`, no],
			]),
		];
		const field_chip = (shown) =>
			chip(
				what.map(([v, l], i) => [v, i === TEXT.length ? __("the sender is a…") : l]),
				shown,
				(v) => {
					const [field, flag] = v.split(":");
					Object.assign(one, { field, op: undefined, value: undefined });
					if (flag !== undefined) one.value = flag === "1";
					else if (field === "sender_is") Object.assign(one, { op: "is", value: KINDS[0] });
					else Object.assign(one, { op: "contains", value: "" });
					draw();
				}
			);
		if (FLAGS.some(([f]) => f === one.field)) return [field_chip(`${one.field}:${one.value === false ? 0 : 1}`), remove];
		if (one.field === "sender_is")
			return [
				words(__("the sender")),
				chip(
					[
						["is", __("is a")],
						["is_not", __("isn't a")],
					],
					one.op || "is",
					(v) => ((one.op = v), draw())
				),
				chip(KINDS.map((k) => [k, __(k)]), one.value || KINDS[0], (v) => ((one.value = v), draw())),
				remove,
			];
		return [
			field_chip(one.field),
			chip(OPS, one.op || "contains", (v) => ((one.op = v), draw())),
			blank(one.value, (v) => (one.value = v), __("words, with commas")),
			remove,
		];
	};

	const conditions = (group, first_word) => {
		group.items = group.items || [];
		const $box = $(`<div class="rb-conditions"></div>`);
		const join = () =>
			chip(
				[
					["and", __("and")],
					["or", __("or")],
				],
				group.any ? "or" : "and",
				(v) => ((group.any = v === "or"), draw())
			).addClass("rb-join");
		group.items.forEach((one, i) => {
			const lead = i === 0 ? words(first_word) : join();
			if ("items" in one) {
				$box.append(line(lead, words(one.any ? __("any of these:") : __("all of these:"))));
				$box.append($(`<div class="rb-subgroup"></div>`).append(conditions(one, "")));
			} else $box.append(line(lead, ...condition(group, one)));
		});
		if (!group.items.length) $box.append(line(words(first_word), words(__("any message")).addClass("rb-muted")));
		const add = (label, make) =>
			$(`<button type="button" class="rb-add-link"></button>`)
				.html(`${frappe.utils.icon("plus", "xs")}<span>${esc(label)}</span>`)
				.on("click", () => (group.items.push(make()), draw()));
		$box.append(
			line(
				add(__("Condition"), () => ({ field: "subject", op: "contains", value: "" })),
				first_word ? add(__("Group"), () => ({ any: true, items: [{ field: "subject", op: "contains", value: "" }] })) : null
			).addClass("rb-adds")
		);
		return $box;
	};

	// ── Actions, each one sentence ──────────────────────────────────────
	const reply_dialog = (step) => {
		const ai = step.with === "OneAI";
		const dialog = new frappe.ui.Dialog({
			title: __("Reply"),
			fields: [
				...(context.ai
					? [
							{
								fieldname: "with",
								fieldtype: "Select",
								label: __("Written By"),
								options: [
									{ value: "Text", label: __("My Own Words") },
									{ value: "OneAI", label: __("OneAI") },
								],
								default: step.with || "Text",
								change: () => {
									const on = dialog.get_value("with") === "OneAI";
									dialog.set_df_property("text", "hidden", on);
									dialog.set_df_property("instruction", "hidden", !on);
									dialog.set_df_property("records", "hidden", !on);
								},
							},
					  ]
					: []),
				{
					fieldname: "text",
					fieldtype: "Small Text",
					label: __("Message"),
					default: step.text || "",
					hidden: ai,
					description: __("{sender_name} and {subject} fill in from the message."),
				},
				{
					fieldname: "instruction",
					fieldtype: "Small Text",
					label: __("Instruction"),
					default: step.instruction || "",
					hidden: !ai,
					description: __("What OneAI's reply should do, such as answering from their orders and promising an answer within a day. OneAI writes the reply itself."),
				},
				{
					fieldname: "records",
					fieldtype: "Check",
					label: __("Their Records"),
					default: step.records ? 1 : 0,
					hidden: !ai,
					description: __("OneAI may read the orders, invoices and deliveries the sender sees on the portal. Only when the sender's address is verified."),
				},
			],
			primary_action_label: __("Done"),
			primary_action: (values) => {
				Object.assign(step, {
					with: values.with || "Text",
					text: values.text || "",
					instruction: values.instruction || "",
					records: values.records ? 1 : 0,
				});
				dialog.hide();
				draw();
			},
		});
		dialog.show();
	};

	const action = (list, step) => {
		const spec = ACTIONS.find((a) => a.type === step.type) || ACTIONS[0];
		const parts = {
			move: () => [
				words(__("Move it to")),
				chip(context.folders.map((f) => [f.value, f.label]), (step.folder = step.folder || (context.folders[0] || {}).value), (v) => ((step.folder = v), draw())),
			],
			read: () => [words(__("Mark it as read"))],
			star: () => [words(__("Star it"))],
			junk: () => [words(__("Move it to Junk"))],
			reply: () =>
				step.with === "OneAI"
					? [
							words(__("Have OneAI write a reply that follows")),
							quote(step.instruction, __("your instruction"), () => reply_dialog(step)).prepend(`${frappe.utils.icon("oneai", "xs")} `),
							chip(
								[
									["1", __("reading their records")],
									["0", __("without their records")],
								],
								step.records ? "1" : "0",
								(v) => ((step.records = Number(v)), draw())
							),
							chip(ONCE, (step.once = step.once || "conversation"), (v) => ((step.once = v), draw())),
					  ]
					: [
							words(__("Reply with")),
							quote(step.text, __("your message"), () => reply_dialog(step)),
							chip(ONCE, (step.once = step.once || "conversation"), (v) => ((step.once = v), draw())),
					  ],
			forward: () => [words(__("Forward it to")), blank(step.to, (v) => (step.to = v), "name@example.com")],
			assign: () => [
				words(__("Assign it to")),
				chip(context.people.map((p) => [p.value, p.label]), (step.user = step.user || (context.people[0] || {}).value), (v) => ((step.user = v), draw())),
			],
			notify: () => [
				words(__("Tell")),
				chip(context.people.map((p) => [p.value, p.label]), (step.user = step.user || (context.people[0] || {}).value), (v) => ((step.user = v), draw())),
				words(__("on the bell")),
			],
			link: () => [words(__("Link it to the sender's customer, supplier or lead"))],
			create: () => [words(__("Create a")), chip(CREATES, (step.doctype = step.doctype || "Lead"), (v) => ((step.doctype = v), draw())), words(__("from it"))],
			stop: () => [words(__("Stop, and skip the rules after this one"))],
		}[step.type];
		return node(list, step, spec.icon, line(...(parts ? parts() : [])), step.type === "stop" ? "rb-node-stop" : "").$node;
	};

	// ── Ask OneAI ───────────────────────────────────────────────────────
	const label_dialog = (step, one) => {
		const dialog = new frappe.ui.Dialog({
			title: one ? __("Label") : __("New Label"),
			fields: [
				{ fieldname: "label", fieldtype: "Data", label: __("Label"), reqd: 1, default: one?.label || "", description: __("Such as Quote Request.") },
				{ fieldname: "about", fieldtype: "Small Text", label: __("Meaning"), default: one?.about || "", description: __("Helps OneAI tell it apart. Optional.") },
			],
			primary_action_label: __("Done"),
			primary_action: ({ label, about }) => {
				if (one) Object.assign(one, { label, about });
				else step.labels.push({ label, about, then: [] });
				dialog.hide();
				draw();
			},
			secondary_action_label: one ? __("Remove") : undefined,
			secondary_action: one ? () => (step.labels.splice(step.labels.indexOf(one), 1), dialog.hide(), draw()) : undefined,
		});
		dialog.show();
	};

	const ask = (list, step) => {
		step.then = step.then || [];
		step.else = step.else || [];
		const mode = chip(
			[
				["yes", __("whether it's")],
				["pick", __("which of these it is:")],
			],
			step.ask || "yes",
			(v) => {
				step.ask = v;
				step.labels = step.labels || [];
				draw();
			}
		);
		let $line;
		if (step.ask === "pick") {
			step.labels = step.labels || [];
			const chips = step.labels.map((one) =>
				$(`<button type="button" class="rb-chip rb-label"></button>`)
					.text(one.label || "…")
					.on("click", () => label_dialog(step, one))
			);
			const add = $(`<button type="button" class="rb-add-link"></button>`)
				.html(`${frappe.utils.icon("plus", "xs")}<span>${esc(__("Label"))}</span>`)
				.on("click", () => label_dialog(step, null));
			$line = line(words(__("Ask OneAI")), mode, ...chips, add);
		} else {
			$line = line(words(__("Ask OneAI")), mode, blank(step.question, (v) => (step.question = v), __("a complaint")));
		}
		const { $node, $body } = node(list, step, "oneai", $line, "rb-node-ai");
		if (!context.reads) {
			const $note = $(`<div class="rb-unread"></div>`)
				.append($("<span></span>").text(__("This step won't run yet, because OneAI isn't reading this mailbox's new mail.")))
				.prependTo($body);
			if (context.to_oneai)
				$(`<button type="button" class="rb-unread-go"></button>`).text(__("Turn It On")).on("click", context.to_oneai).appendTo($note);
		}
		if (step.ask === "pick") {
			for (const one of step.labels) {
				one.then = one.then || [];
				branch($body, __("If it's {0}", [one.label || "…"]), one.then);
			}
			branch($body, __("If it's none of these"), step.else);
		} else {
			branch($body, __("If yes"), step.then);
			branch($body, __("If not"), step.else);
		}
		return $node;
	};

	// ── If ──────────────────────────────────────────────────────────────
	const when = (list, step) => {
		step.test = step.test || { any: false, items: [] };
		step.then = step.then || [];
		step.else = step.else || [];
		const { $node, $body } = node(list, step, "split", conditions(step.test, __("If")), "rb-node-if");
		branch($body, __("Then"), step.then);
		if (step.else.length || step.open_else) branch($body, __("Otherwise"), step.else);
		else
			$body.append(
				$(`<button type="button" class="rb-add-link rb-otherwise"></button>`)
					.html(`${frappe.utils.icon("plus", "xs")}<span>${esc(__("Otherwise"))}</span>`)
					.on("click", () => ((step.open_else = 1), draw()))
			);
		return $node;
	};

	// ── A timeline: its steps, then Add Step ────────────────────────────
	const timeline = (list) => {
		const $list = $(`<div class="rb-timeline"></div>`);
		for (const step of list) $list.append(step.type === "if" ? when(list, step) : step.type === "ask" ? ask(list, step) : action(list, step));
		const add = (make) => () => {
			list.push(make());
			draw();
		};
		const checks = [
			{ label: __("If"), icon: "split", onclick: add(() => ({ type: "if", id: id(), test: { any: false, items: [{ field: "from", op: "contains", value: "" }] }, then: [], else: [] })) },
		];
		if (context.ai) checks.push({ label: __("Ask OneAI"), icon: "oneai", onclick: add(() => ({ type: "ask", id: id(), ask: "yes", question: "", then: [], else: [] })) });
		const $add = $(`<button type="button" class="rb-add-step"></button>`).html(`${frappe.utils.icon("plus", "sm")}<span>${esc(__("Add Step"))}</span>`);
		new frappe.ui.Dropdown({
			trigger: $add,
			options: [
				{ group: __("Check"), options: checks },
				{ group: __("Do"), options: ACTIONS.map((one) => ({ label: one.label, icon: one.icon, onclick: add(() => ({ type: one.type })) })) },
			],
		});
		return $list.append($(`<div class="rb-node rb-node-add"></div>`).append(`<span class="rb-dot rb-dot-add"></span>`, $add));
	};

	const draw = () => {
		const top = $into.scrollTop();
		$into.empty().addClass("rb");
		$into.append(
			$(`<input type="text" class="rb-name">`)
				.attr({ placeholder: __("Name this rule"), "aria-label": __("Name") })
				.val(state.title)
				.on("input", function () {
					state.title = this.value;
				})
		);
		const $start = $(`<div class="rb-node rb-node-start"></div>`).append(
			`<span class="rb-dot">${frappe.utils.icon("inbox", "sm")}</span>`,
			$(`<div class="rb-node-body"></div>`).append(line(words(__("When a message arrives in {0}", [context.email]))))
		);
		$into.append($(`<div class="rb-timeline rb-root"></div>`).append($start), timeline(state.steps).addClass("rb-root"));
		$into.scrollTop(top);
	};

	draw();
	return { value: () => ({ title: state.title, steps: onedesk.rules.strip(state.steps) }) };
};

// What is saved: the steps without what only the builder uses.
onedesk.rules.strip = (steps) =>
	(steps || []).map((one) => {
		const said = { ...one };
		delete said.open_else;
		if (said.then) said.then = onedesk.rules.strip(said.then);
		if (said.else) said.else = onedesk.rules.strip(said.else);
		if (said.labels) said.labels = said.labels.map((label) => ({ ...label, then: onedesk.rules.strip(label.then) }));
		return said;
	});

// Rules to start from: what a mailbox most often wants, ready to change.
// Whether a rule asks OneAI anything or has OneAI write a reply.
onedesk.rules.uses_ai = (steps) =>
	(steps || []).some(
		(step) =>
			step.type === "ask" ||
			(step.type === "reply" && step.with === "OneAI") ||
			onedesk.rules.uses_ai(step.then) ||
			onedesk.rules.uses_ai(step.else) ||
			(step.labels || []).some((label) => onedesk.rules.uses_ai(label.then))
	);

onedesk.rules.starters = (context) => {
	const make = () => Math.random().toString(36).slice(2, 8);
	const folder = (...names) => {
		const found = context.folders.find((one) => names.some((name) => (one.label || "").toLowerCase().includes(name)));
		return (found || context.folders[0] || {}).value;
	};
	const person = (context.people.find((one) => one.value === frappe.session.user) || context.people[0] || {}).value;
	const when = (items, then, { any = false, otherwise = [] } = {}) => ({ type: "if", id: make(), test: { any, items }, then, else: otherwise });
	const reply = (text, once = "conversation") => ({ type: "reply", with: "Text", text, once });
	const said = [
		{
			group: "",
			key: "blank",
			icon: "file",
			title: __("Blank"),
			about: __("Start from nothing."),
			rule: { title: "", steps: [when([{ field: "from", op: "contains", value: "" }], [])] },
		},
		{
			group: __("Replies"),
			key: "auto_reply",
			icon: "reply",
			title: __("Auto Reply"),
			about: __("Answer every message with the same words, once in each conversation."),
			rule: { title: __("Auto Reply"), steps: [reply(__("Thank you for your message. We received it and will reply soon."))] },
		},
		{
			group: __("Replies"),
			key: "acknowledge",
			icon: "mail-check",
			title: __("Acknowledge New Mail"),
			about: __("Answer new conversations from outside, once a day to each sender."),
			rule: {
				title: __("Acknowledge New Mail"),
				steps: [when([{ field: "starts", value: true }, { field: "outside", value: true }], [reply(__("Thank you for your message. We received it and will reply soon."), "day")])],
			},
		},
		{
			group: __("Replies"),
			key: "closed",
			icon: "moon",
			title: __("We're Closed"),
			about: __("Answer mail that arrives after hours or on a holiday."),
			rule: {
				title: __("We're Closed"),
				steps: [
					when(
						[{ field: "outside", value: true }, { any: true, items: [{ field: "after_hours", value: true }, { field: "holiday", value: true }] }],
						[reply(__("Thank you for your message. Our office is closed now, and we will reply when we open."), "day")]
					),
				],
			},
		},
		{
			group: __("Replies"),
			key: "attachment_received",
			icon: "paperclip",
			title: __("Confirm Documents Received"),
			about: __("Tell suppliers their attached documents arrived."),
			rule: {
				title: __("Confirm Documents Received"),
				steps: [
					when(
						[{ field: "sender_is", op: "is", value: "Supplier" }, { field: "attachment", value: true }],
						[reply(__("Thank you. We received your documents and will review them."))]
					),
				],
			},
		},
		{
			group: __("Sorting"),
			key: "newsletters",
			icon: "newspaper",
			title: __("Newsletters to a Folder"),
			about: __("Move newsletters and notices out of the Inbox, already read."),
			rule: {
				title: __("Newsletters"),
				steps: [
					when(
						[
							{ field: "from", op: "contains", value: "newsletter, noreply, no-reply" },
							{ field: "text", op: "contains", value: __("unsubscribe") },
						],
						[{ type: "move", folder: folder("newsletter", "archive") }, { type: "read" }],
						{ any: true }
					),
				],
			},
		},
		{
			group: __("Sorting"),
			key: "invoices",
			icon: "receipt",
			title: __("Invoices to a Folder"),
			about: __("Star mail with an invoice attached and move it to a folder."),
			rule: {
				title: __("Invoices"),
				steps: [
					when(
						[{ field: "subject", op: "contains", value: __("invoice, receipt, statement") }, { field: "attachment", value: true }],
						[{ type: "move", folder: folder("invoice", "account") }, { type: "star" }]
					),
				],
			},
		},
		{
			group: __("Sorting"),
			key: "customers",
			icon: "users",
			title: __("Customers to a Folder"),
			about: __("Move mail from customers into a folder and file it on their record."),
			rule: {
				title: __("Customers"),
				steps: [when([{ field: "sender_is", op: "is", value: "Customer" }], [{ type: "move", folder: folder("customer") }, { type: "link" }])],
			},
		},
		{
			group: __("Sorting"),
			key: "important",
			icon: "star",
			title: __("Important Sender"),
			about: __("Star mail from one address or domain and tell someone on the bell."),
			rule: {
				title: __("Important Sender"),
				steps: [when([{ field: "domain", op: "is", value: "" }], [{ type: "star" }, { type: "notify", user: person }])],
			},
		},
		{
			group: __("Sorting"),
			key: "block",
			icon: "shield-alert",
			title: __("Block a Sender"),
			about: __("Send mail from an address or domain to Junk, and run no other rule on it."),
			rule: { title: __("Block a Sender"), steps: [when([{ field: "domain", op: "is", value: "" }], [{ type: "junk" }, { type: "stop" }])] },
		},
		{
			group: __("People and Records"),
			key: "support",
			icon: "life-buoy",
			title: __("Support Requests"),
			about: __("Make an issue from mail asking for help, and assign it to someone."),
			rule: {
				title: __("Support Requests"),
				steps: [
					when(
						[{ field: "text", op: "contains", value: __("help, problem, not working, broken") }, { field: "outside", value: true }],
						[{ type: "create", doctype: "Issue" }, { type: "assign", user: person }]
					),
				],
			},
		},
		{
			group: __("People and Records"),
			key: "leads",
			icon: "user-plus",
			title: __("New Leads"),
			about: __("Make a lead from a first message by someone the workspace doesn't know yet."),
			rule: {
				title: __("New Leads"),
				steps: [
					when(
						[
							{ field: "starts", value: true },
							{ field: "outside", value: true },
							{ field: "sender_is", op: "is_not", value: "Customer" },
							{ field: "sender_is", op: "is_not", value: "Supplier" },
							{ field: "sender_is", op: "is_not", value: "Lead" },
						],
						[{ type: "create", doctype: "Lead" }, { type: "notify", user: person }]
					),
				],
			},
		},
		{
			group: __("People and Records"),
			key: "tasks",
			icon: "list-checks",
			title: __("Tasks From Mail"),
			about: __("Make a task from mail whose subject starts with Task."),
			rule: {
				title: __("Tasks From Mail"),
				steps: [when([{ field: "subject", op: "starts_with", value: __("Task") }], [{ type: "create", doctype: "Task" }, { type: "read" }])],
			},
		},
		{
			group: __("People and Records"),
			key: "forward_bills",
			icon: "forward",
			title: __("Forward Supplier Bills"),
			about: __("Send a copy of supplier mail with an attachment to another address."),
			rule: {
				title: __("Forward Supplier Bills"),
				steps: [when([{ field: "sender_is", op: "is", value: "Supplier" }, { field: "attachment", value: true }], [{ type: "forward", to: "" }, { type: "link" }])],
			},
		},
		{
			group: __("People and Records"),
			key: "after_hours_team",
			icon: "bell",
			title: __("Urgent After Hours"),
			about: __("Tell someone when customer mail marked urgent arrives after hours."),
			rule: {
				title: __("Urgent After Hours"),
				steps: [
					when(
						[{ field: "sender_is", op: "is", value: "Customer" }, { field: "after_hours", value: true }, { field: "subject", op: "contains", value: __("urgent, asap") }],
						[{ type: "star" }, { type: "notify", user: person }]
					),
				],
			},
		},
	];
	if (context.ai)
		said.push(
			{
				group: __("With OneAI"),
				key: "sort",
				icon: "oneai",
				title: __("Sort by Topic"),
				about: __("OneAI reads each message and picks a label. Each label has its own steps."),
				rule: {
					title: __("Sort by Topic"),
					steps: [
						{
							type: "ask",
							id: make(),
							ask: "pick",
							labels: [
								{ label: __("Quote Request"), about: __("Someone asks for a price or a quotation."), then: [{ type: "create", doctype: "Lead" }, { type: "notify", user: person }] },
								{ label: __("Complaint"), about: __("Someone is unhappy with what they got or how they were treated."), then: [{ type: "star" }, { type: "create", doctype: "Issue" }] },
								{ label: __("Invoice"), about: __("A bill, an invoice or a statement to pay."), then: [{ type: "move", folder: folder("invoice", "account") }] },
							],
							then: [],
							else: [],
						},
					],
				},
			},
			{
				group: __("With OneAI"),
				key: "upset",
				icon: "siren",
				title: __("Upset or Urgent"),
				about: __("OneAI says whether the sender is upset or in a hurry, and someone is told."),
				rule: {
					title: __("Upset or Urgent"),
					steps: [
						{
							type: "ask",
							id: make(),
							ask: "yes",
							question: __("Is the sender upset, or do they need an answer today?"),
							then: [{ type: "star" }, { type: "notify", user: person }],
							else: [],
						},
					],
				},
			},
			{
				group: __("With OneAI"),
				key: "draft",
				icon: "pen-line",
				title: __("Answer From Their Records"),
				about: __("OneAI answers customers' questions about orders, deliveries and prices from their own records."),
				rule: {
					title: __("Answer From Their Records"),
					steps: [
						when(
							[{ field: "sender_is", op: "is", value: "Customer" }],
							[
								{
									type: "ask",
									id: make(),
									ask: "yes",
									question: __("Is this a question about an order, a delivery or a price?"),
									then: [
										{
											type: "reply",
											with: "OneAI",
											instruction: __("Answer the question from their records where they answer it. If they don't, say we will follow up within a day."),
											records: 1,
											once: "conversation",
										},
									],
									else: [],
								},
							]
						),
					],
				},
			},
			{
				group: __("With OneAI"),
				key: "ai_reply",
				icon: "bot",
				title: __("Auto Reply in Their Language"),
				about: __("OneAI answers new conversations from outside, in the sender's language."),
				rule: {
					title: __("Auto Reply in Their Language"),
					steps: [
						when(
							[{ field: "starts", value: true }, { field: "outside", value: true }],
							[
								{
									type: "reply",
									with: "OneAI",
									instruction: __("Thank them, say what you understood they need, and say we will reply soon."),
									once: "conversation",
								},
							]
						),
					],
				},
			}
		);
	return said;
};
