frappe.provide("onedesk.mail");

// OneMail's settings, in frappe's own settings dialog (frappe.ui.SettingsDialog),
// opened from Settings at the foot of OneMail's rail. Mailboxes is everyone's:
// each mailbox they hold, opened into its own tabs (signature, out-of-office
// reply, auto reply, users, connection, rules). Shared Mailboxes, Personal Addresses and Mail Templates are a
// Workspace Administrator's: who reads and sends from each shared mailbox, the
// address the workspace gives each person, which outside mailboxes people may
// connect, and the templates. Wording follows docs/WORDING.md. Every change is
// a call to one_mail/holders.py, connect.py and rules.py, or one/mail_templates.py.
onedesk.mail.settings = (tab) => {
	const H = "onedesk.one_mail.holders.";
	const esc = frappe.utils.escape_html;
	const admin = frappe.user.has_role("Workspace Administrator");
	const saved = () => frappe.show_alert({ message: __("Saved"), indicator: "green" });

	const heading = (title, description) =>
		`<div class="settings-dialog-section-heading"><div class="settings-dialog-section-title">${esc(title)}</div>${
			description ? `<div class="settings-dialog-section-description">${esc(description)}</div>` : ""
		}</div>`;

	// A section heading with a control at its end, such as a picker and Add.
	const heading_with = (title, description) => {
		const $row = $(`<div class="oms-heading">${heading(title, description)}<span class="oms-heading-end"></span></div>`);
		return { $row, $end: $row.find(".oms-heading-end") };
	};

	const kind_of = (box) =>
		box.workspace ? __("Workspace") : box.shared ? __("Shared") : box.connected ? __("External") : __("Personal");
	const icon_of = (box) => (box.workspace ? "building-2" : box.shared ? "users" : box.connected ? "plug" : "at-sign");

	// A list row: a picture or an icon, two lines, and what sits at its end.
	const row = ({ lead, title, sub = "", end = "", open = null }) => {
		const $row = $(`<div class="oms-row${open ? " oms-row-open" : ""}">
			<span class="oms-lead">${lead}</span>
			<span class="oms-text"><span class="oms-title">${esc(title)}</span>${sub ? `<span class="oms-sub">${sub}</span>` : ""}</span>
			<span class="oms-end">${end}</span>
		</div>`);
		if (open) {
			$row.attr({ role: "button", tabindex: 0 }).on("click keydown", (e) => {
				if (e.type === "keydown" && e.key !== "Enter") return;
				if ($(e.target).closest(".oms-end button, .oms-end input, .oms-end label").length) return;
				open();
			});
		}
		return $row;
	};
	const glyph = (name) => `<span class="oms-glyph">${frappe.utils.icon(name, "sm")}</span>`;
	const chevron = () => `<span class="oms-chevron">${frappe.utils.icon("chevron-right", "sm")}</span>`;
	const empty = (words) => `<div class="oms-empty">${esc(words)}</div>`;
	const fields = ($into, list) => {
		const group = new frappe.ui.FieldGroup({ fields: list, body: $into.get(0) });
		group.make();
		return group;
	};
	const button = (opts) => $(frappe.ui.button.html(opts));
	const buttons = ($into) => $(`<div class="oms-buttons"></div>`).appendTo($into);
	const remove = (click) =>
		button({ variant: "ghost", icon: "x", title: __("Remove"), attrs: { "aria-label": __("Remove") } }).on("click", click);
	const disconnect = (account, email, done) =>
		frappe.confirm(__("Disconnect {0}? Mail already synced is kept.", [esc(email)]), async () => {
			await frappe.xcall("onedesk.one_mail.connect.disconnect", { account });
			done();
		});

	// A view inside a tab (one mailbox): frappe's panel view, with Back before
	// its title.
	const view = (panel, opts) => {
		panel.shown = (panel.shown || 0) + 1;
		panel.set_view(opts);
		button({ variant: "ghost", icon: "arrow-left", title: __("Back"), attrs: { "aria-label": __("Back") } })
			.addClass("oms-back")
			.on("click", () => panel.refresh())
			.prependTo(panel.$header.find(".settings-dialog-panel-title"));
		return panel;
	};

	// ── Mailboxes ───────────────────────────────────────────────────────────
	const mailboxes = {
		id: "mailboxes",
		label: __("Mailboxes"),
		icon: "mail",
		title: __("Mailboxes"),
		actions: [
			{
				label: __("Connect Mailbox"),
				icon: "plus",
				click: (panel) => connect(panel),
			},
		],
		async render(panel) {
			const was = panel.shown;
			const boxes = (await frappe.xcall(H + "mailboxes")) || [];
			if (panel.shown !== was) return;
			const $list = $(`<div class="oms-list"></div>`).appendTo(panel.body.empty());
			if (!boxes.length) $list.append(empty(__("No mailboxes")));
			boxes.forEach((box) => {
				const said = [kind_of(box), box.sends ? __("Read and Send") : __("Read Only")];
				if (box.sends && box.signed) said.push(box.signed);
				$list.append(
					row({
						lead: glyph(icon_of(box)),
						title: box.email,
						sub: esc(said.join(" · ")),
						end: (box.error ? frappe.ui.badge.html({ label: __("Disconnected"), theme: "red" }) + " " : "") + chevron(),
						open: () => open(box.name, "mailboxes"),
					})
				);
			});
		},
	};

	// ── One mailbox ─────────────────────────────────────────────────────────
	// Opening a mailbox turns the dialog's tabs into its own, with All
	// Mailboxes above them to go back to the tab it was opened from
	// (frappe's SettingsDialog.reset). Each tab saves on its own, as
	// frappe's settings do. A shared mailbox's settings are its connector's
	// or an administrator's (holders.may_manage).
	const R = "onedesk.one_mail.rules.";
	const managed = __("Only the user who connected it or a Workspace Administrator can change this.");

	// A tab's Save shows only once something in it changed, and goes again
	// once saved (panel.clean). The editor settles its value after drawing,
	// so the starting values are read a moment later.
	const track = (panel) => {
		const $save = panel.$header.find(".oms-save").addClass("hide");
		const now = () => JSON.stringify(panel.fieldgroup ? panel.fieldgroup.get_values(true) : {});
		let was = null;
		setTimeout(() => (was = now()), 600);
		const check = () => was !== null && $save.toggleClass("hide", now() === was);
		(panel.fieldgroup?.fields_list || []).forEach((field) => {
			const before = field.df.change;
			field.df.change = function () {
				if (before) before.apply(this, arguments);
				check();
			};
		});
		panel.body.on("input", check);
		panel.clean = () => {
			was = now();
			$save.addClass("hide");
		};
	};

	// A tab's on/off as a switch after its title, saved as it changes; the
	// tab's fields show only while it is on.
	const header_switch = (panel, value, change) => {
		const control = frappe.ui.form.make_control({
			df: { fieldtype: "Switch", fieldname: "on", label: "" },
			parent: $(`<span class="oms-switch oms-head-switch"></span>`).appendTo(panel.$header.find(".settings-dialog-panel-title")),
			render_input: true,
		});
		control.set_value(value ? 1 : 0);
		control.$input.attr("aria-label", panel.item.title);
		const shown = (on) => panel.body.toggleClass("hide", !on);
		control.$input.on("change", async () => {
			const on = control.get_value() ? 1 : 0;
			shown(on);
			await change(on);
			saved();
		});
		shown(value);
		return control;
	};

	const signature_tab = (box) => ({
		id: "signature",
		label: __("Signature"),
		icon: "signature",
		title: __("Signature"),
		description: !box.sends ? __("Requires Send access.") : box.may_sign ? __("Added to every email sent from this mailbox.") : managed,
		actions: box.may_sign
			? [
					{
						label: __("Save"),
						variant: "solid",
						class: "oms-save",
						click: async (panel) => {
							await frappe.xcall(H + "set_signature", { account: box.name, signature: panel.get_value("signature") || "" });
							saved();
							panel.clean();
						},
					},
			  ]
			: [],
		async render(panel) {
			if (!box.may_sign) return;
			const signature = await frappe.xcall(H + "signature_of", { account: box.name });
			panel.add_fields([{ fieldname: "signature", fieldtype: "Text Editor", default: signature || "" }]);
			track(panel);
			buttons(panel.body).append(
				onedesk.oneai.button(
					__("Write With OneAI"),
					__("Write a short email signature for {0} with my name, job title and contact details for me to approve.", [box.email])
				)
			);
		},
	});

	const away_tab = (box) => ({
		id: "away",
		label: __("Out of Office"),
		icon: "plane",
		title: __("Out of Office"),
		description: box.may_manage ? __("Sent once every 4 days per sender. Not sent to mailing lists.") : managed,
		actions: box.may_manage
			? [
					{
						label: __("Save"),
						variant: "solid",
						class: "oms-save",
						click: async (panel) => {
							await frappe.xcall(R + "set_away", { account: box.name, away: panel.on.get_value() ? 1 : 0, ...panel.get_values() });
							saved();
							panel.clean();
						},
					},
			  ]
			: [],
		async render(panel) {
			if (!box.may_manage) return;
			const away = (await frappe.xcall(R + "away_of", { account: box.name })) || {};
			panel.add_fields([
				{ fieldname: "until", fieldtype: "Date", label: __("Until"), default: away.one_away_until },
				{ fieldname: "message", fieldtype: "Small Text", label: __("Message"), default: away.one_away_message },
			]);
			track(panel);
			panel.on = header_switch(panel, away.one_away, async (on) => {
				await frappe.xcall(R + "set_away", { account: box.name, away: on, ...panel.get_values() });
				panel.clean();
			});
		},
	});

	const auto_tab = (box) => ({
		id: "auto",
		label: __("Auto Reply"),
		icon: "reply",
		title: __("Auto Reply"),
		description: box.may_manage ? __("Sent to the first message of each new conversation. Not sent to replies or mailing lists.") : managed,
		actions: box.may_manage
			? [
					{
						label: __("Save"),
						variant: "solid",
						class: "oms-save",
						click: async (panel) => {
							await frappe.xcall(R + "set_auto_reply", {
								account: box.name,
								on: panel.on.get_value() ? 1 : 0,
								message: panel.get_value("message") || "",
							});
							saved();
							panel.clean();
						},
					},
			  ]
			: [],
		async render(panel) {
			if (!box.may_manage) return;
			const said = (await frappe.xcall(R + "auto_reply_of", { account: box.name })) || {};
			panel.add_fields([
				{
					fieldname: "message",
					fieldtype: "Text Editor",
					label: __("Message"),
					default: said.auto_reply_message || "",
					description: __("Leave empty for a standard reply. {{ sender_name }} adds the sender's name."),
				},
			]);
			track(panel);
			panel.on = header_switch(panel, said.enable_auto_reply, async (on) => {
				await frappe.xcall(R + "set_auto_reply", { account: box.name, on, message: panel.get_value("message") || "" });
				panel.clean();
			});
		},
	});

	// How far OneAI may go with this mailbox (one_mail/gate.py). Off reaches
	// everything that reads mail, the OneAI panel included.
	const G = "onedesk.one_mail.gate.";
	const oneai_tab = (box) => ({
		id: "oneai",
		label: __("OneAI"),
		icon: "sparkles",
		title: __("OneAI"),
		description: box.may_manage ? __("If disabled, OneAI can't read this mailbox, including in the OneAI panel.") : managed,
		actions: box.may_manage
			? [
					{
						label: __("Save"),
						variant: "solid",
						class: "oms-save",
						click: async (panel) => {
							const values = panel.get_values();
							if (!values) return;
							panel.said = await frappe.xcall(G + "set_settings", {
								account: box.name,
								reads: values.reads ? 1 : 0,
								level: values.level,
								attachments: values.attachments ? 1 : 0,
								limit: values.limit || 0,
							});
							saved();
							panel.clean();
						},
					},
			  ]
			: [],
		async render(panel) {
			const said = await frappe.xcall(G + "settings_of", { account: box.name });
			if (!said.ai) {
				panel.set_header({ title: __("OneAI"), description: __("OneAI is turned off for this workspace in Apps.") });
				return;
			}
			if (!said.may_manage) return;
			panel.add_fields([
				{
					fieldname: "reads",
					fieldtype: "Switch",
					label: __("Read New Mail"),
					default: said.reads,
					description: said.reads && said.for ? __("Reads with the permissions of {0}.", [said.for]) : __("Each new message is read and acted on. Uses OneAI credits."),
				},
				{
					fieldname: "level",
					fieldtype: "Select",
					label: __("Reads To"),
					options: [
						{ value: "Sort Only", label: __("Sort Only") },
						{ value: "Read and File", label: __("Read and File") },
						{ value: "Read, File and Act", label: __("Read, File and Act") },
					],
					default: said.level,
					depends_on: "reads",
					description: __("Sort Only moves junk and runs About rules. Act also makes tasks, events and records."),
				},
				{
					fieldname: "attachments",
					fieldtype: "Switch",
					label: __("Read Attachments"),
					default: said.attachments,
					depends_on: "reads",
					description: __("Scans, photos and recordings use the most credits."),
				},
				{
					fieldname: "limit",
					fieldtype: "Int",
					label: __("Monthly Credit Limit"),
					default: said.limit || "",
					depends_on: "reads",
					description: __("{0} used this month. Leave empty for no limit.", [format_number(said.used, null, said.used % 1 ? 2 : 0)]),
				},
			]);
			track(panel);
			panel.on = header_switch(panel, said.on, async (on) => {
				await frappe.xcall(G + "set_settings", { account: box.name, on });
				panel.clean();
			});
		},
	});

	const users_tab = (box, from) => ({
		id: "users",
		label: __("Users"),
		icon: "users",
		title: __("Users"),
		async render(panel) {
			const said = await frappe.xcall(H + "shared");
			const one_box = (said.mailboxes || []).find((one) => one.name === box.name);
			if (!one_box) return;
			const again = () => panel.refresh();
			const actions = [];
			if (one_box.one_connected && !one_box.workspace) {
				actions.push({
					label: __("Set as Workspace Mailbox"),
					click: () =>
						frappe.confirm(__("Set {0} as the workspace mailbox?", [esc(box.email)]), async () => {
							await frappe.xcall(H + "replace", { account: box.name, sends: one_box.enable_outgoing ? 1 : 0 });
							open(box.name, from, "users");
						}),
				});
			}
			if (one_box.one_connected && one_box.workspace) {
				actions.push({
					label: __("Restore Default Address"),
					click: () =>
						frappe.confirm(__("Use the default workspace address again?"), async () => {
							await frappe.xcall(H + "restore");
							home(from);
						}),
				});
			}
			panel.set_header({ title: __("Users"), description: users_said(one_box), actions });
			const $add = $(`<div class="oms-add oms-add-top"></div>`).appendTo(panel.body);
			const pick = frappe.ui.form.make_control({
				df: {
					fieldtype: "Link",
					fieldname: "user",
					options: "User",
					placeholder: __("Select User"),
					get_query: () => ({ filters: { user_type: "System User", enabled: 1 } }),
				},
				parent: $(`<span class="oms-add-pick"></span>`).appendTo($add),
				render_input: true,
			});
			button({ label: __("Add"), variant: "solid" })
				.on("click", async () => {
					const user = pick.get_value();
					if (!user) return;
					await frappe.xcall(H + "grant", { account: box.name, user, sends: one_box.enable_outgoing ? 1 : 0 });
					again();
				})
				.appendTo($add);
			const $list = $(`<div class="oms-list"></div>`).appendTo(panel.body);
			if (!one_box.people.length) $list.append(empty(__("No users")));
			one_box.people.forEach((one) => {
				const $end = row({ lead: frappe.ui.avatar.html({ label: one.name, size: "md" }), title: one.name, sub: esc(one.user) })
					.appendTo($list)
					.find(".oms-end");
				const send = frappe.ui.form.make_control({
					df: { fieldtype: "Switch", fieldname: "sends", label: __("Send"), read_only: !one_box.enable_outgoing },
					parent: $(`<span class="oms-switch"></span>`).appendTo($end),
					render_input: true,
				});
				send.set_value(one.sends);
				send.$input.on("change", async () => {
					await frappe.xcall(H + "grant", { account: box.name, user: one.user, sends: send.get_value() ? 1 : 0 });
					saved();
				});
				remove(() =>
					frappe.confirm(__("Remove {0} from {1}?", [esc(one.name), esc(box.email)]), async () => {
						await frappe.xcall(H + "revoke", { account: box.name, user: one.user });
						again();
					})
				).appendTo($end);
			});
		},
	});
	const users_said = (one_box) =>
		one_box.enable_outgoing ? __("Everyone listed can read. Send allows sending from this mailbox.") : __("Connected without outgoing mail.");

	const connection_tab = (box, from) => ({
		id: "connection",
		label: __("Connection"),
		icon: "plug",
		title: __("Connection"),
		description: box.error ? __("Disconnected. {0}", [box.error]) : __("Connected"),
		actions: [
			{ label: __("Disconnect"), theme: "red", click: () => disconnect(box.name, box.email, () => home(from)) },
			{
				label: __("Reconnect"),
				variant: "solid",
				click: async (panel) => {
					const values = panel.get_values();
					if (!values) return;
					await frappe.xcall("onedesk.one_mail.connect.reconnect", { account: box.name, ...values });
					saved();
					open(box.name, from, "connection");
				},
			},
		],
		fields: [
			{ fieldname: "password", fieldtype: "Password", label: __("Password"), reqd: 1, description: __("Gmail and Outlook require an app password.") },
			{ fieldname: "login", fieldtype: "Data", label: __("Login ID"), description: __("Leave empty to use the email address.") },
		],
	});

	const rules_tab = (box) => ({
		id: "rules",
		label: __("Mail Rules"),
		icon: "list-filter",
		title: __("Mail Rules"),
		description: __("Mark, star or move new mail as it arrives."),
		actions: [
			{
				label: __("Open Mail Rules"),
				icon: "arrow-up-right",
				click: () => {
					dialog.hide();
					frappe.set_route("List", "Mail Rule", { account: box.name });
				},
			},
		],
	});

	// `focus` is the tab to open on: signature, away, auto, users or connection.
	const open = async (name, from = "mailboxes", focus = null) => {
		const box = await frappe.xcall(H + "mailbox", { account: name });
		const items = [];
		if (box.sends || box.may_sign) items.push(signature_tab(box));
		items.push(away_tab(box));
		if (box.shared) items.push(auto_tab(box));
		items.push(oneai_tab(box));
		if (box.shared && admin) items.push(users_tab(box, from));
		if (box.connected && box.may_reconnect) items.push(connection_tab(box, from));
		items.push(rules_tab(box));
		dialog.reset(
			[
				{ items: [{ id: "back", label: __("All Mailboxes"), icon: "arrow-left", render() {} }] },
				{ group: box.email, items },
			],
			items.some((one) => one.id === focus) ? focus : items[0].id
		);
		dialog.$wrapper
			.find('.settings-dialog-tab-item[data-tab-id="back"]')
			.off("click")
			.on("click", () => home(from));
	};
	const home = (tab) => dialog.reset(tabs, tab);

	// Connecting an IMAP mailbox: the user's own from Mailboxes, the
	// workspace's from Shared Mailboxes, which then opens its users.
	const connect = (panel, { shared = false } = {}) => {
		let form = null;
		view(panel, {
			title: shared ? __("Connect Shared Mailbox") : __("Connect Mailbox"),
			description: shared ? __("A workspace address such as sales@. Add its users after connecting.") : "",
			actions: [
				{
					label: __("Connect"),
					variant: "solid",
					click: async () => {
						const values = form.get_values();
						if (!values) return;
						const $go = panel.$header.find(".settings-dialog-panel-actions button").prop("disabled", true);
						try {
							const account = await frappe.xcall("onedesk.one_mail.connect.connect", { ...values, shared: shared ? 1 : 0 });
							frappe.show_alert({ message: __("Mailbox connected"), indicator: "green" });
							if (shared) return open(account, "shared", "users");
							dialog.hide();
							frappe.set_route("onemail", { box: account });
						} finally {
							$go.prop("disabled", false);
						}
					},
				},
			],
			render: (shown) => {
				form = fields($(`<div></div>`).appendTo(shown.body), [
					{ fieldname: "email", fieldtype: "Data", options: "Email", label: __("Email Address"), reqd: 1 },
					{ fieldname: "password", fieldtype: "Password", label: __("Password"), reqd: 1, description: __("Gmail and Outlook require an app password.") },
					{ fieldname: "sends", fieldtype: "Switch", label: __("Enable Outgoing"), default: 1 },
					{ fieldtype: "Section Break", fieldname: "server", label: __("Server"), collapsible: 1 },
					{ fieldname: "login", fieldtype: "Data", label: __("Login ID"), description: __("Leave empty to use the email address.") },
					{ fieldname: "email_server", fieldtype: "Data", label: __("IMAP Server") },
					{ fieldname: "incoming_port", fieldtype: "Int", label: __("IMAP Port") },
					{ fieldname: "use_ssl", fieldtype: "Check", label: __("Use SSL"), default: 1 },
					{ fieldtype: "Column Break" },
					{ fieldname: "smtp_server", fieldtype: "Data", label: __("SMTP Server") },
					{ fieldname: "smtp_port", fieldtype: "Int", label: __("SMTP Port") },
				]);
				// Only needed when the server isn't found on its own.
				form.sections_dict.server?.collapse(true);
			},
		});
	};

	// ── Shared Mailboxes ────────────────────────────────────────────────────
	const shared = {
		id: "shared",
		label: __("Shared Mailboxes"),
		icon: "users",
		title: __("Shared Mailboxes"),
		actions: [
			{
				label: __("Connect Shared Mailbox"),
				icon: "plus",
				click: (panel) => connect(panel, { shared: true }),
			},
		],
		async render(panel) {
			const was = panel.shown;
			const said = await frappe.xcall(H + "shared");
			if (panel.shown !== was) return;
			const $list = $(`<div class="oms-list"></div>`).appendTo(panel.body.empty());
			if (!(said.mailboxes || []).length) $list.append(empty(__("No shared mailboxes")));
			(said.mailboxes || []).forEach((box) => {
				const sends = box.people.filter((one) => one.sends).length;
				$list.append(
					row({
						lead: glyph(box.workspace ? "building-2" : "users"),
						title: box.email_id,
						sub: esc(
							[
								box.workspace ? __("Workspace") : __("Shared"),
								__("{0} Users", [box.people.length]),
								box.enable_outgoing ? __("{0} Can Send", [sends]) : __("Receive Only"),
							].join(" · ")
						),
						end: chevron(),
						open: () => open(box.name, "shared"),
					})
				);
			});
		},
	};

	// ── Personal Addresses ──────────────────────────────────────────────────
	const personal = {
		id: "personal",
		label: __("Personal Addresses"),
		icon: "at-sign",
		title: __("Personal Addresses"),
		async render(panel) {
			const said = await frappe.xcall(H + "shared");
			const $body = panel.body.empty();
			const example = `name.${said.slug || "workspace"}@${said.mail_domain}`;

			// A heading with its switch at the end, saved as it changes.
			const switched = (title, description, value, change) => {
				const top = heading_with(title, description);
				top.$row.appendTo($body);
				const control = frappe.ui.form.make_control({
					df: { fieldtype: "Switch", fieldname: "on", label: "" },
					parent: $(`<span class="oms-switch"></span>`).appendTo(top.$end),
					render_input: true,
				});
				control.set_value(value ? 1 : 0);
				control.$input.on("change", async () => {
					await change(control.get_value() ? 1 : 0);
					saved();
				});
			};

			switched(
				__("Send From Workspace Addresses"),
				__("Each user gets an address such as {0}. If disabled, it only receives mail.", [example]),
				said.personal_sends,
				(on) => frappe.xcall(H + "set_personal_sends", { on })
			);
			switched(
				__("External Mailboxes"),
				__("Mailboxes users connect themselves, such as Gmail or Outlook."),
				said.external,
				async (on) => {
					await frappe.xcall(H + "set_external", { on });
					$domains.toggleClass("hide", !on);
				}
			);
			const $domains = $(`<div class="oms-domains"></div>`).appendTo($body);
			$domains.toggleClass("hide", !said.external);
			const $top = $(`<div class="oms-heading">
				<div><div class="oms-label">${esc(__("Allowed Domains"))}</div><div class="oms-help">${esc(__("Leave empty to allow any domain."))}</div></div>
				<span class="oms-heading-end"></span>
			</div>`).appendTo($domains);
			let domains = said.allowed_domains || [];
			const $list = $(`<div class="oms-list"></div>`).appendTo($domains);
			const save = async (next) => {
				domains = await frappe.xcall(H + "set_allowed_domains", { domains: next });
				draw();
			};
			const draw = () => {
				$list.empty();
				if (!domains.length) $list.append(empty(__("Any domain")));
				domains.forEach((one) => {
					const $row = row({ lead: glyph("globe"), title: "@" + one }).appendTo($list);
					remove(() => save(domains.filter((other) => other !== one))).appendTo($row.find(".oms-end"));
				});
			};
			draw();
			const $add = $(`<div class="oms-add"></div>`).appendTo($top.find(".oms-heading-end"));
			const typed = frappe.ui.form.make_control({
				df: { fieldtype: "Data", fieldname: "domain", placeholder: "gmail.com" },
				parent: $(`<span class="oms-add-pick"></span>`).appendTo($add),
				render_input: true,
			});
			const add = () => {
				const value = (typed.get_value() || "").trim();
				if (!value) return;
				typed.set_value("");
				save([...domains, value]);
			};
			typed.$input.on("keydown", (e) => e.key === "Enter" && add());
			button({ label: __("Add"), variant: "solid" }).on("click", add).appendTo($add);
		},
	};

	// ── Mail Templates ──────────────────────────────────────────────────────
	const templates = {
		id: "templates",
		label: __("Mail Templates"),
		icon: "mails",
		title: __("Mail Templates"),
		actions: [
			{ label: __("New Mail Template"), icon: "plus", click: (panel) => onedesk.mail_templates.edit(null, { done: () => panel.refresh() }) },
		],
		async render(panel) {
			const rows = (await frappe.xcall("onedesk.one.mail_templates.templates")) || [];
			const $body = panel.body.empty();
			const search = frappe.ui.form.make_control({
				df: { fieldtype: "Data", fieldname: "search", placeholder: __("Search") },
				parent: $(`<div class="oms-search"></div>`).appendTo($body),
				render_input: true,
			});
			const $list = $(`<div class="oms-list"></div>`).appendTo($body);
			if (!rows.length) $list.append(empty(__("No mail templates")));
			const $none = $(empty(__("No matches"))).addClass("hide").appendTo($list);
			search.$input.on("input", () => {
				const words = search.$input.val().trim().toLowerCase();
				let shown = 0;
				$list.children(".oms-row").each((_, el) => {
					const match = !words || el.dataset.find.includes(words);
					$(el).toggleClass("hide", !match);
					shown += match ? 1 : 0;
				});
				$none.toggleClass("hide", !rows.length || shown > 0);
			});
			rows.forEach((one) => {
				const said = [one.subject, one.label || __("All Record Types")];
				if ((one.default_for || []).length) said.push(__("Default for {0}", [one.default_for.join(", ")]));
				$list.append(
					row({
						lead: glyph("mail"),
						title: one.name,
						sub: esc(said.filter(Boolean).join(" · ")),
						end: chevron(),
						open: () => onedesk.mail_templates.edit(one.name, { done: () => panel.refresh() }),
					}).attr("data-find", [one.name, one.subject, one.label, ...(one.default_for || [])].join(" ").toLowerCase())
				);
			});
		},
	};

	const tabs = [{ group: __("Your Mail"), items: [mailboxes] }];
	if (admin) tabs.push({ group: __("Workspace"), items: [shared, personal, templates] });
	if (onedesk.mail._settings) onedesk.mail._settings.$wrapper.remove();
	// `connect` and `connect-shared` open a tab on its Connect view, and
	// `mailbox:<name>[:signature|away]` on one mailbox.
	const [opening, named, focus] = String(tab || "").split(":");
	const joining = { connect: "mailboxes", "connect-shared": admin ? "shared" : "mailboxes", mailbox: "mailboxes" }[opening];
	const first = joining || tab;
	const dialog = new frappe.ui.SettingsDialog({
		title: __("OneMail Settings"),
		default_tab: tabs.some((group) => group.items.some((one) => one.id === first)) ? first : "mailboxes",
		tabs,
	});
	onedesk.mail._settings = dialog;
	dialog.$wrapper.addClass("oms");
	dialog.show();
	if (opening === "mailbox") open(named, "mailboxes", focus);
	else if (joining) connect(dialog.get_panel(joining), { shared: joining === "shared" });
	return dialog;
};
