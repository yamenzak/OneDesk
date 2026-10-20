
frappe.provide("onedesk.measure");

onedesk.measure.SIZE = ["one_pieces", "one_length", "one_width"];

onedesk.measure.measured = (row) => ["Length", "Area", "Volume"].includes(row.one_measured_by);

onedesk.measure.sized = (row) => row.one_measured_by === "Piece" || onedesk.measure.measured(row);

onedesk.measure.formatter = (value, df, options, doc) => {
	const shown = frappe.format(value, { ...df, formatter: null }, { ...options, inline: true }, doc);
	const listed = ["uom", "stock_uom"].some((f) => frappe.meta.get_docfield(df.parent, f)?.in_list_view);
	const unit = doc && !listed ? doc.uom || doc.stock_uom : null;
	const symbol = unit && (frappe.boot.one_measure?.symbols?.[unit] || __(unit));
	return frappe.form.formatters._right(unit ? `${shown} ${frappe.utils.escape_html(symbol)}` : shown, options);
};

// A size says the unit it was typed in: 350 cm, 2400 mm.
onedesk.measure.side = (value, df, options, doc) => {
	const shown = frappe.format(value, { ...df, formatter: null }, { ...options, inline: true }, doc);
	const said = frappe.boot.one_measure || {};
	const unit = doc && flt(value) ? doc.one_size_uom || said.size_unit : null;
	const written = unit && (said.written?.[unit] || __(unit));
	return frappe.form.formatters._right(written ? `${shown} ${frappe.utils.escape_html(written)}` : shown, options);
};

onedesk.measure.columns = (frm) => {
	for (const fieldname of frappe.boot.one_measure?.records?.[frm.doctype] || []) {
		const grid = frm.fields_dict[fieldname]?.grid;
		if (!grid) continue;
		const quantities = (grid.docfields || []).filter((df) => ["qty", "rejected_qty"].includes(df.fieldname) && df.formatter !== onedesk.measure.formatter);
		const sides = (grid.docfields || []).filter((df) => ["one_length", "one_width", "one_height"].includes(df.fieldname) && df.formatter !== onedesk.measure.side);
		const formatted = grid.grid_rows?.length && (quantities.length || sides.length);
		if (formatted) {
			quantities.forEach((df) => grid.update_docfield_property(df.fieldname, "formatter", onedesk.measure.formatter));
			sides.forEach((df) => grid.update_docfield_property(df.fieldname, "formatter", onedesk.measure.side));
		}
		const rows = (frm.doc[fieldname] || []).filter((row) => frm.doc.docstatus === 0 || row.one_length);
		const counted = rows.some(onedesk.measure.measured);
		const show = counted ? "counted" : rows.some(onedesk.measure.sized) ? "piece" : "";
		const tall = rows.some((row) => row.one_measured_by === "Volume" || flt(row.one_height));
		const wide = tall || rows.some((row) => row.one_measured_by === "Area" || flt(row.one_width));
		const shape = `${show}:${wide}:${tall}`;
		if (grid.one_shape !== shape) {
			grid.one_shape = shape;
			grid.set_column_disp_in_list_view(onedesk.measure.SIZE, !!show);
			grid.set_column_disp_in_list_view(["one_width"], !!show && wide);
			grid.set_column_disp_in_list_view(["one_height"], !!show && tall);
			if (show === "piece") grid.set_column_disp_in_list_view(["one_pieces"], false);
		} else if (formatted) {
			grid.grid_rows.forEach((row) => row.refresh());
		}
	}
};

onedesk.measure.quantity = async (frm, cdt, cdn) => {
	const row = locals[cdt][cdn];
	onedesk.measure.columns(frm);
	if (!onedesk.measure.measured(row) || !row.item_code || !row.one_length) return;
	if (["Area", "Volume"].includes(row.one_measured_by) && !row.one_width) return;
	if (row.one_measured_by === "Volume" && !row.one_height) return;
	const qty = await frappe.xcall("onedesk.one_inventory.measure.line_quantity", {
		item_code: row.item_code,
		measured_by: row.one_measured_by,
		uom: row.uom || row.stock_uom,
		pieces: row.one_pieces,
		length: row.one_length,
		width: row.one_width,
		height: row.one_height,
		size_uom: row.one_size_uom,
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
		// A size is typed in a length: millimetres, centimetres, inches.
		handlers.setup = (frm) => {
			for (const fieldname of fieldnames) frm.set_query("one_size_uom", fieldname, () => ({ filters: { name: ["in", said.lengths || []] } }));
		};
		frappe.ui.form.on(record, handlers);
	}
	for (const lines of said.lines || []) {
		frappe.ui.form.on(lines, {
			one_measured_by: onedesk.measure.quantity,
			one_pieces: onedesk.measure.quantity,
			one_length: onedesk.measure.quantity,
			one_width: onedesk.measure.quantity,
			one_height: onedesk.measure.quantity,
			one_size_uom: onedesk.measure.quantity,
			uom: onedesk.measure.quantity,
		});
	}
});
