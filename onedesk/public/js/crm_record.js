// A lead's and a deal's page: the answers in a band under the title, and calls
// written down from the sidebar. See one_crm/record.py.
frappe.provide("onedesk.crm_record");

onedesk.crm_record.refresh = (frm) => {
	if (frm.is_new()) return;
	onedesk.crm_record.actions(frm);
	frappe
		.xcall("onedesk.one_crm.record.overview", { doctype: frm.doctype, name: frm.doc.name })
		.then((said) => {
			if (said && frm.doc.name === cur_frm?.doc?.name) {
				onedesk.band.show(frm, onedesk.crm_record.stats(frm, said));
			}
		});
};

onedesk.crm_record.actions = (frm) => {
	frm.sidebar.clear_user_actions();
	if (!frm.perm[0]?.write) return;
	frm.sidebar.add_user_action(__("Log a Call"), () => onedesk.crm_record.call(frm));
};

onedesk.crm_record.stats = (frm, said) => {
	const stat = onedesk.band.stat;
	const stats = [];
	const ago = (when) => frappe.datetime.prettyDate(when);

	if (frm.doctype === "Opportunity") {
		stats.push(stat(
			__("Deal Value · {0}%", [said.probability]),
			format_currency(said.value, said.currency, 0),
		));
		stats.push(stat(said.stage || __("Sales Stage"), __("for {0}", [onedesk.crm_record.since(said.since)])));
	} else {
		stats.push(stat(__("Came In"), ago(said.since)));
	}

	if (said.open) stats.push(onedesk.crm_record.next(said.next));

	stats.push(
		said.contact
			? stat(
				said.contact.kind === "Call" ? __("Last Call") : __("Last Email"),
				ago(said.contact.at),
				`/desk/${frappe.router.slug(said.contact.doctype)}/${encodeURIComponent(said.contact.name)}`,
			)
			: stat(__("Last Contact"), __("None yet"), null, said.open ? "waiting" : "quiet"),
	);

	if (frm.doctype === "Opportunity") {
		if (said.closing) {
			const late = said.open && frappe.datetime.get_diff(said.closing, frappe.datetime.get_today()) < 0;
			stats.push(stat(__("Closes"), frappe.datetime.str_to_user(said.closing), null, late ? "alarm" : null));
		}
		if (said.quotation) {
			const q = said.quotation;
			stats.push(stat(
				__("Quotation"),
				`${__(q.status)} · ${format_currency(q.grand_total, q.currency, 0)}`,
				`/desk/quotation/${encodeURIComponent(q.name)}`,
			));
		}
	} else if (said.deals.count) {
		stats.push(stat(
			__("Deals"),
			__("{0} open of {1}", [said.deals.open, said.deals.count]),
			`/desk/opportunity?opportunity_from=Lead&party_name=${encodeURIComponent(frm.doc.name)}`,
		));
	}

	if (said.source) stats.push(stat(__("Source"), said.source));
	return stats;
};

onedesk.crm_record.next = (next) => {
	if (!next.step && !next.on) return onedesk.band.stat(__("Next Step"), __("None planned"), null, "waiting");
	const late = onedesk.next_step.late(next.on);
	const when = next.on ? frappe.datetime.prettyDate(next.on) : "";
	return onedesk.band.stat(
		__("Next Step") + (when ? ` · ${when}` : ""),
		next.step || __("Next Step"),
		null,
		late ? "alarm" : null,
	);
};

// "12 days", "3 hours": how long, not when. Measured against the system's clock,
// which is the one `when` was written in.
onedesk.crm_record.since = (when) => {
	const hours = moment(frappe.datetime.system_datetime()).diff(moment(when), "hours");
	if (hours < 1) return __("under an hour");
	if (hours < 24) return hours === 1 ? __("an hour") : __("{0} hours", [hours]);
	const days = Math.floor(hours / 24);
	return days === 1 ? __("a day") : __("{0} days", [days]);
};

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
