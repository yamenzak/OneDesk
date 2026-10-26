// AccountCenter (docs/ONE.md): your own account and the workspace's, on the
// settings dialog (onedesk.CENTERS.account). For everybody, Yours: Profile
// and Sign-in; for administrators, Workspace: People, Devices, Plan and
// Credits, and Domains. Each section is an Editor (shell.js) whose page is
// its panel, so a form is saved, refused when somebody saved first, and
// heard when it changes, as anywhere else in One.
frappe.provide("onedesk.account_center");

// What an Editor uses of a page, kept by the panel's header instead: the
// title's indicator, the primary action and the buttons beside it. A
// dialog is its own place, so there are no breadcrumbs.
onedesk.account_center.page = (panel) => {
	const $actions = () => panel.$header.find(".settings-dialog-panel-actions");
	const $title = () => panel.$header.find(".settings-dialog-panel-title");
	return {
		wrapper: [{}],
		set_indicator(label, colour) {
			this.clear_indicator();
			$title().append(`<span class="one-account-status">${frappe.ui.badge.html({ label, theme: colour })}</span>`);
		},
		clear_indicator() {
			$title().find(".one-account-status").remove();
		},
		set_primary_action(label, click, icon) {
			this.clear_primary_action();
			$(frappe.ui.button.html({ label, icon, variant: "solid" })).addClass("one-account-primary").on("click", click).appendTo($actions());
			panel.$header.removeClass("hide");
		},
		clear_primary_action() {
			$actions().find(".one-account-primary").remove();
		},
		// A group's actions are one menu named for it, and the rest share a
		// menu of their own, so the header keeps to a few buttons.
		add_inner_button(label, action, group = null) {
			const name = group || "more";
			let $menu = $actions().find(`.one-account-inner[data-group="${CSS.escape(name)}"]`);
			if (!$menu.length) {
				$menu = $(`<div class="dropdown one-account-inner"><div class="dropdown-menu dropdown-menu-right"></div></div>`)
					.attr("data-group", name)
					.prependTo($actions());
				$(
					frappe.ui.button.html({
						label: group || "",
						icon: group ? null : "ellipsis",
						variant: "subtle",
						attrs: { "data-toggle": "dropdown", "aria-label": group || __("More") },
					})
				).prependTo($menu);
			}
			$(`<a class="dropdown-item" href="#"></a>`)
				.text(label)
				.on("click", (event) => {
					event.preventDefault();
					action();
				})
				.appendTo($menu.find(".dropdown-menu"));
			panel.$header.removeClass("hide");
		},
		clear_inner_toolbar() {
			$actions().find(".one-account-inner").remove();
		},
		set_breadcrumbs() {},
	};
};

