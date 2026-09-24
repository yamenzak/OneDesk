// The operator's own settings, and the one thing on them worth a button.
//
// Every other field here is proved by something failing later — a wrong press
// token is a provisioning job that stops, a wrong R2 secret is an upload that
// refuses. The gateway had no such moment until AI 4 builds the metered call,
// so it gets one now: type a prompt, see the words back, know the token works.
frappe.ui.form.on("One Admin Settings", {
	refresh(frm) {
		frm.add_custom_button(__("Try the Gateway"), () => onedesk.admin.tryGateway());
	},
	// One token, and everything else found or made from it (one_admin/setup.py).
	set_up_cloudflare(frm) {
		if (frm.is_dirty()) return frappe.msgprint(__("Save first, so the token you entered is the one used."));
		frappe.dom.freeze(__("Setting up Cloudflare…"));
		frappe
			.xcall("onedesk.one_admin.setup.set_up")
			.then((said) => {
				frm.reload_doc();
				onedesk.admin.showSetup(said);
			})
			.finally(() => frappe.dom.unfreeze());
	},
});

frappe.provide("onedesk.admin");

onedesk.admin.showSetup = (said) => {
	const esc = frappe.utils.escape_html;
	const colour = { ours: "green", created: "blue", theirs: "gray", failed: "red", "needs attention": "orange" };
	const states = { ours: __("In place"), created: __("Created"), theirs: __("Left as it is"), failed: __("Failed"), "needs attention": __("Needs attention") };
	const rows = said
		.map(
			(one) => `<tr><td>${esc(one.step)}</td>
				<td><span class="indicator-pill ${colour[one.state] || "gray"}">${esc(states[one.state] || one.state)}</span></td>
				<td class="text-muted">${esc(one.detail || "")}</td></tr>`
		)
		.join("");
	frappe.msgprint({ title: __("Cloudflare"), message: `<table class="table table-sm">${rows}</table>`, wide: true });
};

frappe.provide("onedesk.admin");

onedesk.admin.tryGateway = () => {
	const asking = new frappe.ui.Dialog({
		title: __("Try the Gateway"),
		fields: [
			{
				fieldname: "prompt",
				fieldtype: "Small Text",
				label: __("Prompt"),
				reqd: 1,
				default: __("Say hello in one short sentence."),
			},
			{ fieldname: "said", fieldtype: "HTML" },
		],
		primary_action_label: __("Ask"),
		primary_action(values) {
			const where = asking.fields_dict.said.$wrapper;
			where.html(`<p class="text-muted">${__("Asking…")}</p>`);
			asking.get_primary_btn().prop("disabled", true);
			frappe
				.xcall("onedesk.one_admin.operator.try_the_gateway", { prompt: values.prompt })
				.then((answer) => {
					where.html(
						`<p class="text-muted">${frappe.utils.escape_html(answer.model)}</p>` +
							`<p>${frappe.utils.escape_html(answer.said)}</p>`,
					);
				})
				.catch(() => where.empty())
				.finally(() => asking.get_primary_btn().prop("disabled", false));
		},
	});
	asking.show();
};
