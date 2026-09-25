// Settings: everything a person or a workspace sets, in one place. The server
// says which sections the reader may open and holds every read and write
// (one/settings.py); this draws them with frappe's own parts — espresso
// buttons, badges and bars, and FieldGroup for anything that is a form.

frappe.pages["settings"].on_page_load = (wrapper) => {
	const page = frappe.ui.make_app_page({ parent: wrapper, title: __("Settings"), single_column: true });
	wrapper.settings = new onedesk.Settings(page);
};

frappe.pages["settings"].on_page_show = (wrapper) => wrapper.settings && wrapper.settings.show();

frappe.provide("onedesk");

onedesk.Settings = class Settings {
	static API = "onedesk.one.settings.";

	constructor(page) {
		this.page = page;
		this.$body = $(`<div class="os-settings">
			<nav class="os-nav"></nav>
			<section class="os-section"></section>
		</div>`).appendTo(page.main);
		this.$nav = this.$body.find(".os-nav");
		this.$section = this.$body.find(".os-section");
	}

	async show() {
		if (!this.said) {
			this.said = await frappe.xcall(Settings.API + "sections");
			this.draw_nav();
		}
		const asked = frappe.utils.get_query_params().section;
		const known = this.said.sections.map((one) => one.key);
		this.open(known.includes(asked) ? asked : this.key || "profile");
	}

	draw_nav() {
		const esc = frappe.utils.escape_html;
		const group = (name, label) => {
			const rows = this.said.sections.filter((one) => one.group === name);
			if (!rows.length) return "";
			return `<div class="os-nav-group">${label}</div>${rows
				.map(
					(one) => `<button class="os-nav-item" data-key="${esc(one.key)}">${frappe.utils.icon(one.icon, "sm")}<span>${esc(one.label)}</span></button>`
				)
				.join("")}`;
		};
		this.$nav.html(group("you", __("You")) + group("workspace", __("Workspace")));
		this.$nav.find("[data-key]").on("click", (event) => this.open($(event.currentTarget).attr("data-key")));
	}

	async open(key) {
		this.key = key;
		this.$nav.find("[data-key]").removeClass("active");
		this.$nav.find(`[data-key="${key}"]`).addClass("active");
		window.history.replaceState(null, "", `/app/settings?section=${encodeURIComponent(key)}`);
		const section = this.said.sections.find((one) => one.key === key);
		this.$section.html(`<div class="os-head"><h2>${frappe.utils.escape_html(section.label)}</h2></div><div class="os-content"></div>`);
		this.$content = this.$section.find(".os-content");
		this.$content.html(`<div class="os-quiet">${__("Loading…")}</div>`);
		try {
			this.data = await frappe.xcall(Settings.API + "load", { section: key });
		} catch (e) {
			this.$content.html(frappe.ui.alert.html({ title: __("This section could not be opened."), theme: "red" }));
			return;
		}
		this.$content.empty();
		this[`draw_${key}`](this.data);
	}

	// ---------------------------------------------------------------- parts

	button(label, attrs = {}, variant = "subtle", icon = null, theme = null) {
		return frappe.ui.button.html({ label, attrs, variant, icon, theme: theme || undefined });
	}

	card(title, body, note) {
		const esc = frappe.utils.escape_html;
		return `<div class="os-card">${title ? `<div class="os-card-title">${esc(title)}</div>` : ""}${
			note ? `<div class="os-quiet os-card-note">${esc(note)}</div>` : ""
		}${body}</div>`;
	}

	// A form made of the record's own fields, saved in one go.
	form(data, { before = "", after = "" } = {}) {
		const $card = $(`<div class="os-card">${before}<div class="os-form"></div><div class="os-actions"></div>${after}</div>`).appendTo(this.$content);
		const fields = data.fields.map((one) => ({ ...one, default: data.values[one.fieldname] }));
		this.group = new frappe.ui.FieldGroup({ fields, body: $card.find(".os-form")[0] });
		this.group.make();
		this.group.set_values(data.values);
		$card.find(".os-actions").html(this.button(__("Save"), { "data-save": "1" }, "solid"));
		$card.find("[data-save]").on("click", () => this.save(this.group.get_values(true)));
		return $card;
	}

	async save(values) {
		this.data = await frappe.xcall(Settings.API + "save", { section: this.key, values });
		frappe.show_alert({ message: __("Saved."), indicator: "green" });
		this.$content.empty();
		this[`draw_${this.key}`](this.data);
	}

	empty(title, description) {
		return `<div class="os-empty"><div class="os-empty-title">${frappe.utils.escape_html(title)}</div>${
			description ? `<div class="os-quiet">${frappe.utils.escape_html(description)}</div>` : ""
		}</div>`;
	}

	// ---------------------------------------------------------------- you

	draw_profile(data) {
		const esc = frappe.utils.escape_html;
		const who = `<div class="os-who">${frappe.ui.avatar.html({ label: data.full_name, image: data.values.user_image, size: "xl" })}
			<div><div class="os-who-name">${esc(data.full_name || "")}</div><div class="os-quiet">${esc(data.email || "")}</div></div></div>`;
		this.form(data, { before: who });
	}

	draw_notifications(data) {
		this.form(data, { before: `<div class="os-quiet os-card-note">${__("What reaches you in the bell, and what is also mailed to you.")}</div>` });
	}

	draw_mail(data) {
		const esc = frappe.utils.escape_html;
		const rows = (data.mailboxes || [])
			.map((one) => {
				const kind = one.workspace ? __("Workspace") : one.shared ? __("Shared") : one.connected ? __("Connected") : __("Yours");
				const badges = [
					frappe.ui.badge.html({ label: kind, theme: one.workspace ? "blue" : "gray" }),
					one.intake ? frappe.ui.badge.html({ label: __("Read by OneAI"), theme: "violet" }) : "",
					one.error ? frappe.ui.badge.html({ label: __("Not reachable"), theme: "red", title: one.error }) : "",
				].join(" ");
				return `<div class="os-row">
					<div class="os-row-main"><div class="os-row-title">${esc(one.email)}</div><div class="os-row-sub">${badges}</div></div>
					<div class="os-row-actions">${one.sends ? this.button(__("Signature"), { "data-signature": one.name }) : ""}
					${this.button(__("Open"), { "data-open": one.name }, "ghost")}</div>
				</div>`;
			})
			.join("");
		this.$content.html(
			this.card(
				__("Your Mailboxes"),
				(rows || this.empty(__("No mailboxes yet."))) +
					`<div class="os-actions">${this.button(__("Connect a Mailbox"), { "data-connect": "1" }, "solid", "plug")}</div>`,
				__("Mailboxes are connected and read in OneMail. Here you choose what you sign with.")
			)
		);
		this.$content.find("[data-open]").on("click", (event) => frappe.set_route("onemail", { box: $(event.currentTarget).attr("data-open") }));
		this.$content.find("[data-connect]").on("click", () => frappe.set_route("onemail", { connect: 1 }));
		this.$content.find("[data-signature]").on("click", async (event) => {
			const account = $(event.currentTarget).attr("data-signature");
			const signature = await frappe.xcall("onedesk.one_mail.holders.signature_of", { account });
			const dialog = new frappe.ui.Dialog({
				title: __("Signature"),
				fields: [{ fieldname: "signature", fieldtype: "Text Editor", label: __("Signature"), default: signature }],
				primary_action_label: __("Save"),
				primary_action: async (values) => {
					await frappe.xcall("onedesk.one_mail.holders.set_signature", { account, signature: values.signature || "" });
					dialog.hide();
					frappe.show_alert({ message: __("Saved."), indicator: "green" });
				},
			});
			dialog.show();
		});
	}

	draw_calendar(data) {
		const esc = frappe.utils.escape_html;
		const $card = $(
			this.card(
				__("Your Calendar in Other Apps"),
				`<div class="os-feed"></div><div class="os-actions"></div>`,
				__("A private link that shows your events, tasks and deadlines in Google Calendar, Outlook or on a phone.")
			)
		).appendTo(this.$content);
		const draw = (link) => {
			$card.find(".os-feed").html(
				link
					? `<div class="os-copy"><code>${esc(link.webcal)}</code>${this.button(__("Copy"), { "data-copy": link.webcal }, "ghost", "copy")}</div>
					<div class="os-quiet">${__("Anybody with this link can see your calendar. Make a new one if it was shared by mistake.")}</div>`
					: ""
			);
			$card.find(".os-actions").html(
				link
					? this.button(__("Make a New Link"), { "data-renew": "1" }, "subtle", "refresh-cw") + this.button(__("Turn the Link Off"), { "data-stop": "1" }, "ghost", null, "red")
					: this.button(__("Make My Link"), { "data-make": "1" }, "solid")
			);
			$card.find("[data-copy]").on("click", (event) => frappe.utils.copy_to_clipboard($(event.currentTarget).attr("data-copy")));
			$card.find("[data-make]").on("click", async () => draw(await frappe.xcall("onedesk.one_calendar.feed.mine")));
			$card.find("[data-renew]").on("click", () =>
				frappe.confirm(__("The old link stops working. Make a new one?"), async () => draw(await frappe.xcall("onedesk.one_calendar.feed.renew")))
			);
			$card.find("[data-stop]").on("click", () =>
				frappe.confirm(__("Turn the link off? Calendars that read it stop updating."), async () => {
					await frappe.xcall("onedesk.one_calendar.feed.stop");
					draw(null);
				})
			);
		};
		if (data.has_feed) frappe.xcall("onedesk.one_calendar.feed.mine").then(draw);
		else draw(null);
	}

	draw_signin(data) {
		const password = this.card(
			__("Password"),
			`<div class="os-actions">${this.button(__("Change Password"), { "data-password": "1" }, "subtle", "key-round")}</div>`
		);
		const passkey = data.employee
			? this.card(
					__("Passkey for Checking In"),
					`<div class="os-row"><div class="os-row-main">${frappe.ui.badge.html({
						label: data.passkey ? __("Registered") : __("Not registered"),
						theme: data.passkey ? "green" : "gray",
					})}</div>${data.passkey ? "" : `<div class="os-row-actions">${this.button(__("Register This Device"), { "data-passkey": "1" }, "solid")}</div>`}</div>`,
					__("Your fingerprint or face on this phone or laptop, used when you check in.")
			  )
			: "";
		const sessions = this.card(
			__("Where You Are Signed In"),
			`<div class="os-row"><div class="os-row-main">${
				data.sessions ? __("{0} sessions, this one included.", [data.sessions]) : __("Only here.")
			}</div><div class="os-row-actions">${this.button(__("Sign Out Everywhere Else"), { "data-elsewhere": "1" }, "subtle", "log-out")}</div></div>`
		);
		this.$content.html(password + passkey + sessions);
		this.$content.find("[data-password]").on("click", () => {
			const dialog = new frappe.ui.Dialog({
				title: __("Change Password"),
				fields: [
					{ fieldname: "old_password", fieldtype: "Password", label: __("Current Password"), reqd: 1 },
					{ fieldname: "new_password", fieldtype: "Password", label: __("New Password"), reqd: 1 },
				],
				primary_action_label: __("Change"),
				primary_action: async (values) => {
					await frappe.xcall("frappe.core.doctype.user.user.update_password", {
						old_password: values.old_password,
						new_password: values.new_password,
						logout_all_sessions: 0,
					});
					dialog.hide();
					frappe.show_alert({ message: __("Your password is changed."), indicator: "green" });
				},
			});
			dialog.show();
		});
		this.$content.find("[data-passkey]").on("click", async () => {
			await onedesk.passkey.register();
			this.open("signin");
		});
		this.$content.find("[data-elsewhere]").on("click", () =>
			frappe.confirm(__("Sign out on every other phone and computer?"), async () => {
				await frappe.xcall(Settings.API + "sign_out_elsewhere");
				frappe.show_alert({ message: __("Signed out everywhere else."), indicator: "green" });
				this.open("signin");
			})
		);
	}

	draw_memory(data) {
		const esc = frappe.utils.escape_html;
		const rows = (data.facts || [])
			.map(
				(one) => `<div class="os-row">
				<div class="os-row-main"><div>${esc(one.fact || "")}</div>${
					one.about_doctype ? `<div class="os-row-sub os-quiet">${esc(__(one.about_doctype))} ${esc(one.about_name || "")}</div>` : ""
				}</div>
				<div class="os-row-actions">${this.button(__("Forget"), { "data-forget": one.name }, "ghost", "trash-2")}</div>
			</div>`
			)
			.join("");
		this.$content.html(
			this.card(
				__("Remembered"),
				rows || this.empty(__("Nothing yet."), __("When you tell OneAI to remember something, it is listed here.")),
				__("What you asked OneAI to keep in mind when it helps you. Only you see it.")
			)
		);
		this.$content.find("[data-forget]").on("click", async (event) => {
			const said = await frappe.xcall(Settings.API + "forget", { name: $(event.currentTarget).attr("data-forget") });
			this.$content.empty();
			this.draw_memory(said);
		});
	}

	// ---------------------------------------------------------------- the workspace

	draw_general(data) {
		const esc = frappe.utils.escape_html;
		const facts = [
			[__("Workspace"), data.name],
			[__("Company"), data.company],
			[__("Country"), data.country ? __(data.country) : ""],
			[__("Currency"), data.currency],
		]
			.filter(([, value]) => value)
			.map(([label, value]) => `<dt>${esc(label)}</dt><dd>${esc(value)}</dd>`)
			.join("");
		this.$content.append(this.card(null, `<dl class="os-facts">${facts}</dl>`, __("Set when the workspace was made. The currency cannot change once there are books.")));
		this.form(data);
	}

	draw_people(data) {
		const esc = frappe.utils.escape_html;
		const seats = data.seats ? __("{0} of {1} seats used", [data.used, data.seats]) : __("{0} people", [data.used]);
		const options = (value) =>
			data.levels.map((one) => `<option value="${esc(one.value)}" ${one.value === value ? "selected" : ""}>${esc(one.label)}</option>`).join("");
		const head = `<div class="os-people-row os-people-head"><div>${__("Person")}</div>${data.apps
			.map((app) => `<div class="os-people-app">${frappe.utils.icon(app.icon, "sm")}<span>${esc(app.name)}</span></div>`)
			.join("")}<div>${__("Administrator")}</div><div></div></div>`;
		const rows = data.people
			.map(
				(one) => `<div class="os-people-row ${one.enabled ? "" : "os-off"}" data-user="${esc(one.name)}">
				<div class="os-who">${frappe.ui.avatar.html({ label: one.full_name, image: one.user_image, size: "sm" })}
					<div><div class="os-row-title">${esc(one.full_name || one.name)}</div><div class="os-quiet">${esc(one.name)}</div></div></div>
				${data.apps
					.map(
						(app) => `<div><select class="form-control input-xs" data-app="${esc(app.name)}" ${one.enabled ? "" : "disabled"}>${options(one.access[app.name])}</select></div>`
					)
					.join("")}
				<div><input type="checkbox" data-admin ${one.admin ? "checked" : ""} ${one.enabled ? "" : "disabled"}></div>
				<div>${this.button(one.enabled ? __("Turn Off") : __("Turn On"), { "data-enable": one.enabled ? "0" : "1" }, "ghost")}</div>
			</div>`
			)
			.join("");
		this.$content.html(
			this.card(
				null,
				`<div class="os-row"><div class="os-row-main">${frappe.ui.badge.html({ label: seats, theme: "gray" })}</div>
				<div class="os-row-actions">${this.button(__("Invite"), { "data-invite": "1" }, "solid", "plus")}</div></div>
				<div class="os-people">${head}${rows}</div>`,
				__("Everybody has One, OneCloud, OneMail, OneTask and OneCalendar. Here you give each person the apps that are somebody's job.")
			)
		);
		const again = (said) => {
			this.$content.empty();
			this.draw_people(said);
		};
		this.$content.find("[data-app]").on("change", async (event) => {
			const $select = $(event.currentTarget);
			again(
				await frappe.xcall(Settings.API + "set_access", {
					user: $select.closest("[data-user]").attr("data-user"),
					app: $select.attr("data-app"),
					level: $select.val(),
				})
			);
			frappe.show_alert({ message: __("Saved."), indicator: "green" });
		});
		this.$content.find("[data-admin]").on("change", async (event) => {
			const $box = $(event.currentTarget);
			try {
				again(await frappe.xcall(Settings.API + "set_admin", { user: $box.closest("[data-user]").attr("data-user"), on: $box.is(":checked") ? 1 : 0 }));
			} catch (e) {
				$box.prop("checked", !$box.is(":checked"));
			}
		});
		this.$content.find("[data-enable]").on("click", async (event) => {
			const $button = $(event.currentTarget);
			again(await frappe.xcall(Settings.API + "set_enabled", { user: $button.closest("[data-user]").attr("data-user"), on: $button.attr("data-enable") }));
		});
		this.$content.find("[data-invite]").on("click", () => {
			const dialog = new frappe.ui.Dialog({
				title: __("Invite Somebody"),
				fields: [
					{ fieldname: "email", fieldtype: "Data", options: "Email", label: __("Email"), reqd: 1 },
					{ fieldname: "first_name", fieldtype: "Data", label: __("First Name"), reqd: 1 },
					{ fieldname: "last_name", fieldtype: "Data", label: __("Last Name") },
				],
				primary_action_label: __("Invite"),
				primary_action: async (values) => {
					again(await frappe.xcall(Settings.API + "invite", values));
					dialog.hide();
					frappe.show_alert({ message: __("Invited. They get a mail to set their password."), indicator: "green" });
				},
			});
			dialog.show();
		});
	}

	draw_plan(data) {
		const esc = frappe.utils.escape_html;
		const account = data.account || {};
		const gb = (bytes) => (bytes ? (bytes / 1e9).toFixed(bytes < 1e10 ? 1 : 0) : 0);
		const storage =
			account.storage_limit
				? frappe.ui.progress
						.html({
							label: __("Storage"),
							value: Math.min(100, Math.round((100 * (account.storage_bytes || 0)) / account.storage_limit)),
							hint: () => __("{0} GB of {1} GB", [gb(account.storage_bytes), gb(account.storage_limit)]),
							size: "md",
						})
				: "";
		const facts = [
			[__("Plan"), account.plan],
			[__("Status"), account.status ? __(account.status) : ""],
			[__("Seats"), account.seats ? __("{0} of {1} used", [data.used, account.seats]) : __("{0} used, no limit", [data.used])],
			[__("Days Left"), account.days_left ? String(account.days_left) : ""],
		]
			.filter(([, value]) => value)
			.map(([label, value]) => `<dt>${esc(label)}</dt><dd>${esc(value)}</dd>`)
			.join("");
		const credits = [
			[__("Credits"), format_number(account.credits_balance || 0, null, 0)],
			[__("Expiring"), account.credits_expiring ? __("{0} on {1}", [format_number(account.credits_expiring, null, 0), frappe.datetime.str_to_user(account.credits_expires_on)]) : ""],
		]
			.filter(([, value]) => value)
			.map(([label, value]) => `<dt>${esc(label)}</dt><dd>${esc(value)}</dd>`)
			.join("");
		this.$content.html(
			this.card(__("Plan"), `<dl class="os-facts">${facts}</dl>${storage ? `<div class="os-bar">${storage}</div>` : ""}`) +
				this.card(
					__("OneAI Credits"),
					`<dl class="os-facts">${credits}</dl><div class="os-quiet os-card-note">${esc(data.month || "")}</div>
					<div class="os-actions">${this.button(__("Buy Credits"), { "data-buy": "1" }, "solid", "credit-card")}${this.button(__("See What Used Them"), { "data-used": "1" }, "ghost")}</div>`
				)
		);
		this.$content.find("[data-used]").on("click", () => frappe.set_route("query-report", "AI Credits"));
		this.$content.find("[data-buy]").on("click", async () => {
			let packs = [];
			try {
				packs = await frappe.xcall("onedesk.one.account.credit_packs");
			} catch (e) {
				return;
			}
			if (!packs.length) return frappe.msgprint(__("There is nothing to buy just now."));
			const dialog = new frappe.ui.Dialog({
				title: __("Buy Credits"),
				fields: [
					{
						fieldname: "pack",
						fieldtype: "Select",
						label: __("Pack"),
						reqd: 1,
						options: packs.map((one) => ({ value: one.name, label: one.label || one.name })),
					},
				],
				primary_action_label: __("Continue to Payment"),
				primary_action: async (values) => {
					const said = await frappe.xcall("onedesk.one.account.buy_credits", { pack: values.pack });
					dialog.hide();
					if (said && said.url) window.open(said.url, "_blank");
				},
			});
			dialog.show();
		});
	}

	draw_domains(data) {
		const esc = frappe.utils.escape_html;
		const rows = (data.domains || [])
			.map((one) => {
				const status = one.status || "";
				const theme = status === "Active" ? "green" : status ? "amber" : "gray";
				return `<div class="os-row" data-domain="${esc(one.domain)}">
					<div class="os-row-main"><div class="os-row-title">${esc(one.domain)}</div><div class="os-row-sub">
						${status ? frappe.ui.badge.html({ label: __(status), theme }) : ""}
						${one.primary ? frappe.ui.badge.html({ label: __("Primary"), theme: "blue" }) : ""}
						${(one.provided || one.given) ? frappe.ui.badge.html({ label: __("Ours"), theme: "gray" }) : ""}
					</div>${one.said ? `<div class="os-quiet">${esc(one.said)}</div>` : ""}</div>
					<div class="os-row-actions">
						${!one.primary && status === "Active" ? this.button(__("Make Primary"), { "data-primary": "1" }, "ghost") : ""}
						${!(one.provided || one.given) ? this.button(__("Remove"), { "data-drop": "1" }, "ghost", null, "red") : ""}
					</div>
				</div>`;
			})
			.join("");
		this.$content.html(
			this.card(
				__("Addresses"),
				(rows || this.empty(__("No domains yet."))) +
					`<div class="os-actions">${this.button(__("Add a Domain"), { "data-add": "1" }, "solid", "plus")}${this.button(__("Check Again"), { "data-refresh": "1" }, "ghost", "refresh-cw")}</div>`,
				__("Where the workspace answers. The one we provide always works; your own is added once its DNS points here.")
			)
		);
		const again = (domains) => {
			this.$content.empty();
			this.draw_domains({ domains });
		};
		const of = (event) => $(event.currentTarget).closest("[data-domain]").attr("data-domain");
		this.$content.find("[data-primary]").on("click", async (event) => again(await frappe.xcall("onedesk.one.account.domain_primary", { domain: of(event) })));
		this.$content.find("[data-drop]").on("click", (event) => {
			const domain = of(event);
			frappe.confirm(__("Stop answering at {0}?", [domain]), async () => again(await frappe.xcall("onedesk.one.account.domain_drop", { domain })));
		});
		this.$content.find("[data-refresh]").on("click", async () => again(await frappe.xcall("onedesk.one.account.domains_refresh")));
		this.$content.find("[data-add]").on("click", () => {
			const dialog = new frappe.ui.Dialog({
				title: __("Add a Domain"),
				fields: [{ fieldname: "domain", fieldtype: "Data", label: __("Domain"), reqd: 1, description: __("For example office.example.com") }],
				primary_action_label: __("Add"),
				primary_action: async (values) => {
					await frappe.xcall("onedesk.one.account.domain_add", { domain: values.domain });
					dialog.hide();
					this.open("domains");
				},
			});
			dialog.show();
		});
	}

	draw_oneai(data) {
		const esc = frappe.utils.escape_html;
		const rows = (data.actions || [])
			.map(
				(one) => `<div class="os-row" data-action="${esc(one.name)}">
				<div class="os-row-main"><div class="os-row-title">${esc(one.label)}</div>${one.about ? `<div class="os-quiet">${esc(one.about)}</div>` : ""}</div>
				<div class="os-row-actions">${frappe.ui.badge.html({ label: one.model || __("Default"), theme: one.model ? "violet" : "gray" })}
				${this.button(__("Change"), { "data-change": "1" }, "ghost")}</div>
			</div>`
			)
			.join("");
		this.$content.html(
			this.card(
				__("What Runs on Which Model"),
				rows,
				__("Each thing OneAI does can run on a model you choose, and be told something more. Default is what One picked.")
			) +
				this.card(
					__("Knowledge"),
					`<div class="os-row"><div class="os-row-main">${esc(__("{0} notes OneAI reads before it answers", [data.knowledge || 0]))}</div>
				<div class="os-row-actions">${this.button(__("Open"), { "data-knowledge": "1" }, "ghost", "external-link")}</div></div>`
				)
		);
		this.$content.find("[data-knowledge]").on("click", () => frappe.set_route("List", "AI Knowledge"));
		this.$content.find("[data-change]").on("click", (event) => {
			const name = $(event.currentTarget).closest("[data-action]").attr("data-action");
			const one = data.actions.find((row) => row.name === name);
			if (one.setting) frappe.set_route("Form", "AI Action Setting", one.setting);
			else frappe.new_doc("AI Action Setting", { action: one.name });
		});
	}

	draw_intake(data) {
		this.form(data, { before: data.month ? `<div class="os-card-note">${frappe.ui.badge.html({ label: data.month, theme: "violet" })}</div>` : "" });
	}

	draw_holidays(data) {
		const esc = frappe.utils.escape_html;
		const coming = (data.coming || [])
			.map((one) => `<div class="os-row"><div class="os-row-main">${esc(one.what || "")}</div><div class="os-quiet">${frappe.datetime.str_to_user(one.date)}</div></div>`)
			.join("");
		const $card = $(
			this.card(
				__("The Workspace's Holidays"),
				`<div class="os-form"></div><div class="os-actions"></div><div class="os-card-title os-sub-title">${__("Coming Up")}</div>${
					coming || this.empty(__("None in the list."))
				}`,
				__("Days nobody works. Deadlines, leave and check-ins count around them.")
			)
		).appendTo(this.$content);
		this.group = new frappe.ui.FieldGroup({
			fields: [{ fieldname: "holiday_list", fieldtype: "Select", label: __("Holiday List"), options: ["", ...(data.lists || [])], default: data.chosen }],
			body: $card.find(".os-form")[0],
		});
		this.group.make();
		$card.find(".os-actions").html(
			this.button(__("Save"), { "data-save": "1" }, "solid") +
				(data.chosen ? this.button(__("Open the List"), { "data-open": "1" }, "ghost", "external-link") : "") +
				this.button(__("New List"), { "data-new": "1" }, "ghost", "plus")
		);
		$card.find("[data-save]").on("click", () => this.save(this.group.get_values(true)));
		$card.find("[data-open]").on("click", () => frappe.set_route("Form", "Holiday List", data.chosen));
		$card.find("[data-new]").on("click", () => frappe.new_doc("Holiday List"));
	}
};
