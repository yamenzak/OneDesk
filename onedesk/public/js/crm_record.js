// A lead's and a deal's page: calls written down from the sidebar, and a
// possible duplicate said above the form. What the page says above its fields
// and Take This Lead are its Record Head (one_crm/heads.py).
frappe.provide("onedesk.crm_record");

onedesk.crm_record.refresh = (frm) => {
	onedesk.crm_record.one_series(frm);
	if (frm.is_new()) return;
	onedesk.crm_record.actions(frm);
};

// erpnext shows a new record's Series whatever its property setters say
// (erpnext.toggle_naming_series); with one series to pick there is no question.
onedesk.crm_record.one_series = (frm) => {
	const series = frm.fields_dict.naming_series;
	if (frm.is_new() && series && (series.df.options || "").split("\n").filter(Boolean).length < 2) {
		frm.toggle_display("naming_series", false);
	}
};

onedesk.crm_record.actions = (frm) => {
	frm.sidebar.clear_user_actions();
	if (!frm.perm[0]?.write) return;
	frm.sidebar.add_user_action(__("Log a Call"), () => onedesk.crm_record.call(frm));
	if (frm.doctype === "Lead" && frm.doc.one_duplicate_of) onedesk.crm_record.duplicate(frm);
};

// A possible duplicate says so above the form, with the two ways to settle it.
// A lead is settled by OneCRM (one_crm/capture.py); a contact, customer or
// supplier by Intake's identity registry (one_intake/identity.py).
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
			: frappe.xcall(`onedesk.one_intake.identity.${method}`, { doctype: frm.doctype, name: frm.doc.name, ...args });
	if (doctype === frm.doctype) {
		frm.add_custom_button(__("Merge Into {0}", [name]), () =>
			frappe.confirm(
				__("Everything on {0} moves to {1}, and {0} is deleted.", [frm.doc.name, name]),
				() => call("merge", { into: name }).then((into) => frappe.set_route("Form", frm.doctype, into)),
			), group);
	}
	frm.add_custom_button(__("Not a Duplicate"), () => call("not_duplicate").then(() => frm.reload_doc()), group);
};

// A contact, customer or supplier somebody already is. See one_intake/identity.py.
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
			{ fieldtype: "Small Text", fieldname: "summary", label: __("What Was Said") },
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