onedesk.AccountSection = class AccountSection extends onedesk.shell.Editor {
	static API = "onedesk.one_account.center.";

	constructor(panel, key) {
		super(onedesk.account_center.page(panel));
		this.panel = panel;
		this.key = key;
		const heard = (event, key) =>
			frappe.realtime.on(event, () => this.key === key && this.$content && this.$content.is(":visible") && this.refresh());
		heard("one_privacy", "profile");
		heard("one_closing", "plan");
		heard("one_domains", "domains");
	}

	async open(key = this.key, { record = null } = {}) {
		this.key = key;
		this.record = record;
		// OneAI is told which section the reader is on (oneai.js `where`).
		onedesk.centers.here = { page: "account", section: key, record: record || "", label: "AccountCenter" };
		this.panel.set_header(this.panel.item);
		this.unsaved();
		this.$content = $(`<div class="one-shell-body one-account-body" data-tour="account-section">${onedesk.shell.quiet(__("Loading…"))}</div>`).appendTo(
			this.panel.body.empty()
		);
		try {
			this.data = await frappe.xcall(AccountSection.API + "load", { section: key, record });
		} catch (e) {
			this.$content.html(frappe.ui.alert.html({ title: __("Could Not Open This"), theme: "red" }));
			return;
		}
		this.$content.empty();
		this.hear(this.data.opened);
		this.links();
		this[`draw_${key}`](this.data);
	}

	saver(values) {
		return { method: AccountSection.API + "save", args: { section: this.key, values, record: this.record } };
	}

	redraw(said) {
		if (this.trailed) {
			this.unsaved();
			this.panel.set_header(this.panel.item);
			this.$content = $(`<div class="one-shell-body one-account-body" data-tour="account-section"></div>`).appendTo(this.panel.body.empty());
			this.links();
		}
		this[`draw_${this.key}`](said);
	}

	refresh() {
		this.open(this.key, { record: this.record });
	}

	// One record of a section, such as a person in People: its name heads the
	// panel, with Back to the section before it.
	as_record(record) {
		this.trailed = true;
		this.status = record.status || null;
		this.panel.set_header({ title: record.title });
		onedesk.module_settings.kit
			.button({ variant: "ghost", icon: "arrow-left", title: __("Back"), attrs: { "aria-label": __("Back") } })
			.addClass("one-set-back")
			.on("click", () => this.open(this.key))
			.prependTo(this.panel.$header.find(".settings-dialog-panel-title"));
		this.$content = onedesk.shell.record(this.$content, { ...record, parent: null, page: this.page });
		return this.$content;
	}

	// A link to another section of the centre (#people) opens its tab, and a
	// link anywhere else in One closes the centre first.
	links() {
		this.$content.on("click", 'a[href^="#"]', (event) => {
			event.preventDefault();
			this.panel.dialog.activate($(event.currentTarget).attr("href").slice(1));
		});
		this.$content.on("click", 'a[href^="/desk"]', () => this.panel.dialog.hide());
	}

	// Going somewhere else in One closes the centre first.
	leave(go) {
		this.panel.dialog.hide();
		go();
	}

	draw_profile(data) {
		const esc = frappe.utils.escape_html;
		const image = data.values.user_image;
		const employee = data.employee;
		const job = employee ? employee.work.filter((one) => ["designation", "department"].includes(one.fieldname)).map((one) => one.value) : [];
		const check = onedesk.oneai.button(
			__("Check My Profile"),
			__("Look at my profile and my employee record, if I have one. What is empty or looks out of date, and what is each of those used for?")
		);
		const who = `<div class="os-who os-who-large">
			<button class="btn-reset os-photo" data-photo="1" title="${esc(__("Change Photo"))}">
				${frappe.ui.avatar.html({ label: data.full_name, image, size: "3xl" })}
				<span class="os-photo-edit">${frappe.utils.icon("camera", "sm")}</span>
			</button>
			<div class="os-who-text">
				<div class="os-who-name">${esc(data.full_name || "")}</div>
				<div class="one-shell-quiet">${[data.email, ...job].map(esc).join(" · ")}</div>
				<div class="os-who-actions">${onedesk.shell.button(image ? __("Change Photo") : __("Add Photo"), { "data-photo": "1" }, "ghost")}${
					image ? onedesk.shell.button(__("Remove Photo"), { "data-unphoto": "1" }, "ghost") : ""
				}${check}</div>
			</div>
		</div>`;
		const facts = (list) =>
			`<dl class="os-facts">${list.map((one) => `<dt>${esc(one.label)}</dt><dd>${esc(String(one.value))}</dd>`).join("")}</dl>`;
		const bio = onedesk.oneai.button(
			__("Write With OneAI"),
			__("Write a short bio for my profile from my job, my department and what I work on, and suggest it as a change to my profile I can approve.")
		);
		const rows = [
			["first_name", "last_name"],
			["gender", "birth_date"],
			["mobile_no", "location"],
			["bio", ""],
			{ html: `<div class="one-shell-actions os-under-field">${bio}</div>` },
			{ heading: __("Language and Time") },
			["language", "time_zone"],
		];
		if (employee) {
			rows.push(
				{ heading: __("Employment"), note: __("Managed by HR.") },
				{ html: facts(employee.work) },
				{ heading: __("Address") },
				["current_address", "permanent_address"],
				["personal_email", ""],
				{ heading: __("Emergency Contact") },
				["person_to_be_contacted", "relation", "emergency_phone_number"],
				{ heading: __("Personal Details"), note: __("Only you and HR see these.") },
				["marital_status", "blood_group"]
			);
			if (employee.bank.length) rows.push({ heading: __("Bank Details"), note: __("Only HR can change this.") }, { html: facts(employee.bank) });
		}
		rows.push(
			{
				heading: __("Your Data"),
			},
			{ html: this.your_data(data.privacy) }
		);
		const $card = this.form(
			{ ...data, fields: [...data.fields.filter((one) => one.fieldname !== "user_image"), ...(employee ? employee.fields : [])] },
			{ before: who, rows }
		);
		$card.find(".os-photo .es-avatar__fallback").text(frappe.get_abbr(data.full_name || ""));
		const photo = (user_image) => this.save({ ...this.values(), user_image });
		$card.find("[data-photo]").on("click", () => {
			new frappe.ui.FileUploader({
				doctype: "User",
				docname: frappe.session.user,
				fieldname: "user_image",
				restrictions: { allowed_file_types: ["image/*"] },
				make_attachments_public: true,
				on_success: (file) => photo(file.file_url),
			});
		});
		$card.find("[data-unphoto]").on("click", () => photo(""));
		this.your_data_actions($card, data.privacy);
	}

	your_data(state) {
		const when = (on) => frappe.datetime.comment_when(on);
		const esc = frappe.utils.escape_html;
		const copy = state.copy;
		const lines = [];
		if (copy && copy.status === "Waiting") lines.push(__("You requested a copy {0}. It's waiting for approval.", [when(copy.on)]));
		else if (copy && copy.status === "Gathering") lines.push(__("Your copy is being prepared. You'll be notified when it's ready."));
		else if (copy && copy.ready) lines.push(__("Your copy from {0} is ready.", [when(copy.on)]) + (copy.withheld ? " " + __("Withheld: {0}", [esc(copy.withheld)]) : ""));
		if (state.deletion && state.deletion.status === "On Hold") lines.push(__("Account deletion is on hold. {0}", [esc(state.deletion.why || "")]));
		else if (state.deletion && state.deletion.status === "Pending Verification") lines.push(__("Check your email to confirm deleting your account."));
		else if (state.deletion) lines.push(__("You requested account deletion {0}. It's waiting for approval.", [when(state.deletion.on)]));
		const asking = copy && ["Waiting", "Gathering"].includes(copy.status);
		const buttons = [
			copy && copy.ready
				? onedesk.shell.button(__("Download My Data"), { "data-download": copy.url }, "subtle", "download")
				: "",
			asking ? "" : onedesk.shell.button(copy && copy.ready ? __("Request New Copy") : __("Request My Data"), { "data-copy": "1" }, "subtle", "file-down"),
			state.deletion
				? onedesk.shell.button(__("Cancel Deletion"), { "data-withdraw": "1" }, "ghost", "undo-2")
				: onedesk.shell.button(__("Delete My Account"), { "data-delete": "1" }, "ghost", "user-x"),
		];
		return `${lines.map((one) => `<p class="one-shell-quiet">${one}</p>`).join("")}<div class="one-shell-actions">${buttons.join("")}</div>`;
	}

	your_data_actions($card, state) {
		$card.find("[data-download]").on("click", (event) => window.open(encodeURI($(event.currentTarget).attr("data-download")), "_blank"));
		$card.find("[data-copy]").on("click", async () => {
			await frappe.xcall("onedesk.one.privacy_copy.ask");
			frappe.show_alert({ message: __("Requested. You'll be notified when it's ready."), indicator: "green" });
			this.refresh();
		});
		$card.find("[data-withdraw]").on("click", async () => {
			await frappe.xcall("onedesk.one.privacy.withdraw");
			frappe.show_alert({ message: __("Deletion cancelled"), indicator: "green" });
			this.refresh();
		});
		$card.find("[data-delete]").on("click", () => {
			const dialog = new frappe.ui.Dialog({
				title: __("Delete My Account"),
				fields: [
					{
						fieldtype: "HTML",
						options: `<p>${__("An administrator reviews the request. Then you're signed out, and your OneAI chats, memory, notifications and devices are deleted.")} ${__("Records the workspace keeps, such as invoices and tasks, stay without your name and address. HR keeps your employee record, if you have one.")}</p><p>${__("This can't be undone. Request a copy of your data first if you need one.")}</p>`,
					},
					state.password
						? { fieldname: "password", fieldtype: "Password", label: __("Your Password"), reqd: 1 }
						: { fieldtype: "HTML", options: `<p>${__("You'll get an email with a link to confirm.")}</p>` },
				],
				primary_action_label: __("Request Deletion"),
				primary_action: async ({ password }) => {
					await frappe.xcall("onedesk.one.privacy.ask_to_delete", { password });
					dialog.hide();
					frappe.show_alert({
						message: state.password ? __("Requested. You'll be notified of the decision.") : __("Check your email to confirm."),
						indicator: "orange",
					});
					this.refresh();
				},
			});
			dialog.show();
		});
	}

	draw_signin(data) {
		const esc = frappe.utils.escape_html;
		const when = (value) => (value ? frappe.datetime.prettyDate(value) : "");
		const safe = onedesk.oneai.button(
			__("Is My Account Safe?"),
			__("Is my account safe? Look at how I sign in and where I am signed in, and tell me what to do.")
		);
		const intro = `<div class="one-shell-section"><div class="os-notify-intro">${safe}</div></div>`;
		const row = (title, quiet, actions = "") => onedesk.shell.row({ title, quiet, actions });

		const password = onedesk.shell.section(
			__("Password and Two-Factor"),
			row(
				esc(__("Password")),
				esc(data.password_changed ? __("Changed {0}", [when(data.password_changed)]) : __("Never changed")),
				onedesk.shell.button(__("Change Password"), { "data-password": "1" }, "subtle", "key-round")
			) +
				row(
					esc(__("Two-Factor Authentication")),
					esc(
						data.two_factor
							? __("Uses {0}. Set by your workspace.", [__(data.two_factor_method || "OTP App")])
							: __("Set by your workspace.")
					),
					frappe.ui.badge.html({ label: data.two_factor ? __("On") : __("Off"), theme: data.two_factor ? "green" : "gray" })
				)
		);

		const passkey =
			data.passkey || data.passkey_signs_in || data.passkey_clocks
				? onedesk.shell.section(
						__("Passkey"),
						row(
							frappe.ui.badge.html({ label: data.passkey ? __("Registered") : __("Not registered"), theme: data.passkey ? "green" : "gray" }),
							esc((data.passkeys || []).map((one) => one.label).join(" · ")),
							data.add_here || !data.passkey
								? onedesk.shell.button(__("Register This Device"), { "data-passkey": "1" }, "subtle", "fingerprint")
								: data.passkey_clocks
								? ""
								: onedesk.shell.button(__("Remove"), { "data-passkey-remove": "1" }, "ghost", "trash-2")
						),
						data.passkey_clocks
							? data.passkey_signs_in
								? __("Signs you in without a password, and checks you in.")
								: __("Used to check in.")
							: __("Signs you in with your face, fingerprint or screen lock instead of a password.")
				  )
				: "";

		this.$content.html(
			intro + password + passkey + `<div class="one-shell-section" data-list="places"></div><div class="one-shell-section" data-list="recent"></div>`
		);
		onedesk.shell.table(this.$content.find('[data-list="places"]'), {
			title: __("Active Sessions"),
			rows: data.sessions,
			page_size: 10,
			icon: "monitor-smartphone",
			actions:
				data.sessions.length > 1 ? onedesk.shell.button(__("Sign Out Other Sessions"), { "data-elsewhere": "1" }, "ghost", "log-out") : "",
			columns: AccountSection.session_columns((one) =>
				one.here ? frappe.ui.badge.html({ label: __("This Device"), theme: "blue" }) : onedesk.shell.button(__("Sign Out"), { "data-sign-out": one.key }, "ghost", "log-out")
			),
		});
		if (data.recent.length) {
			onedesk.shell.table(this.$content.find('[data-list="recent"]'), {
				title: __("Recent Sign-ins"),
				rows: data.recent,
				columns: AccountSection.signin_columns(),
			});
		}
		this.$content.find("[data-password]").on("click", () => {
			const dialog = new frappe.ui.Dialog({
				title: __("Change Password"),
				fields: [
					{ fieldname: "old_password", fieldtype: "Password", label: __("Current Password"), reqd: 1 },
					{ fieldname: "new_password", fieldtype: "Password", label: __("New Password"), reqd: 1 },
					{
						fieldname: "elsewhere",
						fieldtype: "Switch",
						label: __("Sign Out Other Sessions"),
						description: __("Signs you out on every other device."),
						default: 1,
					},
				],
				primary_action_label: __("Change Password"),
				primary_action: async (values) => {
					await frappe.xcall("frappe.core.doctype.user.user.update_password", {
						old_password: values.old_password,
						new_password: values.new_password,
						logout_all_sessions: values.elsewhere ? 1 : 0,
					});
					dialog.hide();
					frappe.show_alert({ message: __("Password changed"), indicator: "green" });
					this.open("signin");
				},
			});
			dialog.show();
		});
		this.$content.find("[data-passkey]").on("click", async () => {
			await onedesk.passkey.register();
			this.open("signin");
		});
		this.$content.find("[data-passkey-remove]").on("click", () =>
			frappe.confirm(__("Remove your passkey?"), async () => {
				await frappe.xcall("onedesk.one_hr.passkey.remove");
				frappe.show_alert({ message: __("Passkey removed"), indicator: "green" });
				this.open("signin");
			})
		);
		this.$content.on("click", "[data-sign-out]", async (event) => {
			await frappe.xcall("onedesk.one_account.signin.sign_out", { key_of: $(event.currentTarget).attr("data-sign-out") });
			frappe.show_alert({ message: __("Signed out"), indicator: "green" });
			this.open("signin");
		});
		this.$content.on("click", "[data-elsewhere]", () =>
			frappe.confirm(__("Sign out other sessions? You'll be signed out on every other device."), async () => {
				await frappe.xcall(AccountSection.API + "sign_out_elsewhere");
				frappe.show_alert({ message: __("Other sessions signed out"), indicator: "green" });
				this.open("signin");
			})
		);
	}

	static session_columns(last = null) {
		const esc = frappe.utils.escape_html;
		return [
			{
				label: __("Device"),
				render: (one) =>
					esc(one.device) +
					(one.count > 1 ? ` <span class="one-shell-quiet">${esc(__("{0} sessions", [one.count]))}</span>` : ""),
			},
			{ label: __("Address"), fieldname: "address" },
			{ label: __("Last Used"), render: (one) => `<span class="one-shell-quiet">${esc(frappe.datetime.prettyDate(one.last_used))}</span>` },
			...(last ? [{ label: "", render: last }] : []),
		];
	}

	static signin_columns() {
		const esc = frappe.utils.escape_html;
		return [
			{ label: __("When"), render: (one) => esc(frappe.datetime.str_to_user(one.on)) },
			{ label: __("Address"), fieldname: "address" },
			{
				label: __("Result"),
				render: (one) => frappe.ui.badge.html({ label: one.failed ? __("Failed") : __("Signed in"), theme: one.failed ? "red" : "green" }),
			},
		];
	}

	async draw_people(data) {
		if (data.person) return this.draw_person(data);
		const esc = frappe.utils.escape_html;
		const seats = data.seats ? __("{0} of {1} seats used.", [data.used, data.seats]) : __("{0} people.", [data.used]);
		const levels = Object.fromEntries(data.levels.map((one) => [one.value, one.label]));
		this.$content.html(
			`<div class="one-shell-section"><div class="one-shell-quiet">${esc(
				__("Everyone has One, OneCloud, OneMail, OneTask and OneCalendar.")
			)} ${esc(seats)}</div></div>
			<div class="one-shell-section os-people-list" data-list="people"></div>`
		);
		this.page.set_primary_action(__("Invite People"), () => this.invite_dialog(data), "plus");
		onedesk.shell.table(this.$content.find('[data-list="people"]'), {
			title: __("People"),
			rows: data.people.map((one) => ({ ...one, search: `${one.full_name} ${one.name}` })),
			icon: "users",
			empty: __("No people"),
			none: __("No matching people"),
			open: (one) => this.open("people", { record: one.name }),
			columns: [
				{
					label: __("Person"),
					render: (one) => `<div class="os-person">${frappe.ui.avatar.html({ label: one.full_name, image: one.user_image, size: "sm" })}
						<div><div class="os-person-name">${esc(one.full_name || one.name)}${one.enabled ? "" : ` ${frappe.ui.badge.html({ label: __("Disabled"), theme: "gray" })}`}</div>
						<div class="one-shell-quiet">${esc(one.name)}</div></div></div>`,
				},
				{
					label: __("Apps"),
					render: (one) => {
						const said = (level) => levels[level] || level;
						const theme = (level) => (level === "Manager" ? "blue" : level === "User" ? "gray" : "purple");
						const held = new Set(data.apps.map((app) => one.access[app.name]));
						if (held.size === 1 && !held.has("None") && levels[[...held][0]]) {
							const [level] = held;
							return frappe.ui.badge.html({ label: __("All Apps · {0}", [said(level)]), theme: theme(level) });
						}
						return (
							data.apps
								.filter((app) => one.access[app.name] && one.access[app.name] !== "None")
								.map((app) => frappe.ui.badge.html({ label: `${app.name} · ${said(one.access[app.name])}`, theme: theme(one.access[app.name]) }))
								.join(" ") || `<span class="one-shell-quiet">${esc(__("Standard Apps"))}</span>`
						);
					},
				},
				{ label: __("Administrator"), render: (one) => (one.admin ? frappe.ui.badge.html({ label: __("Administrator"), theme: "orange" }) : "") },
				{
					label: __("Last Active"),
					render: (one) => `<span class="one-shell-quiet">${esc(one.last_active ? frappe.datetime.prettyDate(one.last_active) : __("Never"))}</span>`,
				},
			],
		});
	}

	draw_person(data) {
		const esc = frappe.utils.escape_html;
		const one = data.person;
		const name = one.full_name || one.name;
		const done = (message) => frappe.show_alert({ message, indicator: "green" });
		const actions = [];
		if (!one.me && one.enabled && one.joined) {
			actions.push(
				{
					label: __("Sign Out Everywhere"),
					group: __("Actions"),
					action: () =>
						frappe.confirm(__("Sign {0} out on every device?", [esc(name)]), async () => {
							await frappe.xcall(AccountSection.API + "sign_out_everywhere", { user: one.name });
							this.refresh({ fresh: true });
							done(__("Signed out everywhere."));
						}),
				},
				{
					label: __("Send Password Reset"),
					group: __("Actions"),
					action: async () => {
						await frappe.xcall(AccountSection.API + "send_reset", { user: one.name });
						done(__("Password reset sent"));
					},
				}
			);
		}
		if (!one.me && one.enabled && !one.joined) {
			actions.push({
				label: __("Resend Invite"),
				group: __("Actions"),
				action: async () => {
					await frappe.xcall(AccountSection.API + "invite_again", { user: one.name });
					done(__("Invite sent. The old link no longer works."));
				},
			});
		}
		if (!one.me) {
			actions.push(
				one.enabled
					? {
							label: __("Disable"),
							group: __("Actions"),
							action: () =>
								frappe.confirm(__("Disable {0}? They're signed out and can't sign in. Their records stay.", [esc(name)]), async () => {
									await frappe.xcall(AccountSection.API + "set_enabled", { user: one.name, on: 0 });
									this.refresh({ fresh: true });
								}),
					  }
					: {
							label: __("Enable"),
							group: __("Actions"),
							action: async () => {
								await frappe.xcall(AccountSection.API + "set_enabled", { user: one.name, on: 1 });
								this.refresh({ fresh: true });
							},
					  }
			);
		}
		const status = !one.enabled
			? { label: __("Disabled"), colour: "gray" }
			: !one.joined
			? { label: __("Invited"), colour: "blue" }
			: data.values.admin
			? { label: __("Administrator"), colour: "orange" }
			: { label: __("Active"), colour: "green" };
		this.as_record({
			title: name,
			status,
			side: onedesk.shell.side({
				image: one.user_image,
				initials: frappe.get_abbr(name),
				title: name,
				sub: esc(one.name),
				groups: [
					{
						label: __("Links"),
						html: one.employee ? `<a class="one-record-link" href="${frappe.utils.get_form_link("Employee", one.employee)}">${esc(__("Employee Record"))}</a>` : "",
					},
				],
				meta: [one.last_active ? __("Last active {0}", [frappe.datetime.prettyDate(one.last_active)]) : one.joined ? __("Not active recently") : __("Not joined yet")],
			}),
			actions,
		});
		const apps = data.apps.map((app) => `app_${app.icon}`);
		const rows = [
			{ heading: __("Apps"), note: __("Everyone has One, OneCloud, OneMail, OneTask and OneCalendar.") },
			["profile", ""],
			...onedesk.shell.pairs(apps),
			{ stack: ["admin"] },
			{
				heading: __("User Permissions"),
			},
			{ html: '<div data-list="holds"></div>' },
			{ heading: __("Active Sessions") },
			{
				html: one.me
					? `<div class="one-shell-quiet">${esc(__("Your sessions are on the Sign-in page."))}</div>`
					: '<div data-list="places"></div>',
			},
			...(one.recent.length ? [{ heading: __("Recent Sign-ins") }, { html: '<div data-list="recent"></div>' }] : []),
		];
		const $card = this.form(data, { rows });
		onedesk.shell.marks($card, data.apps);
		const picked = this.group.get_field("profile");
		picked &&
			picked.$input.on("change", () => {
				const levels = data.profiles[picked.get_value()];
				if (levels) for (const app of data.apps) this.group.set_value(`app_${app.icon}`, levels[app.name] || "None");
			});
		this.draw_holds($card.find('[data-list="holds"]'), one);
		if (!one.me) {
			onedesk.shell.table($card.find('[data-list="places"]'), {
				rows: one.sessions,
				page_size: 10,
				icon: "monitor-smartphone",
				empty: one.joined ? __("No active sessions") : __("Not joined yet"),
				columns: AccountSection.session_columns(),
			});
		}
		onedesk.shell.table($card.find('[data-list="recent"]'), { rows: one.recent, columns: AccountSection.signin_columns() });
	}

	draw_holds($into, one) {
		const esc = frappe.utils.escape_html;
		const again = () => this.refresh({ fresh: true });
		const add = () => {
			const dialog = new frappe.ui.Dialog({
				title: __("Add User Permission"),
				fields: [
					{ fieldname: "allow", fieldtype: "Select", label: __("Record Type"), reqd: 1, options: one.kinds },
					{ fieldname: "for_value", fieldtype: "Dynamic Link", options: "allow", label: __("Record"), reqd: 1 },
					{
						fieldname: "applicable_for",
						fieldtype: "Link",
						options: "DocType",
						label: __("Applicable For"),
						description: __("Leave empty to apply everywhere."),
					},
				],
				primary_action_label: __("Add"),
				primary_action: async (values) => {
					await frappe.xcall("onedesk.one.access.hold", { user: one.name, ...values });
					dialog.hide();
					again();
				},
			});
			dialog.show();
		};
		onedesk.shell.table($into, {
			rows: one.holds,
			icon: "eye",
			empty: __("No user permissions"),
			actions: $(onedesk.shell.button(__("Add User Permission"), {}, "subtle", "plus")).on("click", add),
			columns: [
				{ label: __("Record Type"), render: (row) => esc(__(row.allow)) },
				{ label: __("Record"), render: (row) => esc(row.for_value) },
				{ label: __("Applicable For"), render: (row) => esc(row.applicable_for ? __(row.applicable_for) : __("All")) },
				{
					type: "actions",
					actions: [
						{
							label: __("Remove"),
							icon: "x",
							action: (row) => frappe.xcall("onedesk.one.access.let_go", { name: row.name }).then(again),
						},
					],
				},
			],
		});
	}

	invite_dialog(data) {
		const dialog = new frappe.ui.Dialog({
			title: __("Invite People"),
			fields: [
				{ fieldname: "email", fieldtype: "Data", options: "Email", label: __("Email"), reqd: 1 },
				{ fieldtype: "Column Break" },
				{ fieldname: "first_name", fieldtype: "Data", label: __("First Name"), reqd: 1 },
				{ fieldname: "last_name", fieldtype: "Data", label: __("Last Name") },
				{ fieldtype: "Section Break", label: __("Apps"), description: __("Everyone has One, OneCloud, OneMail, OneTask and OneCalendar.") },
				...onedesk.shell.two_columns(data.apps, (app) => ({ fieldname: `app_${app.icon}`, fieldtype: "Select", label: app.name, options: app.levels, default: "None" })),
			],
			primary_action_label: __("Invite"),
			primary_action: async (values) => {
				const access = Object.fromEntries(data.apps.map((app) => [app.name, values[`app_${app.icon}`]]));
				const said = await frappe.xcall(AccountSection.API + "invite", { email: values.email, first_name: values.first_name, last_name: values.last_name, access });
				dialog.hide();
				frappe.show_alert({ message: __("Invitation sent"), indicator: "green" });
				this.data = said;
				this.$content.empty();
				this.draw_people(said);
			},
		});
		onedesk.shell.marks(dialog.$wrapper, data.apps);
		dialog.show();
	}

	draw_plan(data) {
		const esc = frappe.utils.escape_html;
		const account = data.account || {};
		const number = (value) => format_number(value || 0, null, 0);
		const money = (value) => format_currency(value || 0, account.plan_currency || "USD", 0);
		// Somebody who may only see the plan (OneAccount's Plan and Credits)
		// reads it; changing it, paying and closing are an administrator's.
		if (data.admin) this.page.set_primary_action(__("Change Plan"), () => this.change_plan(), "arrow-up-down");
		this.$content = onedesk.shell.record(this.$content, {
			page: this.page,
			status: data.state,
			side: onedesk.shell.side({
				initials: frappe.get_abbr(account.workspace_name || "One"),
				title: account.workspace_name || __("This Workspace"),
				sub: account.plan ? esc(__("{0} plan", [account.plan])) : "",
				groups: [
					{
						label: __("Links"),
						html: `<ul class="list-unstyled sidebar-menu">${[
							["#people", __("People")],
							["/desk/onecloud", __("OneCloud")],
							["/desk/query-report/AI Credits", __("Credit Usage")],
						]
							.map(([href, label]) => `<li><a class="one-record-link" href="${esc(href)}">${esc(label)}</a></li>`)
							.join("")}</ul>`,
					},
				],
				meta: [account.last_heard ? __("As of {0}", [frappe.datetime.prettyDate(account.last_heard)]) : __("Not synced yet")],
			}),
			actions: data.admin
				? [
						{ label: __("Storage, Database or Seats"), action: () => this.add_to_plan(data), group: __("Add") },
						{ label: __("OneAI Credits"), action: () => this.buy_credits(), group: __("Add") },
						{ label: __("Payment Method"), action: () => this.payment_portal() },
						{ label: __("Billing Owner"), action: () => this.move_billing(account) },
						{ label: __("Check Again"), action: () => this.check_again() },
				  ]
				: [],
		});
		const facts = (rows) =>
			`<dl class="os-facts">${rows
				.filter(([, value]) => value)
				.map(([label, value]) => `<dt>${esc(label)}</dt><dd>${value}</dd>`)
				.join("")}</dl>`;
		const seats = account.seats ? __("{0} of {1} used", [data.used, account.seats]) : __("{0} used, no limit", [data.used]);
		const bar = (label, used, limit, said) => {
			if (!limit) return "";
			const share = (100 * (used || 0)) / limit;
			return frappe.ui.progress.html({
				label,
				value: Math.min(100, Math.round(share)),
				hint: () => __("{0} of {1}", [said.used, said.limit]),
				size: "md",
				css_class: share > 100 ? "os-bar-over" : share >= 90 ? "os-bar-near" : "",
			});
		};
		const storage = bar(__("Storage"), account.storage_bytes, account.storage_limit, data.storage);
		const database = bar(__("Database"), account.database_bytes, account.database_limit, data.database);
		const add_ons = (data.add_ons || []).length;
		const expiring = account.credits_expiring
			? esc(__("{0} on {1}", [number(account.credits_expiring), frappe.datetime.str_to_user(account.credits_expires_on)]))
			: "";
		const closing = data.closing || {};
		const closes = closing.closing_on
			? __("The workspace closes on {0} and is deleted on {1}.", [
					frappe.datetime.str_to_user(closing.closing_on),
					closing.deleted_on ? frappe.datetime.str_to_user(closing.deleted_on) : __("a later date"),
			  ])
			: "";
		this.$content.html(
			(closes ? `<div class="one-record-news">${frappe.ui.alert.html({ title: closes, theme: "red" })}</div>` : "") +
			(data.said ? `<div class="one-record-news">${frappe.ui.alert.html({ title: data.said.text, theme: data.said.colour === "red" ? "red" : "yellow" })}</div>` : "") +
				onedesk.shell.section(
					__("Plan"),
					facts([
						[__("Plan"), esc(account.plan || "")],
						[__("Monthly"), account.monthly ? esc(money(account.monthly)) : ""],
						[__("Billed To"), esc(account.billed_to || "")],
						[__("Seats"), `<a href="#people">${esc(seats)}</a>`],
					]) +
						(storage ? `<a class="os-bar" href="/desk/onecloud">${storage}</a>` : "") +
						(database ? `<div class="os-bar">${database}</div>` : "") +
						(add_ons ? '<div class="os-add-ons" data-list="add-ons"></div>' : "")
				) +
				onedesk.shell.section(
					__("Invoices"),
					'<div data-list="invoices"><div class="one-shell-quiet">' + esc(__("Loading…")) + "</div></div>"
				) +
				onedesk.shell.section(
					__("OneAI Credits"),
					facts([
						[__("Balance"), esc(number(account.credits_balance))],
						[__("Reserved"), account.credits_held ? esc(number(account.credits_held)) : ""],
						[__("Used (Last 30 Days)"), account.credits_month ? esc(number(account.credits_month)) : ""],
						[__("Expiring"), expiring],
					]),
					__("Monthly credits are used first. Bought credits never expire.")
				) +
				onedesk.shell.section(
					__("Ledger"),
					data.ledger
						? '<div data-list="ledger"></div>'
						: `<div class="one-shell-quiet">${esc(data.linked ? __("Couldn't load the ledger.") : __("Not Connected Yet"))}</div>`,
					__("Last {0} days.", [data.ledger_days])
				) +
				(data.admin ? this.closing_section(closing) : "")
		);
		this.$content.find("[data-closing]").on("click", (event) => this.closing_act($(event.currentTarget).attr("data-closing"), closing));
		this.draw_invoices(this.$content.find('[data-list="invoices"]'));
		if (add_ons) {
			onedesk.shell.table(this.$content.find('[data-list="add-ons"]'), {
				title: __("Add-ons"),
				rows: data.add_ons,
				icon: "package",
				columns: [
					{ label: __("Add-on"), render: (one) => esc(one.quantity > 1 ? __("{0} × {1}", [one.quantity, one.label]) : one.label) },
					{ label: __("Monthly"), render: (one) => esc(money(one.amount * (one.quantity || 1))) },
					{
						label: "",
						render: (one) =>
							`<div class="one-shell-row-actions" data-add-on="${esc(one.offering)}">${onedesk.shell.button(
								one.quantity > 1 ? __("Remove One") : __("Remove"),
								{ "data-drop": "1" },
								"ghost"
							)}</div>`,
					},
				],
			});
		}
		this.$content.find('[data-list="add-ons"]').on("click", "[data-add-on] [data-drop]", (event) => {
			const key = $(event.currentTarget).closest("[data-add-on]").attr("data-add-on");
			const kept = Object.fromEntries((data.add_ons || []).map((one) => [one.offering, one.quantity]));
			const one = (data.add_ons || []).find((row) => row.offering === key);
			kept[key] = (kept[key] || 1) - 1;
			frappe.confirm(
				__("Remove one {0}? This saves {1} a month and removes what it adds.", [
					one ? one.label : key,
					money(one ? one.amount : 0),
				]),
				() => this.take(account.plan_key, kept)
			);
		});
		if (data.ledger) {
			const amount = (value, sign) =>
				value ? `<span class="${sign === "+" ? "text-success" : ""}">${sign}${esc(format_number(value, null, value < 10 ? 2 : 0))}</span>` : "";
			onedesk.shell.table(this.$content.find('[data-list="ledger"]'), {
				rows: data.ledger,
				page_size: 15,
				icon: "coins",
				empty: __("No transactions"),
				columns: [
					{ label: __("Date"), render: (one) => esc(frappe.datetime.str_to_user(one.on)) },
					{ label: __("Description"), fieldname: "what" },
					{ label: __("In"), render: (one) => amount(one.came, "+") },
					{ label: __("Out"), render: (one) => amount(one.went, "−") },
				],
				open: (one) => one.day && this.leave(() => frappe.set_route("query-report", "AI Credits", { from_date: one.day, to_date: one.day, by: "Person" })),
			});
		}
	}

	closing_section(closing) {
		const esc = frappe.utils.escape_html;
		if (!closing.is_payer) {
			return onedesk.shell.section(
				__("Closing the Workspace"),
				`<div class="one-shell-quiet">${esc(
					__("Only {0} can download or close the workspace.", [closing.payer || __("the billing owner")])
				)}</div>`
			);
		}
		const kept = closing.export || {};
		const download = {
			Preparing: __("Preparing. You'll be notified when it's ready."),
			Ready: __("Created {0}, {1}.", [frappe.datetime.prettyDate(kept.on), kept.size]),
			Failed: __("Couldn't create the download. Try again, or reply to any email from One."),
		}[kept.status] || __("One file with the database, every record as a spreadsheet, and all files.");
		const download_actions =
			kept.status === "Ready"
				? onedesk.shell.button(__("Download"), { "data-closing": "download" }, "solid", "download") +
				  onedesk.shell.button(__("Create Again"), { "data-closing": "prepare" }, "ghost")
				: kept.status === "Preparing"
				? ""
				: onedesk.shell.button(__("Create Download"), { "data-closing": "prepare" }, "subtle", "package");
		const close = closing.closing_on
			? onedesk.shell.row({
					title: esc(__("Closing on {0}", [frappe.datetime.str_to_user(closing.closing_on)])),
					sub: esc(__("Until then, everything works as usual.")),
					actions: onedesk.shell.button(__("Cancel Closing"), { "data-closing": "keep" }, "subtle"),
			  })
			: onedesk.shell.row({
					title: esc(__("Close Workspace")),
					sub: esc(
						__("The workspace keeps working for {0} days and everyone is notified. Then sign-in stops, and it's deleted a few weeks later.", [
							closing.notice_days,
						])
					),
					actions: onedesk.shell.button(__("Close Workspace"), { "data-closing": "close" }, "subtle", null, "red"),
			  });
		return onedesk.shell.section(
			__("Closing the Workspace"),
			onedesk.shell.row({ title: esc(__("Full Download")), sub: esc(download), actions: download_actions }) + close,
			__("Only the billing owner sees this.")
		);
	}

	async closing_act(what, closing) {
		if (what === "download") {
			window.open("/api/method/onedesk.one_account.closing.download");
			return;
		}
		if (what === "prepare") {
			await frappe.xcall("onedesk.one_account.closing.prepare");
			frappe.show_alert({ message: __("Creating the download. You'll be notified when it's ready."), indicator: "blue" });
			return this.refresh();
		}
		if (what === "keep") {
			await frappe.xcall("onedesk.one_account.closing.keep");
			frappe.show_alert({ message: __("Closing cancelled. Everyone is notified."), indicator: "green" });
			return this.refresh();
		}
		const kept = (closing.export || {}).status === "Ready";
		const dialog = new frappe.ui.Dialog({
			title: __("Close Workspace"),
			fields: [
				{
					fieldtype: "HTML",
					fieldname: "said",
					options: frappe.ui.alert.html({
						title: kept ? __("You have a full download.") : __("You haven't downloaded the workspace."),
						message: kept
							? __("Create it again if much has changed since.")
							: __("Download it first. Nothing can be exported after the workspace closes."),
						theme: kept ? "blue" : "yellow",
					}),
				},
				{
					fieldtype: "HTML",
					fieldname: "what",
					options: `<p class="text-muted">${frappe.utils.escape_html(
						[
							__("The workspace keeps working for {0} days and everyone is notified.", [closing.notice_days]),
							__("Then sign-in stops and the subscription ends. This month is not refunded."),
							__("The workspace and its files are deleted a few weeks later. You can cancel from this page until then."),
						].join(" ")
					)}</p>`,
				},
				{ fieldtype: "Password", fieldname: "password", label: __("Your Password"), reqd: 1 },
				{ fieldtype: "Check", fieldname: "sure", label: __("Delete Everything"), description: __("I understand everything in the workspace will be deleted."), reqd: 1 },
			],
			primary_action_label: __("Close Workspace"),
			primary_action: async (values) => {
				if (!values.sure) return frappe.msgprint(__("Confirm that you understand first."));
				await frappe.xcall("onedesk.one_account.closing.close", { password: values.password });
				dialog.hide();
				frappe.show_alert({ message: __("Workspace closing. Everyone is notified."), indicator: "orange" });
				this.refresh();
			},
		});
		frappe.ui.button.dress(dialog.get_primary_btn(), { label: __("Close Workspace"), variant: "solid", theme: "red" });
		dialog.show();
	}

	async draw_invoices($into) {
		const esc = frappe.utils.escape_html;
		let said;
		try {
			said = await frappe.xcall("onedesk.one_account.bills.invoices");
		} catch (e) {
			return $into.html(`<div class="one-shell-quiet">${esc(__("Couldn't load invoices."))}</div>`);
		}
		if (said.linked === false) return $into.html(`<div class="one-shell-quiet">${esc(__("Not Connected Yet"))}</div>`);
		const themes = { paid: "green", open: "orange", uncollectible: "red", void: "gray" };
		const states = { paid: __("Paid"), open: __("Due"), uncollectible: __("Unpaid"), void: __("Void") };
		const list = await onedesk.shell.table($into.empty(), {
			rows: said.invoices || [],
			page_size: 12,
			icon: "receipt",
			empty: __("No invoices"),
			columns: [
				{ label: __("Date"), render: (one) => esc(frappe.datetime.str_to_user(frappe.datetime.obj_to_str(new Date(one.created * 1000)))) },
				{ label: __("Number"), fieldname: "number" },
				{ label: __("Amount"), render: (one) => esc(format_currency(one.total, one.currency)) },
				{ label: __("Status"), render: (one) => frappe.ui.badge.html({ label: states[one.status] || one.status, theme: themes[one.status] || "gray" }) },
				{
					label: __("In OneBook"),
					render: (one) =>
						one.bill
							? `<a class="one-record-link" href="${esc(frappe.utils.get_form_link("Purchase Invoice", one.bill))}">${esc(one.bill)}</a>`
							: one.status === "paid"
							? onedesk.shell.button(__("Add to OneBook"), { "data-book": one.id }, "subtle")
							: "",
				},
				{ label: "", render: (one) => (one.pdf ? `<a class="one-record-link" href="${esc(one.pdf)}" target="_blank" rel="noopener">${esc(__("PDF"))}</a>` : "") },
			],
			open: (one) => one.page && window.open(one.page, "_blank", "noopener"),
		});
		$into.on("click", "[data-book]", async (event) => {
			event.stopPropagation();
			const bill = await frappe.xcall("onedesk.one_account.bills.to_books", { invoice: $(event.currentTarget).attr("data-book") });
			frappe.show_alert({ message: __("Added to OneBook as a draft bill."), indicator: "green" });
			this.leave(() => frappe.set_route("Form", "Purchase Invoice", bill));
		});
		$into.on("click", "a[target=_blank]", (event) => event.stopPropagation());
		return list;
	}

	async payment_portal() {
		const said = await frappe.xcall("onedesk.one_account.bills.payment_portal");
		if (said && said.url) window.open(said.url, "_blank", "noopener");
	}

	move_billing(account) {
		const dialog = new frappe.ui.Dialog({
			title: __("Billing Owner"),
			fields: [
				{
					fieldname: "email",
					fieldtype: "Data",
					options: "Email",
					label: __("Email"),
					reqd: 1,
					default: account.billed_to || "",
					description: __("Their One account becomes the owner and receives invoices and payment notices."),
				},
			],
			primary_action_label: __("Change"),
			primary_action: async (values) => {
				if (values.email === account.billed_to) return dialog.hide();
				await frappe.xcall("onedesk.one.account.move_billing", { email: values.email });
				dialog.hide();
				frappe.show_alert({ message: __("Billing moved to {0}", [values.email]), indicator: "green" });
				this.refresh({ fresh: true });
			},
		});
		dialog.show();
	}

	async take(plan, extras, label = null) {
		await frappe.xcall("onedesk.one.account.plans_take", { plan, extras, label });
		frappe.show_alert({ message: __("Plan changed"), indicator: "green" });
		this.refresh({ fresh: true });
	}

	async change_plan() {
		const said = await frappe.xcall("onedesk.one.account.plans_offered");
		const esc = frappe.utils.escape_html;
		const money = (value) => format_currency(value || 0, said.currency, 0);
		const gb = (value) => (value == null ? __("Unlimited") : __("{0} GB", [format_number(value, null, 0)]));
		const table = `<table class="table table-bordered os-plans"><thead><tr>
			<th>${esc(__("Plan"))}</th><th>${esc(__("Seats"))}</th><th>${esc(__("Storage"))}</th><th>${esc(__("Database"))}</th><th>${esc(__("Monthly Credits"))}</th><th>${esc(__("Monthly"))}</th>
		</tr></thead><tbody>${said.plans
			.map(
				(one) => `<tr${one.key === said.plan ? ' class="os-plan-current"' : ""}>
				<td>${esc(one.label)}${one.key === said.plan ? " " + frappe.ui.badge.html({ label: __("Current"), theme: "blue" }) : ""}</td>
				<td>${one.seats == null ? esc(__("Unlimited")) : esc(format_number(one.seats, null, 0))}</td>
				<td>${esc(gb(one.storage_gb))}</td><td>${esc(gb(one.database_gb))}</td>
				<td>${esc(format_number(one.credits_a_month || 0, null, 0))}</td><td>${esc(money(one.price))}</td></tr>`
			)
			.join("")}</tbody></table>`;
		const current = said.plans.find((one) => one.key === said.plan);
		const dialog = new frappe.ui.Dialog({
			title: __("Change Plan"),
			size: "large",
			fields: [
				{ fieldtype: "HTML", fieldname: "plans", options: table },
				{
					fieldname: "plan",
					fieldtype: "Select",
					label: __("New Plan"),
					reqd: 1,
					options: said.plans.filter((one) => one.key !== said.plan).map((one) => ({ value: one.key, label: one.label })),
					change: () => show(),
				},
				{ fieldtype: "HTML", fieldname: "change" },
			],
			primary_action_label: __("Change Plan"),
			primary_action: async (values) => {
				const chosen = said.plans.find((one) => one.key === values.plan);
				dialog.hide();
				await this.take(values.plan, said.add_ons, chosen && chosen.label);
			},
		});
		const show = () => {
			const chosen = said.plans.find((one) => one.key === dialog.get_value("plan"));
			if (!chosen) return dialog.fields_dict.change.$wrapper.empty();
			const step = chosen.price - (current ? current.price : 0);
			dialog.fields_dict.change.$wrapper.html(
				frappe.ui.alert.html({
					title:
						step >= 0
							? __("{0} a month more. The difference for the rest of this month is charged now.", [money(step)])
							: __("{0} a month less. The rest of this month comes off the next invoice.", [money(-step)]),
					theme: "blue",
				})
			);
		};
		dialog.show();
		show();
	}

	async add_to_plan(data) {
		const account = data.account || {};
		const said = await frappe.xcall("onedesk.one.account.plans_offered");
		const esc = frappe.utils.escape_html;
		const money = (value) => format_currency(value || 0, said.currency, 0);
		const sold = said.add_ons_sold || [];
		if (!sold.length) return frappe.msgprint(__("No add-ons available"));
		const dialog = new frappe.ui.Dialog({
			title: __("Add to Plan"),
			fields: [
				{
					fieldname: "add_on",
					fieldtype: "Select",
					label: __("Add-on"),
					reqd: 1,
					options: sold.map((one) => ({ value: one.key, label: __("{0} · {1} a month", [one.label, money(one.price)]) })),
					default: sold[0].key,
					change: () => show(),
				},
				{ fieldname: "count", fieldtype: "Int", label: __("Quantity"), reqd: 1, default: 1, change: () => show() },
				{ fieldtype: "HTML", fieldname: "said" },
			],
			primary_action_label: __("Add"),
			primary_action: async (values) => {
				const extras = { ...said.add_ons };
				extras[values.add_on] = (extras[values.add_on] || 0) + Math.max(1, cint(values.count));
				dialog.hide();
				await this.take(said.plan, extras);
			},
		});
		const show = frappe.utils.debounce(async () => {
			const chosen = sold.find((one) => one.key === dialog.get_value("add_on"));
			const count = Math.max(1, cint(dialog.get_value("count")));
			if (!chosen) return;
			const cost = __("{0} a month more. The difference for the rest of this month is charged now.", [money(chosen.price * count)]);
			const gb = (bytes) => Math.round((bytes || 0) / 1e9);
			const needs = {
				seats: (account.seats || 0) + (chosen.seats || 0) * count,
				storage_gb: gb(account.storage_limit) + (chosen.storage_gb || 0) * count,
				database_gb: gb(account.database_limit) + (chosen.database_gb || 0) * count,
			};
			let better = null;
			try {
				const quoted = await frappe.xcall("onedesk.one.account.plans_quote", { needs });
				const staying = (account.monthly || 0) + chosen.price * count;
				better = (quoted.options || []).find((one) => one.plan !== said.plan && one.monthly < staying);
				if (better) better.saves = staying - better.monthly;
			} catch (e) {
				better = null;
			}
			dialog.fields_dict.said.$wrapper.html(
				frappe.ui.alert.html({ title: cost, theme: "blue" }) +
					(better
						? `<div class="os-better">${frappe.ui.alert.html({
								title: __("{0} Saves {1}", [better.label, money(better.saves)]),
								description: __("{0} gives you this for {1} a month.", [
									[better.label, ...better.extras.map((one) => __("{0} × {1}", [one.count, one.label]))].join(" + "),
									money(better.monthly),
								]),
								theme: "green",
						  })}<div class="one-shell-actions">${onedesk.shell.button(__("Switch to {0}", [better.label]), { "data-better": better.plan }, "subtle")}</div></div>`
						: "")
			);
			dialog.fields_dict.said.$wrapper.find("[data-better]").on("click", async () => {
				dialog.hide();
				await this.take(better.plan, Object.fromEntries(better.extras.map((one) => [one.offering, one.count])), better.label);
			});
		}, 250);
		dialog.show();
		show();
	}

	async check_again() {
		await frappe.xcall("onedesk.one.account.check_again");
		this.refresh({ fresh: true });
	}

	async buy_credits() {
		let packs = [];
		try {
			packs = await frappe.xcall("onedesk.one.account.credit_packs");
		} catch (e) {
			return;
		}
		if (!packs.length) return frappe.msgprint(__("No credit packs available"));
		const dialog = new frappe.ui.Dialog({
			title: __("Buy Credits"),
			fields: [
				{
					fieldname: "pack",
					fieldtype: "Select",
					label: __("Pack"),
					reqd: 1,
					options: packs.map((one) => ({
						value: one.name,
						label: __("{0} credits · {1}", [format_number(one.credits, null, 0), format_currency(one.amount, one.currency, 0)]),
					})),
				},
			],
			primary_action_label: __("Continue to Payment"),
			primary_action: async (values) => {
				const said = await frappe.xcall("onedesk.one.account.buy_credits", { pack: values.pack });
				dialog.hide();
				const url = said && (said.pay_at || said.url);
				if (!url) return;
				window.open(url, "_blank");
				$(window).one("focus", () => this.key === "plan" && this.check_again());
			},
		});
		dialog.show();
	}

	draw_devices(data) {
		const esc = frappe.utils.escape_html;
		const when = (value) => (value ? frappe.datetime.prettyDate(value) : "");
		const rows = data.devices || [];
		const uses = { Shared: __("Shared"), Assigned: __("Assigned") };
		this.$content.html(
			onedesk.shell.section(__("Devices"), '<div data-list="devices"></div>') +
				onedesk.shell.section(__("Passkeys"), '<div data-list="passkeys"></div>')
		);
		onedesk.shell.table(this.$content.find('[data-list="devices"]'), {
			rows,
			icon: "monitor-smartphone",
			empty: __("Nobody has signed in yet"),
			columns: [
				{
					label: __("Name"),
					render: (one) =>
						`<div>${esc(one.device_name)} ${one.here ? frappe.ui.badge.html({ label: __("This Browser"), theme: "blue" }) : ""}</div>${
							one.asset ? `<div class="one-shell-quiet">${esc(one.asset_name || one.asset)}</div>` : ""
						}`,
				},
				{
					label: __("Used By"),
					render: (one) =>
						one.use
							? `${frappe.ui.badge.html({ label: uses[one.use], theme: one.use === "Shared" ? "orange" : "blue" })} ${esc(one.holder)}`
							: `<span class="one-shell-quiet">${esc(__("Not set"))}</span>`,
				},
				{
					label: __("Last Seen"),
					render: (one) => `<div>${esc(one.seen_by)}</div><div class="one-shell-quiet">${esc([when(one.last_seen), one.last_address].filter(Boolean).join(" · "))}</div>`,
				},
				{ label: __("Passkeys"), render: (one) => esc(String(one.passkeys || 0)) },
				{
					label: "",
					render: (one) =>
						`<div class="one-shell-row-actions" data-device="${esc(one.name)}">${onedesk.shell.button(__("Edit"), { "data-edit": "1" }, "ghost", "pencil")}${onedesk.shell.button(
							__("Lost"),
							{ "data-lost": "1" },
							"ghost",
							null,
							"red"
						)}${onedesk.shell.button(__("Retire"), { "data-retire": "1" }, "ghost")}</div>`,
				},
			],
		});
		onedesk.shell.table(this.$content.find('[data-list="passkeys"]'), {
			rows: data.passkeys || [],
			icon: "fingerprint",
			empty: __("Nobody has a passkey yet"),
			columns: [
				{ label: __("Person"), render: (one) => esc(one.person) },
				{
					label: __("Device"),
					render: (one) =>
						`${esc(one.device)} ${one.synced ? frappe.ui.badge.html({ label: __("Synced"), theme: "gray" }) : ""}${
							one.linked ? "" : `<div class="one-shell-quiet">${esc(__("Not linked to a browser"))}</div>`
						}`,
				},
				{ label: __("Registered On"), render: (one) => `<span class="one-shell-quiet">${esc(when(one.registered_on))}</span>` },
				{ label: __("Last Used"), render: (one) => `<span class="one-shell-quiet">${esc(when(one.last_used) || __("Never"))}</span>` },
				{
					label: "",
					render: (one) =>
						`<div class="one-shell-row-actions" data-passkey="${esc(one.name)}">${onedesk.shell.button(__("Retire"), { "data-retire-passkey": "1" }, "ghost", null, "red")}</div>`,
				},
			],
		});
		this.$content.on("click", "[data-retire-passkey]", (event) => {
			const passkey = $(event.currentTarget).closest("[data-passkey]").attr("data-passkey");
			const one = (data.passkeys || []).find((key) => key.name === passkey);
			frappe.confirm(__("Retire {0}'s passkey?", [esc(one.person)]), async () => {
				await frappe.xcall("onedesk.one_account.devices.retire_passkey", { passkey });
				this.refresh();
			});
		});
		const of = (event) => rows.find((one) => one.name === $(event.currentTarget).closest("[data-device]").attr("data-device"));
		this.$content.on("click", "[data-edit]", (event) => this.edit_device(of(event)));
		this.$content.on("click", "[data-lost]", (event) => {
			const one = of(event);
			frappe.confirm(__("Mark {0} as lost? Everyone on it is signed out.", [esc(one.device_name)]), async () => {
				await frappe.xcall("onedesk.one_account.devices.lost", { device: one.name });
				frappe.show_alert({ message: __("Marked as lost"), indicator: "green" });
				this.refresh();
			});
		});
		this.$content.on("click", "[data-retire]", (event) => {
			const one = of(event);
			frappe.confirm(__("Retire {0}?", [esc(one.device_name)]), async () => {
				await frappe.xcall("onedesk.one_account.devices.retire", { device: one.name });
				this.refresh();
			});
		});
	}

	edit_device(one) {
		const dialog = new frappe.ui.Dialog({
			title: __("Edit Device"),
			fields: [
				{ fieldname: "device_name", fieldtype: "Data", label: __("Name"), reqd: 1, default: one.device_name },
				{
					fieldname: "use",
					fieldtype: "Select",
					label: __("Used By"),
					options: [
						{ value: "", label: __("Not set") },
						{ value: "Assigned", label: __("One person") },
						{ value: "Shared", label: __("Several people") },
					],
					default: one.use || "",
				},
				{ fieldname: "user", fieldtype: "Link", options: "User", label: __("Assigned To"), default: one.user, depends_on: "eval:doc.use==='Assigned'", mandatory_depends_on: "eval:doc.use==='Assigned'" },
				{ fieldname: "asset", fieldtype: "Link", options: "Asset", label: __("Asset"), default: one.asset },
			],
			primary_action_label: __("Save"),
			primary_action: async (values) => {
				const said = await frappe.xcall("onedesk.one_account.devices.save", { device: one.name, ...values });
				dialog.hide();
				if (said.retired) frappe.show_alert({ message: __("{0} passkeys on it stopped working", [said.retired]), indicator: "orange" });
				this.refresh();
			},
		});
		dialog.show();
	}

	draw_domains(data) {
		const esc = frappe.utils.escape_html;
		const target = data.target || "";
		const rows = data.domains || [];
		const given = rows.find((one) => one.given);
		const primary = rows.find((one) => one.primary) || given;
		this.page.set_primary_action(__("Add Domain"), () => this.add_domain(target), "plus");
		this.page.add_inner_button(__("Check Again"), async () => {
			await frappe.xcall("onedesk.one.account.domains_refresh");
			this.refresh();
		});
		const waiting = rows.filter((one) => !one.given && one.status !== "Active").map((one) => one.domain);
		this.$content.html(
			onedesk.shell.section(
				__("Addresses"),
				`<div data-list="domains"></div>${
					primary
						? `<div class="one-shell-quiet one-shell-note">${esc(
								__("{0} is the main address.", [primary.domain])
						  )}</div>`
						: ""
				}`,
				__("{0} always works.", [
					given ? given.domain : "",
				])
			) +
				(target
					? onedesk.shell.section(
							__("DNS Records"),
							AccountSection.dns_records(waiting.length ? waiting : [null], target) + AccountSection.dns_note(waiting),
							waiting.length ? __("Takes effect a few minutes after it's added.") : ""
					  )
					: "")
		);
		const states = { Active: [__("Working"), "green"], Pending: [__("Waiting"), "orange"] };
		const said = (one) =>
			one.status === "Active"
				? ""
				: one.problem
				? one.problem
				: one.status === "Pending"
				? __("Waiting for the DNS record below.")
				: __("Not working. Check the DNS record below, then remove the domain and add it again.");
		onedesk.shell.table(this.$content.find('[data-list="domains"]'), {
			rows,
			icon: "globe",
			empty: __("No domains"),
			columns: [
				{
					label: __("Domain"),
					render: (one) =>
						`<div>${esc(one.domain)} ${one.given ? frappe.ui.badge.html({ label: __("Provided by One"), theme: "gray" }) : ""}</div>${
							said(one) ? `<div class="one-shell-quiet">${esc(said(one))}</div>` : ""
						}`,
				},
				{
					label: __("Status"),
					render: (one) => {
						const [label, theme] = states[one.status] || [__("Not Working"), "red"];
						return frappe.ui.badge.html({ label, theme }) + (one.primary ? " " + frappe.ui.badge.html({ label: __("Main Address"), theme: "blue" }) : "");
					},
				},
				{
					label: "",
					render: (one) =>
						`<div class="one-shell-row-actions" data-domain="${esc(one.domain)}">${
							!one.primary && one.status === "Active" ? onedesk.shell.button(__("Make Main Address"), { "data-primary": "1" }, "ghost") : ""
						}${!one.given && !one.primary ? onedesk.shell.button(__("Remove"), { "data-drop": "1" }, "ghost", null, "red") : ""}</div>`,
				},
			],
		});
		const of = (event) => $(event.currentTarget).closest("[data-domain]").attr("data-domain");
		this.$content.on("click", "[data-copy]", (event) => frappe.utils.copy_to_clipboard($(event.currentTarget).attr("data-copy")));
		this.$content.on("click", "[data-primary]", (event) => {
			const domain = of(event);
			frappe.confirm(__("Make {0} the main address? Sign-in, invitations and links in emails will use it.", [esc(domain)]), async () => {
				await frappe.xcall("onedesk.one.account.domain_primary", { domain });
				this.refresh();
			});
		});
		this.$content.on("click", "[data-drop]", (event) => {
			const domain = of(event);
			frappe.confirm(__("Remove {0}? The workspace will no longer open at this domain.", [esc(domain)]), async () => {
				await frappe.xcall("onedesk.one.account.domain_drop", { domain });
				this.refresh();
			});
		});
	}

	static dns_records(names, target) {
		const esc = frappe.utils.escape_html;
		const copy = (value) =>
			`<button type="button" class="os-dns-copy" data-copy="${esc(value)}" title="${esc(__("Copy"))}" aria-label="${esc(__("Copy"))}">${frappe.utils.icon("copy", "sm")}</button>`;
		const row = (kind, name, placeholder) => `<tr>
					<td><span class="os-dns-value">${kind}</span></td>
					<td>${name ? `<span class="os-dns-value">${esc(name)}</span>${copy(name)}` : `<span class="text-muted">${esc(placeholder)}</span>`}</td>
					<td><span class="os-dns-value">${esc(target)}</span>${copy(target)}</td>
				</tr>`;
		const rows = names
			.map((name) => row("CNAME", name, __("Your domain, such as office.example.com")) + (name ? row("TXT", `_one.${name}`) : ""))
			.join("");
		return `<table class="os-dns"><thead><tr><th>${esc(__("Type"))}</th><th>${esc(__("Name"))}</th><th>${esc(__("Value"))}</th></tr></thead><tbody>${rows}</tbody></table>`;
	}

	static dns_note(names) {
		const bare = names.filter((name) => name && name.split(".").length === 2);
		if (!bare.length) return "";
		return `<div class="one-shell-quiet os-dns-lead">${frappe.utils.escape_html(
			[__("{0} is a root domain and needs a CNAME or ALIAS record, which not every DNS provider allows.", [bare[0]]), __("If yours doesn't, add www.{0} instead and redirect {0} to it.", [bare[0]])].join(" ")
		)}</div>`;
	}

	add_domain(target) {
		const dialog = new frappe.ui.Dialog({
			title: __("Add Domain"),
			fields: [
				{
					fieldname: "domain",
					fieldtype: "Data",
					label: __("Domain"),
					reqd: 1,
					placeholder: "office.example.com",
					onchange: () => draw(),
				},
				{ fieldname: "record", fieldtype: "HTML" },
			],
			primary_action_label: __("Add"),
			primary_action: async (values) => {
				await frappe.xcall("onedesk.one.account.domain_add", { domain: values.domain });
				dialog.hide();
				frappe.show_alert({ message: __("Domain added. It works a few minutes after the DNS record is set."), indicator: "green" });
				this.refresh();
			},
		});
		const draw = () => {
			const name = (dialog.get_value("domain") || "").trim().toLowerCase() || null;
			dialog.fields_dict.record.$wrapper.html(
				`<div class="one-shell-quiet os-dns-lead">${frappe.utils.escape_html(__("Add these records at your DNS provider."))}</div>${AccountSection.dns_records(
					[name],
					target
				)}${AccountSection.dns_note([name])}`
			);
		};
		draw();
		dialog.$wrapper.on("click", "[data-copy]", (event) => frappe.utils.copy_to_clipboard($(event.currentTarget).attr("data-copy")));
		dialog.show();
	}
};

