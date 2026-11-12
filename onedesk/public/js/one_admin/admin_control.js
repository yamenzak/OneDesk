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
				{ html: `<div data-admin-areas="1"></div>` },
				{ heading: __("Domains") },
				["tenant_domain", "mail_domain"],
				data.values.environment ? ["sender_email", "environment"] : ["sender_email", ""],
				["config_copy_key", ""],
				{ heading: __("Sign In"), collapsible: true },
				["cloudflare_oauth_client_id", "cloudflare_oauth_client_secret"],
				{ heading: __("Details"), collapsible: true },
				{
					stack: [
						"cloudflare_account",
						"cloudflare_zone",
						"cloudflare_kv",
						"cloudflare_token",
						"office_url",
						"oneos_url",
						"backup_bucket",
						"keeper_url",
						"release_at",
						"cloudflare_oauth_scopes",
						"cloudflare_master_token",
					],
				},
			],
		});
		onedesk.admin.drawAreas($card.find("[data-admin-areas]"), data, {
			busy: () => this.dirty && frappe.msgprint(__("Save before setting up Cloudflare.")),
			done: () => this.refresh(),
			master: () => onedesk.admin.runSetup($card.find("[data-admin-areas]"), () => this.refresh()),
		});
	}

	draw_servers(data) {
		const $card = this.form(data, {
			rows: [
				["aws_access_key_id", "aws_secret_access_key"],
				{ heading: __("GitHub") },
				{ html: `<div data-admin-github="1"></div>` },
				{ heading: __("Personal Token"), collapsible: true },
				["github_token", ""],
			],
		});
		onedesk.admin.drawGitHub($card.find("[data-admin-github]"), data.github, () => this.refresh());
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

// Set Up Cloudflare's last run as a tile per area (control.py areas_of),
// each opening its steps, and the one button that runs it again.
onedesk.admin.drawAreas = ($into, data, { busy, done, master }) => {
	const esc = frappe.utils.escape_html;
	const states = {
		ready: [__("Ready"), "green"],
		failed: [__("Failed"), "red"],
		"needs attention": [__("Needs Attention"), "amber"],
	};
	const names = {
		account: __("Account"),
		addresses: __("Workspace Addresses"),
		mail: __("Mail"),
		storage: __("Storage and Backups"),
		services: __("Services"),
	};
	const tiles = (data.areas || [])
		.map((one) => {
			const [label, theme] = states[one.state] || states.ready;
			return `<a class="os-way one-admin-area" href="#" data-area="${esc(one.key)}">
				<div class="os-way-head"><span class="os-way-icon">${frappe.utils.icon(one.icon, "md")}</span>
				<span class="os-way-title">${esc(names[one.key])}</span>${frappe.ui.badge.html({ label, theme })}</div>
				<div class="os-way-text">${esc(one.found.join(" · ") || __("{0} steps", [one.steps.length]))}</div>
			</a>`;
		})
		.join("");
	const $tiles = $(tiles ? `<div class="os-ways mb-3">${tiles}</div>` : `<p class="text-muted">${__("Not set up yet")}</p>`);
	$tiles.on("click", "[data-area]", (event) => {
		event.preventDefault();
		const one = data.areas.find((it) => it.key === $(event.currentTarget).attr("data-area"));
		frappe.msgprint({ title: names[one.key], message: onedesk.admin.setupTable(one.steps), wide: true });
	});
	const sign_in = frappe.ui.button({
		label: data.running ? __("Setting Up…") : data.areas && data.areas.length ? __("Set Up Again") : __("Sign In to Cloudflare"),
		icon: "log-in",
		variant: "solid",
		onclick: () => {
			if (busy()) return;
			if (!data.signs_in) return master();
			frappe.xcall("onedesk.one_admin.cloudflare_signin.start").then((url) => (window.location.href = url));
		},
	});
	$(sign_in).prop("disabled", !!data.running);
	$into.empty().append($tiles, $(`<div class="d-flex"></div>`).append(sign_in));
	frappe.realtime.off("cloudflare_setup");
	frappe.realtime.on("cloudflare_setup", ({ done: finished }) => finished && done());
};

// The GitHub App as a tile (github_app.status), and its one action: make
// it from a manifest, install it, or check it.
onedesk.admin.drawGitHub = ($into, github, done) => {
	const esc = frappe.utils.escape_html;
	const [label, theme] = github.installed
		? [__("Connected"), "green"]
		: github.app
		? [__("Not Installed"), "amber"]
		: [__("Not Connected"), "gray"];
	const text = github.installed
		? __("Installed on {0}", [github.repository])
		: github.app
		? __("Not installed on {0}", [github.repository])
		: github.personal
		? __("Using the personal token")
		: __("Servers can't read the code");
	const $tile = $(`<div class="os-ways mb-3"><div class="os-way">
		<div class="os-way-head"><span class="os-way-icon">${frappe.utils.icon("github", "md")}</span>
		<span class="os-way-title">${esc(github.app || __("GitHub App"))}</span>${frappe.ui.badge.html({ label, theme })}</div>
		<div class="os-way-text">${esc(text)}</div>
	</div></div>`);
	const connect = () =>
		frappe.xcall("onedesk.one_admin.github_app.start").then(({ action, manifest }) => {
			$(`<form method="post" class="hidden"></form>`)
				.attr("action", action)
				.append($(`<input type="hidden" name="manifest">`).val(manifest))
				.appendTo("body")
				.trigger("submit");
		});
	const check = () =>
		frappe.xcall("onedesk.one_admin.github_app.check").then(() => {
			frappe.show_alert({ message: __("GitHub connected."), indicator: "green" });
			done();
		});
	const action = github.installed
		? frappe.ui.button({ label: __("Check Connection"), icon: "refresh-cw", onclick: check })
		: github.app
		? frappe.ui.button({ label: __("Install App"), icon: "github", variant: "solid", onclick: () => (window.location.href = github.install_url) })
		: frappe.ui.button({ label: __("Connect GitHub"), icon: "github", variant: "solid", onclick: connect });
	const note =
		github.installed && github.personal
			? `<p class="text-muted small mt-2">${__("The personal token is no longer used and can be cleared.")}</p>`
			: "";
	$into.empty().append($tile, $(`<div class="d-flex"></div>`).append(action), note);
};

onedesk.admin.setupTable = (said) => {
	const esc = frappe.utils.escape_html;
	const colour = { ours: "green", created: "blue", theirs: "gray", failed: "red", "needs attention": "amber" };
	const states = { ours: __("Exists"), created: __("Created"), theirs: __("Unchanged"), failed: __("Failed"), "needs attention": __("Needs Attention") };
	const rows = said
		.map(
			(one) => `<tr><td>${esc(one.step)}</td>
				<td>${frappe.ui.badge.html({ label: states[one.state] || one.state, theme: colour[one.state] || "gray" })}</td>
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
