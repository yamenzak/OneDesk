// A source's filters are frappe's own filter control, written to `filters`
// as a list view saves them; Preview shows what a widget would get now.
frappe.ui.form.on("Display Source", {
	refresh(frm) {
		frm.trigger("draw_filters");
		if (!frm.is_new()) {
			frm.add_custom_button(__("Preview"), () =>
				frappe.xcall("onedesk.one_display.sources.peek", { source: frm.doc.name, widget_type: "Custom" }).then((said) => {
					const rows = said.rows?.length ? said.rows : said.whole ? [said.whole] : [];
					frappe.msgprint({
						title: __("What It Shows Now"),
						message: rows.length
							? `<pre class="text-sm">${frappe.utils.escape_html(JSON.stringify(rows.slice(0, 5), null, 2))}</pre>`
							: __("Nothing yet. A records source shows the fields a widget maps."),
						wide: true,
					});
				})
			);
		}
	},
	ref_doctype(frm) {
		frm.set_value("filters", "[]");
		frm.trigger("draw_filters");
	},
	kind(frm) {
		frm.trigger("draw_filters");
	},
	draw_filters(frm) {
		const area = frm.fields_dict.filter_area;
		if (!area || frm.doc.kind !== "Records" || !frm.doc.ref_doctype) return;
		area.$wrapper.empty();
		frappe.model.with_doctype(frm.doc.ref_doctype, () => {
			const group = new frappe.ui.FilterGroup({
				parent: area.$wrapper,
				doctype: frm.doc.ref_doctype,
				on_change: () => frm.set_value("filters", JSON.stringify(group.get_filters())),
			});
			group.wrapper.find(".apply-filters").hide();
			group.add_filters_to_filter_group(JSON.parse(frm.doc.filters || "[]"));
		});
	},
});
