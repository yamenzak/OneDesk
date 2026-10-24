frappe.provide("onedesk.mail");

// OneMail's settings, in frappe's own settings dialog (frappe.ui.SettingsDialog):
// a tab for each part, opened from Settings at the foot of OneMail's rail.
// Your Mailboxes is everyone's: each mailbox they hold, its signature, its
// out-of-office reply, its rules and its connection. Workspace Mailboxes, Own
// Addresses and Mail Templates are a workspace administrator's: who reads and
// who sends from each of the workspace's mailboxes, whether people send from
// their own address, and the templates. Everything here is a call to
// one_mail/holders.py, connect.py and rules.py, or to one/mail_templates.py.
onedesk.mail.settings = (tab) => {
	const H = "onedesk.one_mail.holders.";
	const esc = frappe.utils.escape_html;
	const admin = frappe.user.has_role("Workspace Administrator");

	const heading = (title, description) =>
		`<div class="settings-dialog-section-heading"><div class="settings-dialog-section-title">${esc(title)}</div>${
			description ? `<div class="settings-dialog-section-description">${esc(description)}</div>` : ""
		}</div>`;

	const kind_of = (box) =>
		box.workspace ? __("Workspace") : box.shared ? __("Shared") : box.connected ? __("Connected") : __("Personal");
	const icon_of = (box) => (box.workspace ? "building-2" : box.shared ? "users" : box.connected ? "plug" : "at-sign");

	// A row of a list: a picture or an icon, two lines, and what sits at its end.
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
	const fields = ($into, list) => {
		const group = new frappe.ui.FieldGroup({ fields: list, body: $into.get(0) });
		group.make();
		return group;
	};
	const button = (opts) => $(frappe.ui.button.html(opts));
	const back = { label: __("Back"), icon: "arrow-left", click: (panel) => panel.refresh() };

	// ── Your Mailboxes ──────────────────────────────────────────────────────
	const mailboxes = {
		id: "mailboxes",
		label: __("Your Mailboxes"),
		icon: "mail",
		title: __("Your Mailboxes"),
		description: __("The mailboxes you read, what each signs with, and how it is connected."),
		actions: [
			{
				label: __("Connect Mailbox"),
				icon: "plus",
				click: () => {
					dialog.hide();
					frappe.set_route("onemail", { connect: 1 });
				},
			},
		],
		async render(panel) {
			const boxes = (await frappe.xcall(H + "mailboxes")) || [];
			const $list = $(`<div class="oms-list"></div>`).appendTo(panel.body.empty());
			if (!boxes.length) $list.append(`<div class="oms-empty">${esc(__("You don't read any mailbox yet."))}</div>`);
			boxes.forEach((box) => {
				const said = [kind_of(box), box.sends ? __("Sends") : __("Reads only")];
				if (box.sends) said.push(box.signed ? __("Signs with “{0}”", [box.signed]) : __("No signature"));
				$list.append(
					row({
						lead: glyph(icon_of(box)),
						title: box.email,
						sub: esc(said.join(" · ")),
						end:
							(box.error ? frappe.ui.badge.html({ label: __("Not Connecting"), theme: "red" }) + " " : "") + chevron(),
						open: () => mailbox(panel, box),
					})
				);
			});
		},
	};

	const mailbox = (panel, box) =>
		panel.set_view({
			title: box.email,
			description: kind_of(box),
			actions: [back],
			render: async (view) => {
				const $body = view.body;
				if (box.sends && box.may_sign) {
					$body.append(heading(__("Signature"), __("Added to every email you send from this mailbox.")));
					const $sign = $(`<div></div>`).appendTo($body);
					const signature = await frappe.xcall(H + "signature_of", { account: box.name });
					const group = fields($sign, [{ fieldname: "signature", fieldtype: "Text Editor", default: signature || "" }]);
					const $buttons = $(`<div class="oms-buttons"></div>`).appendTo($body);
					button({ label: __("Save Signature"), variant: "solid" })
						.on("click", async () => {
							await frappe.xcall(H + "set_signature", { account: box.name, signature: group.get_value("signature") || "" });
							frappe.show_alert({ message: __("Saved."), indicator: "green" });
						})
						.appendTo($buttons);
					$buttons.append(
						onedesk.oneai.button(
							__("Write With OneAI"),
							__("Write a short email signature for {0} with my name, job title and contact details for me to approve.", [box.email])
						)
					);
				} else if (!box.sends) {
					$body.append(
						heading(
							__("Signature"),
							__("You read this mailbox but don't send from it. A workspace administrator chooses who may.")
						)
					);
				}

				$body.append(heading(__("Out of Office"), __("Each sender gets one reply every four days. Mailing lists get none.")));
				const away = (await frappe.xcall("onedesk.one_mail.rules.away_of", { account: box.name })) || {};
				const $away = $(`<div></div>`).appendTo($body);
				const reply = fields($away, [
					{ fieldname: "away", fieldtype: "Switch", label: __("Reply automatically"), default: away.one_away },
					{ fieldname: "until", fieldtype: "Date", label: __("Until"), default: away.one_away_until, depends_on: "away" },
					{ fieldname: "message", fieldtype: "Small Text", label: __("Message"), default: away.one_away_message, depends_on: "away" },
				]);
				button({ label: __("Save Reply") })
					.on("click", async () => {
						const values = reply.get_values();
						await frappe.xcall("onedesk.one_mail.rules.set_away", { account: box.name, ...values });
						frappe.show_alert({ message: values.away ? __("Auto reply on") : __("Auto reply off"), indicator: "green" });
					})
					.appendTo($(`<div class="oms-buttons"></div>`).appendTo($body));

				$body.append(heading(__("Rules"), __("Move, label or forward mail as it arrives in this mailbox.")));
				button({ label: __("Open Rules"), icon_right: "arrow-up-right" })
					.on("click", () => {
						dialog.hide();
						frappe.set_route("List", "Mail Rule", { account: box.name });
					})
					.appendTo($(`<div class="oms-buttons"></div>`).appendTo($body));

				if (box.connected && box.may_reconnect) {
					$body.append(
						heading(
							__("Connection"),
							box.error ? __("This mailbox stopped connecting: {0}", [box.error]) : __("Connected over IMAP and SMTP.")
						)
					);
					const $connection = $(`<div></div>`).appendTo($body);
					let again = null;
					if (box.error) {
						again = fields($connection, [
							{ fieldname: "password", fieldtype: "Password", label: __("Password"), description: __("Gmail and Outlook need an app password.") },
							{ fieldname: "login", fieldtype: "Data", label: __("Login"), description: __("If different from the email address.") },
						]);
					}
					const $buttons = $(`<div class="oms-buttons"></div>`).appendTo($body);
					if (again) {
						button({ label: __("Reconnect"), variant: "solid" })
							.on("click", async () => {
								const values = again.get_values();
								if (!values || !values.password) return;
								await frappe.xcall("onedesk.one_mail.connect.reconnect", { account: box.name, ...values });
								frappe.show_alert({ message: __("Reconnected"), indicator: "green" });
								panel.refresh();
							})
							.appendTo($buttons);
					}
					button({ label: __("Disconnect"), theme: "red" })
						.on("click", () =>
							frappe.confirm(__("Stop reading {0}? What was read stays, linked to its records.", [esc(box.email)]), async () => {
								await frappe.xcall("onedesk.one_mail.connect.disconnect", { account: box.name });
								panel.refresh();
							})
						)
						.appendTo($buttons);
				}
			},
		});

	// ── Workspace Mailboxes ─────────────────────────────────────────────────
	const shared = {
		id: "workspace",
		label: __("Workspace Mailboxes"),
		icon: "users",
		title: __("Workspace Mailboxes"),
		description: __("The workspace's mailbox and every shared one: who reads each, and who may also send from it."),
		actions: [
			{
				label: __("Connect Shared Mailbox"),
				icon: "plus",
				click: () => {
					dialog.hide();
					frappe.set_route("onemail", { connect: 1 });
				},
			},
		],
		async render(panel) {
			const said = await frappe.xcall(H + "shared");
			const $list = $(`<div class="oms-list"></div>`).appendTo(panel.body.empty());
			(said.mailboxes || []).forEach((box) => {
				const sends = box.enable_outgoing ? box.people.filter((one) => one.sends).length : 0;
				$list.append(
					row({
						lead: glyph(box.workspace ? "building-2" : "users"),
						title: box.email_id,
						sub: esc(
							[
								box.workspace ? __("Workspace mailbox") : __("Shared"),
								__("{0} read", [box.people.length]),
								box.enable_outgoing ? __("{0} send", [sends]) : __("Receives only"),
							].join(" · ")
						),
						end: chevron(),
						open: () => access(panel, box.name),
					})
				);
			});
		},
	};

	const access = async (panel, name) => {
		const said = await frappe.xcall(H + "shared");
		const box = (said.mailboxes || []).find((one) => one.name === name);
		if (!box) return panel.refresh();
		const again = () => access(panel, name);
		const actions = [back];
		if (box.one_connected && !box.workspace) {
			actions.push({
				label: __("Make Workspace Mailbox"),
				click: () =>
					frappe.confirm(__("{0} becomes the workspace's mailbox: what the workspace receives at and sends as.", [esc(box.email_id)]), async () => {
						await frappe.xcall(H + "replace", { account: box.name, sends: box.enable_outgoing ? 1 : 0 });
						again();
					}),
			});
		}
		if (box.one_connected && box.workspace) {
			actions.push({
				label: __("Use the Workspace's Own Address"),
				click: () =>
					frappe.confirm(__("The workspace receives at and sends as its own address again."), async () => {
						await frappe.xcall(H + "restore");
						again();
					}),
			});
		}
		if (box.one_connected) {
			actions.push({
				label: __("Disconnect"),
				theme: "red",
				click: () =>
					frappe.confirm(__("Stop reading {0}? What was read stays, linked to its records.", [esc(box.email_id)]), async () => {
						await frappe.xcall("onedesk.one_mail.connect.disconnect", { account: box.name });
						panel.refresh();
					}),
			});
		}
		panel.set_view({
			title: box.email_id,
			description: box.workspace ? __("The workspace's mailbox") : __("A shared mailbox"),
			actions,
			render: (view) => {
				view.body.append(
					heading(
						__("People"),
						box.enable_outgoing
							? __("Everyone listed reads this mailbox. Turn on Send for those who may also send from it.")
							: __("Everyone listed reads this mailbox. It was connected without sending, so nobody sends from it.")
					)
				);
				const $list = $(`<div class="oms-list"></div>`).appendTo(view.body);
				if (!box.people.length) $list.append(`<div class="oms-empty">${esc(__("Nobody reads this mailbox yet."))}</div>`);
				box.people.forEach((one) => {
					const $row = row({
						lead: frappe.ui.avatar.html({ label: one.name, size: "md" }),
						title: one.name,
						sub: esc(one.user),
						end: "",
					}).appendTo($list);
					const $end = $row.find(".oms-end");
					const send = frappe.ui.form.make_control({
						df: { fieldtype: "Switch", fieldname: "sends", label: __("Send"), read_only: !box.enable_outgoing },
						parent: $(`<span class="oms-switch"></span>`).appendTo($end),
						render_input: true,
					});
					send.set_value(one.sends);
					send.$input.on("change", async () => {
						await frappe.xcall(H + "grant", { account: box.name, user: one.user, sends: send.get_value() ? 1 : 0 });
						frappe.show_alert({ message: __("Saved."), indicator: "green" });
					});
					button({ variant: "ghost", icon: "x", title: __("Remove"), attrs: { "aria-label": __("Remove") } })
						.on("click", () =>
							frappe.confirm(__("{0} no longer reads {1}.", [esc(one.name), esc(box.email_id)]), async () => {
								await frappe.xcall(H + "revoke", { account: box.name, user: one.user });
								again();
							})
						)
						.appendTo($end);
				});
				const $add = $(`<div class="oms-add"></div>`).appendTo(view.body);
				const pick = frappe.ui.form.make_control({
					df: {
						fieldtype: "Link",
						fieldname: "user",
						options: "User",
						placeholder: __("Add a person"),
						get_query: () => ({ filters: { user_type: "System User", enabled: 1 } }),
					},
					parent: $(`<span class="oms-add-pick"></span>`).appendTo($add),
					render_input: true,
				});
				button({ label: __("Add"), variant: "solid" })
					.on("click", async () => {
						const user = pick.get_value();
						if (!user) return;
						await frappe.xcall(H + "grant", { account: box.name, user, sends: box.enable_outgoing ? 1 : 0 });
						again();
					})
					.appendTo($add);
			},
		});
	};

	// ── Own Addresses ───────────────────────────────────────────────────────
	const own = {
		id: "own",
		label: __("Own Addresses"),
		icon: "at-sign",
		title: __("Own Addresses"),
		description: __("Everyone in the workspace has an address of their own, such as name.workspace@m.4dl.app."),
		async render(panel) {
			const said = await frappe.xcall(H + "shared");
			const group = fields($(`<div></div>`).appendTo(panel.body.empty()), [
				{
					fieldname: "sends",
					fieldtype: "Switch",
					label: __("People send from their own address"),
					description: __("Off, their own address only receives, and they send from a mailbox they may send from."),
					default: said.personal_sends,
				},
			]);
			group.get_field("sends").$input.on("change", async () => {
				await frappe.xcall(H + "set_personal_sends", { on: group.get_value("sends") ? 1 : 0 });
				frappe.show_alert({ message: __("Saved."), indicator: "green" });
			});
		},
	};

	// ── Mail Templates ──────────────────────────────────────────────────────
	const templates = {
		id: "templates",
		label: __("Mail Templates"),
		icon: "mails",
		title: __("Mail Templates"),
		description: __("Reusable email text. The composer offers a template on the kind of record it is for, or everywhere."),
		actions: [
			{ label: __("New Mail Template"), icon: "plus", click: (panel) => onedesk.mail_templates.edit(null, { done: () => panel.refresh() }) },
		],
		async render(panel) {
			const rows = (await frappe.xcall("onedesk.one.mail_templates.templates")) || [];
			const $list = $(`<div class="oms-list"></div>`).appendTo(panel.body.empty());
			if (!rows.length) $list.append(`<div class="oms-empty">${esc(__("No mail templates yet."))}</div>`);
			rows.forEach((one) => {
				const said = [one.subject, one.label || __("Any record")];
				if ((one.default_for || []).length) said.push(__("Default for {0}", [one.default_for.join(", ")]));
				$list.append(
					row({
						lead: glyph("mail"),
						title: one.name,
						sub: esc(said.filter(Boolean).join(" · ")),
						end: chevron(),
						open: () => onedesk.mail_templates.edit(one.name, { done: () => panel.refresh() }),
					})
				);
			});
		},
	};

	const tabs = [{ group: __("You"), items: [mailboxes] }];
	if (admin) tabs.push({ group: __("Workspace"), items: [shared, own, templates] });
	if (onedesk.mail._settings) onedesk.mail._settings.$wrapper.remove();
	const dialog = new frappe.ui.SettingsDialog({
		title: __("OneMail Settings"),
		default_tab: tabs.some((group) => group.items.some((one) => one.id === tab)) ? tab : "mailboxes",
		tabs,
	});
	onedesk.mail._settings = dialog;
	dialog.$wrapper.addClass("oms");
	dialog.show();
	return dialog;
};
