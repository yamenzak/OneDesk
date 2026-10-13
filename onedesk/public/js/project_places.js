// OneProject's places, Projects, Workload, Time and Templates, are its
// panel's rows; the panel is open on each, and the breadcrumb switches
// between them, as in every module (crumb_switch.js, one_project/README.md,
// Finding your way). Rates and Projects Settings are in the Projects list's
// ··· menu (project_list.js).
frappe.provide("onedesk.project");
frappe.provide("onedesk.crumbs.suggest");

// The project's name in its page's breadcrumb offers these before anything
// is typed: the reader's other open projects (view.picker).
onedesk.project.picker = async (current) => {
	const said = await frappe.xcall("onedesk.one_project.view.picker", { project: current });
	const row = (one) => ({ label: one.title, onclick: () => frappe.set_route(`/desk/project/${encodeURIComponent(one.name)}`) });
	return said.open.length ? [{ group: __("Open Projects"), options: said.open.map(row) }] : [];
};
onedesk.crumbs.suggest.Project = onedesk.project.picker;

