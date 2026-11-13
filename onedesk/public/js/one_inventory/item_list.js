{
	const theirs = frappe.listview_settings["Item"] || {};
	const held = {};

	frappe.listview_settings["Item"] = Object.assign({}, theirs, {
		formatters: Object.assign({}, theirs.formatters, {
			stock_uom(value, df, doc) {
				const esc = frappe.utils.escape_html;
				if (!doc.is_stock_item || doc.has_variants) return '<span class="text-muted">–</span>';
				const one = held[doc.name];
				const unit = `<span class="text-muted small">${esc(__(value || ""))}</span>`;
				if (!one) return unit;
				const count = `${format_number(one.on_hand, null, 0)} ${unit}`;
				return one.low ? `${count} <span class="indicator-pill orange">${esc(__("Low", null, "Stock"))}</span>` : count;
			},
		}),
		onload(listview) {
			theirs.onload && theirs.onload(listview);
			if (listview.view !== "List") return;
			listview.columns = listview.columns
				.filter((col) => col.type !== "Status")
				.map((col) => (col.df?.fieldname === "stock_uom" ? { ...col, df: { ...col.df, label: __("On Hand") } } : col));
		},
		refresh(listview) {
			theirs.refresh && theirs.refresh(listview);
			const wanted = (listview.data || []).filter((doc) => doc.is_stock_item && !(doc.name in held)).map((doc) => doc.name);
			if (!wanted.length) return;
			frappe.xcall("onedesk.one_inventory.kinds.stocked", { items: wanted }).then((found) => {
				for (const name of wanted) held[name] = (found || {})[name] || { on_hand: 0, low: false };
				listview.render();
			});
		},
	});
}
