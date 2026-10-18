frappe.ui.form.on("Tenant", {
	refresh(frm) {
		if (frm.is_new()) return;
		onedesk.tenant.said(frm);

		const billing = __("Billing");
		if (frm.doc.customer && frappe.model.can_read("Sales Invoice")) {
			frm.add_custom_button(
				__("Invoices"),
				() => frappe.set_route("List", "Sales Invoice", { customer: frm.doc.customer }),
				billing,
			);
		}
		frm.add_custom_button(__("Give Credits"), () => onedesk.tenant.give(frm), billing);
		frm.add_custom_button(
			__("Credit Ledger"),
			() => frappe.set_route("List", "Credit Ledger Entry", { tenant: frm.doc.name }),
			billing,
		);
		frm.add_custom_button(
			__("AI Usage"),
			() => frappe.set_route("query-report", "AI Usage", { tenant: frm.doc.name, by: "Model" }),
			billing,
		);

		frm.sidebar.sidebar.find(".form-shared").addClass("hidden");
	},
});

frappe.provide("onedesk.tenant");

onedesk.tenant.give = (frm) => {
	frappe.xcall("onedesk.one_admin.operator.credit_standing", { tenant: frm.doc.name }).then((now) => {
		const asking = new frappe.ui.Dialog({
			title: __("Give Credits"),
			fields: [
				{
					fieldtype: "HTML",
					options: `<p class="text-muted">${__("{0} has {1} credits ({2} on hold).", [
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
					description: __("Leave empty for no expiry."),
				},
				{ fieldname: "why", fieldtype: "Small Text", label: __("Note"), reqd: 1 },
			],
			primary_action_label: __("Give Credits"),
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
							message: __("{0} credits left", [answer.standing.balance]),
							indicator: "green",
						});
					});
			},
		});
		asking.show();
	});
};

onedesk.tenant.said = (frm) => {
	const field = frm.get_field("storage_said");
	if (!field) return;
	const held = Number(frm.doc.storage_bytes || 0);
	const limit = Number(frm.doc.storage_limit || 0);
	const pending = Number(frm.doc.storage_pending || 0);

	const lines = [
		limit
			? __("{0} of {1} ({2}%)", [
					onedesk.tenant.size(held),
					onedesk.tenant.size(limit),
					Math.round((held / limit) * 100),
				])
			: __("{0}, unmetered", [onedesk.tenant.size(held)]),
	];
	if (pending) {
		lines.push(
			__("{0} pending", [onedesk.tenant.size(pending)]),
		);
	}
	field.$wrapper.html(
		`<div class="text-muted" style="padding-bottom:8px">${lines.join("<br>")}</div>`,
	);
};
