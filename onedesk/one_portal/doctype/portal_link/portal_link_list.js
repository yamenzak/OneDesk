// The links sent from a record's Portal dialog (one_portal/share.py): one
// state each, and the record it opens in place of its hash.
frappe.listview_settings["Portal Link"] = {
	hide_name_column: true,
	hide_name_filter: true,
	add_fields: ["disabled", "expires_on", "used_on"],
	get_indicator(doc) {
		if (doc.disabled) return [__("Revoked"), "gray", "disabled,=,1"];
		if (doc.expires_on && frappe.datetime.get_diff(doc.expires_on, frappe.datetime.now_datetime()) < 0)
			return [__("Expired"), "gray", `expires_on,<,${frappe.datetime.now_datetime()}`];
		if (doc.used_on) return [__("Answered"), "green", "used_on,is,set"];
		return [__("Open"), "blue", "disabled,=,0"];
	},
};
