// Work Orders: the item with room for its name, where each stands, how many
// are made of how many in one column, when it is wanted and for which
// project. ERPNext showed the two quantities apart, one as "0.000"; the
// number is left off, as on Receipts, and is still on hover and in search.
(() => {
	const settings = (frappe.listview_settings["Work Order"] = frappe.listview_settings["Work Order"] || {});
	settings.hide_name_column = true;
	settings.add_fields = [...new Set([...(settings.add_fields || []), "qty", "stock_uom"])];
	// A whole number without decimals, any other with the reader's two.
	const said = (value) => format_number(value || 0, null, Number.isInteger(flt(value)) ? 0 : 2);
	// Not started is where every order begins, not an alarm: grey, as the Shop
	// Floor says it, where ERPNext says it in red.
	const theirs = settings.get_indicator;
	settings.get_indicator = function (doc) {
		if (doc.status === "Not Started" && doc.docstatus === 1) return [__("Not Started"), "gray", "status,=,Not Started"];
		return theirs ? theirs.call(this, doc) : undefined;
	};
	settings.formatters = Object.assign(settings.formatters || {}, {
		produced_qty(value, df, doc) {
			return frappe.utils.escape_html(__("{0} of {1}", [said(value), said(doc.qty)]));
		},
	});
})();
