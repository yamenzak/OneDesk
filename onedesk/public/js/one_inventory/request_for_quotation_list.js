(() => {
	const settings = (frappe.listview_settings["Request for Quotation"] = frappe.listview_settings["Request for Quotation"] || {});
	const held = {};
	const COLOUR = { Waiting: "orange", Answered: "blue", Ordered: "green" };
	const theirs = settings.get_indicator;
	settings.get_indicator = function (doc) {
		const one = doc.docstatus === 1 && held[doc.name];
		if (one) {
			const label = one.state === "Answered" ? __("{0} of {1} Answered", [one.answered, one.asked]) : __(one.state);
			return [label, COLOUR[one.state], `name,=,${doc.name}`];
		}
		return theirs ? theirs.call(this, doc) : undefined;
	};
	const refresh = settings.refresh;
	settings.refresh = function (listview) {
		refresh && refresh.call(this, listview);
		const wanted = (listview.data || []).filter((doc) => doc.docstatus === 1 && !(doc.name in held)).map((doc) => doc.name);
		if (!wanted.length) return;
		frappe.xcall("onedesk.one_inventory.quotes.states", { names: wanted }).then((found) => {
			Object.assign(held, found || {});
			listview.render();
		});
	};
})();
