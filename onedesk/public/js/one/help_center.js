// HelpCenter and UpdateCenter (one/versions.py): a module's Help pages and
// its versions, or every module's, each a branch of the tree. A page's id
// is the module's own then, `OneMail/overview`, `OneMail@1.6.1`. Both are
// written in English only, for the people using the module.
frappe.provide("onedesk.help_center");

onedesk.help_center.ICONS = { major: "rocket", minor: "sparkles", fix: "wrench" };
onedesk.help_center.KINDS = () => ({ major: __("Major"), minor: __("Update"), fix: __("Fix") });

/** Every module that has versions, One first, then the apps, then the
 * modules that are centres, each kind in the order the boot gives. */
onedesk.help_center.modules = (module) => {
	if (module) return [module];
	const rank = (of) => (of === "One" ? 0 : onedesk.centers.as_centre(of) ? 2 : 1);
	return Object.keys(frappe.boot.one_versions || {})
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

onedesk.centers.declare("updates", {
	at: ({ module, at }) => module && at,
	async sections({ module }) {
		const modules = onedesk.help_center.modules(module);
		const all = await Promise.all(modules.map((one) => frappe.xcall("onedesk.one.versions.whats_new", { module: one })));
		const kinds = onedesk.help_center.KINDS();
		const id = (of, one) => (module ? one.version : `${of}@${one.version}`);
		const icon = (one) => frappe.utils.icon(onedesk.help_center.ICONS[one.kind] || "dot", "sm");
		const items = [];
		const branches = [];
		const index = [];
		all.forEach((said, at) => {
			const of = modules[at];
			for (const one of said.versions) {
				items.push({
					id: id(of, one),
					label: one.version,
					icon_html: icon(one),
					title: module ? one.title : `${of} ${one.version} · ${one.title}`,
					description: [kinds[one.kind] || one.kind, frappe.datetime.str_to_user(one.date)].join(" · "),
					page: one.html,
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
		return { groups: [{ items }], tree: branches, index };
	},
	opened(_centre, { module }) {
		for (const of of onedesk.help_center.modules(module)) {
			const ours = frappe.boot.one_versions && frappe.boot.one_versions[of];
			if (ours) ours.unseen = 0;
			$(document).trigger("one-version-seen", [of]);
		}
	},
});
