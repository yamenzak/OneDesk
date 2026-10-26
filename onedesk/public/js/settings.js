
frappe.provide("onedesk");

onedesk.Settings = class Settings extends onedesk.shell.Editor {
	static API = "onedesk.one.settings.";

	static WIDE = ["people", "oneai", "intake", "numbering", "printing", "approvals"];
	static theirs = (one) => one.standard === "Yes";
	// A role of a module that declares its abilities is set in AccessCenter
	// (docs/READY.md, mechanism 14) rather than on a role's page here.
	static in_access = (app) => ((frappe.boot.one_centers || {}).access || []).includes(app);
	static access = (app) => onedesk.access.open({ module: app, at: `${app}:roles` });

	static SHEET = 794;
	static PAGE = 1123;
	static sheet = (top, foot, scale, whole = false) =>
		`<!doctype html><html><head><style>html,body{margin:0;background:#fff;color:#111;font-family:sans-serif}` +
		`body{padding:24px;width:746px;transform:scale(${scale});transform-origin:0 0}img{max-width:100%}` +
		`.lines{height:48px;margin:16px 0;background:repeating-linear-gradient(to bottom,#e5e7eb 0,#e5e7eb 6px,transparent 6px,transparent 14px)}` +
		(whole ? `html{overflow:hidden}body{box-sizing:border-box;width:794px;height:1123px;padding:45px 53px;display:flex;flex-direction:column}.lines{flex:1;height:auto;margin:32px 0;background:repeating-linear-gradient(to bottom,#f3f4f6 0,#f3f4f6 4px,transparent 4px,transparent 22px)}` : "") +
		`</style></head><body>${top || ""}${foot === null ? "" : `<div class="lines"></div>${foot || ""}`}</body></html>`;
	static frame = (html, className) => {
		const it = document.createElement("iframe");
		it.className = className;
		it.setAttribute("sandbox", "");
		it.srcdoc = html;
		return it;
	};

	constructor(page, group) {
		super(page);
		this.group_name = group;
		this.route = group === "workspace" ? "workspace-settings" : "settings";
		this.$section = page.$shell;
		this.kept = {};
		frappe.realtime.on("one_memory", () => this.key === "memory" && this.$content && this.$content.is(":visible") && this.refresh());
	}

	async show() {
		if (!this.said) this.said = await frappe.xcall(Settings.API + "sections");
		const mine = this.said.sections.filter((one) => one.group === this.group_name);
		const params = frappe.utils.get_query_params();
		if (params.section === "agreements") return frappe.set_route("legal");
		// Your account and the workspace's are AccountCenter (docs/ONE.md),
		// opened over this page.
		if (["profile", "signin", "people", "devices", "plan", "domains"].includes(params.section)) {
			onedesk.account_center.open({ at: params.section, record: params.person || null });
			frappe.route_flags.replace_route = true;
			return frappe.set_route(this.route);
		}
		// A person's notifications are NotificationCenter (docs/READY.md,
		// mechanism 15), opened over this page.
		if (params.section === "notifications") {
			onedesk.notification_center.open();
			frappe.route_flags.replace_route = true;
			return frappe.set_route(this.route);
		}
		// OneAI's settings, what it remembers and its reading are AICenter
		// (docs/AICENTER.md), opened over this page the same way.
		const centre = { oneai: null, memory: "yours", intake: "reading" };
		if (params.section in centre) {
			onedesk.ai_center.open({ at: centre[params.section] });
			frappe.route_flags.replace_route = true;
			return frappe.set_route(this.route);
		}
		const found = mine.find((one) => one.key === params.section) || mine[0];
		this.for_doctype = params.rule === "new" ? params.for || null : null;
		if (found)
			this.open(found.key, {
				record: params.type || params.person || params.list || (params.rule ? `rule:${params.rule}` : null) || (params.level ? `level:${params.level}` : null) ||
					(params.profile ? `profile:${params.profile}` : null) ||
					(params.group ? `group:${params.group}` : null),
			});
	}

	async open(key, { fresh = false, record = null } = {}) {
		const slot = (k, r) => (r ? `${k}:${r}` : k);
		if (this.dirty && this.values) this.kept[slot(this.key, this.record)] = { values: this.values(), opened: this.opened };
		if (fresh) delete this.kept[slot(key, record)];
		this.key = key;
		this.record = record;
		this.unsaved();
		const section = this.said.sections.find((one) => one.key === key);
		onedesk.shell.name(section.label);
		this.$content = onedesk.shell.body(this.$section, { wide: Settings.WIDE.includes(key) });
		try {
			this.data = await frappe.xcall(Settings.API + "load", { section: key, record });
			if (record === "rule:new" && this.for_doctype && this.data.values) this.data.values.document_type = this.for_doctype;
		} catch (e) {
			this.$content.html(frappe.ui.alert.html({ title: __("This section could not be opened."), theme: "red" }));
			return;
		}
		this.$content.empty();
		this.hear(this.data.opened);
		this[`draw_${key}`](this.data);
		if (!this.trailed) onedesk.shell.name(section.label);
		await this.bring_back(slot(key, record));
	}

	async bring_back(key) {
		const kept = this.kept[key];
		delete this.kept[key];
		if (!kept || !this.values) return;
		await this.ready;
		await this.group.set_values(kept.values);
		this.check();
		const moved = kept.opened.some((one) => this.opened.some((now) => now.doctype === one.doctype && now.name === one.name && now.modified !== one.modified));
		if (moved) this.conflict();
	}

	saver(values) {
		return { method: Settings.API + "save", args: { section: this.key, values, record: this.record } };
	}

	redraw(said) {
		const [kind, name] = (said.record || "").split(/:(.*)/s);
		if (said.record && said.record !== this.record && ["rule", "level", "profile", "group"].includes(kind)) {
			frappe.set_route(this.route, { section: this.key, [kind]: name });
			return;
		}
		if (this.trailed) {
			this.unsaved();
			this.$content = onedesk.shell.body(this.$section, { wide: Settings.WIDE.includes(this.key) });
		}
		this[`draw_${this.key}`](said);
	}

	refresh({ fresh = false } = {}) {
		this.open(this.key, { fresh, record: this.record });
	}

	draw_notifications(data) {
		const rows = [{ stack: ["enabled", "enable_email_notifications"] }];
		for (const group of data.groups) rows.push({ heading: group.app }, ...group.rows.map((row) => ({ row, css: "os-kind" })));
		rows.push({ heading: __("Other Emails") }, { stack: ["enable_email_threads_on_assigned_document"] });
		const fewer = onedesk.oneai.button(
			__("Too Many Emails?"),
			__("Which of the notifications I get by email could I leave to the bell, or have pushed instead? Say which to untick and why.")
		);
		const note = __("All notifications appear in One.");
		const $card = this.form(data, {
			before: `<div class="os-notify-intro"><div class="one-shell-quiet">${note}</div>${fewer}</div><div class="os-push"></div>`,
			rows,
		});
		const columns = `<div class="os-kind-columns"><span>${__("Email")}</span><span>${__("Push")}</span></div>`;
		$card.find(".form-section.os-kind.one-shell-part .section-head").each((at, head) => {
			const mark = (data.groups[at] || {}).mark;
			if (mark) $(head).prepend(`<span class="os-kind-mark">${frappe.utils.icon(mark, "md")}</span>`);
			$(head).append(columns);
		});
		$card.find(".os-kind .frappe-control[data-fieldtype='Switch']").each((_, control) => {
			const $control = $(control);
			const name = $control.closest(".section-body").find(".os-kind-name").first().text();
			$control.find("input").attr("aria-label", `${$control.find(".label-area").text()}: ${name}`);
		});
		this.ready.then(() => {
			$card.find("[data-oneai-tag]").replaceWith(onedesk.oneai.tag(__("OneAI")));
			for (const field of this.group.fields_list) {
				if (field.df.fieldtype !== "Switch" || !field.df.read_only) continue;
				field.$wrapper.addClass("os-switch-fixed").toggleClass("os-switch-on", !!cint(field.get_value()));
			}
		});
		this.draw_push($card.find(".os-push"), data.push);
	}

	async draw_push($part, said) {
		const esc = frappe.utils.escape_html;
		const here = await onedesk.push.state();
		const words = {
			on: [__("On in this browser"), "green"],
			off: [__("Off in this browser"), "gray"],
			blocked: [__("Blocked in this browser"), "orange"],
			unsupported: [__("Not supported in this browser"), "gray"],
		}[here.state];
		const others = (said.devices || []).filter((one) => one.endpoint !== here.endpoint);
		const action =
			here.state === "off"
				? onedesk.shell.button(__("Turn On Push"), { "data-push": "on" }, "subtle", "bell-ring")
				: here.state === "on"
				? onedesk.shell.button(__("Send Test"), { "data-push": "test" }, "subtle") + onedesk.shell.button(__("Turn Off"), { "data-push": "off" }, "ghost")
				: "";
		$part.html(
			onedesk.shell.row({
				title: esc(__("Push")),
				sub: frappe.ui.badge.html({ label: words[0], theme: words[1] }),
				quiet: here.state === "blocked" ? esc(__("Allow notifications for this site in your browser settings.")) : "",
				actions: action,
			}) + '<div class="os-push-others"></div>'
		);
		const again = async () => this.draw_push($part, await frappe.xcall("onedesk.one.push.devices"));
		if (others.length) {
			onedesk.shell.table($part.find(".os-push-others"), {
				title: __("Other Browsers"),
				rows: others,
				icon: "bell-ring",
				columns: [
					{ label: __("Browser"), render: (one) => esc(one.label || "") },
					{
						label: __("Last Sent"),
						render: (one) =>
							`<span class="one-shell-quiet">${esc(one.last_sent ? frappe.datetime.prettyDate(one.last_sent) : __("Never"))}</span>`,
					},
					{
						type: "actions",
						actions: [
							{
								label: __("Remove"),
								icon: "trash-2",
								danger: true,
								action: async (one) => {
									await frappe.xcall("onedesk.one.push.forget", { name: one.name });
									again();
								},
							},
						],
					},
				],
			});
		}
		$part.find('[data-push="on"]').on("click", async () => {
			let on = false;
			try {
				on = await onedesk.push.on(said.key);
			} catch (e) {
				on = false;
			}
			if (!on) frappe.show_alert({ message: __("Couldn't turn on push. Private windows don't support it."), indicator: "orange" });
			again();
		});
		$part.find('[data-push="off"]').on("click", async () => {
			await onedesk.push.off();
			again();
		});
		$part.find('[data-push="test"]').on("click", async () => {
			const r = await frappe.xcall("onedesk.one.push.test");
			frappe.show_alert({ message: r.sent ? __("Test sent") : __("Couldn't send test"), indicator: r.sent ? "green" : "orange" });
		});
	}

	draw_calendar(data) {
		const how = onedesk.oneai.button(
			__("How Do I Add It?"),
			__("How do I add my calendar to Google Calendar, Apple Calendar or Outlook?")
		);
		const $card = $(
			onedesk.shell.section(
				__("Calendar Link"),
				`<div class="os-calendar"></div><div class="one-shell-actions">${how}</div>`
			)
		).appendTo(this.$content);
		const draw = (link) => {
			const $body = $card.find(".os-calendar");
			if (!data.allowed) {
				$body.html(`<div class="one-shell-quiet">${__("Calendar links are turned off for this workspace.")}</div>`);
				$card.find(".one-shell-actions").remove();
				return;
			}
			if (!link) {
				$body.html(`<div class="one-shell-quiet">${__("No calendar link")}</div>`);
				this.page.set_primary_action(__("Create Link"), async () => draw(await frappe.xcall("onedesk.one_calendar.feed.mine")), "link");
				return;
			}
			$body.html(onedesk.calendar_link.html(link, { copy: false }));
			onedesk.calendar_link.bind($body, link, { drawn: draw, stopped: () => draw(null) });
			this.page.set_primary_action(__("Copy Link"), () => onedesk.calendar_link.copy(link), "copy");
		};
		draw(data.link);
	}

	static read_switch(on) {
		return `<span class="switch-control one-read-switch" aria-hidden="true"><span class="input-area"><input type="checkbox" tabindex="-1" ${
			on ? "checked" : ""
		}></span><span class="switch-visual"><span class="switch-thumb"></span></span></span>`;
	}

	// signing in. Every field is System Settings', Company's or Global Defaults' own.
	draw_general(data) {
		const esc = frappe.utils.escape_html;
		const facts = [
			[__("Workspace"), data.name],
			[__("Company"), data.company],
			[__("Country"), data.country ? __(data.country) : ""],
			[__("Currency"), data.currency],
		]
			.filter(([, value]) => value)
			.map(([label, value]) => `<dt>${esc(label)}</dt><dd>${esc(value)}</dd>`)
			.join("");
		const rows = [
			{ heading: __("Company"), note: __("The currency can't change once there are transactions.") },
			{ html: `<dl class="os-facts">${facts}</dl>` },
			["email_footer_address", ""],
			{ heading: __("Contact and Branding") },
			["company_logo", "one_brand_colour"],
			["one_frame_colour", ""],
			["phone_no", "email"],
			["website", "tax_id"],
			["address_line1", "address_line2"],
			["city", "state"],
			["pincode", ""],
			{ heading: __("Region and Formats") },
			["language", "time_zone"],
			["date_format", "time_format"],
			["number_format", "first_day_of_the_week"],
			{ html: `<div class="one-shell-quiet os-reads" data-reads="1"></div>` },
			{ stack: ["hide_currency_symbol", "disable_rounded_total", "disable_in_words"] },
			{ heading: __("Sign-in") },
			["one_two_factor", "two_factor_method"],
			["session_expiry", "one_password"],
			["allow_consecutive_login_attempts", "allow_login_after_fail"],
			["force_user_to_reset_password", ""],
			{ stack: ["one_login_with_passkey", "login_with_email_link", "deny_multiple_sessions"] },
			{ heading: __("Sharing") },
			{ stack: ["one_calendar_links", "one_record_sharing"] },
			{
				heading: __("Start Again"),
				note: __("Customers, items, people and settings stay."),
			},
			{ html: onedesk.shell.button(__("Delete All Transactions"), { "data-start-again": "1" }, "subtle", "trash-2") },
		];
		const $card = this.form(data, { rows });
		$card.on("click", "[data-start-again]", () =>
			frappe.confirm(__("Every sale, purchase, stock move, project, payslip, lead and asset is deleted. This can't be undone."), () =>
				frappe
					.call({ method: "onedesk.one.start_again.start", type: "POST", freeze: true })
					.then((r) => frappe.set_route("Form", "Transaction Deletion Record", r.message))
			)
		);
		const reads = () => {
			const values = this.values();
			const now = values.time_zone && moment.tz && moment.tz.zone(values.time_zone) ? moment().tz(values.time_zone) : moment();
			const date = now.format((values.date_format || "dd-mm-yyyy").toUpperCase());
			const time = now.format(values.time_format || "HH:mm:ss");
			const number = format_number(1234567.89, values.number_format, 2);
			$card.find("[data-reads]").text(__("Preview: {0}", [`${date} ${time}, ${number}`]));
		};
		this.ready.then(reads);
		$card.on("change input", "select, input", () => setTimeout(reads));
	}

	draw_access(data) {
		if (data.level) return this.draw_level(data);
		if (data.profile) return this.draw_job_profile(data);
		if (data.group) return this.draw_group(data);
		const esc = frappe.utils.escape_html;
		const named = (title, method, key, more = []) => {
			const dialog = new frappe.ui.Dialog({
				title,
				fields: [{ fieldname: "title", fieldtype: "Data", label: __("Name"), reqd: 1 }, ...more],
				primary_action_label: __("Create"),
				primary_action: async ({ title, members }) => {
					const name = await frappe.xcall(`onedesk.one.access.${method}`, { title, ...(members ? { members } : {}) });
					dialog.hide();
					frappe.set_route("workspace-settings", { section: "access", [key]: name });
				},
			});
			dialog.show();
		};
		this.page.set_primary_action(__("New Role"), () => this.new_level(data), "plus");
		this.$content.html(
			`<div class="one-shell-section" data-list="levels"></div><div class="one-shell-section" data-list="profiles"></div><div class="one-shell-section" data-list="groups"></div>`
		);
		const levels = Object.fromEntries(data.levels.map((one) => [one.name, one.name]));
		const said = (level) => ({ None: null, User: __("User"), Manager: __("Manager") })[level] ?? levels[level] ?? level;
		onedesk.shell.table(this.$content.find('[data-list="profiles"]'), {
			title: __("Profiles"),
			rows: data.profiles,
			icon: "id-card",
			empty: __("No profiles"),
			actions: $(onedesk.shell.button(__("New Profile"), {}, "subtle", "plus")).on("click", () => named(__("New Profile"), "new_profile", "profile")),
			open: (one) => frappe.set_route("workspace-settings", { section: "access", profile: one.name }),
			columns: [
				{ label: __("Profile"), render: (one) => esc(one.name) },
				{
					label: __("Apps"),
					render: (one) =>
						Object.entries(one.levels)
							.filter(([, level]) => level !== "None")
							.map(([app, level]) => frappe.ui.badge.html({ label: `${app} · ${said(level)}`, theme: level === "Manager" ? "blue" : level === "User" ? "gray" : "purple" }))
							.join(" ") || `<span class="one-shell-quiet">${esc(__("Standard Apps"))}</span>`,
				},
				{ label: __("People"), render: (one) => esc(String(one.people)) },
			],
		});
		onedesk.shell.table(this.$content.find('[data-list="groups"]'), {
			title: __("Groups"),
			rows: data.groups,
			icon: "users-round",
			empty: __("No groups"),
			actions: $(onedesk.shell.button(__("New Group"), {}, "subtle", "plus")).on("click", () =>
				frappe.model.with_doctype("User Group Member", () =>
					named(__("New Group"), "new_group", "group", [
						{ fieldname: "members", fieldtype: "Table MultiSelect", options: "User Group Member", label: __("Members"), reqd: 1 },
					])
				)),
			open: (one) => frappe.set_route("workspace-settings", { section: "access", group: one.name }),
			columns: [
				{ label: __("Group"), render: (one) => esc(one.name) },
				{ label: __("People"), render: (one) => esc(String(one.members)) },
			],
		});
		const tier = (one) => (one.own ? esc(one.name) : esc(__(one.name)));
		onedesk.shell.table(this.$content.find('[data-list="levels"]'), {
			title: __("Roles"),
			note: __("Custom roles sit between User and Manager."),
			rows: data.levels,
			icon: "shield-check",
			none: __("No matching roles"),
			open: (one) => (Settings.in_access(one.app) ? Settings.access(one.app) : frappe.set_route("workspace-settings", { section: "access", level: one.key })),
			columns: [
				{
					label: __("Role"),
					render: (one) => tier(one) + (one.own ? " " + frappe.ui.badge.html({ label: __("Custom"), theme: "purple" }) : ""),
				},
				{ label: __("App"), render: (one) => onedesk.shell.app(one.app, one.icon) },
				{ label: __("People"), render: (one) => esc(String(one.people)) },
			],
		});
	}

	new_level(data) {
		const starts = (app) => [
			{ value: "User", label: __("User") },
			...data.levels.filter((one) => one.app === app && one.own).map((one) => ({ value: one.name, label: one.name })),
			{ value: "Manager", label: __("Manager") },
		];
		const dialog = new frappe.ui.Dialog({
			title: __("New Role"),
			fields: [
				{ fieldname: "title", fieldtype: "Data", label: __("Name"), reqd: 1, description: __("For example, Senior Sales.") },
				{
					fieldname: "app",
					fieldtype: "Select",
					label: __("App"),
					reqd: 1,
					options: data.apps.map((app) => app.name),
					change: () => {
						const field = dialog.get_field("start");
						field.df.options = starts(dialog.get_value("app"));
						field.refresh();
						dialog.set_value("start", "User");
					},
				},
				{
					fieldname: "start",
					fieldtype: "Select",
					label: __("Based On"),
					reqd: 1,
					default: "User",
					options: starts(data.apps[0].name),
					description: __("Starts with this role's abilities and permissions."),
				},
			],
			primary_action_label: __("Create"),
			primary_action: async ({ title, app, start }) => {
				const name = await frappe.xcall("onedesk.one.access.make_level", { app, title, start });
				dialog.hide();
				if (Settings.in_access(app)) return Settings.access(app);
				frappe.set_route("workspace-settings", { section: "access", level: name });
			},
		});
		dialog.show();
	}

	draw_level(data) {
		const esc = frappe.utils.escape_html;
		const level = data.level;
		const title = level.own ? level.name : `${level.app} ${__(level.name)}`;
		this.as_record({
			parent: __("Access"),
			route: "/desk/workspace-settings?section=access",
			title,
			status: { label: level.app, colour: "purple" },
			side: onedesk.shell.side({
				mark: level.icon,
				title,
				sub: esc(level.own ? __("Custom role of {0}", [level.app]) : level.name === "User" ? __("Everyone who uses {0}", [level.app]) : __("Everyone who manages {0}", [level.app])),
				groups: [
					{
						label: __("People"),
						html: level.people.length
							? level.people
									.map((one) => `<a class="one-record-link" href="/desk/workspace-settings?section=people&person=${encodeURIComponent(one.name)}">${esc(one.full_name || one.name)}</a>`)
									.join("")
							: `<div class="one-shell-quiet">${esc(__("No people"))}</div>`,
					},
				],
			}),
			actions: level.own
				? [
						{
							label: __("Delete"),
							group: __("Actions"),
							action: () =>
								frappe.confirm(__("Delete {0}? This removes its permissions.", [esc(level.name)]), async () => {
									await frappe.xcall("onedesk.one.access.remove_level", { name: level.name });
									frappe.set_route("workspace-settings", { section: "access" });
								}),
						},
					]
				: [],
		});
		// What the role may do in the module, grouped as the module groups
		// it (one/abilities.py), then its record types.
		const groups = [];
		for (const one of data.abilities || []) {
			const group = groups.find((g) => g.label === one.group) || groups[groups.push({ label: one.group, fields: [] }) - 1];
			group.fields.push(one.fieldname);
		}
		this.form(data, {
			rows: [
				...(level.own ? [{ stack: ["title"] }] : []),
				...groups.flatMap((group, i) => [
					{ heading: group.label, note: i || level.name === "User" ? "" : __("A role above User has everything User has.") },
					...onedesk.shell.pairs(group.fields),
				]),
				...(data.matrix
					? [
							{
								heading: __("Record Types"),
								note: __("Every permission includes Read."),
							},
							{ stack: ["rows"] },
					  ]
					: []),
			],
		});
	}

	draw_job_profile(data) {
		const esc = frappe.utils.escape_html;
		const one = data.profile;
		this.as_record({
			parent: __("Access"),
			route: "/desk/workspace-settings?section=access",
			title: one.name,
			status: { label: __("Profile"), colour: "blue" },
			side: onedesk.shell.side({
				initials: frappe.get_abbr(one.name),
				title: one.name,
				groups: [
					{
						label: __("People"),
						html: one.people.length
							? one.people
									.map((who) => `<a class="one-record-link" href="/desk/workspace-settings?section=people&person=${encodeURIComponent(who.name)}">${esc(who.full_name || who.name)}</a>`)
									.join("")
							: `<div class="one-shell-quiet">${esc(__("No people"))}</div>`,
					},
				],
			}),
			actions: [
				{
					label: __("Delete"),
					group: __("Actions"),
					action: () =>
						frappe.confirm(__("Delete {0}? The people on it keep their apps.", [esc(one.name)]), async () => {
							await frappe.xcall("onedesk.one.access.remove_profile", { name: one.name });
							frappe.set_route("workspace-settings", { section: "access" });
						}),
				},
			],
		});
		const $card = this.form(data, {
			rows: [
				{ stack: ["title"] },
				{ heading: __("Apps"), note: __("Saving updates everyone with this profile.") },
				...onedesk.shell.pairs(data.apps.map((app) => `app_${app.icon}`)),
			],
		});
		onedesk.shell.marks($card, data.apps);
	}

	draw_group(data) {
		const esc = frappe.utils.escape_html;
		const one = data.group;
		this.as_record({
			parent: __("Access"),
			route: "/desk/workspace-settings?section=access",
			title: one.name,
			status: { label: __("{0} people", [one.members]), colour: "gray" },
			side: onedesk.shell.side({ initials: frappe.get_abbr(one.name), title: one.name, sub: esc(__("Group")) }),
			actions: [
				{
					label: __("Delete"),
					group: __("Actions"),
					action: () =>
						frappe.confirm(__("Delete {0}? Records assigned to it stay with the people who had them.", [esc(one.name)]), async () => {
							await frappe.xcall("onedesk.one.access.remove_group", { name: one.name });
							frappe.set_route("workspace-settings", { section: "access" });
						}),
				},
			],
		});
		frappe.model.with_doctype("User Group Member", () =>
			this.form(data, {
				rows: [
					{ stack: ["title"] },
					{ heading: __("Members") },
					{ stack: ["members"] },
				],
			})
		);
	}




	draw_numbering(data) {
		const esc = frappe.utils.escape_html;
		const again = () => this.key === "numbering" && this.open("numbering", { fresh: true });
		const naming = (doctype) => onedesk.doctype_settings.open(doctype, "naming", again);
		this.page.set_primary_action(__("Set Up Naming"), () => onedesk.numbering.set_up(naming), "plus");
		this.$content.html(`<div class="one-shell-section" data-list="numbering"></div>`);
		onedesk.shell.table(this.$content.find('[data-list="numbering"]'), {
			title: __("Numbering"),
			rows: data.rows || [],
			page_size: 100,
			icon: "hash",
			empty: __("No numbered records"),
			none: __("No matching records"),
			open: (one) => naming(one.doctype),
			columns: [
				{ label: __("Record Type"), fieldname: "label" },
				{ label: __("Naming Rule"), fieldname: "named_by" },
				{
					label: __("Series"),
					render: (one) =>
						one.series
							? `<samp>${esc(one.series)}</samp>` + (one.others ? " " + frappe.ui.badge.html({ label: __("+{0} more", [one.others]), theme: "gray" }) : "")
							: "",
				},
				{ label: __("Next"), render: (one) => (one.next ? `<samp>${esc(one.next)}</samp>` : "") },
				{ label: __("Document Naming Rules"), render: (one) => (one.rules ? esc(String(one.rules)) : "") },
			],
		});
	}

	draw_approvals(data) {
		const esc = frappe.utils.escape_html;
		this.page.set_primary_action(__("New Approval"), () => onedesk.approvals.create(), "plus");
		this.$content.html(`<div class="one-shell-section" data-list="approvals"></div>`);
		onedesk.shell.table(this.$content.find('[data-list="approvals"]'), {
			title: __("Approvals"),
			rows: data.rows || [],
			page_size: 100,
			icon: "route",
			empty: __("No approvals"),
			none: __("No matching approvals"),
			open: (one) => frappe.set_route("workflow-builder", one.name),
			columns: [
				{
					label: __("Approval"),
					render: (one) => esc(one.workflow_name || one.name) + (one.is_active ? " " + frappe.ui.badge.html({ label: __("Active"), theme: "green" }) : ""),
				},
				{ label: __("Record Type"), fieldname: "label" },
				{ label: __("Steps"), render: (one) => esc(String(one.steps)) },
			],
		});
	}

	draw_printing(data) {
		const esc = frappe.utils.escape_html;
		this.page.set_primary_action(__("New Letter Head"), () => this.letter_head(), "plus");
		const kinds = [...new Map((data.formats || []).map((one) => [one.doc_type, one.label])).entries()];
		this.$content.html(
			onedesk.shell.section(
				__("Letter Heads"),
				'<div class="one-print-heads"></div>'
			) +
				onedesk.shell.section(
					__("Print Formats"),
					'<div class="one-print-kinds"></div>'
				)
		);
		const $heads = this.$content.find(".one-print-heads");
		const heads = data.letter_heads || [];
		if (!heads.length) {
			$heads.html(onedesk.shell.empty(__("No letter heads"), null, { icon: "image" }));
		} else {
			const $grid = $('<div class="dts-pf-grid"></div>').appendTo($heads);
			heads.forEach((one) => $grid.append(this.letter_head_card(one)));
		}
		const $kinds = this.$content.find(".one-print-kinds");
		if (!kinds.length) {
			$kinds.html(onedesk.shell.empty(__("No print formats"), null, { icon: "printer" }));
			return;
		}
		frappe.require("doctype_settings.bundle.js", () => {
			onedesk.doctype_settings.adapt();
			for (const [doctype, label] of kinds) {
				frappe.model.with_doctype(doctype, () => {
					const panel = new frappe.ui.SettingsDialogPanel({ hide() {} }, {});
					const set_view = panel.set_view.bind(panel);
					panel.set_view = (view) => set_view({ ...view, title: __(label), description: null });
					panel.$el.appendTo($kinds);
					frappe.doctype_settings.builders["print-format"](panel, doctype);
				});
			}
		});
	}

	letter_head_card(one) {
		const $card = $(`
			<div class="dts-pf-card${one.is_default ? " is-default" : ""}">
				<div class="dts-pf-preview">
					<div class="dts-pf-badge one-print-badges">${[
						Settings.theirs(one) ? frappe.ui.badge.html({ label: __("Standard"), theme: "gray" }) : "",
						one.disabled ? frappe.ui.badge.html({ label: __("Disabled"), theme: "gray" }) : "",
					].join("")}</div>
					<button type="button" class="dts-pf-star" data-selected="${one.is_default ? "true" : "false"}">${frappe.utils.icon("star", "sm")}</button>
					<div class="dts-pf-thumb"></div>
				</div>
				<div class="dts-pf-footer"><span class="dts-pf-name ellipsis"></span></div>
			</div>`);
		const $thumb = $card.find(".dts-pf-thumb");
		$card.find(".dts-pf-name").text(one.name).on("click", () => this.letter_head(one));
		$thumb.on("click", () => this.letter_head(one));
		const $star = $card.find(".dts-pf-star");
		if (one.is_default) {
			$star.attr("title", __("Default"));
		} else {
			$star.attr("title", __("Set as Default")).on("click", async (e) => {
				e.stopPropagation();
				await frappe.xcall("onedesk.one.printing.save_letter_head", { values: { name: one.name, modified: one.modified, is_default: 1 } });
				frappe.show_alert({ message: __("Default updated"), indicator: "green" });
				this.refresh({ fresh: true });
			});
		}
		requestAnimationFrame(() => {
			const scale = ($thumb.width() || 200) / Settings.SHEET;
			$thumb.append(Settings.frame(Settings.sheet(one.drawn_top, one.drawn_foot || "", scale, true), "one-print-head-frame"));
		});
		return $card;
	}

	letter_head(one = null) {
		const theirs = !!one && Settings.theirs(one);
		const esc = frappe.utils.escape_html;
		const kept = one && one.one_top ? frappe.utils.parse_json(one.one_top) : null;
		let preset = one ? (kept && kept.preset) || null : "classic";
		const shows = (kept && kept.show) || ["address", "phone", "email", "website"];
		const kept_foot = one && one.one_foot ? frappe.utils.parse_json(one.one_foot) : null;
		let foot = one ? (kept_foot && kept_foot.preset) || (one.footer ? null : "none") : "centred";
		const foot_shows = (kept_foot && kept_foot.show) || ["phone", "website", "tax_id"];
		const SHOWN = [
			["name", __("Name")],
			["address", __("Address")],
			["phone", __("Phone")],
			["email", __("Email")],
			["website", __("Website")],
			["tax_id", __("Tax ID")],
		];
		const page = Settings.sheet;
		const frame = Settings.frame;
		const dialog = new frappe.ui.Dialog({
			title: one ? one.name : __("New Letter Head"),
			size: theirs ? "" : "extra-large",
			fields: [
				...(theirs ? [{ fieldtype: "HTML", fieldname: "theirs", options: frappe.ui.alert.html({ title: __("A standard letter head can only be set as default or disabled."), theme: "gray" }) }] : []),
				{ fieldtype: "Data", fieldname: "letter_head_name", label: __("Name"), reqd: 1, hidden: one ? 1 : 0 },
				{ fieldtype: "HTML", fieldname: "preview" },
				{ fieldtype: "Section Break" },
				{ fieldtype: "Check", fieldname: "is_default", label: __("Default"), description: __("Printed on a document unless another is chosen.") },
				{ fieldtype: "Check", fieldname: "disabled", label: __("Disabled") },
			],
			primary_action_label: one ? __("Update") : __("Create"),
			primary_action: async (values) => {
				await frappe.xcall("onedesk.one.printing.save_letter_head", {
					values: {
						letter_head_name: values.letter_head_name,
						is_default: values.is_default,
						disabled: values.disabled,
						...(preset && !theirs ? { one_top: settings() } : {}),
						...(foot && !theirs ? (foot === "none" ? { one_foot: null, footer_source: "HTML", footer: "" } : { one_foot: foot_settings() }) : {}),
						name: one ? one.name : null,
						modified: one ? one.modified : null,
					},
				});
				dialog.hide();
				frappe.show_alert({ message: one ? __("Letter head updated") : __("Letter head created"), indicator: "green" });
				this.refresh({ fresh: true });
			},
		});
		const group = (fields) => {
			const made = new frappe.ui.FieldGroup({ body: document.createElement("div"), fields });
			made.make();
			return made;
		};
		const top_part = theirs
			? null
			: group([
					{ fieldtype: "HTML", fieldname: "presets" },
					{ fieldtype: "Section Break" },
					{
						fieldtype: "MultiCheck",
						fieldname: "show",
						label: __("Show"),
						columns: 2,
						sort_options: false,
						options: SHOWN.map(([value, label]) => ({ value, label, checked: shows.includes(value) ? 1 : 0 })),
						on_change: () => drawn(),
					},
					{ fieldtype: "Int", fieldname: "logo_height", label: __("Logo Height"), description: __("In pixels."), default: (kept && kept.logo_height) || 60, change: () => drawn() },
					{ fieldtype: "Check", fieldname: "line", label: __("Brand Line"), description: __("A line in the Brand Colour under the header."), default: kept && kept.line ? 1 : 0, change: () => drawn() },
					{ fieldtype: "Select", fieldname: "align", label: __("Logo Alignment"), options: [{ value: "left", label: __("Left") }, { value: "center", label: __("Centre") }, { value: "right", label: __("Right") }], default: (kept && kept.align) || "left", change: () => drawn() },
					{ fieldtype: "HTML", fieldname: "from_general", options: `<p class="text-muted small">${esc(__("The name, logo, address, contacts and colour come from Workspace › General."))}</p>` },
				]);
		const foot_part = theirs
			? null
			: group([
					{ fieldtype: "HTML", fieldname: "feet" },
					{ fieldtype: "Section Break", fieldname: "foot_settings" },
					{
						fieldtype: "MultiCheck",
						fieldname: "foot_show",
						label: __("Show"),
						columns: 2,
						sort_options: false,
						options: [["logo", __("Logo")], ...SHOWN].map(([value, label]) => ({ value, label, checked: foot_shows.includes(value) ? 1 : 0 })),
						on_change: () => drawn(),
					},
					{ fieldtype: "Data", fieldname: "foot_note", label: __("Note"), description: __("For example, a thank-you line."), default: (kept_foot && kept_foot.note) || "", change: () => drawn() },
					{ fieldtype: "Check", fieldname: "foot_line", label: __("Brand Line"), description: __("A line in the Brand Colour over the footer."), default: kept_foot && kept_foot.line ? 1 : 0, change: () => drawn() },
				]);
		const part = (fieldname) => (top_part.fields_dict[fieldname] ? top_part : foot_part);
		const parts = theirs
			? null
			: {
					get_value: (fieldname) => part(fieldname).get_value(fieldname),
					get_field: (fieldname) => part(fieldname).get_field(fieldname),
					set_df_property: (fieldname, property, value) => part(fieldname).set_df_property(fieldname, property, value),
			  };
		if (!theirs) {
			const tabs = new frappe.ui.Tabs({
				tabs: [
					{ label: __("Header"), content: $(top_part.body)[0] },
					{ label: __("Footer"), content: $(foot_part.body)[0] },
				],
			});
			const $studio = $(`<div class="one-lh-studio"><div class="one-lh-side"></div><div class="one-lh-stage"></div></div>`);
			$studio.find(".one-lh-side").append(tabs.$el);
			dialog.get_field("preview").$wrapper.empty().append($studio);
		}
		const settings = () => ({
			preset,
			show: parts.get_value("show") || [],
			logo_height: parts.get_value("logo_height"),
			align: parts.get_value("align"),
			line: parts.get_value("line") ? 1 : 0,
		});
		const foot_settings = () => ({
			preset: foot,
			show: parts.get_value("foot_show") || [],
			note: parts.get_value("foot_note") || "",
			line: parts.get_value("foot_line") ? 1 : 0,
		});
		const foot_html = () => {
			if (foot === "none") return "";
			const chosen = drawn_feet.find((d) => d.preset === foot);
			return chosen ? chosen.html : (one && one.drawn_foot) || "";
		};
		const show_preview = (top, bottom = foot_html()) => {
			const $stage = theirs ? dialog.get_field("preview").$wrapper : dialog.get_field("preview").$wrapper.find(".one-lh-stage");
			const scale = Math.min(1, (($stage.width() || 600) - 2) / Settings.SHEET, (window.innerHeight - 320) / Settings.PAGE);
			const sheet = frame(page(top, bottom, scale, true), "one-letter-head-sheet");
			sheet.style.height = `${Math.ceil(Settings.PAGE * scale) + 2}px`;
			sheet.style.width = `${Math.ceil(Settings.SHEET * scale) + 2}px`;
			$stage.empty().append(sheet);
		};
		let drawn_with = [];
		let drawn_feet = [];
		const cards = () => {
			const field = parts.get_field("presets");
			if (!field) return;
			const $grid = $(`<div class="one-lh-presets"></div>`);
			for (const one_preset of drawn_with) {
				const $card = $(`<button type="button" class="one-lh-preset"></button>`)
					.toggleClass("one-lh-preset--chosen", one_preset.preset === preset)
					.text(one_preset.label)
					.on("mouseenter", () => show_preview(one_preset.html))
					.on("mouseleave", () => shown())
					.on("click", () => {
						preset = one_preset.preset;
						cards();
						shown();
					});
				$grid.append($card);
			}
			const note = preset
				? ""
				: `<p class="text-muted small">${esc(__("This header is custom HTML. Choosing a preset replaces it."))}</p>`;
			field.$wrapper.empty().append(note).append($grid);
		};
		const feet = () => {
			const field = parts.get_field("feet");
			if (!field) return;
			const $grid = $(`<div class="one-lh-presets one-lh-presets--feet"></div>`);
			const top_now = () => (drawn_with.find((d) => d.preset === preset) || {}).html || (one && one.drawn_top);
			for (const one_foot of [...drawn_feet, { preset: "none", label: __("None"), html: "" }]) {
				const $card = $(`<button type="button" class="one-lh-preset"></button>`)
					.toggleClass("one-lh-preset--chosen", one_foot.preset === foot)
					.text(one_foot.label)
					.on("mouseenter", () => show_preview(top_now(), one_foot.html))
					.on("mouseleave", () => shown())
					.on("click", () => {
						foot = one_foot.preset;
						feet();
						shown();
					});
				$grid.append($card);
			}
			const note = foot
				? ""
				: `<p class="text-muted small">${esc(__("This footer is custom HTML. Choosing a preset replaces it."))}</p>`;
			field.$wrapper.empty().append(note).append($grid);
		};
		const shown = () => {
			if (theirs) return show_preview(one.drawn_top);
			parts.set_df_property("align", "hidden", preset !== "logo");
			for (const fieldname of ["foot_show", "foot_note", "foot_line"]) {
				parts.set_df_property(fieldname, "hidden", !foot || foot === "none");
			}
			const chosen = drawn_with.find((d) => d.preset === preset);
			show_preview(chosen ? chosen.html : one && one.drawn_top);
		};
		const drawn = frappe.utils.debounce(async () => {
			if (theirs) return shown();
			[drawn_with, drawn_feet] = await Promise.all([
				frappe.xcall("onedesk.one.letter_heads.presets", { settings_of: settings() }),
				frappe.xcall("onedesk.one.letter_heads.presets", { settings_of: foot_settings(), part: "foot" }),
			]);
			cards();
			feet();
			shown();
		}, 200);
		if (one) dialog.set_values({ letter_head_name: one.letter_head_name || one.name, is_default: one.is_default, disabled: one.disabled });
		if (one && !theirs) {
			dialog.set_secondary_action_label(__("Edit in Builder"));
			dialog.set_secondary_action(() => {
				dialog.hide();
				this.design_letter_head(one.name);
			});
			dialog.add_custom_action(__("Delete"), () =>
				frappe.confirm(__("Delete letter head {0}?", [one.name]), async () => {
					await frappe.xcall("frappe.client.delete", { doctype: "Letter Head", name: one.name });
					dialog.hide();
					this.refresh({ fresh: true });
				})
			);
		}
		dialog.show();
		drawn();
	}

	async design_letter_head(name) {
		const designer = await frappe.xcall("onedesk.one.printing.design_letter_head", { letter_head: name });
		frappe.set_route("print-format-builder", designer);
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
					{ label: "", render: (one) => Settings.read_switch(one.on) },
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
					{ label: "", render: () => Settings.read_switch(true) },
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

	draw_holidays(data) {
		const esc = frappe.utils.escape_html;
		const open_list = (name) => this.open("holidays", { record: name === data.now ? null : name });
		const use_another = () => {
			const dialog = new frappe.ui.Dialog({
				title: __("Use Another List"),
				fields: [
					{ fieldname: "holiday_list", fieldtype: "Link", options: "Holiday List", label: __("Holiday List"), reqd: 1 },
					{
						fieldname: "said",
						fieldtype: "HTML",
						options: `<div class="one-shell-quiet">${esc(
							__("Applies to everyone from today, or from its start date. Used for leave, attendance, check-ins, the calendar and deadlines.")
						)}</div>`,
					},
				],
				primary_action_label: __("Use List"),
				primary_action: async (values) => {
					await frappe.xcall("onedesk.one.holidays.use", { holiday_list: values.holiday_list });
					dialog.hide();
					this.refresh({ fresh: true });
				},
			});
			dialog.show();
		};
		const next_year = async () => {
			const name = await frappe.xcall("onedesk.one.holidays.next_year");
			frappe.show_alert({ message: __("{0} created", [name]), indicator: "green" });
			open_list(name);
		};
		if (data.empty) {
			this.$content.append(
				onedesk.shell.section(__("Holidays"), onedesk.shell.empty(__("No holiday list")))
			);
			this.page.add_inner_button(__("Use Another List"), use_another);
			return;
		}
		const list = data.list;
		const day = (value) => frappe.datetime.str_to_user(value);
		if (list.in_force && !data.next && list.days_left <= 90) {
			const $make = $(onedesk.shell.button(__("Create Next Year's List"), {}, "ghost")).on("click", next_year);
			this.$content.append(
				$(
					frappe.ui.alert({
						title: __("This list ends on {0}, in {1} days", [day(list.to_date), list.days_left]),
						description: __("After that, every day counts as a working day for leave and attendance, until another list starts."),
						theme: "yellow",
						footer: $make,
					})
				).addClass("os-holiday-alert")
			);
		} else if (!list.in_force) {
			const $back = $(onedesk.shell.button(__("Back to {0}", [data.now]), {}, "ghost")).on("click", () => open_list(data.now));
			this.$content.append(
				$(
					frappe.ui.alert({
						title: __("{0} starts on {1}", [list.name, day(list.from_date)]),
						description: __("Until then, {0} applies.", [data.now]),
						theme: "blue",
						footer: $back,
					})
				).addClass("os-holiday-alert")
			);
		}
		const fact = (value, label, href) =>
			`<${href ? `a href="${esc(href)}"` : "div"} class="os-intake-fact"><span class="os-intake-number">${esc(String(value))}</span><span class="one-shell-quiet">${esc(label)}</span></${href ? "a" : "div"}>`;
		const coming = (data.coming || [])[0];
		const facts = `<div class="os-intake-facts">${[
			fact(list.public, __("Public Holidays")),
			fact(list.days_off, __("Weekly Days Off")),
			coming ? fact(day(coming.date), coming.what) : fact("–", __("No More Holidays This Year")),
			fact(day(list.to_date), list.days_left >= 0 ? __("Last Day, in {0} days", [list.days_left]) : __("Ended")),
			...(data.elsewhere ? [fact(data.elsewhere, __("People on Other Lists"), "/desk/holiday-list-assignment?applicable_for=Employee&docstatus=1")] : []),
		].join("")}</div>`;
		this.$content.append(
			onedesk.shell.section(list.name, facts, __("{0} to {1}", [day(list.from_date), day(list.to_date)]))
		);
		this.form(data, {
			rows: [
				{ heading: __("Days Off") },
				{ stack: ["weekly_offs"] },
				{ heading: __("Public Holidays") },
				["country", "subdivision"],
				{ html: onedesk.shell.button(__("Add Public Holidays"), { "data-local": "1" }, "subtle", "plus") },
				{ stack: ["holidays"] },
			],
		});
		const country = this.group.get_field("country");
		const region = this.group.get_field("subdivision");
		const regions = async () => {
			const code = this.group.get_value("country");
			region.set_data(code ? await frappe.xcall("onedesk.one.holidays.subdivisions", { country: code }) : []);
		};
		country.df.onchange = regions;
		this.$content.find("[data-local]").on("click", async () => {
			const code = this.group.get_value("country");
			if (!code) return frappe.msgprint(__("Choose the country first."));
			const found = await frappe.xcall("onedesk.one.holidays.country_holidays", {
				country: code,
				subdivision: this.group.get_value("subdivision") || null,
				from_date: list.from_date,
				to_date: list.to_date,
			});
			const table = this.group.get_field("holidays");
			const held = new Set((table.df.data || []).map((one) => one.holiday_date));
			const added = found.filter((one) => !held.has(one.holiday_date));
			table.df.data = [...(table.df.data || []), ...added].sort((a, b) => (a.holiday_date < b.holiday_date ? -1 : 1));
			table.df.data.forEach((one, at) => (one.idx = at + 1));
			table.grid.refresh();
			this.check();
			frappe.show_alert({ message: added.length ? __("{0} holidays added. Save to keep them.", [added.length]) : __("All holidays are already in the list."), indicator: "blue" });
		});
		if (list.in_force && data.next) this.page.add_inner_button(__("Next Year's List"), () => open_list(data.next));
		else if (list.in_force) this.page.add_inner_button(__("Create Next Year's List"), next_year);
		this.page.add_inner_button(__("Use Another List"), use_another);
	}

	draw_notification_types(data) {
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
		const open_rule = (name) => frappe.set_route("workspace-settings", { section: this.key, rule: name });
		this.$content.html(
			`<div class="one-shell-section one-shell-note one-shell-quiet">${esc(
				__("Blue means on by default.")
			)}</div>
			<div class="one-shell-section" data-list="rules"></div>
			<div class="one-shell-section" data-list="types"></div>`
		);
		onedesk.shell.table(this.$content.find('[data-list="rules"]'), {
			title: __("Rules"),
			rows: data.rules || [],
			icon: "bell-plus",
			empty: __("No rules"),
			open: (one) => open_rule(one.name),
			actions:
				onedesk.oneai.button(
					__("Ask OneAI"),
					__("Help me set up a notification rule. Ask me what should happen and who should be told, then suggest the rule.")
				) +
				onedesk.shell.button(__("New Rule"), { "data-rule-new": "1" }, "subtle", "plus"),
			columns: [
				{ label: __("Rule"), fieldname: "name" },
				{ label: __("Description"), render: (one) => `<span class="one-shell-quiet">${esc(one.said || "")}</span>` },
				{ label: "", render: (one) => (one.enabled ? "" : frappe.ui.badge.html({ label: __("Off"), theme: "gray" })) },
			],
		});
		onedesk.shell.table(this.$content.find('[data-list="types"]'), {
			title: __("Notifications"),
			rows: data.apps.flatMap((group) => group.types.map((one) => ({ ...one, app: group.app, mark: group.mark }))),
			page_size: 100,
			icon: "bell",
			none: __("No matching notifications"),
			open: (one) => one.ours && frappe.set_route("workspace-settings", { section: this.key, type: one.name }),
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
		const rewrite = () =>
			onedesk.oneai.open({
				ask: __(
					'Rewrite the "{0}" notification to be short, plain and friendly. Keep every field it uses and suggest it as a change I can apply.',
					[type.label]
				),
			});
		const reset = async () => {
			await this.group.set_values({ one_subject: type.default_subject, one_message: type.default_message });
			this.check();
			this.preview(type.name, $card);
		};
		this.as_record({
			parent: __("Notifications"),
			route: "/desk/workspace-settings?section=notification_types",
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
			actions:
				type.ours && !type.upstream
					? [
							{ label: __("Rewrite with OneAI"), action: rewrite },
							{ label: __("Reset to Default"), action: reset, group: __("Actions") },
					  ]
					: [],
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
		const said = await frappe.xcall(Settings.API + "preview_notification", {
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
				await frappe.xcall(Settings.API + "delete_rule", { name: rule.name });
				frappe.set_route("workspace-settings", { section: this.key });
			});
		this.as_record({
			parent: __("Notifications"),
			route: "/desk/workspace-settings?section=notification_types",
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
		if (!rule.new && this.record === "rule:new") frappe.set_route("workspace-settings", { section: this.key, rule: rule.name });
	}
};
