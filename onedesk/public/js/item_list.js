// Items as a catalogue: a tab for each kind of thing along the top, so the
// trucks, the services and the profile on the shelf are not one long table, and
// how much of a stock item there is, with Low when a warehouse it is reordered
// in is at or below its level (one_inventory/kinds.py `stocked`). ERPNext's list
// settings are kept and added to.
frappe.provide("onedesk.item");

// Each tab and the filters it is. The first shows everything.
onedesk.item.TABS = () => [
	{ label: __("All"), filters: [] },
	{ label: __("Kept in Stock"), filters: [["is_stock_item", "=", 1], ["has_variants", "=", 0]] },
	{ label: __("Made Here"), filters: [["default_bom", "is", "set"]] },
	{ label: __("Services"), filters: [["is_stock_item", "=", 0], ["is_fixed_asset", "=", 0]] },
	{ label: __("Equipment"), filters: [["is_fixed_asset", "=", 1]] },
	{ label: __("Sizes or Colours"), filters: [["has_variants", "=", 1]] },
];
// The fields a tab sets, cleared before another is applied.
onedesk.item.TABBED = ["is_stock_item", "has_variants", "default_bom", "is_fixed_asset"];

{
	const theirs = frappe.listview_settings["Item"] || {};
	const held = {};

	// The tab whose filters are the ones the list has now.
	const current = (listview) => {
		const on = (listview.filter_area.get() || []).filter((one) => onedesk.item.TABBED.includes(one[1]));
		return onedesk.item.TABS().findIndex(
			(tab) => tab.filters.length === on.length && tab.filters.every((want) => on.some((one) => one[1] === want[0] && one[2] === want[1] && String(one[3]) === String(want[2] ?? "")))
		);
	};

	const draw_tabs = (listview) => {
		let $tabs = listview.$frappe_list.find(".one-item-tabs");
		if (!$tabs.length) {
			$tabs = $(`<div class="one-item-tabs" role="tablist" aria-label="${frappe.utils.escape_html(__("Kind"))}"></div>`).prependTo(listview.$frappe_list);
		}
		const at = current(listview);
		$tabs.html(
			onedesk.item
				.TABS()
				.map((tab, index) => `<button type="button" role="tab" aria-selected="${index === at}" data-tab="${index}">${frappe.utils.escape_html(tab.label)}</button>`)
				.join("")
		);
		$tabs.find("[data-tab]").on("click", async (e) => {
			const tab = onedesk.item.TABS()[Number(e.currentTarget.dataset.tab)];
			const kept = (listview.filter_area.get() || []).filter((one) => !onedesk.item.TABBED.includes(one[1]));
			await listview.filter_area.clear(false);
			await listview.filter_area.add([...kept, ...tab.filters.map((one) => ["Item", ...one])]);
		});
	};

	frappe.listview_settings["Item"] = Object.assign({}, theirs, {
		formatters: Object.assign({}, theirs.formatters, {
			// The unit's column says how many of it there are.
			stock_uom(value, df, doc) {
				const esc = frappe.utils.escape_html;
				// Nothing on hand to say for a service, equipment, or a product whose
				// stock is kept by its versions.
				if (!doc.is_stock_item || doc.has_variants) return "";
				const one = held[doc.name];
				if (!one) return `<span class="text-muted">${esc(__(value || ""))}</span>`;
				const count = `${format_number(one.on_hand, null, 0)} ${esc(__(value || ""))}`;
				return one.low ? `${count} <span class="indicator-pill orange">${esc(__("Low"))}</span>` : count;
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
			draw_tabs(listview);
			const wanted = (listview.data || []).filter((doc) => doc.is_stock_item && !(doc.name in held)).map((doc) => doc.name);
			if (!wanted.length) return;
			frappe.xcall("onedesk.one_inventory.kinds.stocked", { items: wanted }).then((found) => {
				for (const name of wanted) held[name] = (found || {})[name] || { on_hand: 0, low: false };
				listview.render();
			});
		},
	});
}
