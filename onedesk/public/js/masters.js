// Masters (one/masters.py): each kind is frappe's own list and form. What is
// ours is the tree beside any of them, the window's, under the rail's Masters,
// of every kind the reader may open, grouped by the app that uses it, with how
// many values each has; a group folds, and stays folded.
frappe.provide("onedesk.masters");

onedesk.masters.covers = (doctype) => (frappe.boot.one_masters || []).includes(doctype);

onedesk.masters.folded = () => onedesk.masters._folded || [];

onedesk.masters.fold = (group) => {
	const folded = onedesk.masters.folded();
	onedesk.masters._folded = folded.includes(group) ? folded.filter((one) => one !== group) : [...folded, group];
	frappe.model.user_settings.save("Masters", "closed", onedesk.masters._folded);
};

onedesk.masters.draw = async (win, doctype) => {
	if (!onedesk.masters._folded) onedesk.masters._folded = ((await frappe.model.user_settings.get("Masters")) || {}).closed || [];
	const kinds = await frappe.xcall("onedesk.one.masters.kinds");
	const here = kinds.find((one) => one.doctype === doctype);
	const rows = [];
	for (const group of new Set(kinds.map((one) => one.group))) {
		const mine = kinds.filter((one) => one.group === group);
		const open = !onedesk.masters.folded().includes(group) || (here && here.group === group);
		rows.push({ id: `group:${group}`, label: group === "Shared" ? __("Shared") : group, icon: mine[0].mark || "folder", depth: 0, open });
		if (!open) continue;
		for (const one of mine) {
			rows.push({
				id: one.doctype,
				label: one.label,
				depth: 1,
				active: one.doctype === doctype,
				count: cint(one.count) || "0",
				href: `/desk/${frappe.router.slug(one.doctype)}`,
			});
		}
	}
	const redraw = () => onedesk.masters.draw(win, doctype);
	const fold = (id) => {
		onedesk.masters.fold(id.slice("group:".length));
		redraw();
	};
	win.tree({
		label: __("Masters"),
		rows,
		twist: fold,
		pick: (id) => (id.startsWith("group:") ? fold(id) : frappe.set_route("List", id)),
	});
	frappe.model.user_settings.save("Masters", "last", doctype);
};

onedesk.window.trees.push({ covers: onedesk.masters.covers, draw: onedesk.masters.draw });
