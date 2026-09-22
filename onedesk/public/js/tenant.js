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

	// One headline. `set_headline` replaces rather than appends, so two calls
	// meant the address and the storage disappeared the moment a workspace
	// started falling — which is exactly when somebody is reading them.
	const said = [`<b>${frm.doc.domain || frm.doc.site || frm.doc.name}</b>`];
	if (where.days_left === 0 && where.next) {
		said.push(__("Falls to {0} tonight.", [__(where.next)]));
	} else if (where.days_left !== null && where.days_left !== undefined && where.next) {
		said.push(__("Falls to {0} in {1} days.", [__(where.next), where.days_left]));
	}
	frm.dashboard.clear_headline();
	frm.dashboard.set_headline(
		said.join(" &nbsp;·&nbsp; "),
		where.days_left !== null && where.days_left !== undefined && where.days_left <= 2
			? "red"
			: where.owing
				? "orange"
				: "blue",
	);

	onedesk.tenant.bars(frm, where);
	onedesk.tenant.said(frm);

	if (where.next) {
		onedesk.tenant.verb(frm, where.next, where.verb, where.warning);
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
		__("Refresh"),
	);
	frm.add_custom_button(
		__("Refresh domains"),
		() => onedesk.tenant.run(frm, "onedesk.one_admin.operator.refresh_domains", {}),
		__("Refresh"),
	);

	frm.add_custom_button(__("Give credits"), () => onedesk.tenant.give(frm), __("Credits"));
	frm.add_custom_button(__("Ledger"), () =>
		frappe.set_route("List", "Credit Ledger Entry", { tenant: frm.doc.name }),
		__("Credits"),
	);
};

// Credit an operator adds by hand: goodwill, a correction, a trial extended.
//
// A grant rather than an edit to a balance, because there is no balance to
// edit — it is a sum over rows and this writes one of them. The dialog shows
// what the workspace has before and after, since the whole reason somebody
// opens it is that a number was wrong.
onedesk.tenant.give = (frm) => {
	frappe.xcall("onedesk.one_admin.operator.credit_standing", { tenant: frm.doc.name }).then((now) => {
		const asking = new frappe.ui.Dialog({
			title: __("Give credits"),
			fields: [
				{
					fieldtype: "HTML",
					options: `<p class="text-muted">${__("{0} has {1} credits, {2} of them promised to calls in flight.", [
						frappe.utils.escape_html(frm.doc.workspace_name || frm.doc.name),
						now.balance,
						now.held,
					])}</p>`,
				},
				{ fieldname: "credits", fieldtype: "Float", label: __("Credits"), reqd: 1, precision: 6 },
				{
					fieldname: "expires_on",
					fieldtype: "Date",
					label: __("Expires On"),
					description: __("Leave empty for credit that never expires."),
				},
				{ fieldname: "why", fieldtype: "Small Text", label: __("Note"), reqd: 1 },
			],
			primary_action_label: __("Give"),
			primary_action(values) {
				frappe
					.xcall("onedesk.one_admin.operator.give_credits", {
						tenant: frm.doc.name,
						credits: values.credits,
						why: values.why,
						expires_on: values.expires_on,
					})
					.then((answer) => {
						asking.hide();
						frappe.show_alert({
							message: __("{0} credits now.", [answer.standing.balance]),
							indicator: "green",
						});
					});
			},
		});
		asking.show();
	});
};

// The storage tab, in words. The two Long Ints below this say 22548578304 and
// 26843545600, which are the right numbers to settle a bill with and the wrong
// ones to read — so the sentence goes above them rather than replacing them.
onedesk.tenant.said = (frm) => {
	const field = frm.get_field("storage_said");
	if (!field) return;
	const held = Number(frm.doc.storage_bytes || 0);
	const limit = Number(frm.doc.storage_limit || 0);
	const pending = Number(frm.doc.storage_pending || 0);

	const lines = [
		limit
			? __("{0} of {1} — {2}%", [
					onedesk.tenant.size(held),
					onedesk.tenant.size(limit),
					Math.round((held / limit) * 100),
				])
			: __("{0}, unmetered", [onedesk.tenant.size(held)]),
	];
	if (pending) {
		lines.push(
			__("{0} signed for and not yet counted.", [onedesk.tenant.size(pending)]),
		);
	}
	field.$wrapper.html(
		`<div class="text-muted" style="padding-bottom:8px">${lines.join("<br>")}</div>`,
	);
};

// Frappe's own progress bars, the same ones a sales order uses for how much of
// it has shipped. Two here, and both answer a question the fields cannot: a
// Long Int of bytes against another Long Int is arithmetic somebody has to do,
// and a date on a rung is a subtraction.
onedesk.tenant.bars = (frm, where) => {
	const limit = Number(frm.doc.storage_limit || 0);
	const held = Number(frm.doc.storage_bytes || 0);
	if (limit > 0) {
		const part = Math.min(100, (held / limit) * 100);
		const over = held > limit;
		frm.dashboard.add_progress(
			__("Storage"),
			[
				{
					width: `${part}%`,
					progress_class: over ? "progress-bar-danger" : "progress-bar-success",
					title: onedesk.tenant.size(held),
				},
			],
			over
				? __("{0} over the {1} this plan allows.", [
						onedesk.tenant.size(held - limit),
						onedesk.tenant.size(limit),
					])
				: __("{0} of {1}.", [onedesk.tenant.size(held), onedesk.tenant.size(limit)]),
		);
	}

	// Only while it is falling. A live workspace has no clock running against
	// it, and a bar at zero would suggest one does.
	if (where.days_left === null || where.days_left === undefined || !where.next) return;
	const days = where.days || where.days_left;
	const used = Math.max(0, Math.min(100, ((days - where.days_left) / days) * 100));
	frm.dashboard.add_progress(
		__("Time on this rung"),
		[
			{
				width: `${used}%`,
				progress_class: where.days_left <= 2 ? "progress-bar-danger" : "progress-bar-warning",
				title: __("{0} days left", [where.days_left]),
			},
		],
		where.days_left === 0
			? __("Falls to {0} tonight.", [__(where.next)])
			: __("{0} days before it falls to {1}.", [where.days_left, __(where.next)]),
	);
};

// Every fall is confirmed, and the confirmation says what it costs rather than
// asking "are you sure". Dropped deletes files; suspended stops a company
// working. Neither is a thing to agree to without reading a sentence.
onedesk.tenant.verb = (frm, rung, verb, warning) => {
	frm.add_custom_button(verb || __(rung), () => {
		frappe.confirm(
			`<p>${__("{0} {1}?", [verb || __(rung), frm.doc.workspace_name || frm.doc.name])}</p>` +
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


