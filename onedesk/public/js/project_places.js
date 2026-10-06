// OneProject keeps no sidebar open (one_project/README.md, Finding your way).
// Its three places, Projects, Workload and Time, are frappe's TabButtons in
// the page head, and its pages close the module's panel on arrival with
// frappe's own `hide_sidebar`, as OneMail's and OneCloud's do. The panel still
// lists the three, for a phone, whose head has no room for the tabs. Project
// Templates, Rates and Projects Settings are in the Projects list's ··· menu
// (project_list.js).
frappe.provide("onedesk.project");

onedesk.project.places = () => [
	{ value: "projects", label: __("Projects"), route: "/desk/project", is: (r) => ["List", "Tree"].includes(r[0]) && r[1] === "Project" },
	{ value: "workload", label: __("Workload"), route: "/desk/query-report/Workload", is: (r) => r[0] === "query-report" && r[1] === "Workload" },
	{ value: "time", label: __("Time"), route: "/desk/timesheet", is: (r) => r[0] === "List" && r[1] === "Timesheet" },
];

onedesk.project.place = () => {
	const page = frappe.container && frappe.container.page && frappe.container.page.page;
	if (!page || !page.wrapper) return;
	const route = frappe.get_route();
	const places = onedesk.project.places();
	const here = places.find((one) => one.is(route));
	const $area = $(page.wrapper).find(".page-head .title-area").first();
	// Every report shares the one query-report page: the tabs and the closed
	// panel are Workload's alone.
	if (route[0] === "query-report" && !here) {
		page.hide_sidebar = false;
		$area.find(".one-project-places").remove();
	}
	if (!here) return;
	// Not on a phone: its head has no room for the tabs, and its menu is how
	// one gets around.
	page.hide_sidebar = !frappe.is_mobile();
	frappe.app.sidebar && frappe.app.sidebar.apply_page_visibility();
	$area.find(".one-project-places").remove();
	const tabs = new frappe.ui.TabButtons({
		label: __("OneProject"),
		options: places.map((one) => ({ value: one.value, label: one.label })),
		value: here.value,
		on_change: (value) => frappe.set_route(places.find((one) => one.value === value).route),
	});
	tabs.$el.addClass("one-project-places").insertAfter($area.find(".navbar-breadcrumbs").first());
};

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

$(document).on("page-change", () => setTimeout(onedesk.project.place, 0));
