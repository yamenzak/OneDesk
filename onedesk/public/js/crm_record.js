// A lead's and a deal's page: the answers in a band under the title, and calls
// written down from the sidebar. See one_crm/record.py.
frappe.provide("onedesk.crm_record");

onedesk.crm_record.refresh = (frm) => {
	onedesk.crm_record.one_series(frm);
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

// erpnext shows a new record's Series whatever its property setters say
// (erpnext.toggle_naming_series); with one series to pick there is no question.
onedesk.crm_record.one_series = (frm) => {
	const series = frm.fields_dict.naming_series;
	if (frm.is_new() && series && (series.df.options || "").split("\n").filter(Boolean).length < 2) {
		frm.toggle_display("naming_series", false);
	}
};

onedesk.crm_record.OWNER = { Lead: "lead_owner", Opportunity: "opportunity_owner" };

onedesk.crm_record.actions = (frm) => {
	frm.sidebar.clear_user_actions();
	if (!frm.perm[0]?.write) return;
	frm.sidebar.add_user_action(__("Log a Call"), () => onedesk.crm_record.call(frm));

	// Nobody's yet: it came in from the web form or the inbox. See one_crm/capture.py.
	if (!frm.doc[onedesk.crm_record.OWNER[frm.doctype]]) {
		frm.add_custom_button(frm.doctype === "Lead" ? __("Take This Lead") : __("Take This Deal"), () =>
			frappe
				.xcall("onedesk.one_crm.capture.take", { doctype: frm.doctype, name: frm.doc.name })
				.then(() => frm.reload_doc()),
		);
	}
	if (frm.doctype === "Lead" && frm.doc.one_duplicate_of) onedesk.crm_record.duplicate(frm);
};

// A possible duplicate says so above the form, with the two ways to settle it.
onedesk.crm_record.duplicate = (frm) => {
	const { one_duplicate_type: doctype, one_duplicate_of: name, one_duplicate_on: on } = frm.doc;
	const link = `<a href="/desk/${frappe.router.slug(doctype)}/${encodeURIComponent(name)}">${frappe.utils.escape_html(name)}</a>`;
	const matched = { email: __("email"), phone: __("phone"), "business name": __("business name") };
	frm.set_intro(__("This may be {0} {1}: the same {2}.", [__(doctype), link, matched[on] || on]), "orange");
	const group = __("Duplicate");
	if (doctype === "Lead") {
		frm.add_custom_button(__("Merge Into {0}", [name]), () =>
			frappe.confirm(
				__("Everything on {0} moves to {1}, and {0} is deleted.", [frm.doc.name, name]),
				() =>
					frappe
						.xcall("onedesk.one_crm.capture.merge", { lead: frm.doc.name, into: name })
						.then((into) => frappe.set_route("Form", "Lead", into)),
			), group);
	}
	frm.add_custom_button(__("Not a Duplicate"), () =>
		frappe
			.xcall("onedesk.one_crm.capture.not_duplicate", { lead: frm.doc.name })
			.then(() => frm.reload_doc()), group);
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
		// Beside what is usual for the stage, once there is a usual: a deal
		// here longer than most is one to look at.
		stats.push(stat(
			said.stage || __("Sales Stage"),
			said.usual != null
				? __("for {0} · usually {1}", [onedesk.crm_record.since(said.since), onedesk.crm_record.days(said.usual)])
				: __("for {0}", [onedesk.crm_record.since(said.since)]),
			null,
			said.long ? "waiting" : null,
		));
	} else {
		stats.push(stat(__("Came In"), ago(said.since)));
		if (said.first_reply) {
			stats.push(stat(__("First Reply"), __("after {0}", [onedesk.crm_record.since(said.since, said.first_reply)])));
		} else if (said.open) {
			stats.push(stat(__("Waiting For a Reply"), onedesk.crm_record.since(said.since), null, "waiting"));
		}
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

// "12 days", "3 hours": how long, not when, up to `until` or now. Measured
// against the system's clock, which is the one `when` was written in.
onedesk.crm_record.since = (when, until) => {
	const hours = moment(until || frappe.datetime.system_datetime()).diff(moment(when), "hours");
	if (hours < 1) return __("under an hour");
	if (hours < 24) return hours === 1 ? __("an hour") : __("{0} hours", [hours]);
	const days = Math.floor(hours / 24);
	return days === 1 ? __("a day") : __("{0} days", [days]);
};

// A number of days, as a person says it: "a day", "5 days", "under a day".
onedesk.crm_record.days = (days) => {
	const whole = Math.round(days);
	if (whole < 1) return __("under a day");
	return whole === 1 ? __("a day") : __("{0} days", [whole]);
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
