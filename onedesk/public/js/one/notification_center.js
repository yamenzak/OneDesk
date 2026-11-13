// NotificationCenter (docs/READY.md, mechanism 15): what each module sends
// (one/notification_center.py). A module's part, from Notifications in its
// ControlCenter, is Yours (Email and Push for each type the reader gets)
// and, for administrators, Workspace (Send, and whether email and push are
// allowed). Which channels a new person starts with is the module's to say. The whole, from the bell's
// gear and the arrows, starts with Everything (notifications and their
// email on or off, push in this browser), then each module, then, for
// administrators, Words and Rules: what every notification says and the
// workspace's own rules.
frappe.provide("onedesk.notification_center");

onedesk.notification_center.open = async ({ module = null, at = null, record = null, for_doctype = null } = {}) => {
	const N = "onedesk.one.notification_center.";
	const kit = onedesk.module_settings.kit;
	const esc = frappe.utils.escape_html;
	const admin = !!frappe.boot.one_administers;
	const modules = module ? [module] : (frappe.boot.one_centers || {}).notifications || [];

	// A switch at a row's end, saved as it changes; put back if refused.
	const toggle = ($end, { value, label, disabled = false, change }) => {
		const control = frappe.ui.form.make_control({
			df: { fieldtype: "Switch", fieldname: "on", label: "" },
			parent: $(`<span class="one-set-switch"></span>`).appendTo($end),
			render_input: true,
		});
		control.set_value(value ? 1 : 0);
		control.$input.attr("aria-label", label).prop("disabled", disabled);
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
	const named = onedesk.module_settings.named;
	const app_icon = (app) => onedesk.module_settings.app_icon(app);
	const columns = (words) => `<div class="one-notify-columns">${words.map((word) => `<span>${esc(word)}</span>`).join("")}</div>`;

	// The reader's own: Email and Push for each type of one module, or of
	// what no module sends ("").
	const yours = async (app, $body) => {
			const said = await frappe.xcall(N + "yours", { module: app }, "GET");
			const types = said.types.filter((one) => one.app === app);
			if (!said.enabled) $body.append(frappe.ui.alert.html({ title: __("Your notifications are off."), theme: "orange" }));
			if (!types.length) return $body.append(kit.empty(__("Nothing to choose here.")));
			$body.append(columns([__("Email"), __("Push")]));
			const $list = $(`<div class="one-set-list one-notify-list"></div>`).appendTo($body);
			for (const one of types) {
				const $row = kit.row({ lead: "", title: one.label, sub: esc([one.about, one.why].filter(Boolean).join(" ")) }).appendTo($list);
				if (one.oneai) $row.find(".one-set-title").append(" ", onedesk.oneai.tag(__("OneAI")));
				const $end = $row.find(".one-set-end");
				for (const channel of ["email", "push"]) {
					toggle($end, {
						value: one[channel],
						label: `${channel === "email" ? __("Email") : __("Push")}: ${one.label}`,
						disabled: !one[`may_${channel}`] || (channel === "email" && !said.email),
						change: (on) => frappe.xcall(N + "choose", { name: one.name, channel, on }),
					});
				}
			}
	};
	const yours_tab = (app) => ({
		id: `yours:${app}`,
		label: __("Yours"),
		icon: "user",
		title: __("Yours"),
		description: __("What {0} tells you, and how.", [app]),
		render: (panel) => yours(app, panel.body.empty()),
	});

	// The workspace's: for each type a module sends, Send, then whether
	// people may have it by email and by push.
	const workspace = async (app, $body) => {
			const types = await frappe.xcall(N + "workspace", { module: app }, "GET");
			if (!types.length) return $body.append(kit.empty(__("Nothing to set here.")));
			$body.append(columns([__("Send"), __("Email"), __("Push")]));
			const $list = $(`<div class="one-set-list one-notify-list"></div>`).appendTo($body);
			const set = (one, field, on) => frappe.xcall(N + "set_type", { name: one.name, field, value: on }).then(() => (one[field] = on));
			// A type opens as its record in Words and Rules, which says who it
			// goes to.
			const words = (one) => {
				dialog.hide();
				onedesk.notification_center.open({ at: "words", record: one.name });
			};
			for (const one of types) {
				const $row = kit
					.row({ lead: "", title: one.label, sub: esc(one.about || ""), open: one.words ? () => words(one) : null })
					.appendTo($list);
				const $end = $row.find(".one-set-end");
				toggle($end, { value: one.enabled, label: `${__("Send")}: ${one.label}`, disabled: !!one.fixed, change: (on) => set(one, "enabled", on) });
				for (const field of ["one_allow_email", "one_allow_push"]) {
					const email = field.includes("email");
					toggle($end, {
						value: one[field],
						label: `${email ? __("Email") : __("Push")}: ${one.label}`,
						disabled: !one.channels || (email && !!one.always),
						change: (on) => set(one, field, on),
					});
				}
			}
	};
	const workspace_tab = (app) => ({
		id: `workspace:${app}`,
		label: __("Workspace"),
		icon: "building",
		title: __("Workspace"),
		description: __("What {0} sends in this workspace, and the channels people may choose.", [app]),
		render: (panel) => workspace(app, panel.body.empty()),
	});

	// The whole centre has one row per app: what it tells the reader, and
	// for an administrator, by the switch in its head, what it sends in the
	// workspace. What no app sends (the workspace's rules) is Other.
	const app_tab = (app) => ({
		id: `app:${app}`,
		label: app ? named(app) : __("Other"),
		icon: app ? null : "bell",
		icon_html: app ? app_icon(app) : null,
		title: app ? named(app) : __("Other"),
		description: app ? __("What {0} tells you, and how.", [named(app)]) : __("What the workspace's own rules tell you."),
		render(panel) {
			const $body = panel.body.empty();
			const $at = $(`<div></div>`).appendTo($body);
			const draw = (side) => (side === "workspace" ? workspace(app, $at.empty()) : yours(app, $at.empty()));
			const whose = at && at.startsWith("workspace:") && at === `workspace:${app}` ? "workspace" : "yours";
			if (admin && app) {
				const say = (side) =>
					panel.$header.find(".settings-dialog-panel-description").text(
						side === "workspace"
							? __("What {0} sends in this workspace, and the channels people may choose.", [named(app)])
							: __("What {0} tells you, and how.", [named(app)])
					);
				const tabs = new frappe.ui.TabButtons({
					label: __("Whose"),
					options: [
						{ label: __("Yours"), value: "yours" },
						{ label: __("Workspace"), value: "workspace" },
					],
					value: whose,
					on_change: (side) => {
						say(side);
						draw(side);
					},
				});
				panel.$header.removeClass("hide").find(".settings-dialog-panel-actions").empty().append(tabs.$el);
				say(whose);
			}
			draw(whose);
		},
	});

	// The reader's switches over everything, and push in this browser.
	const everything = {
		id: "everything",
		label: __("Everything"),
		icon: "bell-ring",
		title: __("Everything"),
		description: __("Whether you're told at all, by email, and on this device."),
		async render(panel) {
			const said = await frappe.xcall(N + "yours", { module: "" }, "GET");
			const $list = $(`<div class="one-set-list"></div>`).appendTo(panel.body.empty());
			for (const [key, field, glyph, title, sub] of [
				["enabled", "enabled", "bell", __("Notifications"), __("Turn off to stop all notifications.")],
				["email", "enable_email_notifications", "mail", __("Also by Email"), __("Emails you the notifications turned on for email.")],
				["threads", "enable_email_threads_on_assigned_document", "mails", __("Mail About What Is Assigned to You"), __("Mails you each new mail on a record you were given to do.")],
			]) {
				const $row = kit.row({ lead: kit.glyph(glyph), title, sub: esc(sub) }).appendTo($list);
				toggle($row.find(".one-set-end"), {
					value: said[key],
					label: title,
					change: (on) => frappe.xcall(N + "switch", { field, on }),
				});
			}
			push($list);
		},
	};

	const push = async ($list) => {
		await frappe.require("/assets/onedesk/js/one/push.js");
		const here = await onedesk.push.state();
		const [label, theme] = {
			on: [__("On in this browser"), "green"],
			off: [__("Off in this browser"), "gray"],
			blocked: [__("Blocked in this browser"), "orange"],
			unsupported: [__("Not supported in this browser"), "gray"],
		}[here.state];
		const sub = here.state === "blocked" ? esc(__("Allow notifications for this site in your browser settings.")) : frappe.ui.badge.html({ label, theme });
		const $row = kit.row({ lead: kit.glyph("smartphone"), title: __("Push"), sub }).appendTo($list);
		const again = () => {
			$row.remove();
			push($list);
		};
		const $end = $row.find(".one-set-end");
		if (here.state === "off") {
			kit.button({ label: __("Turn On Push"), variant: "outline" })
				.on("click", async () => {
					const said = await frappe.xcall("onedesk.one.push.devices");
					let on = false;
					try {
						on = await onedesk.push.on(said.key);
					} catch (e) {
						on = false;
					}
					if (!on) frappe.show_alert({ message: __("Couldn't turn on push. Private windows don't support it."), indicator: "orange" });
					again();
				})
				.appendTo($end);
		} else if (here.state === "on") {
			kit.button({ label: __("Send Test"), variant: "outline" })
				.on("click", async () => {
					const said = await frappe.xcall("onedesk.one.push.test");
					frappe.show_alert({ message: said.sent ? __("Test sent") : __("Couldn't send test"), indicator: said.sent ? "green" : "orange" });
				})
				.appendTo($end);
			kit.button({ label: __("Turn Off"), variant: "ghost" })
				.on("click", async () => {
					await onedesk.push.off();
					again();
				})
				.appendTo($end);
		}
	};

	// What each notification says and the workspace's rules, a type or a
	// rule opening as the tab's record.
	const words_tab = {
		...onedesk.center_section.tab(onedesk.WordsSection, {
			id: "words",
			label: __("Words and Rules"),
			icon: "bell-ring",
			about: __("What each notification says, the channels it may use, and the workspace's own rules."),
			record: at === "words" ? record : null,
		}),
	};
	const words_render = words_tab.render;
	words_tab.render = (panel) => {
		words_render(panel);
		panel.section.for_doctype = for_doctype;
	};
	const tabs = module
		? [{ items: [yours_tab(module), ...(admin ? [workspace_tab(module)] : [])] }]
		: [
				{ items: [everything] },
				{ group: __("Apps"), items: [...modules.map(app_tab), app_tab("")] },
				...(admin ? [{ group: __("Workspace"), items: [words_tab] }] : []),
		  ];
	const ids = tabs.flatMap((group) => group.items.map((item) => item.id));
	// yours:OneHR and workspace:OneHR, as links into the whole centre still say.
	const app_at = !module && at && /^(yours|workspace):/.test(at) ? `app:${at.split(":")[1]}` : at;
	const dialog = new onedesk.module_settings.Dialog({
		title: "NotificationCenter",
		module,
		center: "notifications",
		tabs,
		default_tab: ids.includes(app_at) ? app_at : ids[0],
		help: ["One", "notifications"],
	});
	dialog.$wrapper.addClass("one-set one-notify");
	dialog.show();
	return dialog;
};

// Words and Rules, for administrators: what each notification says and which
// channels it may use, and the workspace's own rules (one/notification_words.py).
// A type or a rule opens as the record the tab is on.
onedesk.WordsSection = class WordsSection extends onedesk.CenterSection {
	static API = "onedesk.one.notification_words.";
	static HERE = "notifications";
	static LABEL = "NotificationCenter";

	// A new rule opened from a record type's settings starts on that type.
	loaded(data) {
		if (this.record === "rule:new" && this.for_doctype && data.values) data.values.document_type = this.for_doctype;
	}

	draw_words(data) {
		if (data.rule) return this.draw_rule(data);
		if (data.type) return this.draw_notification_type(data);
		const esc = frappe.utils.escape_html;
		const channel = (label, allowed, on) => (allowed ? frappe.ui.badge.html({ label, theme: on ? "blue" : "gray" }) : "");
		const state = (one) =>
			[
				one.enabled ? "" : frappe.ui.badge.html({ label: __("Off"), theme: "gray" }),
				one.edited ? frappe.ui.badge.html({ label: __("Edited"), theme: "violet" }) : "",
			].join(" ");
		const channels = (one) =>
			!one.ours
				? `<span class="one-shell-quiet">${esc(__("Each person chooses"))}</span>`
				: one.mailed_by
				? frappe.ui.badge.html({ label: __("Sent by {0}", [one.mailed_by]), theme: "gray" })
				: one.outside
				? frappe.ui.badge.html({ label: __("External Email"), theme: "gray" })
				: one.always
				? frappe.ui.badge.html({ label: __("Always Emailed"), theme: "gray" })
				: channel(__("Email"), one.email, one.email_default) + " " + channel(__("Push"), one.push, one.push_default);
		const open_rule = (name) => this.open(this.key, { record: `rule:${name}` });
		this.$content.html(
			`<div class="one-shell-section" data-list="rules"></div>
			<div class="one-shell-section" data-list="types"></div>`
		);
		onedesk.shell.table(this.$content.find('[data-list="rules"]'), {
			title: __("Rules"),
			rows: data.rules || [],
			icon: "bell-plus",
			empty: __("No rules"),
			open: (one) => open_rule(one.name),
			actions: onedesk.shell.button(__("New Rule"), { "data-rule-new": "1" }, "subtle", "plus"),
			columns: [
				{ label: __("Rule"), fieldname: "name" },
				{ label: __("Description"), render: (one) => `<span class="one-shell-quiet">${esc(one.said || "")}</span>` },
				{ label: "", render: (one) => (one.enabled ? "" : frappe.ui.badge.html({ label: __("Off"), theme: "gray" })) },
			],
		});
		onedesk.shell.table(this.$content.find('[data-list="types"]'), {
			title: __("Notifications"),
			note: __("Blue means on by default."),
			rows: data.apps.flatMap((group) => group.types.map((one) => ({ ...one, app: group.app, mark: group.mark }))),
			page_size: 100,
			icon: "bell",
			none: __("No matching notifications"),
			open: (one) => one.ours && this.open(this.key, { record: one.name }),
			columns: [
				{
					label: __("Notification"),
					render: (one) =>
						`<div class="os-type-name">${esc(one.label)}</div>${
							one.about ? `<div class="one-shell-quiet">${esc(one.about)}</div>` : ""
						}${one.to ? `<div class="one-shell-quiet os-to">${frappe.utils.icon("users", "xs")}${esc(one.to)}</div>` : ""}`,
				},
				{
					label: __("App"),
					render: (one) => onedesk.shell.app(one.app, one.mark),
				},
				{ label: __("Channels"), render: channels },
				{ label: "", render: state },
			],
		});
		this.$content.on("click", "[data-rule-new]", () => open_rule("new"));
	}

	draw_notification_type(data) {
		const esc = frappe.utils.escape_html;
		const type = data.type;
		const slots = type.slots.map((one) => `<code>{{ ${esc(one)} }}</code>`).join(" ");
		const preview = `<div class="os-preview">
			<div class="os-preview-label">${esc(__("Preview"))}</div>
			<div class="os-preview-subject"></div>
			<div class="os-preview-message"></div>
			<div class="os-preview-wrong"></div>
		</div>`;
		const rows = [["enabled"]];
		if (type.mailed_by) {
			rows.push({
				html: `<div class="one-shell-quiet">${esc(
					type.switch
						? __("{0} sends this email itself. Send This is the same switch as in its settings.", [type.mailed_by])
						: type.notification
						? __("{0} sends this email itself. Send This turns it on and off.", [type.mailed_by])
						: __("{0} sends this email itself. It's listed so you can see everything the workspace sends.", [type.mailed_by])
				)}</div>`,
			});
		} else if (type.upstream) {
			rows.push(
				{
					html: `<div class="one-shell-quiet">${esc(
						type.rule
							? __("The text comes from {0}'s rule {1}.", [type.upstream, type.rule])
							: __("The text comes from {0}.", [type.upstream])
					)}</div>`,
				},
				{ heading: __("Channels"), note: __("In-app notifications are always on.") },
				["one_allow_email", "one_allow_push"]
			);
		} else if (type.ours) {
			rows.push(
				{ heading: __("Message"), note: __("Edited text is no longer translated.") },
				["one_subject"],
				["one_message"],
				{ html: `${slots ? `<div class="one-shell-quiet os-slots">${__("Available fields: {0}", [slots])}</div>` : ""}${preview}` }
			);
			if (type.always) {
				rows.push(
					{ heading: __("Channels"), note: __("Email is always sent so people can reply.") },
					["one_allow_push"]
				);
			} else if (!type.outside) {
				rows.push(
					{ heading: __("Channels"), note: __("In-app notifications are always on.") },
					["one_allow_email", "one_allow_push"]
				);
			} else {
				rows.push({ html: `<div class="one-shell-quiet">${esc(__("Sent to addresses outside the workspace, so there's no channel to choose."))}</div>` });
			}
		}
		const reset = async () => {
			await this.group.set_values({ one_subject: type.default_subject, one_message: type.default_message });
			this.check();
			this.preview(type.name, $card);
		};
		this.as_record({
			title: type.label,
			status: data.values.enabled ? { label: __("On"), colour: "green" } : { label: __("Off"), colour: "gray" },
			side: onedesk.shell.side({
				mark: type.mark || "bell",
				title: type.label,
				sub: type.app ? esc(type.app) : "",
				groups: [
					{ label: __("When"), html: type.about ? `<div>${esc(type.about)}</div>` : "" },
					{ label: __("Recipients"), html: type.to ? `<div>${esc(type.to)}</div>` : "" },
				],
			}),
			actions: type.ours && !type.upstream ? [{ label: __("Reset to Default"), action: reset, group: __("Actions") }] : [],
		});
		const $card = this.form(data, { rows });
		const draw = frappe.utils.debounce(() => this.preview(type.name, $card), 400);
		for (const name of ["one_subject", "one_message"]) {
			const field = this.group.fields_dict[name];
			if (!field) continue;
			const was = field.df.change;
			field.df.change = (...args) => {
				was && was(...args);
				draw();
			};
		}
		if (type.ours && !type.upstream) this.ready.then(() => this.preview(type.name, $card));
	}

	async preview(name, $card) {
		if (!this.group) return;
		const said = await frappe.xcall(WordsSection.API + "preview_notification", {
			name,
			subject: this.group.get_value("one_subject") || "",
			message: this.group.get_value("one_message") || "",
		});
		$card.find(".os-preview-subject").html(said.subject || "");
		$card.find(".os-preview-message").html(said.message || "");
		const wrong = [said.subject_wrong, said.message_wrong].filter(Boolean);
		$card.find(".os-preview-wrong").html(wrong.length ? frappe.ui.alert.html({ title: wrong.join(" "), theme: "red" }) : "");
	}

	draw_rule(data) {
		const esc = frappe.utils.escape_html;
		const rule = data.rule;
		const remove = () =>
			frappe.confirm(__("Delete rule {0}? It stops sending notifications.", [rule.name]), async () => {
				await frappe.xcall(WordsSection.API + "delete_rule", { name: rule.name });
				this.open(this.key);
			});
		this.as_record({
			title: rule.new ? __("New Rule") : rule.name,
			status: rule.new ? { label: __("Not Saved"), colour: "orange" } : data.values.enabled ? { label: __("On"), colour: "green" } : { label: __("Off"), colour: "gray" },
			side: onedesk.shell.side({
				mark: "bell-plus",
				title: rule.new ? __("New Rule") : rule.name,
				sub: esc(__("Workspace rule")),
				groups: [{ label: __("Description"), html: rule.said ? `<div>${esc(rule.said)}</div>` : "" }],
			}),
			actions: rule.new ? [] : [{ label: __("Delete"), action: remove, group: __("Actions") }],
		});
		const rows = [
			["enabled"],
			...(rule.new ? [["rule_name"]] : []),
			{ heading: __("Trigger") },
			["document_type", "event"],
			["date_changed", "days_in_advance"],
			["value_changed"],
			{ html: `<div class="os-filter-label">${esc(__("Conditions"))}</div><div class="os-filters"></div>` },
			{ heading: __("Recipients"), note: __("Only people with access to the record are notified.") },
			["roles"],
			["person_field", "send_to_all_assignees"],
			{ heading: __("Message") },
			["subject"],
			["message"],
			{ heading: __("Channels"), note: __("In-app notifications are always on.") },
			["one_allow_email", "one_allow_push"],
		];
		const $card = this.form(data, { rows });
		const options = (list) => [{ value: "", label: "" }, ...(list || [])];
		const offer = (said) => {
			for (const [field, list] of [
				["date_changed", said && said.dates],
				["value_changed", said && said.values],
				["person_field", said && said.people],
			]) {
				const control = this.group.fields_dict[field];
				if (!control) continue;
				control.df.options = options(list);
				control.refresh();
				control.set_input(this.group.get_value(field) || data.values[field] || "");
			}
		};
		const filters = (doctype, value) => {
			const $filters = $card.find(".os-filters").empty();
			if (!doctype) return $filters.html(`<div class="one-shell-quiet">${esc(__("Select a record type first."))}</div>`);
			frappe.model.with_doctype(doctype, () => {
				const group = new frappe.ui.FilterGroup({
					parent: $filters,
					doctype,
					on_change: () => {
						this.group.set_value("filters", JSON.stringify(group.get_filters()));
						this.check();
					},
				});
				group.add_filters_to_filter_group(value && value !== "[]" ? JSON.parse(value) : []);
			});
		};
		offer(data.options);
		filters(data.values.document_type, data.values.filters);
		const watched = this.group.fields_dict.document_type;
		watched.get_query = () => ({ query: "onedesk.one.rules.watchable" });
		const was = watched.df.change;
		watched.df.change = async (...args) => {
			was && was(...args);
			const doctype = this.group.get_value("document_type");
			if (doctype === this.rule_watches) return;
			this.rule_watches = doctype;
			this.group.set_value("filters", "");
			offer(doctype ? await frappe.xcall("onedesk.one.rules.fields_of", { doctype }) : null);
			filters(doctype, "");
		};
		this.rule_watches = data.values.document_type;
		if (!rule.new && this.record === "rule:new") this.record = `rule:${rule.name}`;
	}
};
