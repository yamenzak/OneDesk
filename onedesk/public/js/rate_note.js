// The exchange rate under a money document's rate, said with the rate in it.
// ERPNext writes "1 EUR = [?] AED" under it, the [?] standing for the box
// above, on every quotation, order, receipt and invoice in another currency.
(() => {
	const controller = window.erpnext?.TransactionController;
	if (!controller) return;
	const proto = controller.prototype;

	function said(frm, field, from) {
		const company = erpnext.get_currency(frm.doc.company);
		if (!from || !company || from === company || !frm.fields_dict[field]) return;
		const rate = flt(frm.doc[field], 6);
		const places = Math.max(2, (String(rate).split(".")[1] || "").length);
		const shown = rate ? format_number(rate, null, places) : "…";
		frm.set_df_property(field, "description", `1 ${from} = ${shown} ${company}`);
	}

	function noted(frm) {
		said(frm, "conversion_rate", frm.doc.currency);
		said(frm, "plc_conversion_rate", frm.doc.price_list_currency);
	}

	for (const method of ["change_form_labels", "conversion_rate", "plc_conversion_rate"]) {
		const theirs = proto[method];
		if (typeof theirs !== "function") continue;
		proto[method] = function (...args) {
			const back = theirs.apply(this, args);
			if (this.frm) noted(this.frm);
			return back;
		};
	}
})();
