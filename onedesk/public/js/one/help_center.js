// HelpCenter and UpdateCenter (one/versions.py): a module's Help pages and
// its versions, or every module's that is on, each a branch of the tree. A
// page's id is the module's own then, `OneMail/overview`, `OneMail@1.6.1`.
// Both are written in English only, for the people using the module.
// UpdateCenter starts with This Workspace: the next update and the window
// it runs in, as OneAdmin said (one/update_window.py).
frappe.provide("onedesk.help_center");

onedesk.help_center.ICONS = { major: "rocket", minor: "sparkles", fix: "wrench" };
onedesk.help_center.KINDS = () => ({ major: __("Major"), minor: __("Update"), fix: __("Fix") });

/** Every module that has versions and is on, One first, then the apps,
 * then the modules that are centres, each kind in the order the boot gives;
 * an app the workspace turned off, or its plan leaves out, is not there. */
onedesk.help_center.modules = (module) => {
	if (module) return [module];
	const rank = (of) => (of === onedesk.names.of("one") ? 0 : onedesk.centers.as_centre(of) ? 2 : 1);
	const versions = frappe.boot.one_versions || {};
	return Object.keys(versions)
		.filter((of) => !versions[of].off)
		.map((of, at) => [of, at])
		.sort((a, b) => rank(a[0]) - rank(b[0]) || a[1] - b[1])
		.map(([of]) => of);
};

/** A module's branch of the whole tree, drawn as the rail draws it; only the
 * first is open, so the tree starts short. */
onedesk.help_center.branch = (of, at, children) => ({
	id: `module:${of}`,
	label: of,
	icon_html: onedesk.centers.app_icon(of, of.toLowerCase()),
	tab: false,
	open: at === 0,
	children,
});

/** A titled row of buttons under a page: Read More, Changed In. */
onedesk.help_center.more = (panel, title, buttons) => {
	if (!buttons.length) return;
	const $more = $(`<div class="one-docs-more"></div>`).appendTo(panel.body);
	$(`<div class="one-docs-more-title"></div>`).text(title).appendTo($more);
	for (const one of buttons) {
		$(frappe.ui.button.html({ label: one.label, variant: "outline", icon: one.icon }))
			.on("click", () => {
				panel.dialog.hide();
				one.click();
			})
			.appendTo($more);
	}
};

onedesk.centers.declare("help", {
	at: ({ module, at }) => module && at,
	async sections(ctx) {
		const { module } = ctx;
		const modules = onedesk.help_center.modules(module);
		const all = await Promise.all(modules.map((one) => frappe.xcall("onedesk.one.versions.help_pages", { module: one })));
		const id = (of, one) => (module ? one : `${of}/${one}`);
		const items = [];
		const tree = [];
		const index = [];
		all.forEach((said, at) => {
			const of = modules[at];
			const nodes = [];
			for (const one of said.pages) {
				const here = id(of, one.id);
				items.push({
					id: here,
					label: one.title,
					icon: one.icon,
					title: one.title,
					page: one.html,
					lang: "en",
					after: (panel) =>
						onedesk.help_center.more(
							panel,
							__("Changed In"),
							(one.changed || []).map((version) => ({
								label: `${version.version} · ${version.title}`,
								icon: "sparkles",
								click: () => onedesk.centers.open("updates", { module: of, at: version.version }),
							})),
						),
				});
				const sections = onedesk.centers.sections(here, one.title, one.html);
				index.push(...sections);
				nodes.push({
					id: here,
					label: one.title,
					icon: one.icon,
					children: sections
						.filter((section) => section.anchor)
						.map((section) => ({ id: `${here}#${section.anchor}`, label: section.title, tab: false, click: () => ctx.centre.go(here, section.anchor) })),
				});
			}
			tree.push(...(module ? nodes : [onedesk.help_center.branch(of, at, nodes)]));
		});
		return { groups: [{ items }], tree, index };
	},
	follow: (centre, to, at = null) => (centre.module ? centre.go(to, at) : centre.go(`${centre.here.split("/")[0]}/${to}`, at)),
	opened(centre, { module, at, anchor }) {
		if (anchor && module) setTimeout(() => centre.go(at, anchor), 300);
	},
});

onedesk.help_center.WINDOW = "one/update_window.";

onedesk.help_center.days = () => [__("Monday"), __("Tuesday"), __("Wednesday"), __("Thursday"), __("Friday"), __("Saturday"), __("Sunday")];
onedesk.help_center.hours = () => Array.from({ length: 24 }, (_, hour) => `${String(hour).padStart(2, "0")}:00`);

