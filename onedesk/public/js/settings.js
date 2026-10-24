
frappe.provide("onedesk");

onedesk.Settings = class Settings extends onedesk.shell.Editor {
	static API = "onedesk.one.settings.";

	static WIDE = ["people", "oneai", "intake", "numbering", "printing", "approvals"];
	static theirs = (one) => one.standard === "Yes";
	// A module whose roles are built in its own settings (docs/ROLES.md)
	// opens them there rather than on a role's page here.
	static ROLES_IN = {
		OneMail: () =>
			frappe.require(["/assets/onedesk/js/onemail_settings.js", "/assets/onedesk/css/onemail_settings.css"]).then(() => onedesk.mail.settings("roles")),
	};

	static SHEET = 794;
	static PAGE = 1123;
	static sheet = (top, foot, scale, whole = false) =>
		`<!doctype html><html><head><style>html,body{margin:0;background:#fff;color:#111;font-family:sans-serif}` +
		`body{padding:24px;width:746px;transform:scale(${scale});transform-origin:0 0}img{max-width:100%}` +
		`.lines{height:48px;margin:16px 0;background:repeating-linear-gradient(to bottom,#e5e7eb 0,#e5e7eb 6px,transparent 6px,transparent 14px)}` +
		(whole ? `html{overflow:hidden}body{box-sizing:border-box;width:794px;height:1123px;padding:45px 53px;display:flex;flex-direction:column}.lines{flex:1;height:auto;margin:32px 0;background:repeating-linear-gradient(to bottom,#f3f4f6 0,#f3f4f6 4px,transparent 4px,transparent 22px)}` : "") +
		`</style></head><body>${top || ""}${foot === null ? "" : `<div class="lines"></div>${foot || ""}`}</body></html>`;
	static frame = (html, className) => {
		const it = document.createElement("iframe");
		it.className = className;
		it.setAttribute("sandbox", "");
		it.srcdoc = html;
		return it;
	};

	constructor(page, group) {
		super(page);
		this.group_name = group;
		this.route = group === "workspace" ? "workspace-settings" : "settings";
		this.$section = page.$shell;
		this.kept = {};
		frappe.realtime.on("one_memory", () => this.key === "memory" && this.$content && this.$content.is(":visible") && this.refresh());
		frappe.realtime.on("one_privacy", () => this.key === "profile" && this.$content && this.$content.is(":visible") && this.refresh());
		frappe.realtime.on("one_oneai", () => this.key === "oneai" && this.$content && this.$content.is(":visible") && this.refresh());
		frappe.realtime.on("one_closing", () => this.key === "plan" && this.$content && this.$content.is(":visible") && this.refresh());
		frappe.realtime.on("one_domains", () => this.key === "domains" && this.$content && this.$content.is(":visible") && this.refresh());
	}

	async show() {
		if (!this.said) this.said = await frappe.xcall(Settings.API + "sections");
		const mine = this.said.sections.filter((one) => one.group === this.group_name);
		const params = frappe.utils.get_query_params();
		if (params.section === "agreements") return frappe.set_route("legal");
		const found = mine.find((one) => one.key === params.section) || mine[0];
		this.for_doctype = params.rule === "new" ? params.for || null : null;
		if (found)
			this.open(found.key, {
				record: params.type || params.person || params.list || (params.rule ? `rule:${params.rule}` : null) || (params.level ? `level:${params.level}` : null) ||
					(params.profile ? `profile:${params.profile}` : null) ||
					(params.group ? `group:${params.group}` : null),
			});
	}

	async open(key, { fresh = false, record = null } = {}) {
		const slot = (k, r) => (r ? `${k}:${r}` : k);
		if (this.dirty && this.values) this.kept[slot(this.key, this.record)] = { values: this.values(), opened: this.opened };
		if (fresh) delete this.kept[slot(key, record)];
		this.key = key;
		this.record = record;
		this.unsaved();
		const section = this.said.sections.find((one) => one.key === key);
		onedesk.shell.name(section.label);
		this.$content = onedesk.shell.body(this.$section, { wide: Settings.WIDE.includes(key) });
		try {
			this.data = await frappe.xcall(Settings.API + "load", { section: key, record });
			if (record === "rule:new" && this.for_doctype && this.data.values) this.data.values.document_type = this.for_doctype;
		} catch (e) {
			this.$content.html(frappe.ui.alert.html({ title: __("This section could not be opened."), theme: "red" }));
			return;
		}
		this.$content.empty();
		this.hear(this.data.opened);
		this[`draw_${key}`](this.data);
		if (!this.trailed) onedesk.shell.name(section.label);
		await this.bring_back(slot(key, record));
	}

	async bring_back(key) {
		const kept = this.kept[key];
		delete this.kept[key];
		if (!kept || !this.values) return;
		await this.ready;
		await this.group.set_values(kept.values);
		this.check();
		const moved = kept.opened.some((one) => this.opened.some((now) => now.doctype === one.doctype && now.name === one.name && now.modified !== one.modified));
		if (moved) this.conflict();
	}

	saver(values) {
		return { method: Settings.API + "save", args: { section: this.key, values, record: this.record } };
	}

	redraw(said) {
		const [kind, name] = (said.record || "").split(/:(.*)/s);
		if (said.record && said.record !== this.record && ["rule", "level", "profile", "group"].includes(kind)) {
			frappe.set_route(this.route, { section: this.key, [kind]: name });
			return;
		}
		if (this.trailed) {
			this.unsaved();
			this.$content = onedesk.shell.body(this.$section, { wide: Settings.WIDE.includes(this.key) });
		}
		this[`draw_${this.key}`](said);
	}

	refresh({ fresh = false } = {}) {
		this.open(this.key, { fresh, record: this.record });
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

	draw_notifications(data) {
		const rows = [{ stack: ["enabled", "enable_email_notifications"] }];
		for (const group of data.groups) rows.push({ heading: group.app }, ...group.rows.map((row) => ({ row, css: "os-kind" })));
		rows.push({ heading: __("Other Emails") }, { stack: ["enable_email_threads_on_assigned_document"] });
		const fewer = onedesk.oneai.button(
			__("Too Many Emails?"),
			__("Which of the notifications I get by email could I leave to the bell, or have pushed instead? Say which to untick and why.")
		);
		const note = __("All notifications appear in One.");
		const $card = this.form(data, {
			before: `<div class="os-notify-intro"><div class="one-shell-quiet">${note}</div>${fewer}</div><div class="os-push"></div>`,
			rows,
		});
		const columns = `<div class="os-kind-columns"><span>${__("Email")}</span><span>${__("Push")}</span></div>`;
		$card.find(".form-section.os-kind.one-shell-part .section-head").each((at, head) => {
			const mark = (data.groups[at] || {}).mark;
			if (mark) $(head).prepend(`<span class="os-kind-mark">${frappe.utils.icon(mark, "md")}</span>`);
			$(head).append(columns);
		});
		$card.find(".os-kind .frappe-control[data-fieldtype='Switch']").each((_, control) => {
			const $control = $(control);
			const name = $control.closest(".section-body").find(".os-kind-name").first().text();
			$control.find("input").attr("aria-label", `${$control.find(".label-area").text()}: ${name}`);
		});
		this.ready.then(() => {
			$card.find("[data-oneai-tag]").replaceWith(onedesk.oneai.tag(__("OneAI")));
			for (const field of this.group.fields_list) {
				if (field.df.fieldtype !== "Switch" || !field.df.read_only) continue;
				field.$wrapper.addClass("os-switch-fixed").toggleClass("os-switch-on", !!cint(field.get_value()));
			}
		});
		this.draw_push($card.find(".os-push"), data.push);
	}

	async draw_push($part, said) {
		const esc = frappe.utils.escape_html;
		const here = await onedesk.push.state();
		const words = {
			on: [__("On in this browser"), "green"],
			off: [__("Off in this browser"), "gray"],
			blocked: [__("Blocked in this browser"), "orange"],
			unsupported: [__("Not supported in this browser"), "gray"],
		}[here.state];
		const others = (said.devices || []).filter((one) => one.endpoint !== here.endpoint);
		const action =
			here.state === "off"
				? onedesk.shell.button(__("Turn On Push"), { "data-push": "on" }, "subtle", "bell-ring")
				: here.state === "on"
				? onedesk.shell.button(__("Send Test"), { "data-push": "test" }, "subtle") + onedesk.shell.button(__("Turn Off"), { "data-push": "off" }, "ghost")
				: "";
		$part.html(
			onedesk.shell.row({
				title: esc(__("Push")),
				sub: frappe.ui.badge.html({ label: words[0], theme: words[1] }),
				quiet: here.state === "blocked" ? esc(__("Allow notifications for this site in your browser settings.")) : "",
				actions: action,
			}) + '<div class="os-push-others"></div>'
		);
		const again = async () => this.draw_push($part, await frappe.xcall("onedesk.one.push.devices"));
		if (others.length) {
			onedesk.shell.table($part.find(".os-push-others"), {
				title: __("Other Browsers"),
				rows: others,
				icon: "bell-ring",
				columns: [
					{ label: __("Browser"), render: (one) => esc(one.label || "") },
					{
						label: __("Last Sent"),
						render: (one) =>
							`<span class="one-shell-quiet">${esc(one.last_sent ? frappe.datetime.prettyDate(one.last_sent) : __("Never"))}</span>`,
					},
					{
						type: "actions",
						actions: [
							{
								label: __("Remove"),
								icon: "trash-2",
								danger: true,
								action: async (one) => {
									await frappe.xcall("onedesk.one.push.forget", { name: one.name });
									again();
								},
							},
						],
					},
				],
			});
		}
		$part.find('[data-push="on"]').on("click", async () => {
			let on = false;
			try {
				on = await onedesk.push.on(said.key);
			} catch (e) {
				on = false;
			}
			if (!on) frappe.show_alert({ message: __("Couldn't turn on push. Private windows don't support it."), indicator: "orange" });
			again();
		});
		$part.find('[data-push="off"]').on("click", async () => {
			await onedesk.push.off();
			again();
		});
		$part.find('[data-push="test"]').on("click", async () => {
			const r = await frappe.xcall("onedesk.one.push.test");
			frappe.show_alert({ message: r.sent ? __("Test sent") : __("Couldn't send test"), indicator: r.sent ? "green" : "orange" });
		});
	}

	draw_calendar(data) {
		const how = onedesk.oneai.button(
			__("How Do I Add It?"),
			__("How do I add my calendar to Google Calendar, Apple Calendar or Outlook?")
		);
		const $card = $(
			onedesk.shell.section(
				__("Calendar Link"),
				`<div class="os-calendar"></div><div class="one-shell-actions">${how}</div>`
			)
		).appendTo(this.$content);
		const draw = (link) => {
			const $body = $card.find(".os-calendar");
			if (!data.allowed) {
				$body.html(`<div class="one-shell-quiet">${__("Calendar links are turned off for this workspace.")}</div>`);
				$card.find(".one-shell-actions").remove();
				return;
			}
			if (!link) {
				$body.html(`<div class="one-shell-quiet">${__("No calendar link")}</div>`);
				this.page.set_primary_action(__("Create Link"), async () => draw(await frappe.xcall("onedesk.one_calendar.feed.mine")), "link");
				return;
			}
			$body.html(onedesk.calendar_link.html(link, { copy: false }));
			onedesk.calendar_link.bind($body, link, { drawn: draw, stopped: () => draw(null) });
			this.page.set_primary_action(__("Copy Link"), () => onedesk.calendar_link.copy(link), "copy");
		};
		draw(data.link);
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
			columns: Settings.session_columns((one) =>
				one.here ? frappe.ui.badge.html({ label: __("This Device"), theme: "blue" }) : onedesk.shell.button(__("Sign Out"), { "data-sign-out": one.key }, "ghost", "log-out")
			),
		});
		if (data.recent.length) {
			onedesk.shell.table(this.$content.find('[data-list="recent"]'), {
				title: __("Recent Sign-ins"),
				rows: data.recent,
				columns: Settings.signin_columns(),
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
			await frappe.xcall("onedesk.one.signin.sign_out", { key_of: $(event.currentTarget).attr("data-sign-out") });
			frappe.show_alert({ message: __("Signed out"), indicator: "green" });
			this.open("signin");
		});
		this.$content.on("click", "[data-elsewhere]", () =>
			frappe.confirm(__("Sign out other sessions? You'll be signed out on every other device."), async () => {
				await frappe.xcall(Settings.API + "sign_out_elsewhere");
				frappe.show_alert({ message: __("Other sessions signed out"), indicator: "green" });
				this.open("signin");
			})
		);
	}

	static read_switch(on) {
		return `<span class="switch-control one-read-switch" aria-hidden="true"><span class="input-area"><input type="checkbox" tabindex="-1" ${
			on ? "checked" : ""
		}></span><span class="switch-visual"><span class="switch-thumb"></span></span></span>`;
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

	async draw_memory(data) {
		const esc = frappe.utils.escape_html;
		const know = onedesk.oneai.button(
			__("What Do You Know About Me?"),
			__("What do you know about me? Say what you remember from our conversations, and what my workspace told you.")
		);
		const facts = data.facts || [];
		const knowledge = data.knowledge || [];
		this.$content.html(
			`<div class="one-shell-section"><div class="os-notify-intro"><div class="one-shell-quiet">${esc(
				__("Only you can see your memories.")
			)}</div>${know}</div></div>
			<div class="one-shell-section os-memories" data-list="remembered"></div>
			${knowledge.length ? '<div class="one-shell-section" data-list="workspace"></div>' : ""}`
		);
		this.page.set_primary_action(__("Add Memory"), () => this.memory_dialog(), "plus");
		const redraw = (said) => {
			this.$content.empty();
			this.draw_memory(said);
		};
		const remembered = await onedesk.shell.table(this.$content.find('[data-list="remembered"]'), {
			title: __("Memories"),
			rows: facts,
			icon: "brain",
			empty: __("No memories"),
			none: __("No matching memories"),
			open: (one) => this.memory_dialog(one),
			actions: facts.length > 1 ? frappe.ui.button.html({ label: __("Forget All"), variant: "ghost", theme: "red", attrs: { "data-forget-all": "1" } }) : "",
			columns: [
				{ label: __("Memory"), fieldname: "fact" },
				{
					label: __("About"),
					render: (one) =>
						one.about_doctype
							? `<a href="${frappe.utils.get_form_link(one.about_doctype, one.about_name)}" onclick="event.stopPropagation();">${esc(one.about_title || one.about_name)}</a>`
							: "",
				},
				{ label: __("Added"), render: (one) => `<span class="one-shell-quiet">${esc(frappe.datetime.prettyDate(one.creation))}</span>` },
				{
					type: "actions",
					actions: [
						{
							label: __("Forget"),
							icon: "trash-2",
							danger: true,
							action: async (one) => redraw(await frappe.xcall(Settings.API + "forget", { name: one.name })),
						},
					],
				},
			],
		});
		remembered.$header.find("[data-forget-all]").on("click", () =>
			frappe.confirm(__("Forget all memories? This can't be undone."), async () => redraw(await frappe.xcall(Settings.API + "forget_all")))
		);
		if (knowledge.length) {
			onedesk.shell.table(this.$content.find('[data-list="workspace"]'), {
				title: __("Workspace Knowledge"),
				rows: knowledge,
				columns: [
					{ label: __("Title"), fieldname: "title" },
					{ label: __("Applies To"), render: (one) => esc(one.applies_to || __("Everything")) },
				],
			});
		}
	}

	memory_dialog(one = null) {
		const dialog = new frappe.ui.Dialog({
			title: one ? __("Edit Memory") : __("Add Memory"),
			fields: [
				{ fieldname: "fact", fieldtype: "Small Text", label: __("Memory"), reqd: 1, default: one ? one.fact : "" },
				{ fieldname: "about_doctype", fieldtype: "Link", options: "DocType", label: __("Record Type"), default: one ? one.about_doctype : "" },
				{ fieldname: "about_name", fieldtype: "Dynamic Link", options: "about_doctype", label: __("Record"), depends_on: "about_doctype", default: one ? one.about_name : "" },
			],
			primary_action_label: one ? __("Save") : __("Add"),
			primary_action: async (values) => {
				const said = await frappe.xcall(Settings.API + "keep", { ...values, name: one ? one.name : null });
				dialog.hide();
				this.$content.empty();
				this.draw_memory(said);
			},
		});
		dialog.show();
	}

	// signing in. Every field is System Settings', Company's or Global Defaults' own.
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
		const rows = [
			{ heading: __("Company"), note: __("The currency can't change once there are transactions.") },
			{ html: `<dl class="os-facts">${facts}</dl>` },
			["email_footer_address", ""],
			{ heading: __("Contact and Branding") },
			["company_logo", "one_brand_colour"],
			["one_frame_colour", ""],
			["phone_no", "email"],
			["website", "tax_id"],
			["address_line1", "address_line2"],
			["city", "state"],
			["pincode", ""],
			{ heading: __("Region and Formats") },
			["language", "time_zone"],
			["date_format", "time_format"],
			["number_format", "first_day_of_the_week"],
			{ html: `<div class="one-shell-quiet os-reads" data-reads="1"></div>` },
			{ stack: ["hide_currency_symbol", "disable_rounded_total", "disable_in_words"] },
			{ heading: __("Sign-in") },
			["one_two_factor", "two_factor_method"],
			["session_expiry", "one_password"],
			["allow_consecutive_login_attempts", "allow_login_after_fail"],
			["force_user_to_reset_password", ""],
			{ stack: ["one_login_with_passkey", "login_with_email_link", "deny_multiple_sessions"] },
			{ heading: __("Sharing") },
			{ stack: ["one_calendar_links", "one_record_sharing"] },
			{
				heading: __("Start Again"),
				note: __("Customers, items, people and settings stay."),
			},
			{ html: onedesk.shell.button(__("Delete All Transactions"), { "data-start-again": "1" }, "subtle", "trash-2") },
		];
		const $card = this.form(data, { rows });
		$card.on("click", "[data-start-again]", () =>
			frappe.confirm(__("Every sale, purchase, stock move, project, payslip, lead and asset is deleted. This can't be undone."), () =>
				frappe
					.call({ method: "onedesk.one.start_again.start", type: "POST", freeze: true })
					.then((r) => frappe.set_route("Form", "Transaction Deletion Record", r.message))
			)
		);
		const reads = () => {
			const values = this.values();
			const now = values.time_zone && moment.tz && moment.tz.zone(values.time_zone) ? moment().tz(values.time_zone) : moment();
			const date = now.format((values.date_format || "dd-mm-yyyy").toUpperCase());
			const time = now.format(values.time_format || "HH:mm:ss");
			const number = format_number(1234567.89, values.number_format, 2);
			$card.find("[data-reads]").text(__("Preview: {0}", [`${date} ${time}, ${number}`]));
		};
		this.ready.then(reads);
		$card.on("change input", "select, input", () => setTimeout(reads));
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
			open: (one) => frappe.set_route("workspace-settings", { section: "people", person: one.name }),
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
								.filter((app) => one.access[app.name] !== "None")
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
							await frappe.xcall(Settings.API + "sign_out_everywhere", { user: one.name });
							this.refresh({ fresh: true });
							done(__("Signed out everywhere."));
						}),
				},
				{
					label: __("Send Password Reset"),
					group: __("Actions"),
					action: async () => {
						await frappe.xcall(Settings.API + "send_reset", { user: one.name });
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
					await frappe.xcall(Settings.API + "invite_again", { user: one.name });
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
									await frappe.xcall(Settings.API + "set_enabled", { user: one.name, on: 0 });
									this.refresh({ fresh: true });
								}),
					  }
					: {
							label: __("Enable"),
							group: __("Actions"),
							action: async () => {
								await frappe.xcall(Settings.API + "set_enabled", { user: one.name, on: 1 });
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
			parent: __("People"),
			route: "/desk/workspace-settings?section=people",
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
			...Settings.pairs(apps),
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
		Settings.marks($card, data.apps);
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
				columns: Settings.session_columns(),
			});
		}
		onedesk.shell.table($card.find('[data-list="recent"]'), { rows: one.recent, columns: Settings.signin_columns() });
	}

	draw_access(data) {
		if (data.level) return this.draw_level(data);
		if (data.profile) return this.draw_job_profile(data);
		if (data.group) return this.draw_group(data);
		const esc = frappe.utils.escape_html;
		const named = (title, method, key, more = []) => {
			const dialog = new frappe.ui.Dialog({
				title,
				fields: [{ fieldname: "title", fieldtype: "Data", label: __("Name"), reqd: 1 }, ...more],
				primary_action_label: __("Create"),
				primary_action: async ({ title, members }) => {
					const name = await frappe.xcall(`onedesk.one.access.${method}`, { title, ...(members ? { members } : {}) });
					dialog.hide();
					frappe.set_route("workspace-settings", { section: "access", [key]: name });
				},
			});
			dialog.show();
		};
		this.page.set_primary_action(__("New Role"), () => this.new_level(data), "plus");
		this.$content.html(
			`<div class="one-shell-section" data-list="levels"></div><div class="one-shell-section" data-list="profiles"></div><div class="one-shell-section" data-list="groups"></div>`
		);
		const levels = Object.fromEntries(data.levels.map((one) => [one.name, one.name]));
		const said = (level) => ({ None: null, User: __("User"), Manager: __("Manager") })[level] ?? levels[level] ?? level;
		onedesk.shell.table(this.$content.find('[data-list="profiles"]'), {
			title: __("Profiles"),
			rows: data.profiles,
			icon: "id-card",
			empty: __("No profiles"),
			actions: $(onedesk.shell.button(__("New Profile"), {}, "subtle", "plus")).on("click", () => named(__("New Profile"), "new_profile", "profile")),
			open: (one) => frappe.set_route("workspace-settings", { section: "access", profile: one.name }),
			columns: [
				{ label: __("Profile"), render: (one) => esc(one.name) },
				{
					label: __("Apps"),
					render: (one) =>
						Object.entries(one.levels)
							.filter(([, level]) => level !== "None")
							.map(([app, level]) => frappe.ui.badge.html({ label: `${app} · ${said(level)}`, theme: level === "Manager" ? "blue" : level === "User" ? "gray" : "purple" }))
							.join(" ") || `<span class="one-shell-quiet">${esc(__("Standard Apps"))}</span>`,
				},
				{ label: __("People"), render: (one) => esc(String(one.people)) },
			],
		});
		onedesk.shell.table(this.$content.find('[data-list="groups"]'), {
			title: __("Groups"),
			rows: data.groups,
			icon: "users-round",
			empty: __("No groups"),
			actions: $(onedesk.shell.button(__("New Group"), {}, "subtle", "plus")).on("click", () =>
				frappe.model.with_doctype("User Group Member", () =>
					named(__("New Group"), "new_group", "group", [
						{ fieldname: "members", fieldtype: "Table MultiSelect", options: "User Group Member", label: __("Members"), reqd: 1 },
					])
				)),
			open: (one) => frappe.set_route("workspace-settings", { section: "access", group: one.name }),
			columns: [
				{ label: __("Group"), render: (one) => esc(one.name) },
				{ label: __("People"), render: (one) => esc(String(one.members)) },
			],
		});
		const tier = (one) => (one.own ? esc(one.name) : esc(__(one.name)));
		onedesk.shell.table(this.$content.find('[data-list="levels"]'), {
			title: __("Roles"),
			note: __("Custom roles sit between User and Manager."),
			rows: data.levels,
			icon: "shield-check",
			none: __("No matching roles"),
			open: (one) => (Settings.ROLES_IN[one.app] ? Settings.ROLES_IN[one.app]() : frappe.set_route("workspace-settings", { section: "access", level: one.key })),
			columns: [
				{
					label: __("Role"),
					render: (one) => tier(one) + (one.own ? " " + frappe.ui.badge.html({ label: __("Custom"), theme: "purple" }) : ""),
				},
				{ label: __("App"), render: (one) => onedesk.shell.app(one.app, one.icon) },
				{ label: __("People"), render: (one) => esc(String(one.people)) },
			],
		});
	}

	new_level(data) {
		const starts = (app) => [
			{ value: "User", label: __("User") },
			...data.levels.filter((one) => one.app === app && one.own).map((one) => ({ value: one.name, label: one.name })),
			{ value: "Manager", label: __("Manager") },
		];
		const dialog = new frappe.ui.Dialog({
			title: __("New Role"),
			fields: [
				{ fieldname: "title", fieldtype: "Data", label: __("Name"), reqd: 1, description: __("For example, Senior Sales.") },
				{
					fieldname: "app",
					fieldtype: "Select",
					label: __("App"),
					reqd: 1,
					options: data.apps.map((app) => app.name),
					change: () => {
						const field = dialog.get_field("start");
						field.df.options = starts(dialog.get_value("app"));
						field.refresh();
						dialog.set_value("start", "User");
					},
				},
				{
					fieldname: "start",
					fieldtype: "Select",
					label: __("Based On"),
					reqd: 1,
					default: "User",
					options: starts(data.apps[0].name),
					description: __("Starts with this role's abilities and permissions."),
				},
			],
			primary_action_label: __("Create"),
			primary_action: async ({ title, app, start }) => {
				const name = await frappe.xcall("onedesk.one.access.make_level", { app, title, start });
				dialog.hide();
				if (Settings.ROLES_IN[app]) return Settings.ROLES_IN[app]();
				frappe.set_route("workspace-settings", { section: "access", level: name });
			},
		});
		dialog.show();
	}

	draw_level(data) {
		const esc = frappe.utils.escape_html;
		const level = data.level;
		const title = level.own ? level.name : `${level.app} ${__(level.name)}`;
		this.as_record({
			parent: __("Access"),
			route: "/desk/workspace-settings?section=access",
			title,
			status: { label: level.app, colour: "purple" },
			side: onedesk.shell.side({
				mark: level.icon,
				title,
				sub: esc(level.own ? __("Custom role of {0}", [level.app]) : level.name === "User" ? __("Everyone who uses {0}", [level.app]) : __("Everyone who manages {0}", [level.app])),
				groups: [
					{
						label: __("People"),
						html: level.people.length
							? level.people
									.map((one) => `<a class="one-record-link" href="/desk/workspace-settings?section=people&person=${encodeURIComponent(one.name)}">${esc(one.full_name || one.name)}</a>`)
									.join("")
							: `<div class="one-shell-quiet">${esc(__("No people"))}</div>`,
					},
				],
			}),
			actions: level.own
				? [
						{
							label: __("Delete"),
							group: __("Actions"),
							action: () =>
								frappe.confirm(__("Delete {0}? This removes its permissions.", [esc(level.name)]), async () => {
									await frappe.xcall("onedesk.one.access.remove_level", { name: level.name });
									frappe.set_route("workspace-settings", { section: "access" });
								}),
						},
					]
				: [],
		});
		// What the role may do in the module, grouped as the module groups
		// it (one/abilities.py), then its record types.
		const groups = [];
		for (const one of data.abilities || []) {
			const group = groups.find((g) => g.label === one.group) || groups[groups.push({ label: one.group, fields: [] }) - 1];
			group.fields.push(one.fieldname);
		}
		this.form(data, {
			rows: [
				...(level.own ? [{ stack: ["title"] }] : []),
				...groups.flatMap((group, i) => [
					{ heading: group.label, note: i || level.name === "User" ? "" : __("A role above User has everything User has.") },
					...Settings.pairs(group.fields),
				]),
				...(data.matrix
					? [
							{
								heading: __("Record Types"),
								note: __("Every permission includes Read."),
							},
							{ stack: ["rows"] },
					  ]
					: []),
			],
		});
	}

	draw_job_profile(data) {
		const esc = frappe.utils.escape_html;
		const one = data.profile;
		this.as_record({
			parent: __("Access"),
			route: "/desk/workspace-settings?section=access",
			title: one.name,
			status: { label: __("Profile"), colour: "blue" },
			side: onedesk.shell.side({
				initials: frappe.get_abbr(one.name),
				title: one.name,
				groups: [
					{
						label: __("People"),
						html: one.people.length
							? one.people
									.map((who) => `<a class="one-record-link" href="/desk/workspace-settings?section=people&person=${encodeURIComponent(who.name)}">${esc(who.full_name || who.name)}</a>`)
									.join("")
							: `<div class="one-shell-quiet">${esc(__("No people"))}</div>`,
					},
				],
			}),
			actions: [
				{
					label: __("Delete"),
					group: __("Actions"),
					action: () =>
						frappe.confirm(__("Delete {0}? The people on it keep their apps.", [esc(one.name)]), async () => {
							await frappe.xcall("onedesk.one.access.remove_profile", { name: one.name });
							frappe.set_route("workspace-settings", { section: "access" });
						}),
				},
			],
		});
		const $card = this.form(data, {
			rows: [
				{ stack: ["title"] },
				{ heading: __("Apps"), note: __("Saving updates everyone with this profile.") },
				...Settings.pairs(data.apps.map((app) => `app_${app.icon}`)),
			],
		});
		Settings.marks($card, data.apps);
	}

	draw_group(data) {
		const esc = frappe.utils.escape_html;
		const one = data.group;
		this.as_record({
			parent: __("Access"),
			route: "/desk/workspace-settings?section=access",
			title: one.name,
			status: { label: __("{0} people", [one.members]), colour: "gray" },
			side: onedesk.shell.side({ initials: frappe.get_abbr(one.name), title: one.name, sub: esc(__("Group")) }),
			actions: [
				{
					label: __("Delete"),
					group: __("Actions"),
					action: () =>
						frappe.confirm(__("Delete {0}? Records assigned to it stay with the people who had them.", [esc(one.name)]), async () => {
							await frappe.xcall("onedesk.one.access.remove_group", { name: one.name });
							frappe.set_route("workspace-settings", { section: "access" });
						}),
				},
			],
		});
		frappe.model.with_doctype("User Group Member", () =>
			this.form(data, {
				rows: [
					{ stack: ["title"] },
					{ heading: __("Members") },
					{ stack: ["members"] },
				],
			})
		);
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

	static marks($wrapper, apps) {
		for (const app of apps) {
			$wrapper.find(`.frappe-control[data-fieldname="app_${app.icon}"] .control-label`).first().prepend(`<span class="one-shell-app-mark">${frappe.utils.icon(app.icon, "sm")}</span>`);
		}
	}

	static pairs(names) {
		const rows = [];
		for (let at = 0; at < names.length; at += 2) rows.push([names[at], names[at + 1] || ""]);
		return rows;
	}

	static two_columns(list, field) {
		const half = Math.ceil(list.length / 2);
		return list.flatMap((one, at) => [...(at === half ? [{ fieldtype: "Column Break" }] : []), field(one, at)]);
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
				...Settings.two_columns(data.apps, (app) => ({ fieldname: `app_${app.icon}`, fieldtype: "Select", label: app.name, options: app.levels, default: "None" })),
			],
			primary_action_label: __("Invite"),
			primary_action: async (values) => {
				const access = Object.fromEntries(data.apps.map((app) => [app.name, values[`app_${app.icon}`]]));
				const said = await frappe.xcall(Settings.API + "invite", { email: values.email, first_name: values.first_name, last_name: values.last_name, access });
				dialog.hide();
				frappe.show_alert({ message: __("Invitation sent"), indicator: "green" });
				this.data = said;
				this.$content.empty();
				this.draw_people(said);
			},
		});
		Settings.marks(dialog.$wrapper, data.apps);
		dialog.show();
	}

	draw_plan(data) {
		const esc = frappe.utils.escape_html;
		const account = data.account || {};
		const number = (value) => format_number(value || 0, null, 0);
		const money = (value) => format_currency(value || 0, account.plan_currency || "USD", 0);
		this.page.set_primary_action(__("Change Plan"), () => this.change_plan(), "arrow-up-down");
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
							["/desk/workspace-settings?section=people", __("People")],
							["/desk/onecloud", __("OneCloud")],
							["/desk/query-report/AI Credits", __("Credit Usage")],
						]
							.map(([href, label]) => `<li><a class="one-record-link" href="${esc(href)}">${esc(label)}</a></li>`)
							.join("")}</ul>`,
					},
				],
				meta: [account.last_heard ? __("As of {0}", [frappe.datetime.prettyDate(account.last_heard)]) : __("Not synced yet")],
			}),
			actions: [
				{ label: __("Storage, Database or Seats"), action: () => this.add_to_plan(data), group: __("Add") },
				{ label: __("OneAI Credits"), action: () => this.buy_credits(), group: __("Add") },
				{ label: __("Payment Method"), action: () => this.payment_portal() },
				{ label: __("Billing Owner"), action: () => this.move_billing(account) },
				{ label: __("Check Again"), action: () => this.check_again() },
			],
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
						[__("Seats"), `<a href="/desk/workspace-settings?section=people">${esc(seats)}</a>`],
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
					data.ledger ? '<div data-list="ledger"></div>' : `<div class="one-shell-quiet">${esc(__("Couldn't load the ledger."))}</div>`,
					__("Last {0} days.", [data.ledger_days])
				) +
				this.closing_section(closing)
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
				open: (one) => one.day && frappe.set_route("query-report", "AI Credits", { from_date: one.day, to_date: one.day, by: "Person" }),
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
			window.open("/api/method/onedesk.one.closing.download");
			return;
		}
		if (what === "prepare") {
			await frappe.xcall("onedesk.one.closing.prepare");
			frappe.show_alert({ message: __("Creating the download. You'll be notified when it's ready."), indicator: "blue" });
			return this.refresh();
		}
		if (what === "keep") {
			await frappe.xcall("onedesk.one.closing.keep");
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
				{ fieldtype: "Check", fieldname: "sure", label: __("I understand everything in it will be deleted"), reqd: 1 },
			],
			primary_action_label: __("Close Workspace"),
			primary_action: async (values) => {
				if (!values.sure) return frappe.msgprint(__("Confirm that you understand first."));
				await frappe.xcall("onedesk.one.closing.close", { password: values.password });
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
			said = await frappe.xcall("onedesk.one.bills.invoices");
		} catch (e) {
			return $into.html(`<div class="one-shell-quiet">${esc(__("Couldn't load invoices."))}</div>`);
		}
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
			const bill = await frappe.xcall("onedesk.one.bills.to_books", { invoice: $(event.currentTarget).attr("data-book") });
			frappe.show_alert({ message: __("Added to OneBook as a draft bill."), indicator: "green" });
			frappe.set_route("Form", "Purchase Invoice", bill);
		});
		$into.on("click", "a[target=_blank]", (event) => event.stopPropagation());
		return list;
	}

	async payment_portal() {
		const said = await frappe.xcall("onedesk.one.bills.payment_portal");
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
								title: __("{0} gives you this for {1} a month, {2} less.", [
									[better.label, ...better.extras.map((one) => __("{0} × {1}", [one.count, one.label]))].join(" + "),
									money(better.monthly),
									money(better.saves),
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

	draw_numbering(data) {
		const esc = frappe.utils.escape_html;
		const again = () => this.key === "numbering" && this.open("numbering", { fresh: true });
		const naming = (doctype) => onedesk.doctype_settings.open(doctype, "naming", again);
		this.page.set_primary_action(__("Set Up Naming"), () => onedesk.numbering.set_up(naming), "plus");
		this.$content.html(`<div class="one-shell-section" data-list="numbering"></div>`);
		onedesk.shell.table(this.$content.find('[data-list="numbering"]'), {
			title: __("Numbering"),
			rows: data.rows || [],
			page_size: 100,
			icon: "hash",
			empty: __("No numbered records"),
			none: __("No matching records"),
			open: (one) => naming(one.doctype),
			columns: [
				{ label: __("Record Type"), fieldname: "label" },
				{ label: __("Naming Rule"), fieldname: "named_by" },
				{
					label: __("Series"),
					render: (one) =>
						one.series
							? `<samp>${esc(one.series)}</samp>` + (one.others ? " " + frappe.ui.badge.html({ label: __("+{0} more", [one.others]), theme: "gray" }) : "")
							: "",
				},
				{ label: __("Next"), render: (one) => (one.next ? `<samp>${esc(one.next)}</samp>` : "") },
				{ label: __("Document Naming Rules"), render: (one) => (one.rules ? esc(String(one.rules)) : "") },
			],
		});
	}

	draw_approvals(data) {
		const esc = frappe.utils.escape_html;
		this.page.set_primary_action(__("New Approval"), () => onedesk.approvals.create(), "plus");
		this.$content.html(`<div class="one-shell-section" data-list="approvals"></div>`);
		onedesk.shell.table(this.$content.find('[data-list="approvals"]'), {
			title: __("Approvals"),
			rows: data.rows || [],
			page_size: 100,
			icon: "route",
			empty: __("No approvals"),
			none: __("No matching approvals"),
			open: (one) => frappe.set_route("workflow-builder", one.name),
			columns: [
				{
					label: __("Approval"),
					render: (one) => esc(one.workflow_name || one.name) + (one.is_active ? " " + frappe.ui.badge.html({ label: __("Active"), theme: "green" }) : ""),
				},
				{ label: __("Record Type"), fieldname: "label" },
				{ label: __("Steps"), render: (one) => esc(String(one.steps)) },
			],
		});
	}

	draw_printing(data) {
		const esc = frappe.utils.escape_html;
		this.page.set_primary_action(__("New Letter Head"), () => this.letter_head(), "plus");
		const kinds = [...new Map((data.formats || []).map((one) => [one.doc_type, one.label])).entries()];
		this.$content.html(
			onedesk.shell.section(
				__("Letter Heads"),
				'<div class="one-print-heads"></div>'
			) +
				onedesk.shell.section(
					__("Print Formats"),
					'<div class="one-print-kinds"></div>'
				)
		);
		const $heads = this.$content.find(".one-print-heads");
		const heads = data.letter_heads || [];
		if (!heads.length) {
			$heads.html(onedesk.shell.empty(__("No letter heads"), null, { icon: "image" }));
		} else {
			const $grid = $('<div class="dts-pf-grid"></div>').appendTo($heads);
			heads.forEach((one) => $grid.append(this.letter_head_card(one)));
		}
		const $kinds = this.$content.find(".one-print-kinds");
		if (!kinds.length) {
			$kinds.html(onedesk.shell.empty(__("No print formats"), null, { icon: "printer" }));
			return;
		}
		frappe.require("doctype_settings.bundle.js", () => {
			onedesk.doctype_settings.adapt();
			for (const [doctype, label] of kinds) {
				frappe.model.with_doctype(doctype, () => {
					const panel = new frappe.ui.SettingsDialogPanel({ hide() {} }, {});
					const set_view = panel.set_view.bind(panel);
					panel.set_view = (view) => set_view({ ...view, title: __(label), description: null });
					panel.$el.appendTo($kinds);
					frappe.doctype_settings.builders["print-format"](panel, doctype);
				});
			}
		});
	}

	letter_head_card(one) {
		const $card = $(`
			<div class="dts-pf-card${one.is_default ? " is-default" : ""}">
				<div class="dts-pf-preview">
					<div class="dts-pf-badge one-print-badges">${[
						Settings.theirs(one) ? frappe.ui.badge.html({ label: __("Standard"), theme: "gray" }) : "",
						one.disabled ? frappe.ui.badge.html({ label: __("Disabled"), theme: "gray" }) : "",
					].join("")}</div>
					<button type="button" class="dts-pf-star" data-selected="${one.is_default ? "true" : "false"}">${frappe.utils.icon("star", "sm")}</button>
					<div class="dts-pf-thumb"></div>
				</div>
				<div class="dts-pf-footer"><span class="dts-pf-name ellipsis"></span></div>
			</div>`);
		const $thumb = $card.find(".dts-pf-thumb");
		$card.find(".dts-pf-name").text(one.name).on("click", () => this.letter_head(one));
		$thumb.on("click", () => this.letter_head(one));
		const $star = $card.find(".dts-pf-star");
		if (one.is_default) {
			$star.attr("title", __("Default"));
		} else {
			$star.attr("title", __("Set as Default")).on("click", async (e) => {
				e.stopPropagation();
				await frappe.xcall("onedesk.one.printing.save_letter_head", { values: { name: one.name, modified: one.modified, is_default: 1 } });
				frappe.show_alert({ message: __("Default updated"), indicator: "green" });
				this.refresh({ fresh: true });
			});
		}
		requestAnimationFrame(() => {
			const scale = ($thumb.width() || 200) / Settings.SHEET;
			$thumb.append(Settings.frame(Settings.sheet(one.drawn_top, one.drawn_foot || "", scale, true), "one-print-head-frame"));
		});
		return $card;
	}

	letter_head(one = null) {
		const theirs = !!one && Settings.theirs(one);
		const esc = frappe.utils.escape_html;
		const kept = one && one.one_top ? frappe.utils.parse_json(one.one_top) : null;
		let preset = one ? (kept && kept.preset) || null : "classic";
		const shows = (kept && kept.show) || ["address", "phone", "email", "website"];
		const kept_foot = one && one.one_foot ? frappe.utils.parse_json(one.one_foot) : null;
		let foot = one ? (kept_foot && kept_foot.preset) || (one.footer ? null : "none") : "centred";
		const foot_shows = (kept_foot && kept_foot.show) || ["phone", "website", "tax_id"];
		const SHOWN = [
			["name", __("Name")],
			["address", __("Address")],
			["phone", __("Phone")],
			["email", __("Email")],
			["website", __("Website")],
			["tax_id", __("Tax ID")],
		];
		const page = Settings.sheet;
		const frame = Settings.frame;
		const dialog = new frappe.ui.Dialog({
			title: one ? one.name : __("New Letter Head"),
			size: theirs ? "" : "extra-large",
			fields: [
				...(theirs ? [{ fieldtype: "HTML", fieldname: "theirs", options: frappe.ui.alert.html({ title: __("A standard letter head can only be set as default or disabled."), theme: "gray" }) }] : []),
				{ fieldtype: "Data", fieldname: "letter_head_name", label: __("Name"), reqd: 1, hidden: one ? 1 : 0 },
				{ fieldtype: "HTML", fieldname: "preview" },
				{ fieldtype: "Section Break" },
				{ fieldtype: "Check", fieldname: "is_default", label: __("Default"), description: __("Printed on a document unless another is chosen.") },
				{ fieldtype: "Check", fieldname: "disabled", label: __("Disabled") },
			],
			primary_action_label: one ? __("Update") : __("Create"),
			primary_action: async (values) => {
				await frappe.xcall("onedesk.one.printing.save_letter_head", {
					values: {
						letter_head_name: values.letter_head_name,
						is_default: values.is_default,
						disabled: values.disabled,
						...(preset && !theirs ? { one_top: settings() } : {}),
						...(foot && !theirs ? (foot === "none" ? { one_foot: null, footer_source: "HTML", footer: "" } : { one_foot: foot_settings() }) : {}),
						name: one ? one.name : null,
						modified: one ? one.modified : null,
					},
				});
				dialog.hide();
				frappe.show_alert({ message: one ? __("Letter head updated") : __("Letter head created"), indicator: "green" });
				this.refresh({ fresh: true });
			},
		});
		const group = (fields) => {
			const made = new frappe.ui.FieldGroup({ body: document.createElement("div"), fields });
			made.make();
			return made;
		};
		const top_part = theirs
			? null
			: group([
					{ fieldtype: "HTML", fieldname: "presets" },
					{ fieldtype: "Section Break" },
					{
						fieldtype: "MultiCheck",
						fieldname: "show",
						label: __("Show"),
						columns: 2,
						sort_options: false,
						options: SHOWN.map(([value, label]) => ({ value, label, checked: shows.includes(value) ? 1 : 0 })),
						on_change: () => drawn(),
					},
					{ fieldtype: "Int", fieldname: "logo_height", label: __("Logo Height"), description: __("In pixels."), default: (kept && kept.logo_height) || 60, change: () => drawn() },
					{ fieldtype: "Check", fieldname: "line", label: __("Brand Line"), description: __("A line in the Brand Colour under the header."), default: kept && kept.line ? 1 : 0, change: () => drawn() },
					{ fieldtype: "Select", fieldname: "align", label: __("Logo Alignment"), options: [{ value: "left", label: __("Left") }, { value: "center", label: __("Centre") }, { value: "right", label: __("Right") }], default: (kept && kept.align) || "left", change: () => drawn() },
					{ fieldtype: "HTML", fieldname: "from_general", options: `<p class="text-muted small">${esc(__("The name, logo, address, contacts and colour come from Workspace › General."))}</p>` },
				]);
		const foot_part = theirs
			? null
			: group([
					{ fieldtype: "HTML", fieldname: "feet" },
					{ fieldtype: "Section Break", fieldname: "foot_settings" },
					{
						fieldtype: "MultiCheck",
						fieldname: "foot_show",
						label: __("Show"),
						columns: 2,
						sort_options: false,
						options: [["logo", __("Logo")], ...SHOWN].map(([value, label]) => ({ value, label, checked: foot_shows.includes(value) ? 1 : 0 })),
						on_change: () => drawn(),
					},
					{ fieldtype: "Data", fieldname: "foot_note", label: __("Note"), description: __("For example, a thank-you line."), default: (kept_foot && kept_foot.note) || "", change: () => drawn() },
					{ fieldtype: "Check", fieldname: "foot_line", label: __("Brand Line"), description: __("A line in the Brand Colour over the footer."), default: kept_foot && kept_foot.line ? 1 : 0, change: () => drawn() },
				]);
		const part = (fieldname) => (top_part.fields_dict[fieldname] ? top_part : foot_part);
		const parts = theirs
			? null
			: {
					get_value: (fieldname) => part(fieldname).get_value(fieldname),
					get_field: (fieldname) => part(fieldname).get_field(fieldname),
					set_df_property: (fieldname, property, value) => part(fieldname).set_df_property(fieldname, property, value),
			  };
		if (!theirs) {
			const tabs = new frappe.ui.Tabs({
				tabs: [
					{ label: __("Header"), content: $(top_part.body)[0] },
					{ label: __("Footer"), content: $(foot_part.body)[0] },
				],
			});
			const $studio = $(`<div class="one-lh-studio"><div class="one-lh-side"></div><div class="one-lh-stage"></div></div>`);
			$studio.find(".one-lh-side").append(tabs.$el);
			dialog.get_field("preview").$wrapper.empty().append($studio);
		}
		const settings = () => ({
			preset,
			show: parts.get_value("show") || [],
			logo_height: parts.get_value("logo_height"),
			align: parts.get_value("align"),
			line: parts.get_value("line") ? 1 : 0,
		});
		const foot_settings = () => ({
			preset: foot,
			show: parts.get_value("foot_show") || [],
			note: parts.get_value("foot_note") || "",
			line: parts.get_value("foot_line") ? 1 : 0,
		});
		const foot_html = () => {
			if (foot === "none") return "";
			const chosen = drawn_feet.find((d) => d.preset === foot);
			return chosen ? chosen.html : (one && one.drawn_foot) || "";
		};
		const show_preview = (top, bottom = foot_html()) => {
			const $stage = theirs ? dialog.get_field("preview").$wrapper : dialog.get_field("preview").$wrapper.find(".one-lh-stage");
			const scale = Math.min(1, (($stage.width() || 600) - 2) / Settings.SHEET, (window.innerHeight - 320) / Settings.PAGE);
			const sheet = frame(page(top, bottom, scale, true), "one-letter-head-sheet");
			sheet.style.height = `${Math.ceil(Settings.PAGE * scale) + 2}px`;
			sheet.style.width = `${Math.ceil(Settings.SHEET * scale) + 2}px`;
			$stage.empty().append(sheet);
		};
		let drawn_with = [];
		let drawn_feet = [];
		const cards = () => {
			const field = parts.get_field("presets");
			if (!field) return;
			const $grid = $(`<div class="one-lh-presets"></div>`);
			for (const one_preset of drawn_with) {
				const $card = $(`<button type="button" class="one-lh-preset"></button>`)
					.toggleClass("one-lh-preset--chosen", one_preset.preset === preset)
					.text(one_preset.label)
					.on("mouseenter", () => show_preview(one_preset.html))
					.on("mouseleave", () => shown())
					.on("click", () => {
						preset = one_preset.preset;
						cards();
						shown();
					});
				$grid.append($card);
			}
			const note = preset
				? ""
				: `<p class="text-muted small">${esc(__("This header is custom HTML. Choosing a preset replaces it."))}</p>`;
			field.$wrapper.empty().append(note).append($grid);
		};
		const feet = () => {
			const field = parts.get_field("feet");
			if (!field) return;
			const $grid = $(`<div class="one-lh-presets one-lh-presets--feet"></div>`);
			const top_now = () => (drawn_with.find((d) => d.preset === preset) || {}).html || (one && one.drawn_top);
			for (const one_foot of [...drawn_feet, { preset: "none", label: __("None"), html: "" }]) {
				const $card = $(`<button type="button" class="one-lh-preset"></button>`)
					.toggleClass("one-lh-preset--chosen", one_foot.preset === foot)
					.text(one_foot.label)
					.on("mouseenter", () => show_preview(top_now(), one_foot.html))
					.on("mouseleave", () => shown())
					.on("click", () => {
						foot = one_foot.preset;
						feet();
						shown();
					});
				$grid.append($card);
			}
			const note = foot
				? ""
				: `<p class="text-muted small">${esc(__("This footer is custom HTML. Choosing a preset replaces it."))}</p>`;
			field.$wrapper.empty().append(note).append($grid);
		};
		const shown = () => {
			if (theirs) return show_preview(one.drawn_top);
			parts.set_df_property("align", "hidden", preset !== "logo");
			for (const fieldname of ["foot_show", "foot_note", "foot_line"]) {
				parts.set_df_property(fieldname, "hidden", !foot || foot === "none");
			}
			const chosen = drawn_with.find((d) => d.preset === preset);
			show_preview(chosen ? chosen.html : one && one.drawn_top);
		};
		const drawn = frappe.utils.debounce(async () => {
			if (theirs) return shown();
			[drawn_with, drawn_feet] = await Promise.all([
				frappe.xcall("onedesk.one.letter_heads.presets", { settings_of: settings() }),
				frappe.xcall("onedesk.one.letter_heads.presets", { settings_of: foot_settings(), part: "foot" }),
			]);
			cards();
			feet();
			shown();
		}, 200);
		if (one) dialog.set_values({ letter_head_name: one.letter_head_name || one.name, is_default: one.is_default, disabled: one.disabled });
		if (one && !theirs) {
			dialog.set_secondary_action_label(__("Edit in Builder"));
			dialog.set_secondary_action(() => {
				dialog.hide();
				this.design_letter_head(one.name);
			});
			dialog.add_custom_action(__("Delete"), () =>
				frappe.confirm(__("Delete letter head {0}?", [one.name]), async () => {
					await frappe.xcall("frappe.client.delete", { doctype: "Letter Head", name: one.name });
					dialog.hide();
					this.refresh({ fresh: true });
				})
			);
		}
		dialog.show();
		drawn();
	}

	async design_letter_head(name) {
		const designer = await frappe.xcall("onedesk.one.printing.design_letter_head", { letter_head: name });
		frappe.set_route("print-format-builder", designer);
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
				await frappe.xcall("onedesk.one.devices.retire_passkey", { passkey });
				this.refresh();
			});
		});
		const of = (event) => rows.find((one) => one.name === $(event.currentTarget).closest("[data-device]").attr("data-device"));
		this.$content.on("click", "[data-edit]", (event) => this.edit_device(of(event)));
		this.$content.on("click", "[data-lost]", (event) => {
			const one = of(event);
			frappe.confirm(__("Mark {0} as lost? Everyone on it is signed out.", [esc(one.device_name)]), async () => {
				await frappe.xcall("onedesk.one.devices.lost", { device: one.name });
				frappe.show_alert({ message: __("Marked as lost"), indicator: "green" });
				this.refresh();
			});
		});
		this.$content.on("click", "[data-retire]", (event) => {
			const one = of(event);
			frappe.confirm(__("Retire {0}?", [esc(one.device_name)]), async () => {
				await frappe.xcall("onedesk.one.devices.retire", { device: one.name });
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
				const said = await frappe.xcall("onedesk.one.devices.save", { device: one.name, ...values });
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
							Settings.dns_records(waiting.length ? waiting : [null], target) + Settings.dns_note(waiting),
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
				`<div class="one-shell-quiet os-dns-lead">${frappe.utils.escape_html(__("Add these records at your DNS provider."))}</div>${Settings.dns_records(
					[name],
					target
				)}${Settings.dns_note([name])}`
			);
		};
		draw();
		dialog.$wrapper.on("click", "[data-copy]", (event) => frappe.utils.copy_to_clipboard($(event.currentTarget).attr("data-copy")));
		dialog.show();
	}

	draw_oneai(data) {
		const esc = frappe.utils.escape_html;
		const params = frappe.utils.get_query_params();
		const only = params.product || null;
		const rows = (data.actions || []).filter((one) => !only || one.product === only);
		const each = Boolean(only || params.action);
		this.page.add_inner_button(__("Knowledge"), () => frappe.set_route("List", "AI Knowledge"));
		this.page.add_inner_button(__("Credit Usage"), () => frappe.set_route("query-report", "AI Credits", { by: "Action" }));
		const note = only
			? __("Showing {0} actions only.", [only])
			: "";
		this.$content.html(
			`${
				only
					? ""
					: onedesk.shell.section(
							__("Models"),
							'<div data-list="jobs"></div>',
							__("Pick a model for each kind of work. Default is the one One recommends."),
							onedesk.shell.button(each ? __("Hide Each Action") : __("Show Each Action"), { "data-each": "1" }, "subtle", "list")
					  )
			}${
				only
					? ""
					: onedesk.shell.section(
							__("Summaries"),
							'<div data-list="briefs"></div>',
							__("A few sentences at the top of each record, written again when something happens to it, at most once a day.")
					  )
			}${onedesk.shell.section(
				__("Actions"),
				`${only ? `<div class="one-shell-note"><a class="one-record-link" data-all>${esc(__("Show All Actions"))}</a></div>` : ""}<div data-list="actions"></div>`,
				note
			)}`
		);
		const $each = this.$content.find('[data-list="actions"]').closest(".one-shell-section");
		if (!only) {
			$each.toggle(each);
			this.$content.find("[data-each]").on("click", (event) => {
				$each.toggle();
				$(event.currentTarget).find(".es-button__label").text($each.is(":visible") ? __("Hide Each Action") : __("Show Each Action"));
			});
			onedesk.shell.table(this.$content.find('[data-list="jobs"]'), {
				rows: data.jobs || [],
				icon: "sparkles",
				empty: __("No actions"),
				columns: [
					{ label: __("Work"), render: (job) => `<div>${esc(job.label)}</div><div class="one-shell-quiet">${esc(job.about)}</div>` },
					{ label: __("Model"), render: (job) => Settings.job_model_html(data.catalogue, job) },
					{ label: __("Last 30 Days"), render: (job) => Settings.used_html(job) },
				],
				open: (job) => this.job_dialog(job, data),
			});
		}
		if (!only) {
			onedesk.shell.table(this.$content.find('[data-list="briefs"]'), {
				rows: data.briefs || [],
				icon: "sparkles",
				columns: [
					{ label: __("Record"), render: (one) => esc(one.label) },
					{
						label: __("Summarised"),
						render: (one) => `<span class="one-shell-quiet">${esc(one.written === 1 ? __("1 record") : one.written ? __("{0} records", [format_number(one.written, null, 0)]) : __("None yet"))}</span>`,
					},
					{ label: "", render: (one) => Settings.read_switch(one.on) },
				],
				open: async (one) => {
					await frappe.xcall("onedesk.one_ai.brief.switch", { doctype: one.doctype, on: one.on ? 0 : 1 });
					this.refresh();
				},
			});
		}
		this.$content.find("[data-all]").on("click", () => {
			frappe.set_route("workspace-settings", { section: "oneai" });
			this.open("oneai");
		});
		onedesk.shell.table(this.$content.find('[data-list="actions"]'), {
			rows,
			page_size: 50,
			icon: "sparkles",
			empty: __("No actions"),
			columns: [
				{
					label: __("Action"),
					render: (one) =>
						`<div class="os-ai-action"><span>${esc(one.label)}</span>${Settings.product_badge(one.product)}</div>${
							one.about ? `<div class="one-shell-quiet">${esc(one.about)}</div>` : ""
						}`,
				},
				{ label: __("Model"), render: (one) => Settings.model_html(Settings.model_of(data.catalogue, one)) },
				{ label: __("Last 30 Days"), render: (one) => Settings.used_html(one) },
			],
			open: (one) => this.action_dialog(one, data.catalogue),
		});
		if (params.action) {
			const one = rows.find((row) => row.name === params.action);
			if (one) this.action_dialog(one, data.catalogue);
		}
	}

	static used_html(one) {
		const esc = frappe.utils.escape_html;
		return one.calls
			? `<span title="${esc(__("{0} calls", [one.calls]))}">${esc(__("{0} credits", [format_number(one.credits, null, one.credits < 10 ? 2 : 0)]))}</span>`
			: `<span class="text-muted">${esc(__("Not used"))}</span>`;
	}

	static job_model_html(catalogue, job) {
		if (job.mixed) return frappe.ui.badge.html({ label: __("Mixed"), theme: "orange" });
		return Settings.model_html(Settings.model_of(catalogue, { capability: job.needs, model: job.model }));
	}

	/** Fast, Balanced or Best by what a model costs against the others on offer. */
	static tiers(offered) {
		const priced = offered.filter((m) => m.read != null && m.written != null);
		const out = {};
		if (priced.length < 3) return out;
		const ranked = [...priced].sort((a, b) => a.read + a.written - (b.read + b.written));
		ranked.forEach((m, at) => {
			const third = Math.floor((at * 3) / ranked.length);
			out[m.name] = [__("Fast"), __("Balanced"), __("Best")][third];
		});
		return out;
	}

	job_dialog(job, data) {
		const esc = frappe.utils.escape_html;
		const offered = ((data.catalogue || {})[job.needs] || []).slice();
		const tiers = Settings.tiers(offered);
		const cost = (m) => (m.read || 0) + (m.written || 0);
		offered.sort((a, b) => cost(a) - cost(b));
		const fallback = offered.find((m) => m.default);
		const covered = (data.actions || []).filter((one) => job.actions.includes(one.name) && one.capability === job.needs);
		const options = [
			{ value: "", label: fallback ? __("Default: {0}", [fallback.label]) : __("Default") },
			...offered.map((m) => ({ value: m.name, label: `${m.label} · ${m.maker}${tiers[m.name] ? ` (${tiers[m.name]})` : ""}` })),
		];
		const dialog = new frappe.ui.Dialog({
			title: job.label,
			fields: [
				{ fieldname: "about", fieldtype: "HTML", options: `<div class="one-shell-quiet">${esc(job.about)}</div>` },
				{
					fieldname: "model",
					fieldtype: "Select",
					label: __("Model"),
					options,
					default: job.model || "",
					onchange: () => dialog.fields_dict.picked.$wrapper.html(Settings.model_detail(offered.find((m) => m.name === dialog.get_value("model")) || fallback)),
				},
				{ fieldname: "picked", fieldtype: "HTML" },
				{
					fieldname: "covers",
					fieldtype: "HTML",
					options: `<div class="one-shell-quiet">${esc(
						`${job.mixed ? `${__("Its actions use different models now. Saving gives this one to all of them.")} ` : ""}${__("Used for {0}.", [
							covered.map((one) => one.label).join(", "),
						])}`
					)}</div>`,
				},
			],
			primary_action_label: __("Save"),
			primary_action: async (values) => {
				await frappe.xcall("onedesk.one_ai.run.set_job", { job: job.key, model: values.model || "" });
				dialog.hide();
				frappe.show_alert({ message: __("Saved."), indicator: "green" });
				this.refresh();
			},
		});
		dialog.fields_dict.picked.$wrapper.html(Settings.model_detail(offered.find((m) => m.name === job.model) || fallback));
		dialog.show();
	}

	static model_detail(m) {
		const esc = frappe.utils.escape_html;
		if (!m) return "";
		const cost =
			m.read != null && m.written != null
				? __("About {0} credits per 1,000 words read and {1} per 1,000 written.", [format_number(m.read, null, 2), format_number(m.written, null, 2)])
				: __("Priced per use.");
		return `<div class="os-ai-picked">${Settings.model_html({ ...m, chosen: true })}<div class="one-shell-quiet">${esc(
			__("Made by {0}, run by {1}.", [m.maker, String(m.company || "").replace(/\.$/, "")])
		)} ${esc(cost)}</div></div>`;
	}

	static model_of(catalogue, one) {
		const offered = (catalogue || {})[one.capability] || [];
		const picked = one.model && offered.find((m) => m.name === one.model);
		const fallback = Settings.fallback(offered, one);
		if (picked) return { ...picked, chosen: true };
		if (one.model) return { name: one.model, label: one.model, chosen: true, gone: true };
		return fallback ? { ...fallback, chosen: false } : null;
	}

	static fallback(offered, one) {
		return (one.default_model && offered.find((m) => m.name === one.default_model)) || offered.find((m) => m.default);
	}

	static product_badge(product) {
		if (!product) return "";
		return frappe.ui.badge.html({ label: product, icon: product.toLowerCase(), size: "sm", css_class: "os-ai-product" });
	}

	static model_html(model) {
		const esc = frappe.utils.escape_html;
		if (!model) return `<span class="text-muted">${esc(__("Default"))}</span>`;
		const logo = model.logo ? `<img class="os-ai-logo" src="${esc(model.logo)}" alt="">` : "";
		const tag = model.chosen ? "" : ` ${frappe.ui.badge.html({ label: __("Default"), theme: "gray" })}`;
		const gone = model.gone ? ` ${frappe.ui.badge.html({ label: __("No longer offered"), theme: "red" })}` : "";
		return `<span class="os-ai-model">${logo}<span>${esc(model.label)}</span>${tag}${gone}</span>`;
	}

	action_dialog(one, catalogue) {
		const esc = frappe.utils.escape_html;
		const offered = (catalogue || {})[one.capability] || [];
		const fallback = Settings.fallback(offered, one);
		const options = [
			{ value: "", label: fallback ? __("Default: {0}", [fallback.label]) : __("Default") },
			...offered.map((m) => ({ value: m.name, label: `${m.label} · ${m.maker}` })),
		];
		const describe = (name) => Settings.model_detail(offered.find((x) => x.name === name) || fallback);
		const dialog = new frappe.ui.Dialog({
			title: one.label,
			fields: [
				{ fieldname: "about", fieldtype: "HTML", options: one.about ? `<div class="one-shell-quiet">${esc(one.about)}</div>` : "" },
				{
					fieldname: "model",
					fieldtype: "Select",
					label: __("Model"),
					options,
					default: one.model || "",
					onchange: () => dialog.fields_dict.picked.$wrapper.html(describe(dialog.get_value("model"))),
				},
				{ fieldname: "picked", fieldtype: "HTML" },
				...(one.name === "chat"
					? [
							{
								fieldname: "people_choose",
								fieldtype: "Check",
								label: __("Allow Model Choice"),
								default: one.people_choose ? 1 : 0,
								description: __("Anyone can pick a model for their own chats in the OneAI panel. When off, only administrators can."),
							},
						]
					: []),
				{
					fieldname: "extra",
					fieldtype: "Small Text",
					label: __("Extra Instructions"),
					default: one.extra || "",
					description: __("Added to {0}'s own instructions for everyone.", [one.label]),
				},
			],
			primary_action_label: __("Save"),
			primary_action: async (values) => {
				await frappe.xcall("onedesk.one_ai.run.set_action", {
					action: one.name,
					model: values.model || "",
					extra: values.extra || "",
					people_choose: values.people_choose ? 1 : 0,
					modified: one.modified || "",
				});
				dialog.hide();
				frappe.show_alert({ message: __("Saved."), indicator: "green" });
				this.refresh();
			},
			secondary_action_label: __("Try It"),
			secondary_action: () => this.try_action(one, dialog.get_value("model"), dialog.get_value("extra")),
		});
		dialog.fields_dict.picked.$wrapper.html(describe(one.model || ""));
		if (one.setting) {
			dialog.add_custom_action(__("Reset to Default"), () =>
				frappe.confirm(__("Reset {0}? It runs on the default model with no extra instructions.", [esc(one.label)]), async () => {
					await frappe.xcall("onedesk.one_ai.run.reset_action", { action: one.name });
					dialog.hide();
					this.refresh();
				})
			);
		}
		dialog.show();
	}

	try_action(one, model, extra) {
		const esc = frappe.utils.escape_html;
		const asking = new frappe.ui.Dialog({
			title: __("Try {0}", [one.label]),
			fields: [
				{ fieldname: "warn", fieldtype: "HTML", options: `<div class="one-shell-quiet">${esc(__("Runs once with the settings above and uses OneAI credits."))}</div>` },
				{ fieldname: "text", fieldtype: "Small Text", label: __("Text"), reqd: 1 },
				{ fieldname: "said", fieldtype: "HTML" },
			],
			primary_action_label: __("Run"),
			primary_action: async (values) => {
				const where = asking.fields_dict.said.$wrapper;
				where.html(`<div class="one-shell-quiet">${esc(__("Running…"))}</div>`);
				try {
					const out = await frappe.xcall("onedesk.one_ai.run.try_it", { action: one.name, text: values.text, model: model || "", extra: extra || "" });
					where.html(
						`<div class="os-ai-said">${esc(out.said || out.text || "")}</div><div class="one-shell-quiet">${esc(
							__("{0} credits.", [format_number(out.credits || 0, null, 2)])
						)}</div>`
					);
				} catch (e) {
					where.empty();
				}
			},
		});
		asking.show();
	}

	draw_intake(data) {
		const esc = frappe.utils.escape_html;
		const month = data.month || {};
		const inbox = (box) => `/desk/intake?box=${box}&everyone=1`;
		const fact = (value, label, href) =>
			`<a class="os-intake-fact" href="${esc(href)}"><span class="os-intake-number">${esc(format_number(value || 0, null, 0))}</span><span class="one-shell-quiet">${esc(label)}</span></a>`;
		const facts = `<div class="os-intake-facts">${[
			fact(month.arrived, __("Received"), inbox("done")),
			fact(month.handled, __("Handled by OneAI"), inbox("done")),
			fact(month.needed, __("Needed Review"), inbox("waiting")),
			fact(month.waiting, __("Waiting"), inbox("waiting")),
			fact(month.undone, __("Undone"), inbox("done")),
		].join("")}</div>`;
		this.$content.append(onedesk.shell.section(__("This Month"), facts));
		this.$content.append(
			onedesk.shell.section(
				__("Sources"),
				`<div class="os-intake-list" data-list="mailboxes"></div><div class="os-intake-list" data-list="folders"></div>`
			)
		);
		const links = (pairs) =>
			`<div class="one-shell-quiet os-intake-links">${pairs
				.map(([href, label]) => `<a class="one-record-link" href="${esc(href)}">${esc(label)}</a>`)
				.join(" · ")}</div>`;
		const marks = data.marks || {};
		this.form(data, {
			rows: [
				{ heading: __("Reading") },
				{ stack: ["records"] },
				["most_pages", "_"],
				{ heading: __("Confidence"), note: __("Below this, a person reviews it.") },
				["floor", "_"],
				{ stack: ["audit"] },
				{ heading: __("Filing") },
				{ stack: ["keep_in_place"] },
				["quiet_minutes", "_"],
				{ heading: __("OneBook"), mark: marks.OneBook },
				{ stack: ["household", "submit_einvoices"] },
				{ html: links([["/desk/query-report/Ready to Submit", __("Ready to Submit")], ["/desk/query-report/Spending", __("Spending")]]) },
				...((data.hr || []).length
					? [
							{ heading: __("OneHR"), note: __("Each uses OneAI credits."), mark: marks.OneHR },
							{ stack: data.hr.filter((name) => name !== "one_keep_recordings_days") },
							...(data.hr.includes("one_keep_recordings_days") ? [["one_keep_recordings_days", "_"]] : []),
					  ]
					: []),
			],
		});
		this.draw_intake_sources(data);
		this.page.add_inner_button(__("Models"), () => frappe.set_route("workspace-settings", { section: "oneai", product: "OneIntake" }));
	}

	draw_reads(data) {
		const esc = frappe.utils.escape_html;
		if (data.off) {
			this.$content.append(onedesk.shell.section("", `<p class="one-shell-quiet">${esc(__("OneIntake is turned off for this workspace."))}</p>`));
			return;
		}
		const marks = data.marks || {};
		const reading = (one) =>
			!one.on ? __("Not read") : one.for && one.for !== frappe.session.user_fullname ? __("Read on behalf of {0}", [one.for]) : __("Read as you");
		const none = (text) => `<p class="one-shell-quiet">${esc(text)}</p>`;
		const mailboxes = data.mailboxes || [];
		const folders = data.folders || [];
		this.$content.append(
			onedesk.shell.section(
				__("Mailboxes"),
				mailboxes.length ? '<div data-list="mailboxes"></div>' : none(__("You don't hold a mailbox.")),
				__("New mail and its attachments are read, filed and acted on as you.")
			),
			onedesk.shell.section(
				__("Folders"),
				folders.length ? '<div data-list="folders"></div>' : none(__("OneAI has no access to any of your folders.")),
				__("New files in the folder and the folders inside it are read, filed and acted on as you."),
				onedesk.shell.button(__("Add Folder"), { "data-add-folder": "1" }, "subtle", "plus")
			)
		);
		if (mailboxes.length)
			onedesk.shell.table(this.$content.find('[data-list="mailboxes"]'), {
				mark: marks.OneMail,
				rows: mailboxes,
				columns: [
					{ label: __("Mailbox"), fieldname: "email" },
					{ label: __("Read by OneAI"), render: (one) => esc(reading(one)) },
					{ label: "", render: (one) => Settings.read_switch(one.on) },
				],
				open: (one) => this.switch_mailbox(one),
			});
		if (folders.length)
			onedesk.shell.table(this.$content.find('[data-list="folders"]'), {
				mark: marks.OneCloud,
				rows: folders,
				columns: [
					{ label: __("Folder"), render: (one) => esc(one.path.replace(/^Home\//, "")) },
					{ label: __("Read by OneAI"), render: (one) => esc(reading({ on: true, for: one.for })) },
					{ label: "", render: () => Settings.read_switch(true) },
				],
				open: (one) => this.stop_folder(one),
			});
		this.$content.on("click", "[data-add-folder]", () => this.add_folder());
	}

	switch_mailbox(one) {
		const esc = frappe.utils.escape_html;
		const set = async (on) => {
			await frappe.xcall("onedesk.one_intake.switches.set_mailbox", { account: one.name, on });
			this.refresh();
		};
		if (one.on) return frappe.confirm(__("Stop OneAI reading new mail in {0}?", [esc(one.email)]), () => set(0));
		if (!one.mine) return frappe.msgprint(__("Only the owner of {0} can turn this on, because OneAI acts on their behalf.", [esc(one.email)]));
		frappe.confirm(
			__("OneAI will read new mail in {0} and its attachments, file them and act on them on your behalf. Scans and photos are read with OneAI credits.", [`<b>${esc(one.email)}</b>`]),
			() => set(1)
		);
	}

	stop_folder(one) {
		frappe.confirm(__("Stop OneAI reading new files in {0} and the folders inside it?", [frappe.utils.escape_html(one.path)]), async () => {
			await frappe.xcall("onedesk.one_intake.switches.set_folder", { folder: one.name, on: 0 });
			this.refresh();
		});
	}

	add_folder() {
		const dialog = new frappe.ui.Dialog({
			title: __("Add Folder"),
			fields: [
				{
					fieldname: "folder",
					fieldtype: "Link",
					options: "File",
					label: __("Folder"),
					reqd: 1,
					get_query: () => ({ filters: { is_folder: 1, one_intake: 0 } }),
				},
				{
					fieldname: "said",
					fieldtype: "HTML",
					options: `<div class="one-shell-quiet">${frappe.utils.escape_html(
						__("OneAI will read, file and act on new files in this folder and its subfolders. Scans and photos use OneAI credits.")
					)}</div>`,
				},
			],
			primary_action_label: __("Add"),
			primary_action: async (values) => {
				await frappe.xcall("onedesk.one_intake.switches.set_folder", { folder: values.folder, on: 1 });
				dialog.hide();
				this.refresh();
			},
		});
		dialog.show();
	}

	draw_intake_sources(data) {
		const esc = frappe.utils.escape_html;
		const marks = data.marks || {};
		onedesk.shell.table(this.$content.find('[data-list="mailboxes"]'), {
			title: __("Mailboxes"),
			mark: marks.OneMail,
			rows: data.mailboxes || [],
			page_size: 10,
			icon: "mail",
			empty: __("No mailboxes"),
			columns: [
				{ label: __("Mailbox"), fieldname: "email" },
				{ label: __("Read by OneAI"), render: (one) => Settings.read_switch(one.on) },
				{ label: __("On Behalf Of"), render: (one) => esc(one.for || "") },
			],
			open: (one) => this.switch_mailbox(one),
		});
		onedesk.shell.table(this.$content.find('[data-list="folders"]'), {
			title: __("Folders"),
			mark: marks.OneCloud,
			rows: data.folders || [],
			page_size: 10,
			icon: "folder",
			empty: __("No folders"),
			columns: [
				{ label: __("Folder"), render: (one) => esc(one.path.replace(/^Home\//, "")) },
				{ label: __("On Behalf Of"), render: (one) => esc(one.for || "") },
			],
			actions: onedesk.shell.button(__("Add Folder"), { "data-add-folder": "1" }, "subtle", "plus"),
			open: (one) => this.stop_folder(one),
		});
		this.$content.on("click", "[data-add-folder]", () => this.add_folder());
	}

	draw_holidays(data) {
		const esc = frappe.utils.escape_html;
		const open_list = (name) => this.open("holidays", { record: name === data.now ? null : name });
		const use_another = () => {
			const dialog = new frappe.ui.Dialog({
				title: __("Use Another List"),
				fields: [
					{ fieldname: "holiday_list", fieldtype: "Link", options: "Holiday List", label: __("Holiday List"), reqd: 1 },
					{
						fieldname: "said",
						fieldtype: "HTML",
						options: `<div class="one-shell-quiet">${esc(
							__("Applies to everyone from today, or from its start date. Used for leave, attendance, check-ins, the calendar and deadlines.")
						)}</div>`,
					},
				],
				primary_action_label: __("Use List"),
				primary_action: async (values) => {
					await frappe.xcall("onedesk.one.holidays.use", { holiday_list: values.holiday_list });
					dialog.hide();
					this.refresh({ fresh: true });
				},
			});
			dialog.show();
		};
		const next_year = async () => {
			const name = await frappe.xcall("onedesk.one.holidays.next_year");
			frappe.show_alert({ message: __("{0} created", [name]), indicator: "green" });
			open_list(name);
		};
		if (data.empty) {
			this.$content.append(
				onedesk.shell.section(__("Holidays"), onedesk.shell.empty(__("No holiday list")))
			);
			this.page.add_inner_button(__("Use Another List"), use_another);
			return;
		}
		const list = data.list;
		const day = (value) => frappe.datetime.str_to_user(value);
		if (list.in_force && !data.next && list.days_left <= 90) {
			const $make = $(onedesk.shell.button(__("Create Next Year's List"), {}, "ghost")).on("click", next_year);
			this.$content.append(
				$(
					frappe.ui.alert({
						title: __("This list ends on {0}, in {1} days", [day(list.to_date), list.days_left]),
						description: __("After that, every day counts as a working day for leave and attendance, until another list starts."),
						theme: "yellow",
						footer: $make,
					})
				).addClass("os-holiday-alert")
			);
		} else if (!list.in_force) {
			const $back = $(onedesk.shell.button(__("Back to {0}", [data.now]), {}, "ghost")).on("click", () => open_list(data.now));
			this.$content.append(
				$(
					frappe.ui.alert({
						title: __("{0} starts on {1}", [list.name, day(list.from_date)]),
						description: __("Until then, {0} applies.", [data.now]),
						theme: "blue",
						footer: $back,
					})
				).addClass("os-holiday-alert")
			);
		}
		const fact = (value, label, href) =>
			`<${href ? `a href="${esc(href)}"` : "div"} class="os-intake-fact"><span class="os-intake-number">${esc(String(value))}</span><span class="one-shell-quiet">${esc(label)}</span></${href ? "a" : "div"}>`;
		const coming = (data.coming || [])[0];
		const facts = `<div class="os-intake-facts">${[
			fact(list.public, __("Public Holidays")),
			fact(list.days_off, __("Weekly Days Off")),
			coming ? fact(day(coming.date), coming.what) : fact("–", __("No More Holidays This Year")),
			fact(day(list.to_date), list.days_left >= 0 ? __("Last Day, in {0} days", [list.days_left]) : __("Ended")),
			...(data.elsewhere ? [fact(data.elsewhere, __("People on Other Lists"), "/desk/holiday-list-assignment?applicable_for=Employee&docstatus=1")] : []),
		].join("")}</div>`;
		this.$content.append(
			onedesk.shell.section(list.name, facts, __("{0} to {1}", [day(list.from_date), day(list.to_date)]))
		);
		this.form(data, {
			rows: [
				{ heading: __("Days Off") },
				{ stack: ["weekly_offs"] },
				{ heading: __("Public Holidays") },
				["country", "subdivision"],
				{ html: onedesk.shell.button(__("Add Public Holidays"), { "data-local": "1" }, "subtle", "plus") },
				{ stack: ["holidays"] },
			],
		});
		const country = this.group.get_field("country");
		const region = this.group.get_field("subdivision");
		const regions = async () => {
			const code = this.group.get_value("country");
			region.set_data(code ? await frappe.xcall("onedesk.one.holidays.subdivisions", { country: code }) : []);
		};
		country.df.onchange = regions;
		this.$content.find("[data-local]").on("click", async () => {
			const code = this.group.get_value("country");
			if (!code) return frappe.msgprint(__("Choose the country first."));
			const found = await frappe.xcall("onedesk.one.holidays.country_holidays", {
				country: code,
				subdivision: this.group.get_value("subdivision") || null,
				from_date: list.from_date,
				to_date: list.to_date,
			});
			const table = this.group.get_field("holidays");
			const held = new Set((table.df.data || []).map((one) => one.holiday_date));
			const added = found.filter((one) => !held.has(one.holiday_date));
			table.df.data = [...(table.df.data || []), ...added].sort((a, b) => (a.holiday_date < b.holiday_date ? -1 : 1));
			table.df.data.forEach((one, at) => (one.idx = at + 1));
			table.grid.refresh();
			this.check();
			frappe.show_alert({ message: added.length ? __("{0} holidays added. Save to keep them.", [added.length]) : __("All holidays are already in the list."), indicator: "blue" });
		});
		if (list.in_force && data.next) this.page.add_inner_button(__("Next Year's List"), () => open_list(data.next));
		else if (list.in_force) this.page.add_inner_button(__("Create Next Year's List"), next_year);
		this.page.add_inner_button(__("Use Another List"), use_another);
	}

	draw_notification_types(data) {
		if (data.rule) return this.draw_rule(data);
		if (data.type) return this.draw_notification_type(data);
		const esc = frappe.utils.escape_html;
		const channel = (label, allowed, on) => (allowed ? frappe.ui.badge.html({ label, theme: on ? "blue" : "gray" }) : "");
		const state = (one) =>
			[
				one.enabled ? "" : frappe.ui.badge.html({ label: __("Off"), theme: "gray" }),
				one.edited ? frappe.ui.badge.html({ label: __("Edited"), theme: "violet" }) : "",
			].join(" ");
		const channels = (one) =>
			!one.ours
				? `<span class="one-shell-quiet">${esc(__("Each person chooses"))}</span>`
				: one.mailed_by
				? frappe.ui.badge.html({ label: __("Sent by {0}", [one.mailed_by]), theme: "gray" })
				: one.outside
				? frappe.ui.badge.html({ label: __("External Email"), theme: "gray" })
				: one.always
				? frappe.ui.badge.html({ label: __("Always Emailed"), theme: "gray" })
				: channel(__("Email"), one.email, one.email_default) + " " + channel(__("Push"), one.push, one.push_default);
		const open_rule = (name) => frappe.set_route("workspace-settings", { section: this.key, rule: name });
		this.$content.html(
			`<div class="one-shell-section one-shell-note one-shell-quiet">${esc(
				__("Blue means on by default.")
			)}</div>
			<div class="one-shell-section" data-list="rules"></div>
			<div class="one-shell-section" data-list="types"></div>`
		);
		onedesk.shell.table(this.$content.find('[data-list="rules"]'), {
			title: __("Rules"),
			rows: data.rules || [],
			icon: "bell-plus",
			empty: __("No rules"),
			open: (one) => open_rule(one.name),
			actions:
				onedesk.oneai.button(
					__("Ask OneAI"),
					__("Help me set up a notification rule. Ask me what should happen and who should be told, then suggest the rule.")
				) +
				onedesk.shell.button(__("New Rule"), { "data-rule-new": "1" }, "subtle", "plus"),
			columns: [
				{ label: __("Rule"), fieldname: "name" },
				{ label: __("Description"), render: (one) => `<span class="one-shell-quiet">${esc(one.said || "")}</span>` },
				{ label: "", render: (one) => (one.enabled ? "" : frappe.ui.badge.html({ label: __("Off"), theme: "gray" })) },
			],
		});
		onedesk.shell.table(this.$content.find('[data-list="types"]'), {
			title: __("Notifications"),
			rows: data.apps.flatMap((group) => group.types.map((one) => ({ ...one, app: group.app, mark: group.mark }))),
			page_size: 100,
			icon: "bell",
			none: __("No matching notifications"),
			open: (one) => one.ours && frappe.set_route("workspace-settings", { section: this.key, type: one.name }),
			columns: [
				{
					label: __("Notification"),
					render: (one) =>
						`<div class="os-type-name">${esc(one.label)}</div>${
							one.about ? `<div class="one-shell-quiet">${esc(one.about)}</div>` : ""
						}${one.to ? `<div class="one-shell-quiet os-to">${frappe.utils.icon("users", "xs")}${esc(one.to)}</div>` : ""}`,
				},
				{
					label: __("App"),
					render: (one) => onedesk.shell.app(one.app, one.mark),
				},
				{ label: __("Channels"), render: channels },
				{ label: "", render: state },
			],
		});
		this.$content.on("click", "[data-rule-new]", () => open_rule("new"));
	}

	draw_notification_type(data) {
		const esc = frappe.utils.escape_html;
		const type = data.type;
		const slots = type.slots.map((one) => `<code>{{ ${esc(one)} }}</code>`).join(" ");
		const preview = `<div class="os-preview">
			<div class="os-preview-label">${esc(__("Preview"))}</div>
			<div class="os-preview-subject"></div>
			<div class="os-preview-message"></div>
			<div class="os-preview-wrong"></div>
		</div>`;
		const rows = [["enabled"]];
		if (type.mailed_by) {
			rows.push({
				html: `<div class="one-shell-quiet">${esc(
					type.switch
						? __("{0} sends this email itself. Send This is the same switch as in its settings.", [type.mailed_by])
						: type.notification
						? __("{0} sends this email itself. Send This turns it on and off.", [type.mailed_by])
						: __("{0} sends this email itself. It's listed so you can see everything the workspace sends.", [type.mailed_by])
				)}</div>`,
			});
		} else if (type.upstream) {
			rows.push(
				{
					html: `<div class="one-shell-quiet">${esc(
						type.rule
							? __("The text comes from {0}'s rule {1}.", [type.upstream, type.rule])
							: __("The text comes from {0}.", [type.upstream])
					)}</div>`,
				},
				{ heading: __("Channels"), note: __("In-app notifications are always on.") },
				["one_allow_email", "one_allow_push"],
				["one_email_default", "one_push_default"]
			);
		} else if (type.ours) {
			rows.push(
				{ heading: __("Message"), note: __("Edited text is no longer translated.") },
				["one_subject"],
				["one_message"],
				{ html: `${slots ? `<div class="one-shell-quiet os-slots">${__("Available fields: {0}", [slots])}</div>` : ""}${preview}` }
			);
			if (type.always) {
				rows.push(
					{ heading: __("Channels"), note: __("Email is always sent so people can reply.") },
					["one_allow_push", "one_push_default"]
				);
			} else if (!type.outside) {
				rows.push(
					{ heading: __("Channels"), note: __("In-app notifications are always on.") },
					["one_allow_email", "one_allow_push"],
					["one_email_default", "one_push_default"]
				);
			} else {
				rows.push({ html: `<div class="one-shell-quiet">${esc(__("Sent to addresses outside the workspace, so there's no channel to choose."))}</div>` });
			}
		}
		const rewrite = () =>
			onedesk.oneai.open({
				ask: __(
					'Rewrite the "{0}" notification to be short, plain and friendly. Keep every field it uses and suggest it as a change I can apply.',
					[type.label]
				),
			});
		const reset = async () => {
			await this.group.set_values({ one_subject: type.default_subject, one_message: type.default_message });
			this.check();
			this.preview(type.name, $card);
		};
		this.as_record({
			parent: __("Notifications"),
			route: "/desk/workspace-settings?section=notification_types",
			title: type.label,
			status: data.values.enabled ? { label: __("On"), colour: "green" } : { label: __("Off"), colour: "gray" },
			side: onedesk.shell.side({
				mark: type.mark || "bell",
				title: type.label,
				sub: type.app ? esc(type.app) : "",
				groups: [
					{ label: __("When"), html: type.about ? `<div>${esc(type.about)}</div>` : "" },
					{ label: __("Recipients"), html: type.to ? `<div>${esc(type.to)}</div>` : "" },
				],
			}),
			actions:
				type.ours && !type.upstream
					? [
							{ label: __("Rewrite with OneAI"), action: rewrite },
							{ label: __("Reset to Default"), action: reset, group: __("Actions") },
					  ]
					: [],
		});
		const $card = this.form(data, { rows });
		const draw = frappe.utils.debounce(() => this.preview(type.name, $card), 400);
		for (const name of ["one_subject", "one_message"]) {
			const field = this.group.fields_dict[name];
			if (!field) continue;
			const was = field.df.change;
			field.df.change = (...args) => {
				was && was(...args);
				draw();
			};
		}
		if (type.ours && !type.upstream) this.ready.then(() => this.preview(type.name, $card));
	}

	async preview(name, $card) {
		if (!this.group) return;
		const said = await frappe.xcall(Settings.API + "preview_notification", {
			name,
			subject: this.group.get_value("one_subject") || "",
			message: this.group.get_value("one_message") || "",
		});
		$card.find(".os-preview-subject").html(said.subject || "");
		$card.find(".os-preview-message").html(said.message || "");
		const wrong = [said.subject_wrong, said.message_wrong].filter(Boolean);
		$card.find(".os-preview-wrong").html(wrong.length ? frappe.ui.alert.html({ title: wrong.join(" "), theme: "red" }) : "");
	}

	draw_rule(data) {
		const esc = frappe.utils.escape_html;
		const rule = data.rule;
		const remove = () =>
			frappe.confirm(__("Delete rule {0}? It stops sending notifications.", [rule.name]), async () => {
				await frappe.xcall(Settings.API + "delete_rule", { name: rule.name });
				frappe.set_route("workspace-settings", { section: this.key });
			});
		this.as_record({
			parent: __("Notifications"),
			route: "/desk/workspace-settings?section=notification_types",
			title: rule.new ? __("New Rule") : rule.name,
			status: rule.new ? { label: __("Not Saved"), colour: "orange" } : data.values.enabled ? { label: __("On"), colour: "green" } : { label: __("Off"), colour: "gray" },
			side: onedesk.shell.side({
				mark: "bell-plus",
				title: rule.new ? __("New Rule") : rule.name,
				sub: esc(__("Workspace rule")),
				groups: [{ label: __("Description"), html: rule.said ? `<div>${esc(rule.said)}</div>` : "" }],
			}),
			actions: rule.new ? [] : [{ label: __("Delete"), action: remove, group: __("Actions") }],
		});
		const rows = [
			["enabled"],
			...(rule.new ? [["rule_name"]] : []),
			{ heading: __("Trigger") },
			["document_type", "event"],
			["date_changed", "days_in_advance"],
			["value_changed"],
			{ html: `<div class="os-filter-label">${esc(__("Conditions"))}</div><div class="os-filters"></div>` },
			{ heading: __("Recipients"), note: __("Only people with access to the record are notified.") },
			["roles"],
			["person_field", "send_to_all_assignees"],
			{ heading: __("Message") },
			["subject"],
			["message"],
			{ heading: __("Channels"), note: __("In-app notifications are always on.") },
			["one_allow_email", "one_allow_push"],
			["one_email_default", "one_push_default"],
		];
		const $card = this.form(data, { rows });
		const options = (list) => [{ value: "", label: "" }, ...(list || [])];
		const offer = (said) => {
			for (const [field, list] of [
				["date_changed", said && said.dates],
				["value_changed", said && said.values],
				["person_field", said && said.people],
			]) {
				const control = this.group.fields_dict[field];
				if (!control) continue;
				control.df.options = options(list);
				control.refresh();
				control.set_input(this.group.get_value(field) || data.values[field] || "");
			}
		};
		const filters = (doctype, value) => {
			const $filters = $card.find(".os-filters").empty();
			if (!doctype) return $filters.html(`<div class="one-shell-quiet">${esc(__("Select a record type first."))}</div>`);
			frappe.model.with_doctype(doctype, () => {
				const group = new frappe.ui.FilterGroup({
					parent: $filters,
					doctype,
					on_change: () => {
						this.group.set_value("filters", JSON.stringify(group.get_filters()));
						this.check();
					},
				});
				group.add_filters_to_filter_group(value && value !== "[]" ? JSON.parse(value) : []);
			});
		};
		offer(data.options);
		filters(data.values.document_type, data.values.filters);
		const watched = this.group.fields_dict.document_type;
		watched.get_query = () => ({ query: "onedesk.one.rules.watchable" });
		const was = watched.df.change;
		watched.df.change = async (...args) => {
			was && was(...args);
			const doctype = this.group.get_value("document_type");
			if (doctype === this.rule_watches) return;
			this.rule_watches = doctype;
			this.group.set_value("filters", "");
			offer(doctype ? await frappe.xcall("onedesk.one.rules.fields_of", { doctype }) : null);
			filters(doctype, "");
		};
		this.rule_watches = data.values.document_type;
		if (!rule.new && this.record === "rule:new") frappe.set_route("workspace-settings", { section: this.key, rule: rule.name });
	}
};
