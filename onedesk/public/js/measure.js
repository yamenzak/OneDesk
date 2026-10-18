
frappe.provide("onedesk.measure");

onedesk.measure.SIZE = ["one_pieces", "one_length", "one_width"];

onedesk.measure.measured = (row) => ["Length", "Area"].includes(row.one_measured_by);

onedesk.measure.formatter = (value, df, options, doc) => {
	const shown = frappe.format(value, { ...df, formatter: null }, { ...options, inline: true }, doc);
	const listed = ["uom", "stock_uom"].some((f) => frappe.meta.get_docfield(df.parent, f)?.in_list_view);
	const unit = doc && !listed ? doc.uom || doc.stock_uom : null;
	const symbol = unit && (frappe.boot.one_measure?.symbols?.[unit] || __(unit));
	return frappe.form.formatters._right(unit ? `${shown} ${frappe.utils.escape_html(symbol)}` : shown, options);
};

onedesk.measure.columns = (frm) => {
	for (const fieldname of frappe.boot.one_measure?.records?.[frm.doctype] || []) {
		const grid = frm.fields_dict[fieldname]?.grid;
		if (!grid) continue;
		const quantities = (grid.docfields || []).filter((df) => ["qty", "rejected_qty"].includes(df.fieldname) && df.formatter !== onedesk.measure.formatter);
		const formatted = grid.grid_rows?.length && quantities.length;
		if (formatted) quantities.forEach((df) => grid.update_docfield_property(df.fieldname, "formatter", onedesk.measure.formatter));
		const show = (frm.doc[fieldname] || []).some((row) => onedesk.measure.measured(row) && (frm.doc.docstatus === 0 || row.one_length));
		if (grid.one_sized !== show) {
			grid.one_sized = show;
			grid.set_column_disp_in_list_view(onedesk.measure.SIZE, show);
		} else if (formatted) {
			grid.grid_rows.forEach((row) => row.refresh());
		}
	}
};

onedesk.measure.quantity = async (frm, cdt, cdn) => {
	const row = locals[cdt][cdn];
	onedesk.measure.columns(frm);
	if (!onedesk.measure.measured(row) || !row.item_code || !row.one_length) return;
	if (row.one_measured_by === "Area" && !row.one_width) return;
	const qty = await frappe.xcall("onedesk.one_inventory.measure.line_quantity", {
		item_code: row.item_code,
		measured_by: row.one_measured_by,
		uom: row.uom || row.stock_uom,
		pieces: row.one_pieces,
		length: row.one_length,
		width: row.one_width,
	});
	const places = precision("qty", row);
	if (flt(qty, places) !== flt(row.qty, places)) {
		frappe.model.set_value(cdt, cdn, "qty", flt(qty, places));
	}
};

$(document).on("app_ready", () => {
	const said = frappe.boot.one_measure || {};
	for (const [record, fieldnames] of Object.entries(said.records || {})) {
		const handlers = { refresh: onedesk.measure.columns };
		for (const fieldname of fieldnames) handlers[`${fieldname}_remove`] = onedesk.measure.columns;
		frappe.ui.form.on(record, handlers);
	}
	for (const lines of said.lines || []) {
		frappe.ui.form.on(lines, {
			one_measured_by: onedesk.measure.quantity,
			one_pieces: onedesk.measure.quantity,
			one_length: onedesk.measure.quantity,
			one_width: onedesk.measure.quantity,
			uom: onedesk.measure.quantity,
		});
	}
});
