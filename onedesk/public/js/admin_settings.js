frappe.ui.form.on("One Admin Settings", {
	refresh(frm) {
		frm.add_custom_button(__("Test Gateway"), () => onedesk.admin.tryGateway());
		frm.sidebar.sidebar.find(".form-shared").addClass("hidden");
		onedesk.admin.drawSetup(frm);
	},
	set_up_cloudflare(frm) {
		if (frm.is_dirty()) return frappe.msgprint(__("Save before setting up Cloudflare."));
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

onedesk.admin.drawSetup = (frm) => {
	const field = frm.fields_dict.cloudflare_setup_said;
	if (!field) return;
	let said = [];
	try {
		said = JSON.parse(frm.doc.cloudflare_setup || "[]");
	} catch {
		said = [];
	}
	field.$wrapper.html(
		said.length
			? `<div class="control-label">${__("Last Setup")}</div>${onedesk.admin.setupTable(said)}`
			: `<p class="text-muted small">${__("Not set up yet")}</p>`,
	);
};

onedesk.admin.showSetup = (said) => {
	frappe.msgprint({ title: __("Cloudflare"), message: onedesk.admin.setupTable(said), wide: true });
};

onedesk.admin.setupTable = (said) => {
	const esc = frappe.utils.escape_html;
	const colour = { ours: "green", created: "blue", theirs: "gray", failed: "red", "needs attention": "orange" };
	const states = { ours: __("Exists"), created: __("Created"), theirs: __("Unchanged"), failed: __("Failed"), "needs attention": __("Needs Attention") };
	const rows = said
		.map(
			(one) => `<tr><td>${esc(one.step)}</td>
				<td><span class="indicator-pill ${colour[one.state] || "gray"}">${esc(states[one.state] || one.state)}</span></td>
				<td class="text-muted">${esc(one.detail || "")}</td></tr>`
		)
		.join("");
	return `<div class="table-responsive"><table class="table table-sm">${rows}</table></div>`;
};

frappe.provide("onedesk.admin");

onedesk.admin.tryGateway = () => {
	const asking = new frappe.ui.Dialog({
		title: __("Test Gateway"),
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
		primary_action_label: __("Send Prompt"),
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
