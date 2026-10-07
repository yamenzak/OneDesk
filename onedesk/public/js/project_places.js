// OneProject's four places, Projects, Workload, Time and Templates, are its
// panel's rows, and the panel stays open on each (one_project/README.md,
// Finding your way). A phone keeps the panel shut, so there the place's name
// in the breadcrumb, "Projects ▾", is a menu of the four. A project's page
// and a template's page are records and close the panel themselves, so on
// them the place's name before the record's is that menu, at any width.
// Rates and Projects Settings are in the Projects list's ··· menu
// (project_list.js).
frappe.provide("onedesk.project");

// `holds`: the record pages under the place, whose crumb names it first.
onedesk.project.places = () => [
	{
		label: __("Projects"),
		route: "/desk/project",
		is: (r) => ["List", "Tree"].includes(r[0]) && r[1] === "Project",
		holds: (r) => r[0] === "project-view",
	},
	{ label: __("Workload"), route: "/desk/query-report/Workload", is: (r) => r[0] === "query-report" && r[1] === "Workload" },
	{ label: __("Time"), route: "/desk/timesheet", is: (r) => r[0] === "List" && r[1] === "Timesheet" },
	{
		label: __("Templates"),
		route: "/desk/project-template",
		is: (r) => r[0] === "List" && r[1] === "Project Template",
		holds: (r) => r[0] === "project-template-view",
	},
];

// A crumb made the menu of the four, frappe.ui.Dropdown's rows, the place it
// names ticked.
onedesk.project.menu = ($crumb, here) => {
	const places = onedesk.project.places();
	$crumb.removeClass("disabled").addClass("one-places");
	$crumb.find("a").removeAttr("href");
	$crumb.append(` ${frappe.utils.icon("chevron-down", "xs")}`);
	new frappe.ui.Dropdown({
		trigger: $crumb,
		options: places.map((one) => ({
			label: one.label,
			icon: one.label === here.label ? "check" : null,
			onclick: () => frappe.set_route(one.route),
		})),
	});
};

// A place's crumb is whatever its page sets, a list's name or a report's; a
// board sets none, so it is given the place's. Frappe redraws the crumb on
// every `breadcrumbs.update`, so this follows each one rather than racing the
// page, and leaves the name to the page, which writes it again
// (`page.set_title`).
{
	const theirs = frappe.breadcrumbs.update.bind(frappe.breadcrumbs);
	frappe.breadcrumbs.update = function () {
		const route = frappe.get_route();
		const places = onedesk.project.places();
		const here = places.find((one) => one.is(route));
		const above = places.find((one) => one.holds && one.holds(route));
		const key = this.current_page();
		if (here && !this.all[key]) this.all[key] = { type: "Custom", label: frappe.utils.escape_html(here.label), route: here.route };
		theirs();
		$(".navbar-breadcrumbs").each((i, crumbs) => {
			// On a phone, the place's own crumb.
			if (here && frappe.is_mobile()) {
				const $last = $(crumbs).find("li").last();
				if ($last.length) onedesk.project.menu($last, here);
			}
			// Over a record, the place's name before it. A phone shows only the
			// record's name, which is the record's own menu.
			if (above) {
				const $first = $(crumbs).find("li").first();
				if ($first.length && $first.find(`a[href="${above.route}"]`).length) onedesk.project.menu($first, above);
			}
		});
	};
}

// The project's name in its page's breadcrumb opens this: its parent and
// sub-projects, then the reader's other open projects (view.picker), as
// frappe.ui.Dropdown's rows.
onedesk.project.picker = async (current) => {
	const said = await frappe.xcall("onedesk.one_project.view.picker", { project: current });
	const row = (one) => ({ label: one.title, onclick: () => frappe.set_route(`/desk/project/${encodeURIComponent(one.name)}`) });
	return [
		said.family.length && { group: __("Parent and Sub-projects"), options: said.family.map(row) },
		said.open.length && { group: __("Open Projects"), options: said.open.map(row) },
		{ label: __("All Projects"), icon: "list", onclick: () => frappe.set_route("List", "Project") },
	].filter(Boolean);
};