/** This Workspace, at the top of UpdateCenter: Next Update (when, whether
 * it waits for the organisation's agreement, what it brings, and Update
 * Now) and Update Window, the day and hour it runs. */
onedesk.help_center.workspace = (ctx, held, coming) => {
	const kit = onedesk.centers.kit;
	const esc = frappe.utils.escape_html;
	const call = (method, args, type) => frappe.xcall(`onedesk.${onedesk.help_center.WINDOW}${method}`, args, type);
	const days = onedesk.help_center.days();
	const hours = onedesk.help_center.hours();
	const again = (said) => {
		Object.assign(held, said);
		const panel = ctx.centre.get_panel("next");
		if (panel) panel.refresh();
	};
	const next = {
		id: "next",
		label: __("Next Update"),
		icon: "calendar-clock",
		title: __("Next Update"),
		description: __("When {0} next updates this workspace, and what the update brings.", [onedesk.names.of("one")]),
		page: "",
		after(panel) {
			if (!held.linked) return kit.nothing(panel.body, __("This workspace isn't connected to its account yet, so this isn't available."), "calendar-clock");
			const $list = $(`<div class="one-set-list"></div>`).appendTo(panel.body);
			const when = held.moving
				? __("Updating now. The workspace is offline for a few minutes.")
				: held.at
					? frappe.datetime.str_to_user(held.at)
					: __("No update is waiting.");
			kit.row({ lead: kit.glyph(held.moving ? "loader" : "calendar-clock"), title: __("Next Update"), sub: esc(when) }).appendTo($list);
			kit.row({
				lead: kit.glyph("clock"),
				title: __("Update Window"),
				sub: esc(__("Updates run on {0} at {1}:00.", [days[held.weekday], String(held.hour).padStart(2, "0")])),
				open: () => ctx.centre.activate("window"),
			}).appendTo($list);
			if (held.held_until && !held.moving) {
				kit.row({
					lead: kit.glyph("file-clock"),
					title: __("Waiting for Agreement"),
					sub: esc(__("Your organisation hasn't agreed to the new terms yet. The update goes ahead on {0} even so.", [frappe.datetime.str_to_user(held.held_until)])),
					end: frappe.ui.badge.html({ label: __("Waiting"), theme: "amber" }),
					open: () => (ctx.centre.hide(), onedesk.centers.open("trust", { at: "changes" })),
				}).appendTo($list);
			}
			if (held.may && held.at && !held.moving && !held.held_until) {
				kit.button({ label: __("Update Now"), variant: "solid" })
					.on("click", async () => {
						const go = await onedesk.interface.ask({
							question: __("Update now?"),
							effect: __("The workspace is offline for a few minutes."),
							verb: __("Update Now"),
						});
						if (!go) return;
						const said = await call("update_now", {});
						if (said.waiting) frappe.show_alert({ message: __("Update started."), indicator: "green" });
						else frappe.msgprint({ title: __("Update Now"), message: __("This workspace already runs the newest release.") });
						again(said);
					})
					.appendTo(kit.buttons(panel.body));
			}
			if (!coming.length) return;
			panel.body.append(kit.heading(__("What It Brings"), __("The versions the next update brings, by app.")));
			const $coming = $(`<div class="one-set-list"></div>`).appendTo(panel.body);
			for (const one of coming) {
				kit.row({
					lead: kit.glyph("sparkles"),
					title: `${one.module} ${one.version}`,
					sub: esc(one.title),
					end: kit.chevron(),
					open: () => ctx.centre.go(one.id),
				}).appendTo($coming);
			}
		},
	};
	const slot = {
		id: "window",
		label: __("Update Window"),
		icon: "clock",
		title: __("Update Window"),
		description: __("Updates run in the workspace's time zone, {0}.", [held.zone]),
		fields: () => [
			{ fieldname: "day", fieldtype: "Select", label: __("Day"), options: days.join("\n"), reqd: 1, default: days[held.weekday], read_only: held.may ? 0 : 1 },
			{ fieldname: "hour", fieldtype: "Select", label: __("Hour"), options: hours.join("\n"), reqd: 1, default: hours[held.hour], read_only: held.may ? 0 : 1 },
		],
		save: async (values) => again(await call("set_window", { weekday: days.indexOf(values.day), hour: hours.indexOf(values.hour) })),
	};
	return held.linked ? [next, slot] : [next];
};

