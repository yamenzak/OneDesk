// AccountCenter (docs/ONE.md): your own account and the workspace's, on the
// settings dialog (onedesk.CENTERS.account). For everybody, Yours: Profile
// and Sign-in; for administrators, Workspace: People, Devices, Plan and
// Credits, and Domains. Each section is a CenterSection (center_section.js).
frappe.provide("onedesk.account_center");

onedesk.AccountSection = class AccountSection extends onedesk.CenterSection {
	static API = "onedesk.account_center.center.";
	static HERE = "account";
	static LABEL = onedesk.names.of("account_center");

	constructor(panel, key) {
		super(panel, key);
		this.heard("one_privacy", "profile");
		this.heard("one_closing", "plan");
		this.heard("one_domains", "domains");
	}

	body() {
		return $(`<div class="one-shell-body one-account-body" data-tour="account-section"></div>`).appendTo(this.panel.body.empty());
	}

	// Profile's parts (center.PROFILE_PARTS): each draws only its own fields
	// from one load, so its Save sends only those.
	part(data, names, rows, opts = {}) {
		const all = [...data.fields, ...(data.employee ? data.employee.fields : [])];
		const shown = new Set(names);
		return this.form({ ...data, fields: all.filter((one) => shown.has(one.fieldname)) }, { rows, ...opts });
	}

	static facts(list) {
		const esc = frappe.utils.escape_html;
		return `<dl class="os-facts">${list.map((one) => `<dt>${esc(one.label)}</dt><dd>${esc(String(one.value))}</dd>`).join("")}</dl>`;
	}

	draw_profile(data) {
		const esc = frappe.utils.escape_html;
		const image = data.values.user_image;
		const employee = data.employee;
		const job = employee ? employee.work.filter((one) => ["designation", "department"].includes(one.fieldname)).map((one) => one.value) : [];
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
				}${onedesk.shell.button(__("Sign Out"), { "data-sign-out-here": "1" }, "ghost", "log-out")}</div>
			</div>
		</div>`;
		const rows = [
			["first_name", "middle_name", "last_name"],
			["gender", "birth_date"],
			["mobile_no", "location"],
			["bio", ""],
			{ heading: __("Language and Time") },
			["language", "time_zone"],
			{ heading: __("Your Data") },
			{ html: this.your_data(data.privacy) },
		];
		const names = ["first_name", "middle_name", "last_name", "gender", "birth_date", "mobile_no", "location", "bio", "language", "time_zone"];
		const $card = this.part(data, names, rows, { before: who });
		$card.find(".os-photo .es-avatar__fallback").text(frappe.get_abbr(data.full_name || ""));
		const photo = (user_image) => this.save({ ...this.values(), user_image });
		$card.find("[data-sign-out-here]").on("click", () =>
			frappe.call({ method: "logout" }).then(() => {
				frappe.app.logged_out = true;
				frappe.app.redirect_to_login();
			})
		);
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
		this.write_bio($card);
		this.your_data_actions($card, data.privacy);
	}

	draw_personal(data) {
		this.part(
			data,
			["current_address", "permanent_address", "personal_email", "prefered_contact_email", "person_to_be_contacted", "relation", "emergency_phone_number", "marital_status", "blood_group"],
			[
				{ heading: __("Address") },
				["current_address", "permanent_address"],
				["personal_email", "prefered_contact_email"],
				{ heading: __("Emergency Contact") },
				["person_to_be_contacted", "relation", "emergency_phone_number"],
				{ heading: __("Private"), note: __("Only you and HR see these.") },
				["marital_status", "blood_group"],
			]
		);
	}

	draw_work(data) {
		const employee = data.employee;
		const rows = [
			{ heading: __("Employment"), note: __("Managed by HR.") },
			{ html: AccountSection.facts(employee.work) },
			{ heading: __("Education") },
			["education"],
			{ heading: __("Past Work") },
			["external_work_history"],
		];
		if (employee.bank.length) rows.push({ heading: __("Bank Details"), note: __("Only HR can change this.") }, { html: AccountSection.facts(employee.bank) });
		this.part(data, ["education", "external_work_history"], rows);
	}

	// Your Files: the person's Employee room in OneCloud (one_cloud), where
	// a scan on a row lands when Profile saves, and where they may add more.
	draw_documents(data) {
		const $card = this.part(data, ["one_documents"], [
			["one_documents"],
			{ heading: __("Your Files"), note: __("Scans and papers HR keeps for you.") },
			{ html: `<div class="one-account-files" data-your-files></div>` },
		]);
		onedesk.mount_cloud($card.find("[data-your-files]"), { room: `@records/Employee/${data.employee.name}` });
	}

	// Write My Bio (account_center/agent.py): on Bio's label row, at its end, opening
	// OneAI's quick panel; Use puts the words in the field, unsaved.
	write_bio($card) {
		const html = onedesk.oneai.action("write_bio", __("Write My Bio"), { css_class: "one-ai-field-action" });
		const field = this.group.fields_dict.bio;
		if (!html || !field) return;
		const $label = field.$wrapper.find(".control-label").first();
		const $button = $(html);
		$(`<div class="one-field-head"></div>`).insertBefore($label).append($label, $button);
		onedesk.oneai.quick($button, {
			title: __("Write My Bio"),
			ask: __("Say a little about yourself and your work."),
			run: (told) => frappe.xcall("onedesk.account_center.agent.write_bio", { told }),
			use: (words) => {
				this.group.set_value("bio", words);
				this.check();
			},
		});
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
						options: `<p>${__("An administrator reviews the request. Then you're signed out, and your {0} chats, memory, notifications and devices are deleted.", [onedesk.names.of("one_ai")])} ${__("Records the workspace keeps, such as invoices and tasks, stay without your name and address. HR keeps your employee record, if you have one.")}</p><p>${__("This can't be undone. Request a copy of your data first if you need one.")}</p>`,
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

	// Sign-in (account_center/signin.py): what is weak, said plainly; then the
	// ways in, a tile each; then where the person is signed in.
	draw_signin(data) {
		const esc = frappe.utils.escape_html;
		const when = (value) => (value ? frappe.datetime.prettyDate(value) : "");
		const tile = ({ icon, title, state, theme, text, action = "" }) => `<div class="os-way">
				<div class="os-way-head"><span class="os-way-icon">${frappe.utils.icon(icon, "md")}</span>
				<span class="os-way-title">${esc(title)}</span>${frappe.ui.badge.html({ label: state, theme })}</div>
				<div class="os-way-text">${esc(text)}</div>
				${action ? `<div class="os-way-actions">${action}</div>` : ""}
			</div>`;

		const password = tile({
			icon: "key-round",
			title: __("Password"),
			state: data.password_changed ? __("Changed {0}", [when(data.password_changed)]) : __("Never changed"),
			theme: data.password_changed ? "gray" : "orange",
			text: __("Asked for when you sign in without a passkey."),
			action: onedesk.shell.button(__("Change Password"), { "data-password": "1" }, "subtle"),
		});

		const by = data.two_factor_method === "Email" ? __("A code sent to your email after your password.") : __("A code from an authenticator app on your phone after your password.");
		const two_factor = tile({
			icon: "shield-check",
			title: __("Two-Factor"),
			state: data.two_factor ? __("On") : __("Off"),
			theme: data.two_factor ? "green" : "gray",
			text: data.two_factor
				? data.two_factor_ready || data.two_factor_method === "Email"
					? by
					: __("You set up your authenticator app the next time you sign in.")
				: __("Your workspace hasn't turned it on."),
			action:
				data.two_factor && data.two_factor_ready && data.two_factor_method !== "Email"
					? onedesk.shell.button(__("New Phone"), { "data-two-factor-reset": "1" }, "subtle")
					: !data.two_factor && data.administers
					? onedesk.shell.button(__("Turn On for the Workspace"), { "data-two-factor-on": "1" }, "subtle")
					: "",
		});

		const offered = data.passkey || data.passkey_signs_in || data.passkey_clocks;
		const passkey = offered
			? tile({
					icon: "fingerprint-pattern",
					title: __("Passkey"),
					state: data.passkey ? __("Registered") : __("Not registered"),
					theme: data.passkey ? "green" : "gray",
					text: data.passkey
						? __("On {0}.", [(data.passkeys || []).map((one) => one.label).join(", ")])
						: data.passkey_clocks && !data.passkey_signs_in
						? __("Checks you in with your face, fingerprint or screen lock.")
						: __("Signs you in with your face, fingerprint or screen lock instead of a password."),
					action:
						data.add_here || !data.passkey
							? onedesk.shell.button(__("Register This Device"), { "data-passkey": "1" }, "subtle")
							: data.passkey_clocks
							? ""
							: onedesk.shell.button(__("Remove"), { "data-passkey-remove": "1" }, "ghost"),
			  })
			: "";

		this.$content.html(
			`<div class="one-shell-section" data-warnings></div>
			<div class="one-shell-section"><div class="os-ways">${password}${two_factor}${passkey}</div></div>
			<div class="one-shell-section" data-list="places"></div><div class="one-shell-section" data-list="recent"></div>`
		);
		const $warnings = this.$content.find("[data-warnings]");
		(data.warnings || []).forEach((text) => $warnings.append(onedesk.alert({ text, colour: "orange" })));
		if (!(data.warnings || []).length) $warnings.remove();
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
		this.$content.find("[data-two-factor-reset]").on("click", () =>
			frappe.confirm(__("Set up two-factor again on a new phone? Your old phone's codes stop working, and you scan a new code the next time you sign in."), async () => {
				await frappe.xcall("onedesk.account_center.signin.reset_two_factor");
				frappe.show_alert({ message: __("Set it up again the next time you sign in"), indicator: "green" });
				this.open("signin");
			})
		);
		this.$content.find("[data-two-factor-on]").on("click", () => onedesk.centers.open("settings", { at: "signin" }));
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
			await frappe.xcall("onedesk.account_center.signin.sign_out", { key_of: $(event.currentTarget).attr("data-sign-out") });
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

	// A device as a list shows it: what it is (signin.kind) as an icon, then
	// its name.
	static device(kind, html) {
		const icon = { phone: "smartphone", tablet: "tablet", computer: "monitor" }[kind] || "monitor";
		return `<div class="os-device"><span class="os-device-icon">${frappe.utils.icon(icon, "md")}</span><div>${html}</div></div>`;
	}

	static session_columns(last = null) {
		const esc = frappe.utils.escape_html;
		return [
			{
				label: __("Device"),
				render: (one) =>
					AccountSection.device(one.kind, esc(one.device)) +
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
				__("Everyone has {4}, {0}, {1}, {2} and {3}.", [onedesk.names.of("one_cloud"), onedesk.names.of("one_mail"), onedesk.names.of("one_task"), onedesk.names.of("one_calendar"), onedesk.names.of("one")])
			)} ${esc(seats)}</div></div>
			<div class="one-shell-section os-people-list" data-list="people"></div>`
		);
		this.page.set_primary_action(__("Invite People"), () => this.invite_dialog(data), "plus");
		onedesk.shell.table(this.$content.find('[data-list="people"]'), {
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
				{ label: __("Apps"), render: (one) => `<span class="os-people-apps">${esc(AccountSection.apps_said(one.access, data.apps, levels))}</span>` },
				{ label: __("Sign-in"), render: (one) => AccountSection.way_in(one.way_in) },
				{ label: __("Administrator"), render: (one) => (one.admin ? frappe.ui.badge.html({ label: __("Administrator"), theme: "orange" }) : "") },
				{
					label: __("Last Active"),
					render: (one) => `<span class="one-shell-quiet">${esc(one.last_active ? frappe.datetime.prettyDate(one.last_active) : __("Never"))}</span>`,
				},
			],
		});
	}

	// A person's apps in one line: every app at one level, or the highest
	// level first with the apps at it, and how many more.
	static apps_said(access, apps, levels) {
		const held = apps.filter((app) => access[app.name] && access[app.name] !== "None");
		if (!held.length) return __("Standard apps");
		const at = [...new Set(held.map((app) => access[app.name]))];
		const said = (level) => levels[level] || level;
		if (at.length === 1 && held.length === apps.length) return __("{0} in every app", [said(at[0])]);
		const top = ["Manager", "User"].find((level) => at.includes(level)) || at[0];
		const names = held.filter((app) => access[app.name] === top).map((app) => app.name);
		const more = held.length - Math.min(names.length, 2);
		const listed = names.slice(0, 2).join(", ");
		return more > 0 ? __("{0} in {1} +{2}", [said(top), listed, more]) : __("{0} in {1}", [said(top), listed]);
	}

	// How a person signs in, at its strongest (signin.way_in), as a badge.
	static way_in(way) {
		const said = {
			passkey: [__("Passkey"), "green"],
			two_factor: [__("Two-Factor"), "green"],
			two_factor_pending: [__("Two-Factor Not Set Up"), "orange"],
			password: [__("Password Only"), "gray"],
		}[way] || [__("Password Only"), "gray"];
		return frappe.ui.badge.html({ label: said[0], theme: said[1] });
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
				...(["two_factor", "two_factor_pending"].includes(one.way_in)
					? [
							{
								label: __("Reset Two-Factor"),
								group: __("Actions"),
								action: () =>
									frappe.confirm(__("Reset two-factor for {0}? Their old phone's codes stop working, and they set it up again the next time they sign in.", [esc(name)]), async () => {
										await frappe.xcall(AccountSection.API + "reset_two_factor", { user: one.name });
										this.refresh({ fresh: true });
										done(__("Two-factor reset"));
									}),
							},
					  ]
					: []),
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
					{ label: __("Signs In With"), html: AccountSection.way_in(one.way_in) },
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
			{ heading: __("Apps"), note: __("Everyone has {4}, {0}, {1}, {2} and {3}.", [onedesk.names.of("one_cloud"), onedesk.names.of("one_mail"), onedesk.names.of("one_task"), onedesk.names.of("one_calendar"), onedesk.names.of("one")]) },
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
				{ fieldtype: "Section Break", label: __("Apps"), description: __("Everyone has {4}, {0}, {1}, {2} and {3}.", [onedesk.names.of("one_cloud"), onedesk.names.of("one_mail"), onedesk.names.of("one_task"), onedesk.names.of("one_calendar"), onedesk.names.of("one")]) },
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
		// Not connected to its account: what it last said, if anything, and
		// nothing that has to ask the account (changing, paying, invoices).
		const known = Boolean(account.last_heard);
		const called = account.workspace_name || frappe.boot.sysdefaults?.company || __("This Workspace");
		// Somebody who may only see the plan (AccountCenter's Plan and Credits)
		// reads it; changing it, paying and closing are an administrator's.
		if (data.admin && data.linked) this.page.set_primary_action(__("Change Plan"), () => this.change_plan(), "arrow-up-down");
		this.$content = onedesk.shell.record(this.$content, {
			page: this.page,
			status: data.state,
			actions: data.admin && data.linked
				? [
						{ label: __("Payment Method"), action: () => this.change_card() },
						{ label: __("Billing Details"), action: () => this.payment_portal() },
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
		// What the plan holds, a tile each, with how to get more of it right
		// there: buying asks the account, so only an administrator of a
		// connected workspace sees the buttons.
		const buying = data.admin && data.linked;
		const add_ons = (data.add_ons || []).length;
		const meter = ({ icon, title, used, of, share, text, href, buy, kind }) => {
			const over = share > 100, near = share >= 90;
			return `<div class="os-way os-meter">
				<div class="os-way-head"><span class="os-way-icon">${frappe.utils.icon(icon, "md")}</span>
				<span class="os-way-title">${esc(title)}</span>${
					share == null ? "" : over ? frappe.ui.badge.html({ label: __("Full"), theme: "red" }) : near ? frappe.ui.badge.html({ label: __("Nearly Full"), theme: "orange" }) : ""
				}</div>
				<${href ? `a href="${esc(href)}"` : "div"} class="os-meter-figure">${esc(used)}${of ? ` <span>${esc(of)}</span>` : ""}</${href ? "a" : "div"}>
				${share == null ? "" : frappe.ui.progress.html({ value: Math.min(100, Math.round(share)), size: "md", css_class: over ? "os-bar-over" : near ? "os-bar-near" : "" })}
				<div class="os-way-text">${esc(text || "")}</div>
				${buying ? `<div class="os-way-actions">${onedesk.shell.button(buy, { "data-buy": kind }, "subtle")}${
					kind === "credits" ? onedesk.shell.button(__("Monthly Limit"), { "data-limit": "1" }, "ghost") : ""
				}</div>` : ""}
			</div>`;
		};
		const share = (used, limit) => (Number(limit) ? (100 * (Number(used) || 0)) / Number(limit) : null);
		const credits_said = [
			account.credits_month && __("{0} used in the last 30 days", [number(account.credits_month)]),
			account.credits_held && __("{0} reserved", [number(account.credits_held)]),
			account.credits_expiring && __("{0} expire on {1}", [number(account.credits_expiring), frappe.datetime.str_to_user(account.credits_expires_on)]),
		].filter(Boolean);
		// The plan itself: its name and price, what it holds, who pays.
		const holds = [
			account.seats && __("{0} seats", [number(account.seats)]),
			Number(account.storage_limit) && __("{0} storage", [data.storage.limit]),
			Number(account.database_limit) && __("{0} database", [data.database.limit]),
			add_ons && (add_ons === 1 ? __("1 add-on") : __("{0} add-ons", [add_ons])),
		].filter(Boolean);
		const plan = `<div class="os-plan">
			<div class="os-plan-mark">${frappe.utils.icon("gem", "lg")}</div>
			<div class="os-plan-body">
				<div class="os-plan-name">${esc(account.plan ? __("{0} Plan", [account.plan]) : called)}</div>
				${holds.length ? `<div class="os-plan-holds">${esc(holds.join(" · "))}</div>` : ""}
				<div class="os-plan-meta">${esc(
					[
						account.billed_to && __("Billed to {0}", [frappe.user.full_name(account.billed_to)]),
						account.last_heard ? __("As of {0}", [frappe.datetime.prettyDate(account.last_heard)]) : __("Not synced yet"),
					]
						.filter(Boolean)
						.join(" · ")
				)}</div>
			</div>
			${account.monthly ? `<div class="os-plan-price">${esc(money(account.monthly))}<span>${esc(__("a month"))}</span></div>` : ""}
		</div>`;
		const meters = `<div class="os-ways os-meters">${[
			meter({
				icon: "users",
				title: __("Seats"),
				used: number(data.used),
				of: account.seats ? __("of {0}", [number(account.seats)]) : __("no limit"),
				share: share(data.used, account.seats),
				text: __("People turned on take a seat."),
				href: data.admin ? "#people" : "",
				buy: __("Add Seats"),
				kind: "seats",
			}),
			meter({
				icon: "hard-drive",
				title: __("Storage"),
				used: data.storage.used,
				of: Number(account.storage_limit) ? __("of {0}", [data.storage.limit]) : __("no limit"),
				share: share(account.storage_bytes, account.storage_limit),
				text: __("Files in {0} and on records.", [onedesk.names.of("one_cloud")]),
				href: "/desk/onecloud",
				buy: __("Add Storage"),
				kind: "storage_gb",
			}),
			meter({
				icon: "database",
				title: __("Database"),
				used: data.database.used,
				of: Number(account.database_limit) ? __("of {0}", [data.database.limit]) : __("no limit"),
				share: share(account.database_bytes, account.database_limit),
				text: __("Every record in the workspace."),
				buy: __("Add Database"),
				kind: "database_gb",
			}),
			meter({
				icon: "sparkles",
				title: __("Credits"),
				used: number(account.credits_balance),
				of: __("left"),
				share: null,
				text: [
					...credits_said,
					account.credits_limit ? __("{0} of the {1} monthly limit spent", [number(account.credits_spent), number(account.credits_limit)]) : "",
				].filter(Boolean).join(" · ") || __("Monthly credits are used first. Bought credits last 12 months."),
				buy: __("Buy Credits"),
				kind: "credits",
			}),
		].join("")}</div>`;
		const closing = data.closing || {};
		const closes = closing.closing_on
			? __("The workspace closes on {0} and is deleted on {1}.", [
					frappe.datetime.str_to_user(closing.closing_on),
					closing.deleted_on ? frappe.datetime.str_to_user(closing.deleted_on) : __("a later date"),
			  ])
			: "";
		const unlinked = data.linked
			? ""
			: `<div class="one-record-news">${frappe.ui.alert.html({
					title: known
						? __("Not connected to its account. Last heard {0}. Seats, storage and credits can be bought once it's connected.", [frappe.datetime.prettyDate(account.last_heard)])
						: __("This workspace isn't connected to its account yet, so its plan, invoices and credits can't be shown."),
					theme: "yellow",
			  })}</div>`;
		if (!data.linked && !known) {
			this.$content.html(unlinked + (data.admin ? this.closing_section(closing) : ""));
			this.$content.find("[data-closing]").on("click", (event) => this.closing_act($(event.currentTarget).attr("data-closing"), closing));
			return;
		}
		this.$content.html(
			unlinked +
			(closes ? `<div class="one-record-news">${frappe.ui.alert.html({ title: closes, theme: "red" })}</div>` : "") +
			(data.said ? `<div class="one-record-news">${frappe.ui.alert.html({ title: data.said.text, theme: data.said.colour === "red" ? "red" : "yellow" })}</div>` : "") +
				onedesk.shell.section(
					__("Plan"),
					plan +
						meters +
						(add_ons ? '<div class="os-add-ons" data-list="add-ons"></div>' : "")
				) +
				(data.linked
					? onedesk.shell.section(
							__("Invoices"),
							'<div data-list="invoices"><div class="one-shell-quiet">' + esc(__("Loading…")) + "</div></div>"
					  )
					: "") +
				(data.linked
					? onedesk.shell.section(
							__("Credits Ledger"),
							data.ledger ? '<div data-list="ledger"></div>' : `<div class="one-shell-quiet">${esc(__("Couldn't load the ledger."))}</div>`,
							__("Last {0} days. Monthly credits are used first. Bought credits last 12 months.", [data.ledger_days])
					  )
					: "") +
				(data.admin && data.linked ? this.auto_topup_section() : "") +
				(data.admin && data.linked ? this.updates_section(account) : "") +
				(data.admin ? this.closing_section(closing) : "")
		);
		this.$content.find("[data-auto-topup]").on("click", () => this.auto_topup());
		this.$content.find("[data-update-window]").on("click", () => this.update_window(account));
		this.$content.find("[data-update-now]").on("click", () => this.update_now());
		this.$content.find("[data-closing]").on("click", (event) => this.closing_act($(event.currentTarget).attr("data-closing"), closing));
		this.$content.find("[data-limit]").on("click", () => this.set_limit(account));
		this.$content.find("[data-buy]").on("click", (event) => {
			const kind = $(event.currentTarget).attr("data-buy");
			kind === "credits" ? this.buy_credits() : this.add_to_plan(data, kind);
		});
		if (data.linked) this.draw_invoices(this.$content.find('[data-list="invoices"]'));
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
							!(data.admin && data.linked)
								? ""
								: `<div class="one-shell-row-actions" data-add-on="${esc(one.offering)}">${onedesk.shell.button(
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

	week_days() {
		return [__("Monday"), __("Tuesday"), __("Wednesday"), __("Thursday"), __("Friday"), __("Saturday"), __("Sunday")];
	}

	auto_topup_section() {
		return onedesk.shell.section(
			__("Auto Top-Up"),
			`<div class="one-shell-quiet">${frappe.utils.escape_html(__("Buy a pack on the saved card when the balance runs low."))}</div>
			<div class="os-way-actions">${onedesk.shell.button(__("Change Auto Top-Up"), { "data-auto-topup": "1" }, "ghost")}</div>`
		);
	}

	async auto_topup() {
		const held = await frappe.xcall("onedesk.account_center.bills.auto_topup");
		const named = Object.fromEntries((held.packs || []).map((one) => [`${one.label} · ${format_currency(one.amount, one.currency)}`, one.name]));
		const shown = Object.keys(named).find((label) => named[label] === held.pack) || Object.keys(named)[0];
		frappe.prompt(
			[
				{ fieldname: "enabled", fieldtype: "Check", label: __("Enable Auto Top-Up"), default: held.enabled },
				{ fieldname: "pack", fieldtype: "Select", label: __("Pack"), options: Object.keys(named).join("\n"), default: shown, mandatory_depends_on: "enabled" },
				{ fieldname: "below", fieldtype: "Int", label: __("Minimum Balance"), default: held.below || 100, mandatory_depends_on: "enabled" },
				{ fieldname: "cap", fieldtype: "Int", label: __("Monthly Pack Limit"), default: held.cap || 1, mandatory_depends_on: "enabled" },
			],
			({ enabled, pack, below, cap }) =>
				frappe
					.xcall("onedesk.account_center.bills.set_auto_topup", { enabled: enabled ? 1 : 0, pack: named[pack] || "", below, cap })
					.then(() => frappe.show_alert({ message: __("Auto Top-Up saved."), indicator: "green" })),
			__("Auto Top-Up"),
			__("Save")
		);
	}

	updates_section(account) {
		const esc = frappe.utils.escape_html;
		const day = this.week_days()[account.update_weekday];
		const hour = String(account.update_hour).padStart(2, "0");
		const said = account.update_at
			? __("The next update is on {0}.", [frappe.datetime.str_to_user(account.update_at)])
			: __("Updates run on {0} at {1}:00.", [day, hour]);
		return onedesk.shell.section(
			__("Updates"),
			`<div class="one-shell-quiet">${esc(said)}</div>
			<div class="os-way-actions">${onedesk.shell.button(__("Change Window"), { "data-update-window": "1" }, "ghost")}${
				account.update_at ? onedesk.shell.button(__("Update Now"), { "data-update-now": "1" }, "ghost") : ""
			}</div>`
		);
	}

	update_window(account) {
		const days = this.week_days();
		const hours = Array.from({ length: 24 }, (_, hour) => `${String(hour).padStart(2, "0")}:00`);
		frappe.prompt(
			[
				{ fieldname: "day", fieldtype: "Select", label: __("Day"), options: days.join("\n"), reqd: 1, default: days[account.update_weekday] },
				{ fieldname: "hour", fieldtype: "Select", label: __("Hour"), options: hours.join("\n"), reqd: 1, default: hours[account.update_hour] },
			],
			({ day, hour }) =>
				frappe
					.xcall("onedesk.account_center.bills.set_update_window", { weekday: days.indexOf(day), hour: hours.indexOf(hour) })
					.then(() => {
						frappe.show_alert({ message: __("Update window saved."), indicator: "green" });
						this.refresh();
					}),
			__("Change Window"),
			__("Save")
		);
	}

	async update_now() {
		const go = await onedesk.interface.ask({
			question: __("Update now?"),
			effect: __("The workspace is offline for a few minutes."),
			verb: __("Update Now"),
		});
		if (!go) return;
		const said = await frappe.xcall("onedesk.account_center.bills.update_now");
		frappe.show_alert({ message: said.waiting ? __("Update started.") : __("No update is waiting."), indicator: "green" });
		this.refresh();
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
			Failed: __("Couldn't create the download. Try again, or reply to any email from {0}.", [onedesk.names.of("one")]),
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
			window.open("/api/method/onedesk.account_center.closing.download");
			return;
		}
		if (what === "prepare") {
			await frappe.xcall("onedesk.account_center.closing.prepare");
			frappe.show_alert({ message: __("Creating the download. You'll be notified when it's ready."), indicator: "blue" });
			return this.refresh();
		}
		if (what === "keep") {
			await frappe.xcall("onedesk.account_center.closing.keep");
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
				await frappe.xcall("onedesk.account_center.closing.close", { password: values.password });
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
			said = await frappe.xcall("onedesk.account_center.bills.invoices");
		} catch (e) {
			return $into.html(`<div class="one-shell-quiet">${esc(__("Couldn't load invoices."))}</div>`);
		}
		if (said.linked === false) return $into.html(`<div class="one-shell-quiet">${esc(__("Not Connected Yet"))}</div>`);
		if (said.reached === false) return $into.html(`<div class="one-shell-quiet">${esc(__("Couldn't load invoices."))}</div>`);
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
					label: __("In {0}", [onedesk.names.of("one_book")]),
					render: (one) =>
						one.bill
							? `<a class="one-record-link" href="${esc(frappe.utils.get_form_link("Purchase Invoice", one.bill))}">${esc(one.bill)}</a>`
							: one.status === "paid"
							? onedesk.shell.button(__("Add to {0}", [onedesk.names.of("one_book")]), { "data-book": one.id }, "subtle")
							: "",
				},
				{ label: "", render: (one) => (one.pdf ? `<a class="one-record-link" href="${esc(one.pdf)}" target="_blank" rel="noopener">${esc(__("PDF"))}</a>` : "") },
			],
			open: (one) => one.page && window.open(one.page, "_blank", "noopener"),
		});
		$into.on("click", "[data-book]", async (event) => {
			event.stopPropagation();
			const bill = await frappe.xcall("onedesk.account_center.bills.to_books", { invoice: $(event.currentTarget).attr("data-book") });
			frappe.show_alert({ message: __("Added to {0} as a draft bill.", [onedesk.names.of("one_book")]), indicator: "green" });
			this.leave(() => frappe.set_route("Form", "Purchase Invoice", bill));
		});
		$into.on("click", "a[target=_blank]", (event) => event.stopPropagation());
		return list;
	}

	async payment_portal() {
		const said = await frappe.xcall("onedesk.account_center.bills.payment_portal");
		if (said && said.url) window.open(said.url, "_blank", "noopener");
	}

	async change_card() {
		const said = await frappe.xcall("onedesk.account_center.bills.change_card");
		if (!said || !said.checkout) return;
		this.pay(said.checkout, __("Payment Method"), () =>
			frappe.show_alert({ message: __("Card saved. The next invoice is paid with it."), indicator: "green" })
		);
	}

	// Stripe's Checkout drawn in a dialog (public/js/one_admin/one_pay.js): nobody
	// leaves One to pay. `done` runs once Stripe says it is paid or saved.
	async pay(checkout, title, done) {
		await frappe.require("/assets/onedesk/js/one_admin/one_pay.js");
		const dialog = new frappe.ui.Dialog({ title, size: "large", fields: [{ fieldtype: "HTML", fieldname: "pay" }] });
		const $at = dialog.fields_dict.pay.$wrapper.addClass("os-pay");
		$at.html(`<div class="one-shell-quiet">${frappe.utils.escape_html(__("Loading…"))}</div>`);
		let drawn = null;
		dialog.onhide = () => drawn && drawn.destroy();
		dialog.show();
		try {
			const into = $('<div class="os-pay-form"></div>').appendTo($at.empty())[0];
			drawn = await window.onePay(into, checkout, {
				locale: frappe.boot.lang || "auto",
				done: () =>
					setTimeout(() => {
						dialog.hide();
						done && done();
					}, 1500),
			});
		} catch (e) {
			$at.html(frappe.ui.alert.html({ title: __("Payment Form Not Loaded"), description: __("Check the connection and try again."), theme: "red" }));
		}
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
					description: __("The {0} account with this email becomes the owner and receives invoices and payment notices.", [onedesk.names.of("one")]),
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

	async add_to_plan(data, kind) {
		const account = data.account || {};
		const said = await frappe.xcall("onedesk.one.account.plans_offered");
		const esc = frappe.utils.escape_html;
		const money = (value) => format_currency(value || 0, said.currency, 0);
		const all = said.add_ons_sold || [];
		const of_kind = kind ? all.filter((one) => one[kind]) : [];
		const sold = of_kind.length ? of_kind : all;
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

	set_limit(account) {
		frappe.prompt(
			{
				fieldname: "limit",
				fieldtype: "Int",
				label: __("Monthly Limit (Credits)"),
				default: account.credits_limit || 0,
				non_negative: 1,
				description: __("Set to 0 for no limit."),
			},
			({ limit }) =>
				frappe.xcall("onedesk.account_center.bills.set_spend_limit", { limit }).then(() => {
					frappe.show_alert({ message: __("Monthly limit saved."), indicator: "green" });
					this.refresh();
				}),
			__("Monthly Limit"),
			__("Save")
		);
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
					default: packs[0].name,
					options: packs.map((one) => ({
						value: one.name,
						label: __("{0} credits · {1}", [format_number(one.credits, null, 0), format_currency(one.amount, one.currency, 0)]),
					})),
				},
			],
			primary_action_label: __("Continue to Payment"),
			primary_action: async (values) => {
				const pack = packs.find((one) => one.name === values.pack);
				const said = await frappe.xcall("onedesk.one.account.buy_credits", { pack: values.pack });
				dialog.hide();
				if (!said || !said.checkout) return;
				this.pay(said.checkout, __("Buy {0} Credits", [format_number(pack ? pack.credits : said.credits, null, 0)]), () => {
					frappe.show_alert({ message: __("Paid. The credits arrive in a moment."), indicator: "green" });
					this.check_again();
				});
			},
		});
		dialog.show();
	}

	// Devices (account_center/devices.py): the company's computers and phones,
	// then the browsers nobody has named yet, then every passkey. A device
	// opens to be named, sorted, marked lost or retired.
	draw_devices(data) {
		const esc = frappe.utils.escape_html;
		const when = (value) => (value ? frappe.datetime.prettyDate(value) : "");
		const rows = data.devices || [];
		const ours = rows.filter((one) => one.use);
		const others = rows.filter((one) => !one.use);
		const uses = { Shared: __("Shared"), Assigned: __("Assigned") };
		const name = (one) =>
			AccountSection.device(
				one.kind,
				`<div>${esc(one.device_name)} ${one.here ? frappe.ui.badge.html({ label: __("This Browser"), theme: "blue" }) : ""}</div>${
					one.asset ? `<div class="one-shell-quiet">${esc(one.asset_name || one.asset)}</div>` : ""
				}`
			);
		const seen = (one) => `<div>${esc(one.seen_by)}</div><div class="one-shell-quiet">${esc([when(one.last_seen), one.last_address].filter(Boolean).join(" · "))}</div>`;
		const keys = (one) => (one.passkeys ? esc(String(one.passkeys)) : "");
		this.$content.html(
			`<div class="one-shell-section" data-list="ours"></div>` +
				(others.length
					? onedesk.shell.section(__("Other Browsers"), '<div data-list="others"></div>', __("Browsers someone signed in on that nobody has named. Unnamed ones are forgotten after a month unseen."))
					: "") +
				onedesk.shell.section(__("Passkeys"), '<div data-list="passkeys"></div>')
		);
		onedesk.shell.table(this.$content.find('[data-list="ours"]'), {
			rows: ours,
			icon: "monitor-smartphone",
			empty: __("No company devices yet. Open a browser under Other Browsers to name it."),
			open: (one) => this.edit_device(one),
			columns: [
				{ label: __("Name"), render: name },
				{ label: __("Used By"), render: (one) => `${frappe.ui.badge.html({ label: uses[one.use], theme: one.use === "Shared" ? "orange" : "blue" })} ${esc(one.holder)}` },
				{ label: __("Last Seen"), render: seen },
				{ label: __("Passkeys"), render: keys },
			],
		});
		if (others.length) {
			onedesk.shell.table(this.$content.find('[data-list="others"]'), {
				rows: others,
				page_size: 10,
				icon: "monitor-smartphone",
				open: (one) => this.edit_device(one),
				columns: [
					{ label: __("Browser"), render: name },
					{ label: __("Last Seen"), render: seen },
					{ label: __("Passkeys"), render: keys },
				],
			});
		}
		onedesk.shell.table(this.$content.find('[data-list="passkeys"]'), {
			rows: data.passkeys || [],
			icon: "fingerprint-pattern",
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
			event.stopPropagation();
			const passkey = $(event.currentTarget).closest("[data-passkey]").attr("data-passkey");
			const one = (data.passkeys || []).find((key) => key.name === passkey);
			frappe.confirm(__("Retire {0}'s passkey?", [esc(one.person)]), async () => {
				await frappe.xcall("onedesk.account_center.devices.retire_passkey", { passkey });
				this.refresh();
			});
		});
	}

	// One device: its name, who uses it and the asset it is; and, at the
	// foot, Lost (everyone on it signed out, its passkeys off) and Retire.
	edit_device(one) {
		const esc = frappe.utils.escape_html;
		const dialog = new frappe.ui.Dialog({
			title: one.use ? __("Edit Device") : __("Make a Company Device"),
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
				const said = await frappe.xcall("onedesk.account_center.devices.save", { device: one.name, ...values });
				dialog.hide();
				if (said.retired) frappe.show_alert({ message: __("{0} passkeys on it stopped working", [said.retired]), indicator: "orange" });
				this.refresh();
			},
		});
		dialog.add_custom_action(__("Retire"), () =>
			frappe.confirm(__("Retire {0}? It leaves the list, and passkeys on it stop working.", [esc(one.device_name)]), async () => {
				await frappe.xcall("onedesk.account_center.devices.retire", { device: one.name });
				dialog.hide();
				this.refresh();
			})
		);
		dialog.add_custom_action(
			__("Lost"),
			() =>
				frappe.confirm(__("Mark {0} as lost? Everyone on it is signed out.", [esc(one.device_name)]), async () => {
					await frappe.xcall("onedesk.account_center.devices.lost", { device: one.name });
					dialog.hide();
					frappe.show_alert({ message: __("Marked as lost"), indicator: "green" });
					this.refresh();
				}),
			"btn-danger"
		);
		dialog.show();
	}

	draw_domains(data) {
		const esc = frappe.utils.escape_html;
		const target = data.target || "";
		const rows = data.domains || [];
		const given = rows.find((one) => one.given);
		const primary = rows.find((one) => one.primary) || given;
		// Adding, removing and the main address ask the account, so a
		// workspace not connected to it shows what it last said and no more.
		const changing = Boolean(data.linked);
		if (changing) {
			this.page.set_primary_action(__("Add Domain"), () => this.add_domain(target), "plus");
			this.page.add_inner_button(__("Check Again"), async () => {
				await frappe.xcall("onedesk.one.account.domains_refresh");
				this.refresh();
			});
		}
		const waiting = rows.filter((one) => !one.given && one.status !== "Active").map((one) => one.domain);
		const unlinked = changing
			? ""
			: `<div class="one-record-news">${frappe.ui.alert.html({
					title: rows.length
						? __("This workspace isn't connected to its account. These are the addresses it last said, {0}. Adding or removing one waits until it's connected.", [
								frappe.datetime.prettyDate(data.last_heard),
						  ])
						: __("This workspace isn't connected to its account yet, so its addresses can't be shown."),
					theme: "yellow",
			  })}</div>`;
		if (!rows.length && !changing) return this.$content.html(unlinked);
		// The main address first, as the plan is on Plan and Credits: where
		// sign-in, invitations and links in emails send people.
		const main = primary
			? `<div class="os-plan">
				<div class="os-plan-mark">${frappe.utils.icon("globe", "lg")}</div>
				<div class="os-plan-body">
					<div class="os-plan-name">${esc(primary.domain)}</div>
					<div class="os-plan-holds">${esc(__("The main address. Sign-in, invitations and links in emails use it."))}</div>
					${given && given !== primary ? `<div class="os-plan-meta">${esc(__("{0} always works too.", [given.domain]))}</div>` : ""}
				</div>
				${frappe.ui.button.html({ label: __("Open"), variant: "outline", attrs: { "data-open-domain": `https://${primary.domain}` } })}
			</div>`
			: "";
		this.$content.html(
			unlinked +
				onedesk.shell.section(__("Addresses"), main + '<div class="os-domains" data-list="domains"></div>') +
				(target && waiting.length
					? onedesk.shell.section(
							__("DNS Records"),
							AccountSection.dns_records(waiting, target) + AccountSection.dns_note(waiting),
							__("Add these at your DNS provider. Each address works a few minutes after its records are found.")
					  )
					: "")
		);
		this.$content.find("[data-open-domain]").on("click", (event) => window.open($(event.currentTarget).attr("data-open-domain"), "_blank", "noopener"));
		const states = { Active: [__("Working"), "green"], Pending: [__("Waiting"), "orange"] };
		const said = (one) =>
			one.status === "Active"
				? ""
				: one.problem
				? one.problem
				: one.status === "Pending"
				? __("Waiting for the DNS records below.")
				: __("Not working. Check the DNS records below, then remove the domain and add it again.");
		onedesk.shell.table(this.$content.find('[data-list="domains"]'), {
			rows,
			icon: "globe",
			empty: __("No domains"),
			columns: [
				{
					label: __("Domain"),
					render: (one) =>
						`<div>${esc(one.domain)} ${one.given ? frappe.ui.badge.html({ label: __("Provided by {0}", [onedesk.names.of("one")]), theme: "gray" }) : ""}</div>${
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
						!changing
							? ""
							: `<div class="one-shell-row-actions" data-domain="${esc(one.domain)}">${
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
	{ id: "profile", about: __("Your name, photo, bio and language.") },
	{ id: "personal", about: __("Where you live, who to call and the details only HR sees.") },
	{ id: "work", about: __("Your job as HR keeps it, and your education and past work.") },
	{ id: "documents", about: __("Your ID, passport and permits. HR is told when you add or change one.") },
	{ id: "signin", about: __("Your password, your passkey and where you are signed in.") },
	{ id: "people", about: __("Everyone in the workspace, and inviting someone new.") },
	{ id: "devices", about: __("The company's computers and phones, and the passkeys on people's own.") },
	{ id: "plan", about: __("The plan, its seats and storage, credits and invoices.") },
	{ id: "domains", about: __("The addresses the workspace answers on.") },
];

// The help page each tab is explained on (account_center/help).
onedesk.account_center.HELP = {
	profile: "your-account",
	personal: "your-account",
	work: "your-account",
	documents: "your-account",
	signin: "your-account",
	people: "people-and-devices",
	devices: "people-and-devices",
	plan: "plan-and-credits",
	domains: "plan-and-credits",
};

// AccountCenter: Yours for everybody, Workspace for administrators. at
// opens one section, and record one record in it, such as a person. It
// starts with what is left to set up, while something is.
onedesk.account_center.open = async ({ at = null, record = null } = {}) => {
	const said = await frappe.xcall(onedesk.AccountSection.API + "sections_of");
	const allowed = Object.fromEntries(said.sections.map((one) => [one.key, one]));
	const named = { yours: __("Yours"), workspace: __("Workspace") };
	const steps = (frappe.boot.one_setup || {}).AccountCenter || [];
	const starting = steps.some((step) => !step.done) ? [{ group: __("Start Here"), items: [onedesk.module_settings.getting_started(onedesk.names.of("account_center"))] }] : [];
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
		title: onedesk.names.of("account_center"),
		center: { center: "account", label: frappe.session.user_fullname, icon: "user" },
		tabs,
		default_tab: ids.includes(at) ? at : ids.find((id) => id !== "getting_started"),
		// Help opens at the page for the tab being read.
		help: (tab) => [onedesk.names.of("account_center"), onedesk.account_center.HELP[tab] || "overview"],
	});
	dialog.$wrapper.addClass("one-set one-account");
	dialog.$wrapper.find(".settings-dialog-sidebar").wrapInner('<div class="one-account-tabs" data-tour="account-tabs"></div>');
	dialog.show();
	// AccountCenter has no foot to start its tour from, so it starts here
	// the first time it opens.
	if ((frappe.boot.one_tours_unseen || []).includes("AccountCenter:account")) {
		setTimeout(async () => {
			const tour = await onedesk.tour.here(onedesk.names.of("account_center"));
			if (tour && dialog.display) onedesk.tour.run(onedesk.names.of("account_center"), tour);
		}, 600);
	}
	return dialog;
};
