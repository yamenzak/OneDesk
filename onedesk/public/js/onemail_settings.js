frappe.provide("onedesk.mail");

// OneMail's settings, in frappe's own settings dialog (frappe.ui.SettingsDialog),
// opened from Settings at the foot of OneMail's rail. Mailboxes is everyone's:
// each mailbox they hold, its signature, out-of-office reply, rules and
// connection. Shared Mailboxes, Personal Addresses and Mail Templates are a
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
	const disconnect = (panel, account, email) =>
		frappe.confirm(__("Disconnect {0}? Mail already synced is kept.", [esc(email)]), async () => {
			await frappe.xcall("onedesk.one_mail.connect.disconnect", { account });
			panel.refresh();
		});

	// A view inside a tab (one mailbox): frappe's panel view, with Back before
	// its title.
	const view = (panel, opts) => {
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
				click: () => {
					dialog.hide();
					frappe.set_route("onemail", { connect: 1 });
				},
			},
		],
		async render(panel) {
			const boxes = (await frappe.xcall(H + "mailboxes")) || [];
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
						open: () => mailbox(panel, box),
					})
				);
			});
		},
	};

	// One Save in the header, as frappe's own settings do: it writes the
	// signature, the auto reply and, when a password is typed, reconnects.
	const mailbox = (panel, box) => {
		let sign = null;
		let reply = null;
		let again = null;
		const save = async () => {
			if (sign) await frappe.xcall(H + "set_signature", { account: box.name, signature: sign.get_value("signature") || "" });
			if (reply) await frappe.xcall("onedesk.one_mail.rules.set_away", { account: box.name, ...reply.get_values() });
			const login = again && again.get_values();
			if (login && login.password) {
				await frappe.xcall("onedesk.one_mail.connect.reconnect", { account: box.name, ...login });
				saved();
				return mailbox(panel, { ...box, error: null });
			}
			saved();
		};
		const actions = [{ label: __("Save"), variant: "solid", click: save }];
		if (box.connected && box.may_reconnect) {
			actions.unshift({ label: __("Disconnect"), theme: "red", click: () => disconnect(panel, box.name, box.email) });
		}
		view(panel, {
			title: box.email,
			description: kind_of(box),
			actions,
			render: async (shown) => {
				const $body = shown.body;
				$body.append(heading(__("Signature"), box.sends ? "" : __("Requires Send access.")));
				if (box.sends && box.may_sign) {
					const signature = await frappe.xcall(H + "signature_of", { account: box.name });
					sign = fields($(`<div></div>`).appendTo($body), [
						{ fieldname: "signature", fieldtype: "Text Editor", default: signature || "" },
					]);
					buttons($body).append(
						onedesk.oneai.button(
							__("Write With OneAI"),
							__("Write a short email signature for {0} with my name, job title and contact details for me to approve.", [box.email])
						)
					);
				}

				$body.append(heading(__("Out of Office"), __("Sent once every 4 days per sender. Not sent to mailing lists.")));
				const away = (await frappe.xcall("onedesk.one_mail.rules.away_of", { account: box.name })) || {};
				reply = fields($(`<div></div>`).appendTo($body), [
					{ fieldname: "away", fieldtype: "Switch", label: __("Enable Auto Reply"), default: away.one_away },
					{ fieldname: "until", fieldtype: "Date", label: __("Until"), default: away.one_away_until, depends_on: "away" },
					{ fieldname: "message", fieldtype: "Small Text", label: __("Message"), default: away.one_away_message, depends_on: "away" },
				]);

				if (box.connected && box.may_reconnect && box.error) {
					$body.append(heading(__("Connection"), __("Disconnected. {0}", [box.error])));
					again = fields($(`<div></div>`).appendTo($body), [
						{ fieldname: "password", fieldtype: "Password", label: __("Password"), description: __("Gmail and Outlook require an app password.") },
						{ fieldname: "login", fieldtype: "Data", label: __("Login ID"), description: __("Leave empty to use the email address.") },
					]);
				}

				$body.append(heading(__("Mail Rules")));
				button({ label: __("Open Mail Rules"), icon_right: "arrow-up-right" })
					.on("click", () => {
						dialog.hide();
						frappe.set_route("List", "Mail Rule", { account: box.name });
					})
					.appendTo(buttons($body));
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
				click: () => {
					dialog.hide();
					frappe.set_route("onemail", { connect: 1 });
				},
			},
		],
		async render(panel) {
			const said = await frappe.xcall(H + "shared");
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
		const actions = [];
		if (box.one_connected && !box.workspace) {
			actions.push({
				label: __("Set as Workspace Mailbox"),
				click: () =>
					frappe.confirm(__("Set {0} as the workspace mailbox?", [esc(box.email_id)]), async () => {
						await frappe.xcall(H + "replace", { account: box.name, sends: box.enable_outgoing ? 1 : 0 });
						again();
					}),
			});
		}
		if (box.one_connected && box.workspace) {
			actions.push({
				label: __("Restore Default Address"),
				click: () =>
					frappe.confirm(__("Use the default workspace address again?"), async () => {
						await frappe.xcall(H + "restore");
						again();
					}),
			});
		}
		if (box.one_connected) actions.push({ label: __("Disconnect"), theme: "red", click: () => disconnect(panel, box.name, box.email_id) });
		view(panel, {
			title: box.email_id,
			description: box.workspace ? __("Workspace Mailbox") : __("Shared Mailbox"),
			actions,
			render: (shown) => {
				const users = heading_with(
					__("Users"),
					box.enable_outgoing ? __("Everyone listed can read. Send allows sending from this mailbox.") : __("Connected without outgoing mail.")
				);
				users.$row.appendTo(shown.body);
				const $add = $(`<div class="oms-add"></div>`).appendTo(users.$end);
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
						await frappe.xcall(H + "grant", { account: box.name, user, sends: box.enable_outgoing ? 1 : 0 });
						again();
					})
					.appendTo($add);
				const $list = $(`<div class="oms-list"></div>`).appendTo(shown.body);
				if (!box.people.length) $list.append(empty(__("No users")));
				box.people.forEach((one) => {
					const $end = row({ lead: frappe.ui.avatar.html({ label: one.name, size: "md" }), title: one.name, sub: esc(one.user) })
						.appendTo($list)
						.find(".oms-end");
					const send = frappe.ui.form.make_control({
						df: { fieldtype: "Switch", fieldname: "sends", label: __("Send"), read_only: !box.enable_outgoing },
						parent: $(`<span class="oms-switch"></span>`).appendTo($end),
						render_input: true,
					});
					send.set_value(one.sends);
					send.$input.on("change", async () => {
						await frappe.xcall(H + "grant", { account: box.name, user: one.user, sends: send.get_value() ? 1 : 0 });
						saved();
					});
					remove(() =>
						frappe.confirm(__("Remove {0} from {1}?", [esc(one.name), esc(box.email_id)]), async () => {
							await frappe.xcall(H + "revoke", { account: box.name, user: one.user });
							again();
						})
					).appendTo($end);
				});
			},
		});
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
