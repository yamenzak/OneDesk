frappe.provide("onedesk.crm_record");

onedesk.crm_record.refresh = (frm) => {
	onedesk.crm_record.one_series(frm);
	if (frm.is_new()) return;
	onedesk.crm_record.actions(frm);
};

onedesk.crm_record.one_series = (frm) => {
	const series = frm.fields_dict.naming_series;
	if (frm.is_new() && series && (series.df.options || "").split("\n").filter(Boolean).length < 2) {
		frm.toggle_display("naming_series", false);
	}
};

onedesk.crm_record.actions = (frm) => {
	frm.sidebar.clear_user_actions();
	if (!frm.perm[0]?.write) return;
	frm.sidebar.add_user_action(`${frappe.utils.icon("phone-call", "sm")}<span>${__("Log a Call")}</span>`, () => onedesk.crm_record.call(frm));
	if (frm.doctype === "Lead" && frm.doc.one_duplicate_of) onedesk.crm_record.duplicate(frm);
};

onedesk.crm_record.duplicate = (frm) => {
	const { one_duplicate_type: doctype, one_duplicate_of: name, one_duplicate_on: on } = frm.doc;
	const link = `<a href="/desk/${frappe.router.slug(doctype)}/${encodeURIComponent(name)}">${frappe.utils.escape_html(name)}</a>`;
	const matched = {
		email: __("email"),
		phone: __("phone"),
		"business name": __("business name"),
		Email: __("email"),
		"VAT ID": __("VAT ID"),
		"Tax Number": __("tax number"),
		IBAN: __("IBAN"),
		"Register Number": __("register number"),
		"Document Number": __("document number"),
	};
	frm.set_intro(__("This may be {0} {1}: the same {2}.", [__(doctype), link, matched[on] || on]), "orange");
	const group = __("Duplicate");
	const lead = frm.doctype === "Lead";
	const call = (method, args) =>
		lead
			? frappe.xcall(`onedesk.one_crm.capture.${method}`, { lead: frm.doc.name, ...args })
			: frappe.xcall(`onedesk.one_ai.reading.identity.${method}`, { doctype: frm.doctype, name: frm.doc.name, ...args });
	if (doctype === frm.doctype) {
		frm.add_custom_button(__("Merge Into {0}", [name]), () =>
			frappe.confirm(
				__("Everything on {0} moves to {1}, and {0} is deleted.", [frm.doc.name, name]),
				() => call("merge", { into: name }).then((into) => frappe.set_route("Form", frm.doctype, into)),
			), group);
	}
	frm.add_custom_button(__("Not a Duplicate"), () => call("not_duplicate").then(() => frm.reload_doc()), group);
};

["Contact", "Customer", "Supplier"].forEach((doctype) =>
	frappe.ui.form.on(doctype, {
		refresh(frm) {
			if (frm.doc.one_duplicate_of) onedesk.crm_record.duplicate(frm);
		},
	}),
);

onedesk.crm_record.call = (frm) => {
	const dialog = new frappe.ui.Dialog({
		title: __("Log a Call"),
		fields: [
			{
				fieldtype: "Select",
				fieldname: "direction",
				label: __("Call"),
				options: [
					{ value: "Outgoing", label: __("Outgoing") },
					{ value: "Incoming", label: __("Incoming") },
				],
				default: "Outgoing",
			},
			{
				fieldtype: "Select",
				fieldname: "outcome",
				label: __("Outcome"),
				options: [
					{ value: "Answered", label: __("Answered") },
					{ value: "No Answer", label: __("No Answer") },
					{ value: "Busy", label: __("Busy") },
				],
				default: "Answered",
			},
			{ fieldtype: "Column Break" },
			{
				fieldtype: "Int",
				fieldname: "minutes",
				label: __("Duration (Minutes)"),
				depends_on: "eval:doc.outcome === 'Answered'",
			},
			{ fieldtype: "Section Break" },
			{ fieldtype: "Small Text", fieldname: "summary", label: __("Summary") },
		],
		primary_action_label: __("Save"),
		primary_action: async (values) => {
			await frappe.xcall("onedesk.one_crm.record.log_call", {
				doctype: frm.doctype,
				name: frm.doc.name,
				...values,
			});
			dialog.hide();
			frappe.show_alert({ message: __("Call logged"), indicator: "green" });
			frm.reload_doc();
		},
	});
	dialog.show();
};
