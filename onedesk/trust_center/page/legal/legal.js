// The agreements' address, /desk/legal: TrustCenter opened on the workspace
// (docs/READY.md, mechanism 13), on a document when the address names one,
// over the desk, which the address gives way to.
frappe.pages["legal"].on_page_show = () => {
	const query = frappe.utils.get_query_params();
	frappe.route_flags.replace_route = true;
	frappe.set_route("");
	onedesk.centers.open("trust", { at: query.document ? `doc:${query.document}` : query.at || null });
};
