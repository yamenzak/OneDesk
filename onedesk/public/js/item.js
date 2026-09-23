// An item's page answers first: on hand, free to sell, on order, worth, time
// to reorder, and what it last cost. See one_inventory/item.py.
frappe.ui.form.on("Item", {
	refresh(frm) {
		if (frm.is_new()) return;
		const name = frm.doc.name;
		frappe.xcall("onedesk.one_inventory.item.said", { item: name }).then((said) => {
			if (frm.doc.name !== name) return;
			onedesk.band.show(frm, onedesk.item.stats(frm, said));
		});
	},
});

frappe.provide("onedesk.item");

onedesk.item.stats = (frm, said) => {
	const stat = onedesk.band.stat;
	const item = encodeURIComponent(frm.doc.name);
	const count = (n) => `${format_number(n, null, 0)} ${__(said.uom || "")}`.trim();
	const stats = [];
	if (frm.doc.is_fixed_asset) {
		stats.push(stat(__("Assets"), said.assets, `/desk/asset?item_code=${item}`));
		if (said.drafts) stats.push(stat(__("Not Yet Registered"), said.drafts, `/desk/asset?item_code=${item}&docstatus=0`, "waiting"));
		return stats;
	}
	if (frm.doc.is_stock_item) {
		stats.push(
			stat(__("On Hand"), count(said.on_hand), `/desk/query-report/Stock Balance?item_code=${item}`, said.on_hand > 0 ? null : "quiet"),
			stat(__("Free to Sell"), count(said.free)),
			stat(__("On Order"), count(said.ordered), said.ordered ? `/desk/purchase-order?item_code=${item}&docstatus=1&status=["not in",["Completed","Closed"]]` : null, said.ordered ? null : "quiet"),
			stat(__("Worth"), format_currency(said.value)),
		);
		if (said.below.length) {
			stats.push(stat(__("Reorder"), __("Low in {0}", [said.below.join(", ")]), null, "alarm"));
		} else if (said.levels) {
			stats.push(stat(__("Reorder"), __("Above its level"), null, "quiet"));
		} else {
			stats.push(stat(__("Reorder"), __("No level set"), null, "quiet"));
		}
	}
	// A service that is only ever sold was never bought, and saying so is noise.
	const last = said.last;
	if (last) {
		stats.push(stat(__("Last Bought"), __("{0} from {1} · {2}", [format_currency(last.rate), last.supplier, frappe.datetime.str_to_user(last.on_date)])));
	} else if (frm.doc.is_stock_item) {
		stats.push(stat(__("Last Bought"), __("Never"), null, "quiet"));
	}
	return stats;
};
