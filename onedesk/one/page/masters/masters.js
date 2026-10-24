// Masters is each kind's own frappe list (one/masters.py); this address,
// the rail's and the homes', only opens the one asked for, else the one last
// open, else the first, in place of itself.
frappe.pages["masters"].on_page_show = async () => {
	const kinds = frappe.boot.one_masters || [];
	const asked = frappe.utils.get_url_arg("type");
	const last = ((await frappe.model.user_settings.get("Masters")) || {}).last;
	const kind = [asked, last, kinds[0]].find((one) => one && kinds.includes(one));
	if (!kind) return frappe.msgprint(__("Only administrators and an app's managers see Masters."));
	frappe.route_flags.replace_route = true;
	frappe.set_route("List", kind);
};
