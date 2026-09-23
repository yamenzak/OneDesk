// An asset's page answers first: worth now, what it cost, how far through its
// life, the next depreciation, where it is and who has it. See
// one_inventory/assets.py.
frappe.ui.form.on("Asset", {
	refresh(frm) {
		if (frm.is_new()) return;
		onedesk.asset.custody(frm);
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
	if (doc.docstatus === 1) {
		stats.push(
			doc.custodian
				? stat(__("Who Has It"), said.custodian_name || doc.custodian, `/desk/employee/${encodeURIComponent(doc.custodian)}`)
				: stat(__("Who Has It"), __("Nobody"), null, "quiet"),
		);
	}
	return stats;
};

// Give To… and Take Back: the two movements a person makes, one step each.
// See one_inventory/custody.py.
onedesk.asset.custody = (frm) => {
	if (frm.doc.docstatus !== 1 || !frappe.model.can_create("Asset Movement")) return;
	// A sold or scrapped asset is nobody's to give.
	if (["Sold", "Scrapped"].includes(frm.doc.status)) return;
	const done = (message) => () => {
		frappe.ui.toast({ message, type: "success" });
		frm.reload_doc();
	};
	frm.add_custom_button(frm.doc.custodian ? __("Hand To…") : __("Give To…"), () =>
		frappe.prompt(
			{ fieldtype: "Link", fieldname: "employee", label: __("Employee"), options: "Employee", reqd: 1, filters: { status: "Active" } },
			({ employee }) =>
				frappe.xcall("onedesk.one_inventory.custody.give", { asset: frm.doc.name, employee }).then(done(__("Given."))),
			frm.doc.custodian ? __("Hand To Somebody Else") : __("Give To"),
			__("Give"),
		),
	);
	if (frm.doc.custodian) {
		frm.add_custom_button(__("Take Back"), () =>
			frappe.prompt(
				{ fieldtype: "Link", fieldname: "location", label: __("Kept At"), options: "Location", reqd: 1, default: frm.doc.location },
				({ location }) =>
					frappe.xcall("onedesk.one_inventory.custody.take_back", { asset: frm.doc.name, location }).then(done(__("Taken back."))),
				__("Take Back"),
				__("Take Back"),
			),
		);
	}
};
