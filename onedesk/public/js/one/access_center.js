// AccessCenter (docs/READY.md, mechanism 14): who may do what in each module
// that declares its abilities (one/access_center.py). A module's part, from
// Roles and Access in its ControlCenter, is three tabs: its Roles matrix,
// its People and their role in it, and what people were given On One
// Record. The whole, from the key in the bottom bar and the arrows, is every
// such module, each a group of the three. For workspace administrators.
frappe.provide("onedesk.access");

onedesk.access.ROLE_FILES = ["/assets/onedesk/js/one/role_matrix.js", "/assets/onedesk/css/one/role_matrix.css"];

onedesk.centers.declare("access", {
	instead: () =>
		!frappe.boot.one_administers &&
		(() => {
			frappe.show_alert({ message: __("Only the workspace's administrators set who may do what."), indicator: "orange" });
			return null;
		}),
	files: onedesk.access.ROLE_FILES,
	help: ["One", "access-and-the-audit-log"],
	css: "one-access",
	async sections(ctx) {
		const { module, at, record } = ctx;
		const A = "onedesk.one.access_center.";
		const kit = onedesk.centers.kit;
		const esc = frappe.utils.escape_html;
		const apps = module ? [module] : await frappe.xcall(A + "modules");
		const app_icon = (app) => onedesk.centers.app_icon(app, "shield-check");

		const role_actions = (app) => [
			{ label: __("Show Roles"), icon: "eye", click: (panel) => onedesk.roles.pick(panel, app) },
			{ label: __("New Role"), icon: "plus", click: (panel) => onedesk.roles.create(panel, app) },
		];
		const roles_tab = (app) => ({
			id: `${app}:roles`,
			label: __("Roles"),
			icon: "shield-check",
			title: __("Roles"),
			description: __("What each role can do in {0}.", [app]),
			actions: role_actions(app),
			/** The role matrix: a switch for each role and ability (role_matrix.js),
			 * which no declared kind draws. */
			render(panel) {
				onedesk.roles.draw(panel, app);
			},
		});

		// Everybody and their role in the app, changed in place as People
		// changes it.
		const people_tab = (app) => ({
			id: `${app}:people`,
			label: __("People"),
			icon: "users",
			title: __("People"),
			description: __("Everybody's role in {0}.", [app]),
			/** Each person with a picker of their role at the row's end, saved as
			 * it changes and put back if refused: rows whose end is a control. */
			render: (panel) => people(app, panel.body.empty()),
		});
		const people = async (app, $body) => {
				const said = await frappe.xcall(A + "people", { app });
				const $list = $(`<div class="one-set-list one-access-people"></div>`).appendTo($body);
				for (const one of said.people) {
					const $row = kit
						.row({ lead: frappe.avatar(null, "avatar-small", one.name, one.image || ""), title: one.name, sub: esc(one.user) })
						.attr("data-find", `${one.name} ${one.user}`.toLowerCase())
						.appendTo($list);
					const control = frappe.ui.form.make_control({
						df: { fieldtype: "Select", fieldname: "level", label: "", options: said.levels },
						parent: $(`<span class="one-access-level"></span>`).appendTo($row.find(".one-set-end")),
						render_input: true,
						only_input: true,
					});
					control.set_value(one.level);
					control.$input.attr("aria-label", __("{0}'s role in {1}", [one.name, app])).on("change", async () => {
						const level = control.get_value();
						try {
							one.level = await frappe.xcall(A + "put", { app, user: one.user, level });
							kit.saved();
						} catch (e) {
							control.set_value(one.level);
						}
					});
				}
		};

		// What people were given on one record beyond their role (a shared
		// mailbox's Users), each changed or taken away here as on the record.
		const records_tab = (app) => ({
			id: `${app}:records`,
			label: __("On One Record"),
			icon: "key-round",
			title: __("On One Record"),
			description: __("People given more than their role on one record, from that record's own screen."),
			/** Each grant with Edit and Remove at its end, and nothing to say
			 * when there are none: rows with buttons of their own. */
			render: (panel) => records(app, panel.body.empty(), panel),
		});
		const records = async (app, $body, panel) => {
				const said = await frappe.xcall(A + "records", { app });
				const labelled = Object.fromEntries(said.abilities.map((one) => [one.key, one.label]));
				if (!said.grants.length) {
					return $(`<div class="one-shell-quiet"></div>`).text(__("Nobody has been given more than their role.")).appendTo($body);
				}
				const $list = $(`<div class="one-set-list"></div>`).appendTo($body);
				for (const one of said.grants) {
					const $row = kit
						.row({
							lead: frappe.ui.avatar.html({ label: one.name, size: "md" }),
							title: one.name,
							sub: esc(__("{0}: {1}", [one.title, one.given.map((key) => labelled[key]).join(", ")])),
						})
						.appendTo($list);
					const $end = $row.find(".one-set-end");
					kit.button({ label: __("Edit"), variant: "outline", size: "sm" })
						.on("click", () => edit(app, said, one, panel))
						.appendTo($end);
					kit.remove(() =>
						frappe.confirm(__("Take away what {0} was given on {1}?", [esc(one.name), esc(one.title)]), async () => {
							await frappe.xcall(A + "give", { app, record: one.record, user: one.user, keys: [] });
							panel.refresh();
						})
					).appendTo($end);
				}
		};

		// The whole centre has one row per app, its Roles, People and, where
		// the app gives access on one record, On One Record chosen in the head.
		const SIDES = { roles: __("Roles"), people: __("People"), records: __("On One Record") };
		const ABOUT = {
			roles: (app) => __("What each role can do in {0}.", [app]),
			people: (app) => __("Everybody's role in {0}.", [app]),
			records: () => __("People given more than their role on one record, from that record's own screen."),
		};
		const app_tab = (app, sides, side) => ({
			id: `app:${app}`,
			label: app,
			icon_html: app_icon(app),
			title: app,
			description: ABOUT[side](app),
			/** Roles, People and On One Record for one app, chosen by TabButtons
			 * in the head: three bodies behind one section. */
			render(panel) {
				const $body = panel.body.empty();
				const $tools = $(`<div class="one-access-tools"></div>`).appendTo($body);
				const $at = $(`<div></div>`).appendTo($body);
				// The role matrix draws into a panel's body; this one is the page's.
				const part = Object.assign(Object.create(panel), { body: $at, shown: 0 });
				const draw = (chosen) => {
					panel.$header.find(".settings-dialog-panel-description").text(ABOUT[chosen](app));
					$tools.empty();
					if (chosen === "roles") {
						for (const one of role_actions(app)) {
							kit.button({ label: one.label, icon: one.icon, variant: "subtle" }).on("click", () => one.click(part)).appendTo($tools);
						}
						return onedesk.roles.draw(part, app);
					}
					return chosen === "people" ? people(app, $at.empty()) : records(app, $at.empty(), { refresh: () => draw("records") });
				};
				const tabs = new frappe.ui.TabButtons({
					label: __("Show"),
					options: sides.map((one) => ({ label: SIDES[one], value: one })),
					value: side,
					on_change: draw,
				});
				panel.$header.removeClass("hide").find(".settings-dialog-panel-actions").empty().append(tabs.$el);
				draw(side);
			},
		});

		const edit = (app, said, one, panel) => {
			const dialog = new frappe.ui.Dialog({
				title: __("Access for {0}", [one.name]),
				fields: [
					{ fieldname: "where", fieldtype: "HTML", options: `<p class="text-muted small">${esc(__("Only in {0}.", [one.title]))}</p>` },
					{
						fieldname: "keys",
						fieldtype: "MultiCheck",
						columns: 2,
						options: said.abilities.map((ability) => ({ label: ability.label, value: ability.key, checked: one.given.includes(ability.key) })),
					},
				],
				primary_action_label: __("Save"),
				primary_action: async ({ keys }) => {
					await frappe.xcall(A + "give", { app, record: one.record, user: one.user, keys: keys || [] });
					dialog.hide();
					kit.saved();
					panel.refresh();
				},
			});
			dialog.show();
		};

		// The whole starts with the workspace's own roles, profiles and groups,
		// for every app that doesn't declare its abilities.
		const across = module
			? []
			: [
					{
						group: null,
						items: [
							{
								id: "access",
								label: __("Roles and Profiles"),
								icon: "id-card",
								description: __("Profiles give people their apps at once, groups share records, and custom roles sit between User and Manager."),
								section: onedesk.AccessSection,
								record: at === "access" ? record : null,
							},
						],
					},
			  ];
		// Who changed what, who signed in, and what left as a file or a print,
		// newest first (one/audit.py `log`), each row opening frappe's record.
		const audit_tab = {
			id: "audit",
			label: __("Audit Log"),
			icon: "scroll-text",
			title: __("Audit Log"),
			description: __("Who changed what, who signed in, and what left the workspace as a file or a print."),
			/** A row of filters over the log, each loading it again: rows that
			 * change with a choice above them. */
			async render(panel) {
				const kinds = [
					["", __("Everything")],
					["changes", __("Changes")],
					["signins", __("Sign-ins")],
					["exports", __("Exports and Prints")],
				];
				const glyphs = { changes: "pencil", signins: "log-in", exports: "file-down" };
				const $body = panel.body.empty();
				const $chips = $(`<div class="one-set-chips"></div>`).appendTo($body);
				const $list = $(`<div class="one-set-list"></div>`).appendTo($body);
				const draw = async (kind) => {
					$chips.empty();
					for (const [one, label] of kinds) {
						kit.button({ label, variant: one === kind ? "solid" : "subtle", size: "sm" }).attr("data-kind", one).on("click", () => draw(one)).appendTo($chips);
					}
					const rows = await frappe.xcall(A.replace("access_center.", "audit.") + "log", { kind }, "GET");
					$list.empty();
					if (!rows.length) $list.append(kit.empty(__("Nothing yet.")));
					for (const one of rows) {
						kit.row({
							lead: kit.glyph(glyphs[one.kind]),
							title: [one.what, one.of].filter(Boolean).join(" "),
							sub: esc([one.who, frappe.datetime.prettyDate(one.when), one.ip].filter(Boolean).join(" · ")),
							open: () => (ctx.centre.hide(), frappe.set_route("Form", one.doctype, one.name)),
						}).appendTo($list);
					}
				};
				draw("");
			},
		};
		if (across.length) across[0].items.push(audit_tab);
		const shared = (frappe.boot.one_centers || {}).shared || [];
		// OneMail:people and the like, as links into the whole centre still say.
		const [at_app, at_side] = !module && at && at.includes(":") ? (at.startsWith("app:") ? [at.slice(4), null] : at.split(":")) : [null, null];
		const sides_of = (app) => ["roles", "people", ...(shared.includes(app) ? ["records"] : [])];
		const tabs = module
			? [{ group: null, items: [roles_tab(module), people_tab(module), ...(shared.includes(module) ? [records_tab(module)] : [])] }]
			: [
					...across,
					{
						group: __("Apps"),
						items: apps.map((app) => app_tab(app, sides_of(app), app === at_app && sides_of(app).includes(at_side) ? at_side : "roles")),
					},
			  ];
		ctx.at = at_app ? `app:${at_app}` : at;
		return tabs;
	},
});

