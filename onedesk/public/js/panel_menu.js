// Where the module's panel is not out beside the page, its breadcrumb is the
// way between the module's places (docs/PASSOVER.md, The panel). This is for
// every module, read from the panel itself, so a module needs nothing of its
// own:
// - on a phone, where the panel stays shut, the place's name at the top of a
//   page the panel lists, "Projects ▾", is a menu of the panel's rows;
// - on a page that closes the panel (a record's page, `hide_sidebar`), the
//   crumb that leads back to its place is that menu, at any width.
// The rows are the panel's own, in its order and under its section names, so
// the menu is the panel folded into the crumb.
frappe.provide("onedesk.panel");

// An address without the panel it names: frappe writes the panel into the
// address (/desk/oneproject/project), and a crumb leaves it out (/desk/project).
onedesk.panel.bare = (href) => {
	const path = decodeURIComponent(String(href || "").split("?")[0].split("#")[0])
		.replace(/^\/app\//, "/desk/")
		.replace(/\/$/, "");
	const parts = path.split("/");
	const route = parts.slice(2);
	return parts[1] === "desk" && route.length > 1 && frappe.router.begins_with_shell?.(route)
		? ["", "desk", ...route.slice(1)].join("/")
		: path;
};

// A row's address and a page's, alike: without its view (a list's row leads
// to /project/view/list and the list opens at /project), its query, its panel or
// a trailing slash, and with /app/ read as /desk/.
onedesk.panel.path = (href) => onedesk.panel.bare(href).replace(/\/view\/[^/]+(\/.*)?$/, "");

// The panel's rows, `{ label, href, section }`, as it lists them now.
onedesk.panel.rows = () =>
	[...document.querySelectorAll(".body-sidebar .sidebar-items .item-anchor")]
		.filter((a) => a.getAttribute("href"))
		.map((a) => {
			const section = a.closest(".section-item");
			const head = section && section.querySelector(".item-anchor:not([href])");
			return { label: a.innerText.trim(), href: a.getAttribute("href"), section: head ? head.innerText.trim() : "" };
		})
		.filter((row) => row.label);

// The row a path is, if the panel lists it: the row for that very view (Deal
// and Pipeline are two views of one list), or else for its list.
onedesk.panel.row = (path) => {
	const exact = onedesk.panel.bare(path);
	const here = onedesk.panel.path(path);
	if (!here) return null;
	const rows = onedesk.panel.rows();
	return rows.find((row) => onedesk.panel.bare(row.href) === exact) || rows.find((row) => onedesk.panel.path(row.href) === here) || null;
};

// Whether the panel is out beside a page.
onedesk.panel.out = (page = frappe.container?.page?.page) => !frappe.is_mobile() && !(page && page.hide_sidebar);

// The panel's rows as frappe.ui.Dropdown's, read when it opens, in sections,
// the row `here` ticked.
onedesk.panel.options = (here) => {
	const groups = [];
	for (const row of onedesk.panel.rows()) {
		let group = groups[groups.length - 1];
		if (!group || group.name !== row.section) groups.push((group = { name: row.section, rows: [] }));
		group.rows.push({
			label: row.label,
			icon: here && row.href === here.href ? "check" : null,
			onclick: () => frappe.set_route(row.href),
		});
	}
	return groups.flatMap((group) => (group.name ? [{ group: group.name, options: group.rows }] : group.rows));
};

// A crumb made that menu.
onedesk.panel.menu = ($crumb, here) => {
	$crumb.addClass("one-places");
	$crumb.find("a").removeAttr("href");
	$crumb.children().first().append(frappe.utils.icon("chevron-down", "xs"));
	new frappe.ui.Dropdown({ trigger: $crumb, options: () => onedesk.panel.options(here) });
};

// A page draws its own trail (`Page.render_breadcrumbs`), its title the last
// crumb, so the menu follows each drawing and leaves the names to the page.
{
	const Page = frappe.ui.Page;
	const drawn = Page.prototype.render_breadcrumbs;
	Page.prototype.render_breadcrumbs = function () {
		drawn.call(this);
		if (!this.$breadcrumbs?.length || onedesk.panel.out(this)) return;
		const $crumbs = this.$breadcrumbs.children("li");
		const here = onedesk.panel.row(window.location.pathname);
		// The place's own page: its name, the last crumb.
		if (here && frappe.is_mobile()) return void ($crumbs.length && onedesk.panel.menu($crumbs.last(), here));
		// A page under a place: the crumb that leads back to it.
		for (const li of $crumbs.toArray()) {
			const row = onedesk.panel.row($(li).find("a").attr("href"));
			if (row) return void onedesk.panel.menu($(li), row);
		}
	};
}

// The panel is drawn after the page on a cold load: the trail is drawn again
// once it is there.
{
	const Sidebar = frappe.ui.Sidebar;
	if (Sidebar && !Sidebar.prototype.__one_panel_menu) {
		Sidebar.prototype.__one_panel_menu = true;
		const made = Sidebar.prototype.make_sidebar;
		Sidebar.prototype.make_sidebar = function (...args) {
			const result = made.apply(this, args);
			frappe.get_current_page?.()?.render_breadcrumbs();
			return result;
		};
	}
}
