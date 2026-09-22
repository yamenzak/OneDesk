// A signup, from the operator's side.
//
// The record is read-only: every field on it was typed by somebody on the
// sign-up page or written by the Stripe webhook, and a status an operator can
// set to Done is a customer who paid and never got a workspace.
//
// What it gains is the one verb the screen was missing. A request that is Paid
// with no workspace, or Failed with a reason, is money taken and nothing given,
// and until now the only way to finish it was to replay the webhook.
frappe.ui.form.on("Account Request", {
	refresh(frm) {
		if (frm.is_new()) return;
		onedesk.request.draw(frm);
	},
});

frappe.provide("onedesk.request");

onedesk.request.SAYS = {
	New: ["grey", __("Not paid")],
	Paying: ["orange", __("At checkout")],
	Paid: ["orange", __("Paid, not built")],
	Provisioning: ["blue", __("Being set up")],
	Done: ["green", __("Done")],
	Failed: ["red", __("Stopped")],
};

onedesk.request.draw = (frm) => {
	const [colour, word] = onedesk.request.SAYS[frm.doc.status] || ["grey", frm.doc.status];
	frm.page.set_indicator(word, colour);

	frm.dashboard.clear_headline();
	const said = onedesk.request.headline(frm.doc);
	if (said) frm.dashboard.set_headline(said[1], said[0]);

	if (frm.doc.tenant) {
		frm.add_custom_button(__("Open Workspace"), () =>
			frappe.set_route("Form", "Tenant", frm.doc.tenant),
		);
		return;
	}
	if (frm.doc.status !== "Paid" && frm.doc.status !== "Failed") return;

	frm.add_custom_button(__("Build Workspace"), () => {
		frappe.confirm(
			__("Create {0} for {1} now?", [frm.doc.slug, frm.doc.email]),
			() =>
				frappe
					.xcall("onedesk.one_admin.operator.retry_signup", { request: frm.doc.name })
					.then(() => frm.reload_doc()),
		);
	}).addClass("btn-primary");
};

// One headline, and the one that costs money wins. A paid request with no
// workspace is somebody waiting; a failed one says why it stopped, because the
// reason is what decides whether building it again will work.
onedesk.request.headline = (doc) => {
	if (doc.status === "Failed") {
		return [
			"red",
			doc.failed_reason
				? __("Stopped: {0}", [doc.failed_reason])
				: __("Stopped before the workspace was created."),
		];
	}
	if (doc.status === "Paid" && !doc.tenant) {
		return ["orange", __("Paid, and no workspace was created. Build it.")];
	}
	if (doc.status === "Provisioning") {
		return ["blue", __("The workspace is being set up. Its job has the detail.")];
	}
	return null;
};
