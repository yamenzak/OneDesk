// Where the module's panel is not out beside the page, its breadcrumb is the
// way between the module's places (docs/PASSOVER.md, The panel). This is for
// every module, read from the panel itself, so a module needs nothing of its
// own:
// - on a phone, where the panel stays shut, the place's name at the top of a
//   page the panel lists, "Projects ▾", is a menu of the panel's rows;
// - on a page that closes the panel (a record's page, `hide_sidebar`), the
//   crumb that leads back to its place is that menu, at any width.
// The rows are the panel's own, in its order and under its section names, so
// the menu is the panel folded into the crumb. A page the panel lists but
// that sets no crumb, as a board does, is given its row's name.
frappe.provide("onedesk.panel");

// A row's address and a page's, alike: without its view (a list's row leads
// to /project/view/list and the list opens at /project), its query or a
// trailing slash, and with /app/ read as /desk/.
onedesk.panel.path = (href) =>
	decodeURIComponent(String(href || "").split("?")[0].split("#")[0])
		.replace(/^\/app\//, "/desk/")
		.replace(/\/view\/[^/]+(\/.*)?$/, "")
		.replace(/\/$/, "");

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
	const exact = decodeURIComponent(String(path || "").split("?")[0]).replace(/^\/app\//, "/desk/").replace(/\/$/, "");
	const here = onedesk.panel.path(path);
	if (!here) return null;
	const rows = onedesk.panel.rows();
	const view = (href) => decodeURIComponent(href.split("?")[0]).replace(/\/$/, "");
	return rows.find((row) => view(row.href) === exact) || rows.find((row) => onedesk.panel.path(row.href) === here) || null;
};

// Whether the panel is out beside the page.
onedesk.panel.out = () => {
	const page = frappe.container && frappe.container.page && frappe.container.page.page;
	return !frappe.is_mobile() && !(page && page.hide_sidebar);
};

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
	$crumb.removeClass("disabled").addClass("one-places");
	$crumb.find("a").removeAttr("href");
	$crumb.append(` ${frappe.utils.icon("chevron-down", "xs")}`);
	new frappe.ui.Dropdown({ trigger: $crumb, options: () => onedesk.panel.options(here) });
};

// Frappe redraws the crumb on every `breadcrumbs.update`, so this follows each
// one rather than racing the page, and leaves the names to the page.
{
	const theirs = frappe.breadcrumbs.update.bind(frappe.breadcrumbs);
	frappe.breadcrumbs.update = function () {
		const at = window.location.pathname;
		const here = onedesk.panel.row(at);
		const key = this.current_page();
		if (here && !this.all[key]) this.all[key] = { type: "Custom", label: frappe.utils.escape_html(here.label), route: here.href };
		theirs();
		if (onedesk.panel.out()) return;
		$(".navbar-breadcrumbs").each((i, crumbs) => {
			const $crumbs = $(crumbs).find("li");
			// The place's own page: its name, the last crumb.
			if (here && frappe.is_mobile()) return void ($crumbs.length && onedesk.panel.menu($crumbs.last(), here));
			// A page under a place: the crumb that leads back to it.
			for (const li of $crumbs.toArray()) {
				const row = onedesk.panel.row($(li).find("a").attr("href"));
				if (row) return void onedesk.panel.menu($(li), row);
			}
		});
	};
}

// The panel is drawn after the page on a cold load: the crumb is drawn again
// once it is there.
{
	const Sidebar = frappe.ui.Sidebar;
	if (Sidebar && !Sidebar.prototype.__one_panel_menu) {
		Sidebar.prototype.__one_panel_menu = true;
		const made = Sidebar.prototype.make_sidebar;
		Sidebar.prototype.make_sidebar = function (...args) {
			const result = made.apply(this, args);
			if (frappe.breadcrumbs.all[frappe.breadcrumbs.current_page()]) frappe.breadcrumbs.update();
			return result;
		};
	}
}
