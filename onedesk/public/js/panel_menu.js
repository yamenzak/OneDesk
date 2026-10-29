frappe.provide("onedesk.panel");

onedesk.panel.decoded = (text) => {
	try {
		return decodeURIComponent(text);
	} catch {
		return text;
	}
};

onedesk.panel.bare = (href) => {
	const path = onedesk.panel.decoded(String(href || "").split("?")[0].split("#")[0])
		.replace(/^\/app\//, "/desk/")
		.replace(/\/$/, "");
	const parts = path.split("/");
	const route = parts.slice(2);
	return parts[1] === "desk" && route.length > 1 && frappe.router.begins_with_shell?.(route)
		? ["", "desk", ...route.slice(1)].join("/")
		: path;
};

onedesk.panel.path = (href) => onedesk.panel.bare(href).replace(/\/view\/[^/]+(\/.*)?$/, "");

onedesk.panel.rows = () =>
	[...document.querySelectorAll(".body-sidebar .sidebar-items .item-anchor")]
		.filter((a) => a.getAttribute("href"))
		.map((a) => {
			const section = a.closest(".section-item");
			const head = section && section.querySelector(".item-anchor:not([href])");
			return { label: a.innerText.trim(), href: a.getAttribute("href"), section: head ? head.innerText.trim() : "" };
		})
		.filter((row) => row.label);

onedesk.panel.row = (path) => {
	const exact = onedesk.panel.bare(path);
	const here = onedesk.panel.path(path);
	if (!here) return null;
	const rows = onedesk.panel.rows();
	return rows.find((row) => onedesk.panel.bare(row.href) === exact) || rows.find((row) => onedesk.panel.path(row.href) === here) || null;
};

onedesk.panel.out = (page = frappe.container?.page?.page) => !frappe.is_mobile() && !(page && page.hide_sidebar);

onedesk.panel.options = (here) => {
	const groups = [];
	for (const row of onedesk.panel.rows()) {
		let group = groups[groups.length - 1];
		if (!group || group.name !== row.section) groups.push((group = { name: row.section, rows: [] }));
		group.rows.push({
			label: row.label,
			selected: !!here && row.href === here.href,
			onclick: () => frappe.set_route(row.href),
		});
	}
	return groups.flatMap((group) => (group.name ? [{ group: group.name, options: group.rows }] : group.rows));
};
