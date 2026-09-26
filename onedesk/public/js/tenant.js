// A workspace, from the operator's side.
//
// The record is read-only, all of it, because every field on it is the record
// of something that happened rather than a setting. Where it stands, its
// storage, credits and rung, and the verbs that move it are its Record Head
// (one_admin/heads.py). What is left here is what is not a head: the storage
// sentence on its own tab, and the credit actions in the sidebar.
frappe.ui.form.on("Tenant", {
	refresh(frm) {
		if (frm.is_new()) return;
		onedesk.tenant.said(frm);

		// Credits, in the form's own sidebar: none of them changes where the
		// workspace stands, so none of them belongs beside the verbs that do.
		frm.sidebar.clear_user_actions();
		frm.sidebar.add_user_action(__("Give credits"), () => onedesk.tenant.give(frm));
		frm.sidebar.add_user_action(__("Credit ledger"), () =>
			frappe.set_route("List", "Credit Ledger Entry", { tenant: frm.doc.name }),
		);
		frm.sidebar.add_user_action(__("AI usage"), () =>
			frappe.set_route("query-report", "AI Usage", { tenant: frm.doc.name, by: "Model" }),
		);
	},
});

frappe.provide("onedesk.tenant");

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
