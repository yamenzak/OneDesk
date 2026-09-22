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
});

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
