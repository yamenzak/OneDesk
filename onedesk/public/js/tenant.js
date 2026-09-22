// A workspace, from the operator's side.
//
// The record is read-only, all of it, because every field on it is the record
// of something that happened rather than a setting: a signup, a call to press,
// a measurement, a rung. The verbs are here instead, and each one does what the
// nightly ladder does rather than a faster version of it — `one_admin/operator.py`
// names the same `lifecycle` calls, so an operator acting early and a clock
// acting on time run the same code.
//
// The rung a button offers comes from the server. Working it out here would be
// a second copy of the ladder, and the two would disagree the week somebody
// changed one of them.
frappe.ui.form.on("Tenant", {
	refresh(frm) {
		if (frm.is_new()) return;
		frm.page.clear_indicator();

		frappe
			.xcall("onedesk.one_admin.operator.standing", { tenant: frm.doc.name })
			.then((where) => onedesk.tenant.draw(frm, where));
	},
});

frappe.provide("onedesk.tenant");

// What each rung looks like at a glance, and the one word for it.
onedesk.tenant.SAYS = {
	Requested: ["orange", __("Waiting to be built")],
	Provisioning: ["blue", __("Being built")],
	Live: ["green", __("Live")],
	Overdue: ["orange", __("Payment overdue")],
	Suspended: ["red", __("Suspended")],
	Archived: ["grey", __("Archived")],
	Dropped: ["grey", __("Dropped")],
	Failed: ["red", __("Provisioning failed")],
};

onedesk.tenant.draw = (frm, where) => {
	const [colour, word] = onedesk.tenant.SAYS[frm.doc.status] || ["grey", frm.doc.status];
	frm.page.set_indicator(word, colour);

	// Bytes are what the field holds and not what anybody reads. The headline is
	// the only place the number is meant to be understood rather than compared.
	const held = onedesk.tenant.size(frm.doc.storage_bytes);
	const limit = frm.doc.storage_limit
		? __("of {0}", [onedesk.tenant.size(frm.doc.storage_limit)])
		: __("unmetered");
	frm.dashboard.clear_headline();
	frm.dashboard.set_headline(
		[
			`<b>${frm.doc.domain || frm.doc.site || frm.doc.name}</b>`,
			__("{0} {1}", [held, limit]),
			where.since ? __("on this rung since {0}", [frappe.datetime.str_to_user(where.since)]) : "",
		]
			.filter(Boolean)
			.join(" &nbsp;·&nbsp; "),
		"blue",
	);

	if (where.days_left !== null && where.days_left !== undefined && where.next) {
		const soon =
			where.days_left === 0
				? __("Falls to {0} tonight.", [__(where.next)])
				: __("Falls to {0} in {1} days.", [__(where.next), where.days_left]);
		frm.dashboard.clear_headline();
		frm.dashboard.set_headline(soon, where.days_left <= 2 ? "red" : "orange");
	}

	if (where.next) {
		onedesk.tenant.verb(frm, where.next, where.warning);
	}
	if (where.may_restore) {
		frm.add_custom_button(__("Restore"), () =>
			onedesk.tenant.run(frm, "onedesk.one_admin.operator.restore", {}),
		).addClass("btn-primary");
	}

	// Under a group, because neither is something anybody does daily and both
	// cost a round trip to somebody else's service.
	frm.add_custom_button(
		__("Measure storage"),
		() => onedesk.tenant.run(frm, "onedesk.one_admin.operator.measure", {}),
		__("Look again"),
	);
	frm.add_custom_button(
		__("Refresh domains"),
		() => onedesk.tenant.run(frm, "onedesk.one_admin.operator.refresh_domains", {}),
		__("Look again"),
	);
};

// Every fall is confirmed, and the confirmation says what it costs rather than
// asking "are you sure". Dropped deletes files; suspended stops a company
// working. Neither is a thing to agree to without reading a sentence.
onedesk.tenant.verb = (frm, rung, warning) => {
	frm.add_custom_button(__("Send to {0}", [__(rung)]), () => {
		frappe.confirm(
			`<p>${__("Send {0} to {1}?", [frm.doc.workspace_name || frm.doc.name, __(rung)])}</p>` +
				(warning ? `<p class="text-danger">${warning}</p>` : ""),
			() => onedesk.tenant.run(frm, "onedesk.one_admin.operator.fall", { rung }),
		);
	});
};

onedesk.tenant.run = (frm, method, args) =>
	frappe
		.xcall(method, { tenant: frm.doc.name, ...args })
		.then(() => frm.reload_doc())
		.catch(() => frm.reload_doc());


