frappe.ui.form.on("One Admin Settings", {
	refresh(frm) {
		frm.add_custom_button(__("Test Gateway"), () => onedesk.admin.tryGateway());
		frm.sidebar.sidebar.find(".form-shared").addClass("hidden");
		onedesk.admin.drawSetup(frm);
		onedesk.admin.drawOperators(frm);
	},
	set_up_cloudflare(frm) {
		if (frm.is_dirty()) return frappe.msgprint(__("Save before setting up Cloudflare."));
		// It runs in the background (setup.run): each step shows as it ends,
		// and leaving the page stops nothing.
		frappe.realtime.off("cloudflare_setup");
		frappe.realtime.on("cloudflare_setup", ({ said, done }) => {
			frm.doc.cloudflare_setup = JSON.stringify(said);
			onedesk.admin.drawSetup(frm, !done);
			if (done) {
				frappe.realtime.off("cloudflare_setup");
				frm.reload_doc();
			}
		});
		frappe.xcall("onedesk.one_admin.setup.set_up").then(() => onedesk.admin.drawSetup(frm, true));
	},
	sign_in_to_cloudflare(frm) {
		if (frm.is_dirty()) return frappe.msgprint(__("Save before signing in to Cloudflare."));
		frappe.xcall("onedesk.one_admin.cloudflare_signin.start").then((url) => (window.location.href = url));
	},
	create_aws_user(frm) {
		if (frm.is_dirty()) return frappe.msgprint(__("Save before creating the AWS user."));
		frappe.xcall("onedesk.one_admin.aws.link").then((url) => window.open(url, "_blank", "noopener"));
	},
});

frappe.provide("onedesk.admin");

// Who may run OneAdmin (site.operators): one line each, a person added from
// the workspace's members, and the last one kept (site.make_operator).
onedesk.admin.drawOperators = async (frm, said = null) => {
	const field = frm.fields_dict.operators;
	if (!field) return;
	const people = said || (await frappe.xcall("onedesk.one_admin.site.operators"));
	const esc = frappe.utils.escape_html;
	const change = (user, on) =>
		frappe.xcall("onedesk.one_admin.site.make_operator", { user, on }).then((now) => onedesk.admin.drawOperators(frm, now));
	const $list = $(`<div class="mb-3"></div>`);
	for (const one of people) {
		$(`<div class="d-flex align-items-center mb-2" style="gap: var(--padding-sm)">
				${frappe.avatar(one.user, "avatar-small")}
				<span>${esc(one.name)}</span>
				<span class="text-muted flex-fill">${esc(one.user)}</span>
			</div>`)
			.append(
				people.length > 1
					? frappe.ui.button({ label: __("Remove"), variant: "ghost", size: "sm", onclick: () => change(one.user, 0) })
					: ""
			)
			.appendTo($list);
	}
	const $add = frappe.ui.button({
		label: __("Add Operator"),
		icon: "plus",
		size: "sm",
		onclick: () => {
			const asking = new frappe.ui.Dialog({
				title: __("Add Operator"),
				fields: [
					{
						fieldtype: "Link",
						fieldname: "user",
						label: __("Person"),
						options: "User",
						reqd: 1,
						get_query: () => ({ filters: { enabled: 1, user_type: "System User", name: ["not in", ["Administrator", "Guest"]] } }),
					},
				],
				primary_action_label: __("Add"),
				primary_action: ({ user }) => change(user, 1).then(() => asking.hide()),
			});
			asking.show();
		},
	});
	field.$wrapper.empty().append($list, $add);
};

onedesk.admin.drawSetup = (frm, running = false) => {
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
			? `<div class="control-label">${running ? __("Setting Up…") : __("Last Setup")}</div>${onedesk.admin.setupTable(said)}`
			: `<p class="text-muted small">${running ? __("Setting Up…") : __("Not set up yet")}</p>`,
	);
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
