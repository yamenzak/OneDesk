(() => {
	const settings = (frappe.listview_settings["Batch"] = frappe.listview_settings["Batch"] || {});
	settings.add_fields = [...new Set([...(settings.add_fields || []), "stock_uom"])];
	settings.formatters = Object.assign(settings.formatters || {}, {
		batch_qty(value, df, doc) {
			const unit = doc.stock_uom ? ` <span class="text-muted">${frappe.utils.escape_html(__(doc.stock_uom))}</span>` : "";
			return `${format_number(value || 0, null, Number.isInteger(flt(value)) ? 0 : 2)}${unit}`;
		},
	});
})();
