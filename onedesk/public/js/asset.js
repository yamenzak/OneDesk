// An asset's page answers first: worth now, what it cost, how far through its
// life, the next depreciation, where it is and who has it. See
// one_inventory/assets.py.
frappe.ui.form.on("Asset", {
	refresh(frm) {
		if (frm.is_new()) return;
		const name = frm.doc.name;
		frappe.xcall("onedesk.one_inventory.assets.said", { asset: name }).then((said) => {
			if (frm.doc.name !== name) return;
			onedesk.band.show(frm, onedesk.asset.stats(frm, said));
		});
	},
});

frappe.provide("onedesk.asset");

onedesk.asset.stats = (frm, said) => {
	const stat = onedesk.band.stat;
	const doc = frm.doc;
	const money = (value) => format_currency(value, frappe.defaults.get_default("currency"));
	const stats = [stat(__("Worth Now"), money(said.worth)), stat(__("Cost"), money(said.cost))];
	if (doc.docstatus === 0) {
		stats.push(stat(__("Depreciation"), __("Starts when registered"), null, "waiting"));
	} else if (said.depreciates && said.months) {
		stats.push(stat(__("Written Off"), __("{0} of {1} months", [said.booked * said.frequency, said.months * said.frequency])));
		stats.push(
			said.next
				? stat(__("Next Depreciation"), __("{0} on {1}", [money(said.next.depreciation_amount), frappe.datetime.str_to_user(said.next.schedule_date)]))
				: stat(__("Next Depreciation"), __("None left"), null, "quiet"),
		);
	} else {
		stats.push(stat(__("Depreciation"), __("Does not depreciate"), null, "quiet"));
	}
	stats.push(stat(__("Where"), doc.location || __("Nowhere yet"), null, doc.location ? null : "waiting"));
	return stats;
};
