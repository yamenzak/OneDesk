// Lists (one/lists.py): the short lists a module's records pick their values
// from. Each is frappe's own list and form; what is ours is Lists at the end
// of the module's ControlCenter, and the module's other lists in the nav pane
// beside any one of them.
frappe.provide("onedesk.lists");

onedesk.lists.module_of = (doctype) =>
	Object.keys(frappe.boot.one_lists || {}).find((module) => frappe.boot.one_lists[module].includes(doctype));

onedesk.lists.draw = async (win, doctype) => {
	const module = onedesk.lists.module_of(doctype);
	const kinds = await frappe.xcall("onedesk.one.lists.kinds", { module });
	win.tree({
		label: __("{0} Lists", [module]),
		heading: __("Lists"),
		alone: true,
		rows: kinds.map((one) => ({
			id: one.doctype,
			label: one.label,
			icon: one.icon || "tags",
			depth: 0,
			active: one.doctype === doctype,
			count: cint(one.count) || "0",
			href: `/desk/${frappe.router.slug(one.doctype)}`,
		})),
		pick: (id) => frappe.set_route("List", id),
	});
};

onedesk.interface.trees.push({ covers: (doctype) => !!onedesk.lists.module_of(doctype), draw: onedesk.lists.draw });

// How many a list holds, in its own word where it has one (lists.py COUNTED).
onedesk.lists.counted = (count, words = null) => {
	count = cint(count);
	if (words) return count === 1 ? words[0] : __(words[1], [count]);
	if (!count) return __("No values");
	return count === 1 ? __("1 value") : __("{0} values", [count]);
};

// What a module's ControlCenter ends with, found rather than drawn: Lists,
// each opening its own list in the module's own rail, wherever the centre
// was opened, for whoever keeps the module's lists.
onedesk.lists.tab = (module) => {
	if (!((frappe.boot.one_lists || {})[module] || []).length) return [];
	const kit = onedesk.centers.kit;
	const item = {
		id: "lists",
		label: __("Lists"),
		icon: "tags",
		title: __("Lists"),
		description: __("The values {0}'s records pick from, each opening as its own list.", [module]),
		rows: async (panel) =>
			(await frappe.xcall("onedesk.one.lists.kinds", { module })).map((one) => ({
				lead: kit.glyph(one.icon || "tags"),
				title: one.label,
				sub: frappe.utils.escape_html(onedesk.lists.counted(one.count, one.counted)),
				end: kit.chevron(),
				open: () => {
					panel.dialog.hide();
					frappe.set_route(`/desk/${frappe.router.shell_slug(module)}/${frappe.router.slug(one.doctype)}`);
				},
			})),
	};
	return [{ group: null, items: [item] }];
};
