// A contact who has the portal shows where their login stands (Contact.one_portal,
// kept by one_portal/gate.py); everyone else shows nothing.
const PORTAL = { Invited: "orange", "Signed In": "green", Revoked: "gray" };

frappe.listview_settings["Contact"] = {
	...frappe.listview_settings["Contact"],
	hide_name_column: true,
	hide_name_filter: true,
	add_fields: [...(frappe.listview_settings["Contact"]?.add_fields || []), "one_portal"],
	get_indicator(doc) {
		if (PORTAL[doc.one_portal]) return [__(doc.one_portal), PORTAL[doc.one_portal], `one_portal,=,${doc.one_portal}`];
	},
};