// The sections, in order, each with what it is for under its title. The
// server says which the reader may open and what each is called.
onedesk.account_center.SECTIONS = [
	{ id: "profile", about: __("Your name, photo and language, and your employee details if you have them.") },
	{ id: "signin", about: __("Your password, your passkey and where you are signed in.") },
	{ id: "people", about: __("Everyone in the workspace, and inviting someone new.") },
	{ id: "devices", about: __("The company's computers and phones, and the passkeys on people's own.") },
	{ id: "plan", about: __("The plan, its seats and storage, OneAI credits and invoices.") },
	{ id: "domains", about: __("The addresses the workspace answers on.") },
];

// AccountCenter: Yours for everybody, Workspace for administrators. `at`
// opens one section, and `record` one record in it, such as a person. It
// starts with what is left to set up, while something is.
onedesk.account_center.open = async ({ at = null, record = null } = {}) => {
	const said = await frappe.xcall(onedesk.AccountSection.API + "sections_of");
	const allowed = Object.fromEntries(said.sections.map((one) => [one.key, one]));
	const named = { yours: __("Yours"), workspace: __("Workspace") };
	const steps = (frappe.boot.one_setup || {}).OneAccount || [];
	const starting = steps.some((step) => !step.done) ? [{ group: __("Start Here"), items: [onedesk.module_settings.getting_started("OneAccount")] }] : [];
	const tabs = [
		...starting,
		...Object.entries(named).map(([group, label]) => ({
			group: label,
			items: onedesk.account_center.SECTIONS.filter((one) => allowed[one.id] && allowed[one.id].group === group).map((one) => ({
				id: one.id,
				label: allowed[one.id].label,
				icon: allowed[one.id].icon,
				title: allowed[one.id].label,
				description: one.about,
				render(panel) {
					panel.section = panel.section || new onedesk.AccountSection(panel, one.id);
					panel.section.open(one.id, { record: one.id === at ? record : null });
				},
			})),
		})),
	].filter((group) => group.items.length);
	const ids = tabs.flatMap((group) => group.items.map((item) => item.id));
	const dialog = new onedesk.module_settings.Dialog({
		title: "AccountCenter",
		center: { center: "account", label: frappe.session.user_fullname, icon: "user" },
		tabs,
		default_tab: ids.includes(at) ? at : ids.find((id) => id !== "getting_started"),
		expand: false,
	});
	dialog.$wrapper.addClass("one-set one-account");
	dialog.$wrapper.find(".settings-dialog-sidebar").wrapInner('<div class="one-account-tabs" data-tour="account-tabs"></div>');
	dialog.show();
	// AccountCenter has no foot to start its tour from, so it starts here
	// the first time it opens.
	if ((frappe.boot.one_tours_unseen || []).includes("OneAccount:account")) {
		setTimeout(async () => {
			const tour = await onedesk.tour.here("OneAccount");
			if (tour && dialog.display) onedesk.tour.run("OneAccount", tour);
		}, 600);
	}
	return dialog;
};
