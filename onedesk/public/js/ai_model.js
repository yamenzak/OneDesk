frappe.ui.form.on("AI Model", {
	refresh(frm) {
		frm.sidebar.sidebar.find(".form-shared").addClass("hidden");
		onedesk.model.markup(frm);
		if (frm.is_new() || !frm.doc.offered) return;
		frm.add_custom_button(__("Test Call"), () => onedesk.model.price(frm));
	},
});

frappe.provide("onedesk.model");

onedesk.model.markup = (frm) => {
	const field = frm.fields_dict.markup;
	if (!field || frm.doc.markup) return;
	frappe.db.get_single_value("One Admin Settings", "default_markup").then((times) => {
		field.$input && field.$input.val("").attr("placeholder", __("Default, {0}×", [times || 0]));
		field.$wrapper.find(".control-value").text(__("Default, {0}×", [times || 0]));
	});
};

onedesk.model.price = (frm) => {
	const asking = new frappe.ui.Dialog({
		title: __("Test Call"),
		fields: [
			{
				fieldname: "tenant",
				fieldtype: "Link",
				label: __("Workspace"),
				options: "Tenant",
				reqd: 1,
				description: __("The call is real and charged to this workspace."),
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
			},
			{ fieldname: "said", fieldtype: "HTML" },
		],
		primary_action_label: __("Send Prompt"),
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
			(u.asked ? " " + __("(estimated)") : ""),
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
