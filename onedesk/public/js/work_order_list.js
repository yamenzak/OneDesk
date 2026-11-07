(() => {
	const settings = (frappe.listview_settings["Work Order"] = frappe.listview_settings["Work Order"] || {});
	settings.hide_name_column = true;
	settings.add_fields = [...new Set([...(settings.add_fields || []), "qty", "stock_uom", "expected_delivery_date"])];
	const said = (value) => format_number(value || 0, null, Number.isInteger(flt(value)) ? 0 : 2);
	const theirs = settings.get_indicator;
	const OPEN = ["Not Started", "In Process", "Stock Reserved", "Stock Partially Reserved"];
	settings.get_indicator = function (doc) {
		const late = doc.docstatus === 1 && OPEN.includes(doc.status) && doc.expected_delivery_date && doc.expected_delivery_date < frappe.datetime.get_today();
		if (late) return [__("Late"), "red", `expected_delivery_date,<,${frappe.datetime.get_today()}`];
		if (doc.status === "Not Started" && doc.docstatus === 1) return [__("Not Started"), "gray", "status,=,Not Started"];
		return theirs ? theirs.call(this, doc) : undefined;
	};
	settings.formatters = Object.assign(settings.formatters || {}, {
		produced_qty(value, df, doc) {
			return frappe.utils.escape_html(__("{0} of {1}", [said(value), said(doc.qty)]));
		},
	});
})();