// The workspace's own roles, profiles and groups, for the apps that don't
// declare abilities (one/access_center.py `load`): a role, profile or group
// opens as the record the tab is on, with Back to the lists.
onedesk.AccessSection = class AccessSection extends onedesk.CenterSection {
	static API = "onedesk.one.access_center.";
	static HERE = "access";
	static LABEL = "AccessCenter";
	// A role of a module that declares its abilities is that module's part.
	static in_access = (app) => ((frappe.boot.one_centers || {}).access || []).includes(app);
	static access = (app) => onedesk.centers.open("access", { module: app, at: `${app}:roles` });

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
					this.open("access", { record: `${key}:${name}` });
				},
			});
			dialog.show();
		};
		this.page.clear_primary_action();
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
			open: (one) => this.open("access", { record: `profile:${one.name}` }),
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
			open: (one) => this.open("access", { record: `group:${one.name}` }),
			columns: [
				{ label: __("Group"), render: (one) => esc(one.name) },
				{ label: __("People"), render: (one) => esc(String(one.members)) },
			],
		});
		const tier = (one) => (one.own ? esc(one.name) : esc(__(one.name)));
		onedesk.shell.table(this.$content.find('[data-list="levels"]'), {
			title: __("Roles"),
			rows: data.levels,
			actions: $(onedesk.shell.button(__("New Role"), {}, "subtle", "plus")).on("click", () => this.new_level(data)),
			icon: "shield-check",
			none: __("No matching roles"),
			open: (one) => (AccessSection.in_access(one.app) ? AccessSection.access(one.app) : this.open("access", { record: `level:${one.key}` })),
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
				if (AccessSection.in_access(app)) return AccessSection.access(app);
				this.open("access", { record: `level:${name}` });
			},
		});
		dialog.show();
	}

	draw_level(data) {
		const esc = frappe.utils.escape_html;
		const level = data.level;
		const title = level.own ? level.name : `${level.app} ${__(level.name)}`;
		this.as_record({
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
									.map((one) => `<a class="one-record-link" href="/desk/one?center=account&at=people&record=${encodeURIComponent(one.name)}">${esc(one.full_name || one.name)}</a>`)
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
									this.open("access");
								}),
						},
					]
				: [],
		});
		// What the role may do in the module, grouped as the module groups
		// it (one/rights.py), then its record types.
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
									.map((who) => `<a class="one-record-link" href="/desk/one?center=account&at=people&record=${encodeURIComponent(who.name)}">${esc(who.full_name || who.name)}</a>`)
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
							this.open("access");
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
							this.open("access");
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
};
