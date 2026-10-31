// The Sources list: a source's pill says its kind, or Disabled when it is
// off; its name is its title, so no ID column. Adding one opens Add News
// Source (js/one/news_add.js), which holds the library too.
frappe.listview_settings["News Source"] = {
	hide_name_column: true,
	get_indicator(doc) {
		if (!doc.enabled) return [__("Disabled"), "gray", "enabled,=,0"];
		return [__(doc.kind), "blue", `kind,=,${doc.kind}`];
	},
	add_fields: ["kind", "enabled"],
};
