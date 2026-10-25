// AccessCenter (docs/READY.md, mechanism 14): who may do what in each module
// that declares its abilities (one/access_center.py). A module's part, from
// Roles and Access in its ControlCenter, is three tabs: its Roles matrix,
// its People and their role in it, and what people were given On One
// Record. The whole, from the key in the bottom bar and the arrows, is every
// such module, each a group of the three. For workspace administrators.
frappe.provide("onedesk.access");

onedesk.access.ROLE_FILES = ["/assets/onedesk/js/role_matrix.js", "/assets/onedesk/css/role_matrix.css"];

onedesk.access.open = async ({ module = null, at = null } = {}) => {
	const A = "onedesk.one.access_center.";
	const kit = onedesk.module_settings.kit;
	const esc = frappe.utils.escape_html;
	await frappe.require(onedesk.access.ROLE_FILES);
	const apps = module ? [module] : await frappe.xcall(A + "modules");

	const roles_tab = (app) => ({
		id: `${app}:roles`,
		label: __("Roles"),
		icon: "shield-check",
		title: __("Roles"),
		description: __("What each role can do in {0}.", [app]),
		actions: [
			{ label: __("Show Roles"), icon: "eye", click: (panel) => onedesk.roles.pick(panel, app) },
			{ label: __("New Role"), icon: "plus", click: (panel) => onedesk.roles.create(panel, app) },
		],
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
		async render(panel) {
			const said = await frappe.xcall(A + "people", { app });
			const $body = panel.body.empty();
			const $list = $(`<div class="one-set-list"></div>`).appendTo($body);
			for (const one of said.people) {
				const $row = kit
					.row({ lead: frappe.ui.avatar.html({ label: one.name, image: one.image, size: "md" }), title: one.name, sub: esc(one.user) })
					.attr("data-find", `${one.name} ${one.user}`.toLowerCase())
					.appendTo($list);
				const control = frappe.ui.form.make_control({
					df: { fieldtype: "Select", fieldname: "level", label: "", options: said.levels },
					parent: $(`<span class="one-access-level"></span>`).appendTo($row.find(".one-set-end")),
					render_input: true,
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
		},
	});

	// What people were given on one record beyond their role (a shared
	// mailbox's Users), each changed or taken away here as on the record.
	const records_tab = (app) => ({
		id: `${app}:records`,
		label: __("On One Record"),
		icon: "key-round",
		title: __("On One Record"),
		description: __("People given more than their role on one record, from that record's own screen."),
		async render(panel) {
			const said = await frappe.xcall(A + "records", { app });
			const labelled = Object.fromEntries(said.abilities.map((one) => [one.key, one.label]));
			const $list = $(`<div class="one-set-list"></div>`).appendTo(panel.body.empty());
			if (!said.grants.length) $list.append(kit.empty(__("Nobody has been given more than their role.")));
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

	const tabs = apps.map((app) => ({ group: module ? null : app, items: [roles_tab(app), people_tab(app), records_tab(app)] }));
	const ids = tabs.flatMap((group) => group.items.map((item) => item.id));
	const dialog = new onedesk.module_settings.Dialog({
		title: "AccessCenter",
		module,
		center: "access",
		tabs,
		default_tab: ids.includes(at) ? at : ids[0],
		expand: module
			? () => {
					dialog.hide();
					onedesk.access.open();
			  }
			: null,
	});
	dialog.$wrapper.addClass("one-set one-access");
	dialog.show();
	return dialog;
};
