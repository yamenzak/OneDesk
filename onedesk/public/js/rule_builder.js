frappe.provide("onedesk.rules");

// A mail rule as steps, top to bottom (one_mail/flow.py): When mail arrives,
// then each step in turn: an If with conditions in groups that nest, an Ask
// OneAI with a branch for each answer, or an action. A branch is steps too.
// The rule is one object kept here and saved whole; typing changes it in
// place, and only adding, removing or moving a step draws it again.
onedesk.rules.builder = ($into, rule, context) => {
	const esc = frappe.utils.escape_html;
	const id = () => Math.random().toString(36).slice(2, 8);
	const state = { title: rule.title || "", steps: JSON.parse(JSON.stringify(rule.steps || [])) };

	const TEXT_OPS = [
		["contains", __("Contains")],
		["not_contains", __("Doesn't Contain")],
		["is", __("Is")],
		["is_not", __("Isn't")],
		["starts_with", __("Starts With")],
		["ends_with", __("Ends With")],
	];
	const CONDITIONS = [
		{ field: "from", label: __("From"), kind: "text" },
		{ field: "to", label: __("To or Cc"), kind: "text" },
		{ field: "subject", label: __("Subject"), kind: "text" },
		{ field: "text", label: __("Subject or Text"), kind: "text" },
		{ field: "domain", label: __("Sender's Domain"), kind: "text" },
		{ field: "sender_is", label: __("Sender"), kind: "kind" },
		{ field: "outside", label: __("From Outside the Workspace"), kind: "flag" },
		{ field: "starts", label: __("Starts a Conversation"), kind: "flag" },
		{ field: "attachment", label: __("Has an Attachment"), kind: "flag" },
		{ field: "after_hours", label: __("Arrives After Hours"), kind: "flag" },
		{ field: "holiday", label: __("Arrives on a Holiday"), kind: "flag" },
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
		["conversation", __("Once per Conversation")],
		["day", __("Once a Day per Sender")],
		["week", __("Once a Week per Sender")],
		["month", __("Once a Month per Sender")],
	];
	const CREATES = [
		["Lead", __("Lead")],
		["Issue", __("Issue")],
		["Task", __("Task")],
	];

	// Small controls in frappe's own look, bound to one key of one object.
	const select = (options, value, change, label) =>
		$(`<select class="form-control rb-input"></select>`)
			.attr("aria-label", label || "")
			.append(options.map(([v, l]) => $(`<option></option>`).attr("value", v).text(l)))
			.val(value ?? options[0]?.[0])
			.on("change", function () {
				change(this.value);
			});
	const input = (value, change, placeholder) =>
		$(`<input type="text" class="form-control rb-input">`)
			.attr("placeholder", placeholder || "")
			.val(value || "")
			.on("input", function () {
				change(this.value);
			});
	const area = (value, change, placeholder) =>
		$(`<textarea class="form-control rb-input rb-area" rows="4"></textarea>`)
			.attr("placeholder", placeholder || "")
			.val(value || "")
			.on("input", function () {
				change(this.value);
			});
	const icon_button = (icon, title, click) =>
		$(frappe.ui.button.html({ variant: "ghost", size: "sm", icon, title, attrs: { "aria-label": title } })).on("click", (e) => {
			e.preventDefault();
			click();
		});

	// ── Conditions ──────────────────────────────────────────────────────
	const condition_row = (group, one, redraw) => {
		const $row = $(`<div class="rb-condition"></div>`);
		const spec = () => CONDITIONS.find((c) => c.field === one.field) || CONDITIONS[0];
		$row.append(
			select(
				CONDITIONS.map((c) => [c.field, c.label]),
				one.field,
				(v) => {
					one.field = v;
					const kind = spec().kind;
					one.op = kind === "text" ? "contains" : kind === "kind" ? "is" : undefined;
					one.value = kind === "flag" ? true : kind === "kind" ? KINDS[0] : "";
					redraw();
				},
				__("Condition")
			)
		);
		const kind = spec().kind;
		if (kind === "text") {
			$row.append(select(TEXT_OPS, one.op || "contains", (v) => (one.op = v), __("How")));
			$row.append(input(one.value, (v) => (one.value = v), __("Words, separated by commas")));
		} else if (kind === "kind") {
			$row.append(select([["is", __("Is a")], ["is_not", __("Isn't a")]], one.op || "is", (v) => (one.op = v)));
			$row.append(select(KINDS.map((k) => [k, __(k)]), one.value || KINDS[0], (v) => (one.value = v)));
		} else {
			$row.append(select([["1", __("Yes")], ["0", __("No")]], one.value === false ? "0" : "1", (v) => (one.value = v === "1")));
			$row.append(`<span></span>`);
		}
		$row.append(
			icon_button("x", __("Remove"), () => {
				group.items.splice(group.items.indexOf(one), 1);
				redraw();
			})
		);
		return $row;
	};

	const group_box = (group, redraw, nested = null) => {
		group.items = group.items || [];
		const $box = $(`<div class="rb-group"></div>`).toggleClass("rb-group-nested", !!nested);
		const $head = $(`<div class="rb-group-head"></div>`).appendTo($box);
		$head.append(`<span class="rb-quiet">${esc(nested ? __("And this group, where") : __("Where"))}</span>`);
		$head.append(
			select(
				[
					["all", __("All of These Are True")],
					["any", __("Any of These Is True")],
				],
				group.any ? "any" : "all",
				(v) => (group.any = v === "any"),
				__("Match")
			)
		);
		if (nested)
			$head.append(
				icon_button("x", __("Remove Group"), () => {
					nested.items.splice(nested.items.indexOf(group), 1);
					redraw();
				})
			);
		for (const one of group.items) $box.append("items" in one ? group_box(one, redraw, group) : condition_row(group, one, redraw));
		if (!group.items.length) $box.append(`<div class="rb-quiet rb-empty">${esc(__("No conditions, so every message."))}</div>`);
		const $add = $(`<div class="rb-adds"></div>`).appendTo($box);
		$add.append(
			$(frappe.ui.button.html({ label: __("Add Condition"), variant: "subtle", size: "sm", icon: "plus" })).on("click", () => {
				group.items.push({ field: "from", op: "contains", value: "" });
				redraw();
			})
		);
		$add.append(
			$(frappe.ui.button.html({ label: __("Add Group"), variant: "ghost", size: "sm", icon: "brackets" })).on("click", () => {
				group.items.push({ any: true, items: [{ field: "subject", op: "contains", value: "" }] });
				redraw();
			})
		);
		return $box;
	};

	// ── Actions ─────────────────────────────────────────────────────────
	const action_body = (step) => {
		const $body = $(`<div class="rb-fields"></div>`);
		const field = (label, $control, help) =>
			$(`<label class="rb-field"><span class="rb-label">${esc(label)}</span></label>`)
				.append($control)
				.append(help ? `<span class="rb-help">${esc(help)}</span>` : "")
				.appendTo($body);
		if (step.type === "move") {
			if (!step.folder && context.folders[0]) step.folder = context.folders[0].value;
			field(__("Folder"), select(context.folders.map((f) => [f.value, f.label]), step.folder, (v) => (step.folder = v)));
		} else if (step.type === "reply") {
			const withs = [["Text", __("My Own Words")], ...(context.ai ? [["OneAI", __("OneAI Writes It")]] : [])];
			step.with = step.with || "Text";
			step.once = step.once || "conversation";
			field(__("Reply With"), select(withs, step.with, (v) => ((step.with = v), draw())));
			if (step.with === "OneAI") {
				field(__("What It Should Say"), area(step.instruction, (v) => (step.instruction = v), __("Such as sending the price list and promising an answer within a day.")));
				const $review = $(`<input type="checkbox">`).prop("checked", step.review !== 0 && step.review !== false).on("change", function () {
					step.review = this.checked ? 1 : 0;
				});
				field(__("Review Before Sending"), $review, __("It waits as a card for whoever made the rule."));
			} else {
				field(__("Message"), area(step.text, (v) => (step.text = v)), __("{sender_name} and {subject} fill in from the message."));
			}
			field(__("How Often"), select(ONCE, step.once, (v) => (step.once = v)), __("Never to automatic mail or mailing lists."));
		} else if (step.type === "forward") {
			field(__("To"), input(step.to, (v) => (step.to = v), "accounts@example.com"));
		} else if (step.type === "assign" || step.type === "notify") {
			if (!step.user && context.people[0]) step.user = context.people[0].value;
			field(__("Who"), select(context.people.map((p) => [p.value, p.label]), step.user, (v) => (step.user = v)), __("One of the people who use this mailbox."));
		} else if (step.type === "create") {
			step.doctype = step.doctype || "Lead";
			field(__("What"), select(CREATES, step.doctype, (v) => (step.doctype = v)), __("Filed with the message, and yours."));
		} else if (step.type === "stop") {
			$body.append(`<div class="rb-quiet">${esc(__("Rules after this one don't run on this message."))}</div>`);
		} else if (step.type === "link") {
			$body.append(`<div class="rb-quiet">${esc(__("Filed on the customer, supplier or lead the sender is."))}</div>`);
		}
		return $body.children().length ? $body : null;
	};

	// ── Steps ───────────────────────────────────────────────────────────
	const card = (list, step, title, icon) => {
		const $card = $(`<div class="rb-card"></div>`);
		const $head = $(`<div class="rb-card-head"></div>`).appendTo($card);
		$head.append(`<span class="rb-icon">${frappe.utils.icon(icon, "sm")}</span><span class="rb-title">${esc(title)}</span>`);
		const at = list.indexOf(step);
		const $tools = $(`<span class="rb-tools"></span>`).appendTo($head);
		if (at > 0) $tools.append(icon_button("arrow-up", __("Move Up"), () => (list.splice(at - 1, 0, list.splice(at, 1)[0]), draw())));
		if (at < list.length - 1) $tools.append(icon_button("arrow-down", __("Move Down"), () => (list.splice(at + 1, 0, list.splice(at, 1)[0]), draw())));
		$tools.append(icon_button("trash-2", __("Remove Step"), () => (list.splice(at, 1), draw())));
		return $card;
	};

	const branch = (label, list, tone) =>
		$(`<div class="rb-branch"></div>`)
			.addClass(tone ? `rb-branch-${tone}` : "")
			.append(`<div class="rb-branch-label">${esc(label)}</div>`)
			.append(steps_box(list));

	const step_card = (list, step) => {
		if (step.type === "if") {
			step.test = step.test || { any: false, items: [] };
			step.then = step.then || [];
			step.else = step.else || [];
			const $card = card(list, step, __("If"), "split");
			$card.append(group_box(step.test, draw));
			$card.append(branch(__("Then"), step.then, "yes"));
			if (step.else.length || step.open_else) $card.append(branch(__("Otherwise"), step.else, "no"));
			else
				$card.append(
					$(`<button type="button" class="rb-link"></button>`)
						.text(__("Add Otherwise"))
						.on("click", () => ((step.open_else = 1), draw()))
				);
			return $card;
		}
		if (step.type === "ask") {
			step.then = step.then || [];
			step.else = step.else || [];
			const $card = card(list, step, __("Ask OneAI"), "sparkles");
			const $fields = $(`<div class="rb-fields"></div>`).appendTo($card);
			$(`<label class="rb-field"><span class="rb-label">${esc(__("Question"))}</span></label>`)
				.append(
					select(
						[
							["yes", __("Yes or No")],
							["pick", __("Pick One Label")],
						],
						step.ask || "yes",
						(v) => {
							step.ask = v;
							if (v === "pick" && !(step.labels || []).length) step.labels = [{ label: "", then: [] }, { label: "", then: [] }];
							draw();
						}
					)
				)
				.appendTo($fields);
			if (step.ask === "pick") {
				for (const one of step.labels) {
					one.then = one.then || [];
					const $label = $(`<div class="rb-label-row"></div>`)
						.append(input(one.label, (v) => (one.label = v), __("Label, such as Quote Request")))
						.append(input(one.about, (v) => (one.about = v), __("What it means, for OneAI (optional)")))
						.append(icon_button("x", __("Remove"), () => (step.labels.splice(step.labels.indexOf(one), 1), draw())));
					$fields.append($label);
				}
				$fields.append(
					$(frappe.ui.button.html({ label: __("Add Label"), variant: "subtle", size: "sm", icon: "plus" })).on("click", () => {
						step.labels.push({ label: "", then: [] });
						draw();
					})
				);
				for (const one of step.labels) $card.append(branch(__("If It's {0}", [one.label || "…"]), one.then, "yes"));
				$card.append(branch(__("None of These"), step.else, "no"));
			} else {
				$fields.append(
					$(`<label class="rb-field"><span class="rb-label">${esc(__("Is the Message…"))}</span></label>`).append(
						input(step.question, (v) => (step.question = v), __("Such as a complaint, or about an invoice"))
					)
				);
				$card.append(branch(__("Yes"), step.then, "yes"));
				$card.append(branch(__("No"), step.else, "no"));
			}
			return $card;
		}
		const spec = ACTIONS.find((a) => a.type === step.type) || ACTIONS[0];
		const $card = card(list, step, spec.label, spec.icon).addClass("rb-card-action");
		const $body = action_body(step);
		if ($body) $card.append($body);
		return $card;
	};

	// Adding a step: frappe's own menu, checks first, then what to do.
	const add_menu = (list) => {
		const add = (make) => () => {
			list.push(make());
			draw();
		};
		const checks = [
			{ label: __("If"), icon: "split", onclick: add(() => ({ type: "if", id: id(), test: { any: false, items: [{ field: "from", op: "contains", value: "" }] }, then: [], else: [] })) },
		];
		if (context.ai) checks.push({ label: __("Ask OneAI"), icon: "sparkles", onclick: add(() => ({ type: "ask", id: id(), ask: "yes", question: "", then: [], else: [] })) });
		return $(`<div class="rb-add"></div>`).append(
			frappe.ui.dropdown({
				button: { label: __("Add Step"), variant: "ghost", size: "sm", icon: "plus" },
				options: [
					{ group: __("Check"), options: checks },
					{ group: __("Do"), options: ACTIONS.map((one) => ({ label: one.label, icon: one.icon, onclick: add(() => ({ type: one.type })) })) },
				],
			})
		);
	};

	const steps_box = (list) => {
		const $box = $(`<div class="rb-steps"></div>`);
		for (const step of list) $box.append(step_card(list, step));
		return $box.append(add_menu(list));
	};

	const draw = () => {
		const top = $into.scrollTop();
		$into.empty().addClass("rb");
		$(`<label class="rb-field rb-name"><span class="rb-label">${esc(__("Name"))}</span></label>`)
			.append(input(state.title, (v) => (state.title = v), __("Such as Quotes from customers")))
			.appendTo($into);
		$into.append(
			`<div class="rb-card rb-card-start"><div class="rb-card-head"><span class="rb-icon">${frappe.utils.icon("inbox", "sm")}</span><span class="rb-title">${esc(
				__("When mail arrives in {0}'s Inbox", [context.email])
			)}</span></div></div>`
		);
		$into.append(steps_box(state.steps));
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
onedesk.rules.starters = (context) => {
	const make = () => Math.random().toString(36).slice(2, 8);
	const said = [
		{
			key: "blank",
			icon: "file",
			title: __("Blank"),
			about: __("Start from nothing."),
			rule: { title: "", steps: [{ type: "if", id: make(), test: { any: false, items: [{ field: "from", op: "contains", value: "" }] }, then: [], else: [] }] },
		},
		{
			key: "acknowledge",
			icon: "reply",
			title: __("Acknowledge New Mail"),
			about: __("Answer new conversations from outside, once a day to each sender."),
			rule: {
				title: __("Acknowledge New Mail"),
				steps: [
					{
						type: "if",
						id: make(),
						test: { any: false, items: [{ field: "starts", value: true }, { field: "outside", value: true }] },
						then: [{ type: "reply", with: "Text", text: __("Thank you for your message. We received it and will reply soon."), once: "day" }],
						else: [],
					},
				],
			},
		},
		{
			key: "closed",
			icon: "moon",
			title: __("We're Closed"),
			about: __("Answer mail that arrives after hours or on a holiday."),
			rule: {
				title: __("We're Closed"),
				steps: [
					{
						type: "if",
						id: make(),
						test: { any: false, items: [{ field: "outside", value: true }, { any: true, items: [{ field: "after_hours", value: true }, { field: "holiday", value: true }] }] },
						then: [{ type: "reply", with: "Text", text: __("Thank you for your message. Our office is closed now, and we will reply when we open."), once: "day" }],
						else: [],
					},
				],
			},
		},
		{
			key: "customers",
			icon: "users",
			title: __("Customers to a Folder"),
			about: __("Move mail from customers into a folder and file it on their record."),
			rule: {
				title: __("Customers"),
				steps: [
					{
						type: "if",
						id: make(),
						test: { any: false, items: [{ field: "sender_is", op: "is", value: "Customer" }] },
						then: [{ type: "move", folder: (context.folders[0] || {}).value }, { type: "link" }],
						else: [],
					},
				],
			},
		},
	];
	if (context.ai)
		said.push({
			key: "sort",
			icon: "sparkles",
			title: __("Sort With OneAI"),
			about: __("OneAI reads each message and picks a label. Each label has its own steps."),
			rule: {
				title: __("Sort With OneAI"),
				steps: [{ type: "ask", id: make(), ask: "pick", labels: [{ label: __("Quote Request"), then: [] }, { label: __("Complaint"), then: [] }], then: [], else: [] }],
			},
		});
	return said;
};
