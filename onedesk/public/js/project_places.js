// OneProject's places, Projects, Workload, Time and Templates, are its
// panel's rows; the panel is open on each, and where it is not out the
// breadcrumb is the menu of them, as in every module (panel_menu.js,
// one_project/README.md, Finding your way). Rates and Projects Settings are in
// the Projects list's ··· menu (project_list.js).
frappe.provide("onedesk.project");

// The project's name in its page's breadcrumb opens this: the reader's other
// open projects (view.picker), as frappe.ui.Dropdown's rows.
onedesk.project.picker = async (current) => {
	const said = await frappe.xcall("onedesk.one_project.view.picker", { project: current });
	const row = (one) => ({ label: one.title, onclick: () => frappe.set_route(`/desk/project/${encodeURIComponent(one.name)}`) });
	return [
		said.open.length && { group: __("Open Projects"), options: said.open.map(row) },
		{ label: __("All Projects"), icon: "list", onclick: () => frappe.set_route("List", "Project") },
	].filter(Boolean);
};

