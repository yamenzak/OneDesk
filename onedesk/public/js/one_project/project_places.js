frappe.provide("onedesk.project");
frappe.provide("onedesk.crumbs.suggest");

onedesk.project.picker = async (current) => {
	const said = await frappe.xcall("onedesk.one_project.view.picker", { project: current });
	const row = (one) => ({ label: one.title, onclick: () => frappe.set_route(`/desk/project/${encodeURIComponent(one.name)}`) });
	return said.open.length ? [{ group: __("Open Projects"), options: said.open.map(row) }] : [];
};
onedesk.crumbs.suggest.Project = onedesk.project.picker;