onedesk.centers.declare("updates", {
	help: [onedesk.names.of("one"), "updates"],
	at: ({ at }) => at,
	async sections(ctx) {
		const { module } = ctx;
		const modules = onedesk.help_center.modules(module);
		const [held, ...all] = await Promise.all([
			module ? null : frappe.xcall(`onedesk.${onedesk.help_center.WINDOW}state`, {}, "GET"),
			...modules.map((one) => frappe.xcall("onedesk.one.versions.whats_new", { module: one })),
		]);
		const kinds = onedesk.help_center.KINDS();
		const id = (of, one) => (module ? one.version : `${of}@${one.version}`);
		const icon = (one) => frappe.utils.icon(onedesk.help_center.ICONS[one.kind] || "dot", "sm");
		const items = [];
		const branches = [];
		const index = [];
		const coming = [];
		all.forEach((said, at) => {
			const of = modules[at];
			for (const one of said.versions) {
				if (one.coming) coming.push({ id: id(of, one), module: of, version: one.version, title: one.title });
				items.push({
					id: id(of, one),
					label: one.version,
					icon_html: icon(one),
					title: module ? one.title : `${of} ${one.version} · ${one.title}`,
					description: [kinds[one.kind] || one.kind, frappe.datetime.str_to_user(one.date)].join(" · "),
					page: one.html,
					lang: "en",
					before(panel) {
						const $title = panel.$header.find(".settings-dialog-panel-title");
						if (one.new) $title.append(" ", frappe.ui.badge.html({ label: __("New"), theme: "blue" }));
						if (one.coming) $title.append(" ", frappe.ui.badge.html({ label: __("Coming"), theme: "amber" }));
					},
					after: (panel) =>
						onedesk.help_center.more(
							panel,
							__("Read More"),
							one.docs.map((page) => ({ label: page.title, icon: "book-open", click: () => onedesk.centers.open("help", { module: of, at: page.id }) })),
						),
				});
				index.push(...onedesk.centers.sections(id(of, one), `${one.version} ${one.title}`, one.html));
			}
			const nodes = {};
			for (const one of said.versions) {
				nodes[one.version] = { id: id(of, one), label: one.version, hint: one.title, unseen: !!one.new, icon_html: icon(one), open: true, children: [] };
			}
			const roots = [];
			for (const one of said.versions) {
				const [major, minor] = one.version.split(".");
				const parent = { fix: nodes[`${major}.${minor}.0`] || nodes[`${major}.0.0`], minor: nodes[`${major}.0.0`] }[one.kind];
				(parent && parent !== nodes[one.version] ? parent.children : roots).push(nodes[one.version]);
			}
			branches.push(...(module ? roots : [onedesk.help_center.branch(of, at, roots)]));
		});
		if (module) return { groups: [{ items }], tree: branches, index };
		const ours = onedesk.help_center.workspace(ctx, held, coming);
		return {
			groups: [
				{ group: __("This Workspace"), items: ours },
				{ group: __("What's New"), items },
			],
			tree: [{ heading: __("This Workspace") }, ...ours, { heading: __("What's New") }, ...branches],
			index,
		};
	},
	opened(_centre, { module }) {
		for (const of of onedesk.help_center.modules(module)) {
			const ours = frappe.boot.one_versions && frappe.boot.one_versions[of];
			if (ours) ours.unseen = 0;
			$(document).trigger("one-version-seen", [of]);
		}
	},
});

// Every Help page of an app that is on is found by Ctrl+K too, by its
// title, and opens in HelpCenter on its page.
if (frappe.search?.utils && !frappe.search.utils.one_help) {
	const utils = frappe.search.utils;
	utils.one_help = true;
	const pages = utils.get_pages;
	utils.get_pages = function (keywords) {
		const found = [];
		const versions = frappe.boot.one_versions || {};
		for (const module of onedesk.help_center.modules()) {
			for (const [page, title] of versions[module].pages || []) {
				const said = this.fuzzy_search(keywords, title, true);
				if (!said.score) continue;
				found.push({
					type: "Help",
					label: __("{0} in {1} Help", [said.marked_string || frappe.utils.escape_html(title), module]),
					value: __("{0} in {1} Help", [title, module]),
					match: title,
					index: said.score - 1,
					onclick: () => onedesk.centers.open("help", { module, at: page }),
				});
			}
		}
		return pages.call(this, keywords).concat(found);
	};
}
