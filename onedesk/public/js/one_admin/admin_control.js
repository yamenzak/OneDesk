// OneAdmin's ControlCenter (docs/ONE.md): One Admin Settings, a tab each,
// and Operators (one_admin/control.py). Operators only, on the admin site.
frappe.provide("onedesk.admin_control");
frappe.provide("onedesk.admin");

onedesk.AdminSection = class AdminSection extends onedesk.CenterSection {
	static API = "onedesk.one_admin.control.";
	static HERE = "oneadmin";
	static LABEL = "ControlCenter";

	draw_operators(data) {
		const $card = $(`<div class="one-shell-section"></div>`).appendTo(this.$content);
		onedesk.admin.drawOperators($card, data.operators);
	}

	draw_cloudflare(data) {
		const $card = this.form(data, {
			rows: [
				{ heading: __("Account") },
				["cloudflare_account", "cloudflare_zone"],
				["cloudflare_kv", "environment"],
				["cloudflare_master_token", "cloudflare_token"],
				{ heading: __("Domains") },
				["tenant_domain", "mail_domain"],
				["sender_email", ""],
				{ heading: __("Set Up Cloudflare"), note: __("Finds or makes everything a workspace needs from Cloudflare.") },
				{ html: `<div data-admin-setup="1"></div><div data-admin-said="1"></div>` },
				{ heading: __("Made by Setup") },
				["office_url", "backup_bucket"],
				["keeper_url", "release_at"],
			],
		});
		const $said = $card.find("[data-admin-said]");
		onedesk.admin.drawSetup($said, data.setup);
		$card.find("[data-admin-setup]").append(
			frappe.ui.button({
				label: __("Set Up Cloudflare"),
				icon: "play",
				onclick: () => {
					if (this.dirty) return frappe.msgprint(__("Save before setting up Cloudflare."));
					onedesk.admin.runSetup($said, () => this.refresh());
				},
			})
		);
	}

	draw_servers(data) {
		this.form(data, { rows: [["aws_access_key_id", "aws_secret_access_key"], ["github_token", ""]] });
	}

	draw_storage(data) {
		this.form(data, { rows: [["bucket_global", "bucket_eu"], ["r2_key_id", "r2_secret"]] });
	}

	draw_stripe(data) {
		this.form(data, { rows: [["stripe_publishable_key", ""], ["stripe_secret_key", "stripe_webhook_secret"]] });
	}

	draw_gateway(data) {
		this.form(data, { rows: [["ai_gateway", "ai_gateway_token"]] });
		this.page.add_inner_button(__("Test Gateway"), () => onedesk.admin.tryGateway());
	}

	draw_weather(data) {
		this.form(data, { rows: [["openweather_key", ""]] });
	}

	draw_grace(data) {
		this.form(data, { rows: [["grace_days", "held_days"], ["kept_days", ""]] });
	}
};

onedesk.admin_control.open = ({ at = null } = {}) => {
	const tab = (id, label, icon, about) => onedesk.center_section.tab(onedesk.AdminSection, { id, label, icon, about });
	const dialog = onedesk.module_settings.open({
		module: "OneAdmin",
		tabs: [
			{
				group: null,
				items: [
					tab("operators", __("Operators"), "users", __("Who may run OneAdmin.")),
					tab("cloudflare", __("Cloudflare"), "cloud", __("The Cloudflare account, its domains and what setup made there.")),
					tab("servers", __("AWS and GitHub"), "server", __("The keys that order servers and read the code.")),
					tab("storage", __("Storage"), "database", __("The R2 buckets workspaces keep their files in.")),
					tab("stripe", __("Stripe"), "credit-card", __("The keys that take payments.")),
					tab("gateway", __("AI Gateway"), "oneai", __("The Cloudflare gateway OneAI goes through.")),
					tab("weather", __("Weather"), "cloud-sun", __("The key that fetches the forecast on Home.")),
					tab("grace", __("Grace Periods"), "clock", __("How long a workspace waits at each step when it stops paying.")),
				],
			},
		],
		default_tab: at,
	});
	dialog.show();
	return dialog;
};

frappe.provide("onedesk.control_centers");
onedesk.control_centers.OneAdmin = onedesk.admin_control.open;

$(document).on("page-change", () =>
	setTimeout(() => {
		const sidebar = frappe.app && frappe.app.sidebar;
		const win = onedesk.interface.current();
		if (!win || win.$foot_action || !sidebar || sidebar.current_module !== "One Admin") return;
		win.module_foot({ module: "OneAdmin", settings: () => onedesk.admin_control.open() });
		onedesk.interface.nav.place();
	}, 0)
);

onedesk.admin.drawOperators = async ($into, said = null) => {
	const people = said || (await frappe.xcall("onedesk.one_admin.site.operators"));
	const esc = frappe.utils.escape_html;
	const change = (user, on) =>
		frappe.xcall("onedesk.one_admin.site.make_operator", { user, on }).then((now) => onedesk.admin.drawOperators($into, now));
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
	$into.empty().append($list, $add);
};

onedesk.admin.drawSetup = ($into, setup, running = false) => {
	let said = [];
	try {
		said = JSON.parse(setup || "[]");
	} catch {
		said = [];
	}
	$into.html(
		said.length
			? `<div class="control-label">${running ? __("Setting Up…") : __("Last Setup")}</div>${onedesk.admin.setupTable(said)}`
			: `<p class="text-muted small">${running ? __("Setting Up…") : __("Not set up yet")}</p>`
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

// Set Up Cloudflare runs in the background (setup.run): each step shows as
// it ends, and leaving the page stops nothing.
onedesk.admin.runSetup = ($said, done) => {
	frappe.realtime.off("cloudflare_setup");
	frappe.realtime.on("cloudflare_setup", ({ said, done: finished }) => {
		onedesk.admin.drawSetup($said, JSON.stringify(said), !finished);
		if (finished) {
			frappe.realtime.off("cloudflare_setup");
			done();
		}
	});
	frappe.xcall("onedesk.one_admin.setup.set_up").then(() => onedesk.admin.drawSetup($said, null, true));
};

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
							`<p>${frappe.utils.escape_html(answer.said)}</p>`
					);
				})
				.catch(() => where.empty())
				.finally(() => asking.get_primary_btn().prop("disabled", false));
		},
	});
	asking.show();
};
