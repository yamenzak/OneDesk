// OneProject's four places, Projects, Workload, Time and Templates, are its
// panel's rows, and the panel stays open on each (one_project/README.md,
// Finding your way). A phone keeps the panel shut, so there the place's name
// in the breadcrumb, "Projects ▾", is a menu of the four, frappe's own
// `menu_items` crumb. A project's page and a template's page are records and
// close the panel themselves. Rates and Projects Settings are in the Projects
// list's ··· menu (project_list.js).
frappe.provide("onedesk.project");

onedesk.project.places = () => [
	{ label: __("Projects"), route: "/desk/project", is: (r) => ["List", "Tree"].includes(r[0]) && r[1] === "Project" },
	{ label: __("Workload"), route: "/desk/query-report/Workload", is: (r) => r[0] === "query-report" && r[1] === "Workload" },
	{ label: __("Time"), route: "/desk/timesheet", is: (r) => r[0] === "List" && r[1] === "Timesheet" },
	{ label: __("Templates"), route: "/desk/project-template", is: (r) => r[0] === "List" && r[1] === "Project Template" },
];

// A place's crumb is whatever its page sets, a list's name or a report's; a
// board sets none, so it is given the place's. On a phone the crumb is also
// the menu of the four. Frappe redraws the crumb on every `breadcrumbs.update`,
// so this follows each one rather than racing the page, and leaves the name
// to the page, which writes it again (`page.set_title`).
{
	const theirs = frappe.breadcrumbs.update.bind(frappe.breadcrumbs);
	frappe.breadcrumbs.update = function () {
		const places = onedesk.project.places();
		const here = places.find((one) => one.is(frappe.get_route()));
		const key = this.current_page();
		if (here && !this.all[key]) this.all[key] = { type: "Custom", label: frappe.utils.escape_html(here.label), route: here.route };
		theirs();
		if (!here || !frappe.is_mobile()) return;
		$(".navbar-breadcrumbs").each((i, crumbs) => {
			const $last = $(crumbs).find("li").last();
			if (!$last.length) return;
			$last.removeClass("disabled").addClass("one-places");
			$last.find("a").removeAttr("href");
			$last.append(` ${frappe.utils.icon("chevron-down", "xs")}`);
			new frappe.ui.Dropdown({
				trigger: $last,
				options: places.map((one) => ({
					label: one.label,
					icon: one === here ? "check" : null,
					onclick: () => frappe.set_route(one.route),
				})),
			});
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

