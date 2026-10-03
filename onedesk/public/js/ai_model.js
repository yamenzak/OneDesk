// One model in the catalogue, from the operator's side. Whether it is offered
// and the markup in effect are its Record Head (one_admin/heads.py); this is
// the one verb that shows its answer in the dialog it was asked from.
frappe.ui.form.on("AI Model", {
	refresh(frm) {
		// Only operators read the catalogue, so sharing a model gives nobody anything.
		frm.sidebar.sidebar.find(".form-shared").addClass("hidden");
		onedesk.model.markup(frm);
		if (frm.is_new() || !frm.doc.offered) return;
		frm.add_custom_button(__("Price a call"), () => onedesk.model.price(frm));
	},
});

frappe.provide("onedesk.model");

// No markup of its own is the default, and a column that cannot be empty holds
// it as 0: shown as "0.00" it reads as "sold at cost". So the box stays empty
// and says the default it falls back to.
onedesk.model.markup = (frm) => {
	const field = frm.fields_dict.markup;
	if (!field || frm.doc.markup) return;
	frappe.db.get_single_value("One Admin Settings", "default_markup").then((times) => {
		field.$input && field.$input.val("").attr("placeholder", __("Default, {0}×", [times || 0]));
		field.$wrapper.find(".control-value").text(__("Default, {0}×", [times || 0]));
	});
};

// What one call would cost, against a real workspace's real credits — because
// a number worked out any other way is a number nobody can check against a
// bill. The call is made and charged; that is the point of it.
onedesk.model.price = (frm) => {
	const asking = new frappe.ui.Dialog({
		title: __("Price a call"),
		fields: [
			{
				fieldname: "tenant",
				fieldtype: "Link",
				label: __("Workspace"),
				options: "Tenant",
				reqd: 1,
				description: __("The call is really made and really charged."),
			},
			{
				fieldname: "prompt",
				fieldtype: "Small Text",
				label: __("Prompt"),
				reqd: 1,
				default: __("Say hello in one short sentence."),
			},
			{
				fieldname: "output_tokens",
				fieldtype: "Int",
				label: __("Output Tokens"),
				default: 256,
				description: __("What the hold is priced from. The settle replaces it."),
			},
			{ fieldname: "said", fieldtype: "HTML" },
		],
		primary_action_label: __("Call"),
		primary_action(values) {
			const where = asking.fields_dict.said.$wrapper;
			where.html(`<p class="text-muted">${__("Asking…")}</p>`);
			frappe
				.xcall("onedesk.one_admin.operator.price_a_call", {
					model: frm.doc.name,
					tenant: values.tenant,
					prompt: values.prompt,
					output_tokens: values.output_tokens,
				})
				.then((out) => where.html(onedesk.model.said(out)))
				.catch(() => where.empty());
		},
	});
	asking.show();
};

onedesk.model.said = (out) => {
	const lines = (out.used || [])
		.map((u) =>
			__("{0} {1} of {2} {3}", [u.count, u.unit, u.kind, u.modality]) +
			(u.asked ? " " + __("(from what was asked for)") : ""),
		)
		.join("<br>");
	const how = out.metered
		? __("{0} credits.", [out.credits])
		: __("{0} credits held. Usage couldn't be measured.", [out.credits]);
	return (
		`<p><b>${frappe.utils.escape_html(out.said || "")}</b></p>` +
		`<p>${how}</p>` +
		(lines ? `<p class="text-muted">${lines}</p>` : "") +
		(out.why ? `<p class="text-muted">${frappe.utils.escape_html(out.why)}</p>` : "")
	);
};
