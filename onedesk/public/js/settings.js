// Settings: everything a person or a workspace sets. The sections are entries
// in One's own sidebar (one/sidebar/one/one.json), under You and Workspace, so
// the page is one wide column: the section the address names. The server says
// which sections the reader may open and holds every read and write
// (one/settings.py); this draws them with frappe's own parts — espresso
// buttons, badges and bars, and FieldGroup for anything that is a form.
//
// Two pages share it: `settings` for everybody's own, and `workspace-settings`
// for the workspace's, a page only its administrators may open, so frappe
// leaves those sidebar entries out for everybody else.

frappe.provide("onedesk");

onedesk.Settings = class Settings extends onedesk.shell.Editor {
	static API = "onedesk.one.settings.";

	// Sections that are a table rather than a form, so they get the width a
	// table needs. Every other section is a column in the middle of the page.
	static WIDE = ["people", "oneai", "intake"];

	constructor(page, group) {
		// Dirty, the warning on leaving, saving against `modified` and hearing
		// another save are the shell's Editor, which is what a desk form does.
		super(page);
		this.group_name = group;
		this.route = group === "workspace" ? "workspace-settings" : "settings";
		this.$section = page.$shell;
		// A section left with unsaved changes keeps them, as frappe keeps an
		// unsaved document in `locals`, until it is saved or refreshed.
		this.kept = {};
		// Agreeing in the dialog changes what the Agreements section shows.
		$(document).on("legal-agreed", () => this.key === "agreements" && this.open("agreements"));
		// A mailbox broke or came back (one_mail/sync.py).
		frappe.realtime.on("one_mailbox", () => this.key === "mail" && this.$content && this.$content.is(":visible") && this.refresh());
		// A memory was kept or forgotten, here, in the panel or in another tab.
		frappe.realtime.on("one_memory", () => this.key === "memory" && this.$content && this.$content.is(":visible") && this.refresh());
		// An action's model or instructions changed (one_ai/run.py, _told).
		frappe.realtime.on("one_oneai", () => this.key === "oneai" && this.$content && this.$content.is(":visible") && this.refresh());
		// A domain started or stopped working (one/account.py, _tell_domains).
		frappe.realtime.on("one_domains", () => this.key === "domains" && this.$content && this.$content.is(":visible") && this.refresh());
	}

	async show() {
		if (!this.said) this.said = await frappe.xcall(Settings.API + "sections");
		const mine = this.said.sections.filter((one) => one.group === this.group_name);
		const params = frappe.utils.get_query_params();
		const found = mine.find((one) => one.key === params.section) || mine[0];
		// A notification type is ?type=, a workspace rule ?rule= (or ?rule=new),
		// a person ?person=, a holiday list other than today's ?list=.
		if (found) this.open(found.key, { record: params.type || params.person || params.list || (params.rule ? `rule:${params.rule}` : null) });
	}

	// `record` is the one record a section that lists several is open on, as a
	// notification type is: the section is then that record's form.
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
		} catch (e) {
			this.$content.html(frappe.ui.alert.html({ title: __("This section could not be opened."), theme: "red" }));
			return;
		}
		this.$content.empty();
		this.hear(this.data.opened);
		this[`draw_${key}`](this.data);
		// The router names the page after show; the section's name wins,
		// unless a record in it named itself after it (as_record).
		if (!this.trailed) onedesk.shell.name(section.label);
		await this.bring_back(slot(key, record));
	}

	// Unsaved changes left in this section come back, and if the record has
	// changed underneath them since, the page says so, as a form does.
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

	// ---------------------------------------------------------------- saving, for the shell's Editor

	saver(values) {
		return { method: Settings.API + "save", args: { section: this.key, values, record: this.record } };
	}

	redraw(said) {
		this[`draw_${this.key}`](said);
	}

	refresh({ fresh = false } = {}) {
		this.open(this.key, { fresh, record: this.record });
	}

	// ---------------------------------------------------------------- you

	// Who you are to everybody here, and, when you work here, what your
	// employee record says. The photo is the avatar itself: click it to change
	// it. What HR owns (your job, where your pay goes) is shown, not asked.
	draw_profile(data) {
		const esc = frappe.utils.escape_html;
		const image = data.values.user_image;
		const employee = data.employee;
		const job = employee ? employee.work.filter((one) => ["designation", "department"].includes(one.fieldname)).map((one) => one.value) : [];
		// The page's own suggestion (one/ai.py), so it is answered the same way.
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
				<div class="os-who-actions">${onedesk.shell.button(image ? __("Change Photo") : __("Add a Photo"), { "data-photo": "1" }, "ghost")}${
					image ? onedesk.shell.button(__("Remove Photo"), { "data-unphoto": "1" }, "ghost") : ""
				}${check}</div>
			</div>
		</div>`;
		const facts = (list) =>
			`<dl class="os-facts">${list.map((one) => `<dt>${esc(one.label)}</dt><dd>${esc(String(one.value))}</dd>`).join("")}</dl>`;
		const bio = onedesk.oneai.button(
			__("Write It With OneAI"),
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
				{ heading: __("At Work"), note: __("As HR keeps it. Ask them if something here is wrong.") },
				{ html: facts(employee.work) },
				{ heading: __("Where You Live") },
				["current_address", "permanent_address"],
				["personal_email", ""],
				{ heading: __("In an Emergency"), note: __("Who HR calls if something happens to you at work.") },
				["person_to_be_contacted", "relation", "emergency_phone_number"],
				{ heading: __("About You"), note: __("Only you and HR see these.") },
				["marital_status", "blood_group"]
			);
			if (employee.bank.length) rows.push({ heading: __("Where Your Pay Goes"), note: __("Only HR can change this.") }, { html: facts(employee.bank) });
		}
		const $card = this.form(
			{ ...data, fields: [...data.fields.filter((one) => one.fieldname !== "user_image"), ...(employee ? employee.fields : [])] },
			{ before: who, rows }
		);
		// Both initials, as the rail's avatar says them: espresso's fallback is
		// the first letter only.
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
	}

	// Everything One can tell you reaches the bell. What is also mailed, and
	// what is pushed to the browsers you turned push on in, is a pair of
	// frappe's switches per kind, under an Email and a Push column, grouped by
	// the app that sends it, and only the kinds you can receive: HR's are for
	// HR. A switch the workspace does not allow is shown and cannot be moved,
	// so the list is the whole answer.
	draw_notifications(data) {
		const rows = [{ stack: ["enabled", "enable_email_notifications"] }];
		for (const group of data.groups) rows.push({ heading: group.app }, ...group.rows.map((row) => ({ row, css: "os-kind" })));
		rows.push({ heading: __("Other Mail") }, { stack: ["enable_email_event_reminders", "enable_email_threads_on_assigned_document"] });
		// The page's own suggestion (one/ai.py), so it is answered the same way.
		const fewer = onedesk.oneai.button(
			__("Too Many Emails?"),
			__("Which of the notifications I get by email could I leave to the bell, or have pushed instead? Say which to untick and why.")
		);
		const note = __("Everything One tells you reaches your bell. Choose what also comes by email, and what is pushed to your browsers.");
		const $card = this.form(data, {
			before: `<div class="os-notify-intro"><div class="one-shell-quiet">${note}</div>${fewer}</div><div class="os-push"></div>`,
			rows,
		});
		// Each app's part says which column is which, once, in its heading.
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
			// An HTML field draws its options once its value is in.
			$card.find("[data-oneai-tag]").replaceWith(onedesk.oneai.tag(__("OneAI")));
			// Frappe draws a read-only switch with no input, so it always looks
			// off: an always-mailed kind would read as never mailed.
			for (const field of this.group.fields_list) {
				if (field.df.fieldtype !== "Switch" || !field.df.read_only) continue;
				field.$wrapper.addClass("os-switch-fixed").toggleClass("os-switch-on", !!cint(field.get_value()));
			}
		});
		this.draw_push($card.find(".os-push"), data.push);
	}

	// Push in this browser, and the others this person turned it on in. Not a
	// field of the record: turning it on asks the browser, and is done at once.
	async draw_push($part, said) {
		const esc = frappe.utils.escape_html;
		const here = await onedesk.push.state();
		const words = {
			on: [__("On in this browser"), "green"],
			off: [__("Off in this browser"), "gray"],
			blocked: [__("Blocked by this browser"), "orange"],
			unsupported: [__("This browser cannot receive push"), "gray"],
		}[here.state];
		const others = (said.devices || []).filter((one) => one.endpoint !== here.endpoint);
		const action =
			here.state === "off"
				? onedesk.shell.button(__("Turn On Push"), { "data-push": "on" }, "subtle", "bell-ring")
				: here.state === "on"
				? onedesk.shell.button(__("Send a Test"), { "data-push": "test" }, "subtle") + onedesk.shell.button(__("Turn Off"), { "data-push": "off" }, "ghost")
				: "";
		$part.html(`<div class="one-shell-row">
				<div class="one-shell-row-main"><div class="one-shell-row-title">${esc(__("Push"))}</div>
					<div class="one-shell-row-sub">${frappe.ui.badge.html({ label: words[0], theme: words[1] })}</div>
					${here.state === "blocked" ? `<div class="one-shell-quiet">${esc(__("Allow notifications for this site in the browser's settings, then come back."))}</div>` : ""}
				</div>
				<div class="one-shell-row-actions">${action}</div>
			</div>
			${others
				.map(
					(one) => `<div class="one-shell-row"><div class="one-shell-row-main"><div>${esc(one.label || "")}</div><div class="one-shell-quiet">${esc(
						one.last_sent ? __("Last pushed {0}", [frappe.datetime.prettyDate(one.last_sent)]) : __("Nothing pushed yet")
					)}</div></div><div class="one-shell-row-actions">${onedesk.shell.button(__("Remove"), { "data-forget": one.name }, "ghost", "trash-2")}</div></div>`
				)
				.join("")}`);
		const again = async () => this.draw_push($part, await frappe.xcall("onedesk.one.push.devices"));
		$part.find('[data-push="on"]').on("click", async () => {
			// A browser may refuse even when it offers push: a private window
			// does, and so does one whose push service cannot be reached.
			let on = false;
			try {
				on = await onedesk.push.on(said.key);
			} catch (e) {
				on = false;
			}
			if (!on) frappe.show_alert({ message: __("This browser did not turn push on. A private window cannot have it."), indicator: "orange" });
			again();
		});
		$part.find('[data-push="off"]').on("click", async () => {
			await onedesk.push.off();
			again();
		});
		$part.find('[data-push="test"]').on("click", async () => {
			const r = await frappe.xcall("onedesk.one.push.test");
			frappe.show_alert({ message: r.sent ? __("Sent. It should appear in a moment.") : __("It could not be sent."), indicator: r.sent ? "green" : "orange" });
		});
		$part.find("[data-forget]").on("click", async (event) => {
			await frappe.xcall("onedesk.one.push.forget", { name: $(event.currentTarget).attr("data-forget") });
			again();
		});
	}

	// The mailboxes the reader holds, each saying what it signs with, and why
	// when it cannot sign or has stopped connecting. Connecting one is the
	// page's one action, in its head; it happens in OneMail.
	draw_mail(data) {
		const esc = frappe.utils.escape_html;
		const rows = (data.mailboxes || [])
			.map((one) => {
				const kind = one.workspace ? __("Workspace") : one.shared ? __("Shared") : one.connected ? __("Connected") : __("Yours");
				const badges = [
					frappe.ui.badge.html({ label: kind, theme: one.workspace ? "blue" : "gray" }),
					one.intake ? onedesk.oneai.tag(__("Read by OneAI")) : "",
					one.receives_only ? frappe.ui.badge.html({ label: __("Receives Only"), theme: "gray" }) : "",
					one.error ? frappe.ui.badge.html({ label: __("Not Connecting"), theme: "red" }) : "",
				].join(" ");
				const said = one.error
					? `<div class="one-shell-row-note text-danger">${esc(one.error)}</div>`
					: one.sends
					? `<div class="one-shell-row-note one-shell-quiet">${one.signed ? esc(__("Signs with “{0}”", [one.signed])) : esc(__("No signature"))}</div>`
					: "";
				const actions = [
					one.error && one.may_reconnect ? onedesk.shell.button(__("Reconnect"), { "data-reconnect": one.name, "data-email": one.email }) : "",
					one.may_sign ? onedesk.shell.button(__("Signature"), { "data-signature": one.name }, one.error ? "ghost" : "subtle") : "",
					onedesk.shell.button(__("Open"), { "data-open": one.name }, "ghost"),
				].join("");
				return `<div class="one-shell-row">
					<div class="one-shell-row-main"><div class="one-shell-row-title">${esc(one.email)}</div><div class="one-shell-row-sub">${badges}</div>${said}</div>
					<div class="one-shell-row-actions">${actions}</div>
				</div>`;
			})
			.join("");
		this.$content.html(
			onedesk.shell.section(
				__("Your Mailboxes"),
				rows || onedesk.shell.empty(__("No mailboxes yet.")),
				__("Mailboxes are read in OneMail. Here you see what each one signs with, and fix one that stopped connecting.")
			)
		);
		this.page.set_primary_action(__("Connect a Mailbox"), () => frappe.set_route("onemail", { connect: 1 }), "plug");
		this.$content.find("[data-open]").on("click", (event) => frappe.set_route("onemail", { box: $(event.currentTarget).attr("data-open") }));
		this.$content.find("[data-signature]").on("click", (event) => this.sign($(event.currentTarget).attr("data-signature")));
		this.$content.find("[data-reconnect]").on("click", (event) =>
			this.reconnect($(event.currentTarget).attr("data-reconnect"), $(event.currentTarget).attr("data-email"))
		);
	}

	async sign(account) {
		const signature = await frappe.xcall("onedesk.one_mail.holders.signature_of", { account });
		// The same question as the page's own suggestion (one/ai.py), so OneAI
		// answers it as a card to approve.
		const write = onedesk.oneai.button(
			__("Write It With OneAI"),
			__("Write a signature for the mailbox I send from, from my name, my job and how to reach me. Keep it short, and suggest it as a card I can approve.")
		);
		const dialog = new frappe.ui.Dialog({
			title: __("Signature"),
			fields: [
				{ fieldname: "signature", fieldtype: "Text Editor", label: __("Signature"), default: signature },
				{ fieldname: "write", fieldtype: "HTML", options: `<div class="one-shell-actions">${write}</div>` },
			],
			primary_action_label: __("Save"),
			primary_action: async (values) => {
				await frappe.xcall("onedesk.one_mail.holders.set_signature", { account, signature: values.signature || "" });
				dialog.hide();
				frappe.show_alert({ message: __("Saved."), indicator: "green" });
				this.refresh();
			},
		});
		dialog.show();
	}

	// The password again, tried on the servers the mailbox already has.
	reconnect(account, email) {
		const dialog = new frappe.ui.Dialog({
			title: __("Reconnect {0}", [email]),
			fields: [
				{
					fieldname: "password",
					fieldtype: "Password",
					label: __("Password"),
					reqd: 1,
					description: __("Gmail and Outlook want an app password here, made in the account's security settings."),
				},
				{ fieldname: "login", fieldtype: "Data", label: __("Login, if not the address") },
			],
			primary_action_label: __("Reconnect"),
			primary_action: async (values) => {
				dialog.disable_primary_action();
				try {
					await frappe.xcall("onedesk.one_mail.connect.reconnect", { account, ...values });
					dialog.hide();
					frappe.show_alert({ message: __("Connected again. Its mail is on its way."), indicator: "green" });
					this.refresh();
				} finally {
					dialog.enable_primary_action();
				}
			},
		});
		dialog.show();
	}

	// The reader's calendar link, drawn as OneCalendar's Subscribe draws it
	// (calendar_link.js). The page's one action is making the link, or, once
	// there is one, copying it; a new link and switching it off are quiet.
	draw_calendar(data) {
		const how = onedesk.oneai.button(
			__("How Do I Add It?"),
			__("How do I add my calendar link to Google Calendar, Apple Calendar or Outlook, on my computer and my phone, and what does it carry?")
		);
		const $card = $(
			onedesk.shell.section(
				__("Your Calendar in Other Apps"),
				`<div class="os-calendar"></div><div class="one-shell-actions">${how}</div>`,
				__("A private link that shows your calendar in Google Calendar, Apple Calendar or Outlook, on a computer or a phone.")
			)
		).appendTo(this.$content);
		const draw = (link) => {
			const $body = $card.find(".os-calendar");
			if (!data.allowed) {
				$body.html(`<div class="one-shell-quiet">${__("Your workspace does not allow calendar links. Its administrators decide this under Workspace › General.")}</div>`);
				$card.find(".one-shell-actions").remove();
				return;
			}
			if (!link) {
				$body.html(`<div class="one-shell-quiet">${__("You have no calendar link. Make one to see your calendar in another app.")}</div>`);
				this.page.set_primary_action(__("Make My Link"), async () => draw(await frappe.xcall("onedesk.one_calendar.feed.mine")), "link");
				return;
			}
			$body.html(onedesk.calendar_link.html(link, { copy: false }));
			onedesk.calendar_link.bind($body, link, { drawn: draw, stopped: () => draw(null) });
			this.page.set_primary_action(__("Copy Link"), () => onedesk.calendar_link.copy(link), "copy");
		};
		draw(data.link);
	}

	// How the reader signs in, and where they are signed in, read from what
	// frappe keeps (one/signin.py). Nothing here is saved as a form: each
	// action is done at once, so the page head has none.
	draw_signin(data) {
		const esc = frappe.utils.escape_html;
		const when = (value) => (value ? frappe.datetime.prettyDate(value) : "");
		const safe = onedesk.oneai.button(
			__("Is My Account Safe?"),
			__("Is my account safe? Look at how I sign in and where I am signed in, and tell me what to do.")
		);
		const intro = `<div class="one-shell-section"><div class="os-notify-intro"><div class="one-shell-quiet">${esc(
			__("How you sign in to One, and every place you are signed in now.")
		)}</div>${safe}</div></div>`;
		const row = (title, sub, actions = "") =>
			`<div class="one-shell-row"><div class="one-shell-row-main"><div class="one-shell-row-title">${title}</div>${
				sub ? `<div class="one-shell-quiet">${sub}</div>` : ""
			}</div>${actions ? `<div class="one-shell-row-actions">${actions}</div>` : ""}</div>`;

		const password = onedesk.shell.section(
			__("Signing In"),
			row(
				esc(__("Password")),
				esc(data.password_changed ? __("Changed {0}", [when(data.password_changed)]) : __("No change recorded")),
				onedesk.shell.button(__("Change Password"), { "data-password": "1" }, "subtle", "key-round")
			) +
				row(
					esc(__("Two-Factor Sign-in")),
					esc(
						data.two_factor
							? __("A code is asked for after your password ({0}). Your workspace decides this.", [__(data.two_factor_method || "OTP App")])
							: __("Not asked for. Your workspace decides this.")
					),
					frappe.ui.badge.html({ label: data.two_factor ? __("On") : __("Off"), theme: data.two_factor ? "green" : "gray" })
				)
		);

		const passkey = data.employee
			? onedesk.shell.section(
					__("Passkey"),
					row(
						frappe.ui.badge.html({ label: data.passkey ? __("Registered") : __("Not registered"), theme: data.passkey ? "green" : "gray" }),
						"",
						data.passkey ? "" : onedesk.shell.button(__("Register This Device"), { "data-passkey": "1" }, "subtle", "fingerprint")
					),
					data.passkey_signs_in
						? __("Your fingerprint or face on this phone or laptop. You use it to check in, and to sign in.")
						: __("Your fingerprint or face on this phone or laptop, used when you check in.")
			  )
			: "";

		this.$content.html(
			intro + password + passkey + `<div class="one-shell-section" data-list="places"></div><div class="one-shell-section" data-list="recent"></div>`
		);
		// Where you are signed in and your last sign-ins: frappe's table, as
		// every list of records is, this one first and the rest by last use.
		onedesk.shell.table(this.$content.find('[data-list="places"]'), {
			title: __("Where You Are Signed In"),
			rows: data.sessions,
			page_size: 10,
			icon: "monitor-smartphone",
			actions:
				data.sessions.length > 1 ? onedesk.shell.button(__("Sign Out Everywhere Else"), { "data-elsewhere": "1" }, "ghost", "log-out") : "",
			columns: Settings.session_columns((one) =>
				one.here ? frappe.ui.badge.html({ label: __("This One"), theme: "blue" }) : onedesk.shell.button(__("Sign Out"), { "data-sign-out": one.key }, "ghost", "log-out")
			),
		});
		if (data.recent.length) {
			onedesk.shell.table(this.$content.find('[data-list="recent"]'), {
				title: __("Recent Sign-ins"),
				note: __("A failed sign-in you did not make is somebody trying your password. Change it."),
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
						label: __("Sign Out Everywhere Else"),
						description: __("Every other phone and computer signed in as you is signed out."),
						default: 1,
					},
				],
				primary_action_label: __("Change"),
				primary_action: async (values) => {
					await frappe.xcall("frappe.core.doctype.user.user.update_password", {
						old_password: values.old_password,
						new_password: values.new_password,
						logout_all_sessions: values.elsewhere ? 1 : 0,
					});
					dialog.hide();
					frappe.show_alert({ message: __("Your password is changed."), indicator: "green" });
					this.open("signin");
				},
			});
			dialog.show();
		});
		this.$content.find("[data-passkey]").on("click", async () => {
			await onedesk.passkey.register();
			this.open("signin");
		});
		this.$content.on("click", "[data-sign-out]", async (event) => {
			await frappe.xcall("onedesk.one.signin.sign_out", { key_of: $(event.currentTarget).attr("data-sign-out") });
			frappe.show_alert({ message: __("Signed out there."), indicator: "green" });
			this.open("signin");
		});
		this.$content.on("click", "[data-elsewhere]", () =>
			frappe.confirm(__("Sign out on every other phone and computer?"), async () => {
				await frappe.xcall(Settings.API + "sign_out_elsewhere");
				frappe.show_alert({ message: __("Signed out everywhere else."), indicator: "green" });
				this.open("signin");
			})
		);
	}

	// A session as the tables of them read: the device, where from, when
	// last used, and what can be done about it (`last`).
	static session_columns(last = null) {
		const esc = frappe.utils.escape_html;
		return [
			{ label: __("Device"), fieldname: "device" },
			{ label: __("Address"), fieldname: "address" },
			{ label: __("Last Used"), render: (one) => `<span class="one-shell-quiet">${esc(frappe.datetime.prettyDate(one.last_used))}</span>` },
			...(last ? [{ label: "", render: last }] : []),
		];
	}

	// A sign-in as the tables of them read: when, where from, and whether it
	// worked, a failed one in red.
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

	// What OneAI keeps for the reader, which they add, correct and forget
	// here as much as in a conversation; and, to read only, what the
	// workspace's administrators told OneAI for everybody. Both are frappe's
	// EmbeddedList: one line each, searchable once there are many, a row
	// opening the memory as a list row opens its record.
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
				__("What OneAI keeps in mind when it helps you. Only you see it, and you can change or forget any of it.")
			)}</div>${know}</div></div>
			<div class="one-shell-section os-memories" data-list="remembered"></div>
			${knowledge.length ? '<div class="one-shell-section" data-list="workspace"></div>' : ""}`
		);
		this.page.set_primary_action(__("Add a Memory"), () => this.memory_dialog(), "plus");
		const redraw = (said) => {
			this.$content.empty();
			this.draw_memory(said);
		};
		const remembered = await onedesk.shell.table(this.$content.find('[data-list="remembered"]'), {
			title: __("Remembered"),
			note: __("Click one to change it."),
			rows: facts,
			icon: "brain",
			empty: __("Nothing yet. Tell OneAI to remember something, or add it here."),
			none: __("No memory says that."),
			open: (one) => this.memory_dialog(one),
			// Everything at once is the header's quiet second action, asking first.
			actions: facts.length > 1 ? frappe.ui.button.html({ label: __("Forget Everything"), variant: "ghost", theme: "red", attrs: { "data-forget-all": "1" } }) : "",
			columns: [
				{ label: __("Memory"), fieldname: "fact" },
				{
					label: __("About"),
					render: (one) =>
						one.about_doctype
							? `<a href="${frappe.utils.get_form_link(one.about_doctype, one.about_name)}" onclick="event.stopPropagation();">${esc(one.about_title || one.about_name)}</a>`
							: "",
				},
				{ label: __("Kept"), render: (one) => `<span class="one-shell-quiet">${esc(frappe.datetime.prettyDate(one.creation))}</span>` },
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
			frappe.confirm(__("Forget everything OneAI remembers about you?"), async () => redraw(await frappe.xcall(Settings.API + "forget_all")))
		);
		if (knowledge.length) {
			onedesk.shell.table(this.$content.find('[data-list="workspace"]'), {
				title: __("From Your Workspace"),
				note: __("Written by your workspace's administrators for everybody. OneAI uses it when it helps you; they change it."),
				rows: knowledge,
				columns: [
					{ label: __("Title"), fieldname: "title" },
					{ label: __("Used On"), render: (one) => esc(one.applies_to || __("Everything")) },
				],
			});
		}
	}

	// A memory the reader writes or corrects: frappe's own controls, the
	// record it is about being any the reader can open.
	memory_dialog(one = null) {
		const dialog = new frappe.ui.Dialog({
			title: one ? __("Edit Memory") : __("Add a Memory"),
			fields: [
				{ fieldname: "fact", fieldtype: "Small Text", label: __("What OneAI Should Keep in Mind"), reqd: 1, default: one ? one.fact : "" },
				{ fieldname: "about_doctype", fieldtype: "Link", options: "DocType", label: __("About a Record Of"), default: one ? one.about_doctype : "" },
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

	// Every agreement: what you agreed to, what your organisation agreed to and
	// who agreed for it, and what is only published. Each opens on the
	// Agreements page; an older version, as it was agreed.
	draw_agreements(data) {
		const esc = frappe.utils.escape_html;
		const read = (key, version) =>
			`/app/legal?document=${encodeURIComponent(key)}${version ? `&version=${encodeURIComponent(version)}` : ""}`;
		const state = (one, whose) => {
			if (!one.version) return frappe.ui.badge.html({ label: __("Not agreed yet"), theme: "orange" });
			const when = whose === "organisation" ? __("by {0} on {1}", [one.by, one.on]) : __("on {0}", [one.on]);
			// A new revision asks again; a clarified text (a new hash only) is
			// still agreed, and what was agreed can still be read.
			const was = one.version === one.current ? "" : ` <a href="${read(one.key, one.version)}" target="_blank" rel="noopener">${esc(__("Read what was agreed"))}</a>`;
			if (!one.owed) return `${frappe.ui.badge.html({ label: __("Agreed"), theme: "green" })} <span class="one-shell-quiet">${esc(when)}</span>${was}`;
			return `${frappe.ui.badge.html({ label: __("Updated since"), theme: "orange" })} <span class="one-shell-quiet">${esc(when)}</span>${was}`;
		};
		const row = (doc, whose) => `<div class="one-shell-row">
			<div class="one-shell-row-main">
				<div class="one-shell-row-title"><a href="${read(doc.key)}" target="_blank" rel="noopener">${esc(doc.title)}</a></div>
				<div class="one-shell-quiet">${esc(doc.summary)}</div>
				${whose ? `<div class="one-shell-row-sub">${state({ ...doc[whose], key: doc.key }, whose)}</div>` : ""}
			</div>
			<div class="one-shell-row-actions">${onedesk.shell.button(__("Read"), { "data-read": doc.key }, "ghost", "file-text")}</div>
		</div>`;
		const yours = data.documents.filter((doc) => doc.you);
		const ours = data.documents.filter((doc) => doc.organisation);
		const published = data.documents.filter((doc) => !doc.you && !doc.organisation);
		const owed = data.documents.some((doc) => (doc.you && doc.you.owed) || (data.admin && doc.organisation && doc.organisation.owed));
		this.$content.html(
			(owed
				? `<div class="one-shell-section">${frappe.ui.alert.html({ title: __("Some of these are waiting for you to agree."), theme: "yellow" })}
					<div class="one-shell-actions">${onedesk.shell.button(__("Agree Now"), { "data-agree": "1" }, "solid")}</div></div>`
				: "") +
				onedesk.shell.section(__("Yours"), yours.map((doc) => row(doc, "you")).join(""), __("About your own personal data, so only you can agree to them.")) +
				onedesk.shell.section(
					__("Your Organisation's"),
					ours.map((doc) => row(doc, "organisation")).join("") +
						(data.admin ? `<div class="one-shell-actions">${onedesk.shell.button(__("Everybody's Agreements"), { "data-everybody": "1" }, "ghost", "list")}</div>` : ""),
					__("Agreed once, by an administrator, for everybody in the workspace.")
				) +
				onedesk.shell.section(__("Published"), published.map((doc) => row(doc, null)).join(""), __("To read. Nobody is asked to agree to these."))
		);
		this.$content.find("[data-read]").on("click", (event) => window.open(read($(event.currentTarget).attr("data-read")), "_blank"));
		this.$content.find("[data-agree]").on("click", () => onedesk.legal.check());
		this.$content.find("[data-everybody]").on("click", () => frappe.set_route("List", "Legal Acceptance"));
	}

	// ---------------------------------------------------------------- the workspace

	// The workspace's own settings, in three parts: what it was made with and
	// its logo, how dates, times and numbers read, and the rules for signing
	// in. Every field is System Settings' or Company's own.
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
			{ heading: __("Company"), note: __("Set when the workspace was made. The currency cannot change once there are books.") },
			{ html: `<dl class="os-facts">${facts}</dl>` },
			["company_logo", ""],
			["email_footer_address", ""],
			{ heading: __("Region and Formats") },
			["language", "time_zone"],
			["date_format", "time_format"],
			["number_format", "first_day_of_the_week"],
			{ html: `<div class="one-shell-quiet os-reads" data-reads="1"></div>` },
			{ heading: __("Signing In"), note: __("The rules for everybody who signs in to this workspace.") },
			["one_two_factor", "two_factor_method"],
			["session_expiry", "one_password"],
			["allow_consecutive_login_attempts", "allow_login_after_fail"],
			["force_user_to_reset_password", ""],
			{ stack: ["one_login_with_passkey", "login_with_email_link", "deny_multiple_sessions"] },
			{ heading: __("Sharing") },
			{ stack: ["one_calendar_links", "one_record_sharing"] },
		];
		const $card = this.form(data, { rows });
		// How a date, a time and a number will read, as they are chosen.
		const reads = () => {
			const values = this.values();
			const now = values.time_zone && moment.tz && moment.tz.zone(values.time_zone) ? moment().tz(values.time_zone) : moment();
			const date = now.format((values.date_format || "dd-mm-yyyy").toUpperCase());
			const time = now.format(values.time_format || "HH:mm:ss");
			const number = format_number(1234567.89, values.number_format, 2);
			$card.find("[data-reads]").text(__("Now it reads {0} {1}, and a number {2}.", [date, time, number]));
		};
		this.ready.then(reads);
		$card.on("change input", "select, input", () => setTimeout(reads));
	}

	// Everybody on the workspace, one line each, in frappe's EmbeddedList: what
	// they may use, whether they administer it, when they were last here. A
	// row opens the person (draw_person), as a list row opens its record.
	async draw_people(data) {
		if (data.person) return this.draw_person(data);
		const esc = frappe.utils.escape_html;
		const seats = data.seats ? __("{0} of {1} seats used.", [data.used, data.seats]) : __("{0} people.", [data.used]);
		const levels = Object.fromEntries(data.levels.map((one) => [one.value, one.label]));
		this.$content.html(
			`<div class="one-shell-section"><div class="one-shell-quiet">${esc(
				__("Everybody has One, OneCloud, OneMail, OneTask and OneCalendar. Here you give each person the apps that are somebody's job.")
			)} ${esc(seats)}</div></div>
			<div class="one-shell-section os-people-list" data-list="people"></div>`
		);
		this.page.set_primary_action(__("Invite Somebody"), () => this.invite_dialog(data), "plus");
		onedesk.shell.table(this.$content.find('[data-list="people"]'), {
			title: __("People"),
			note: __("Click somebody to change what they can use, or to sign them out."),
			rows: data.people.map((one) => ({ ...one, search: `${one.full_name} ${one.name}` })),
			icon: "users",
			empty: __("Nobody yet. Invite somebody."),
			none: __("Nobody by that name."),
			open: (one) => frappe.set_route("workspace-settings", { section: "people", person: one.name }),
			columns: [
				{
					label: __("Person"),
					render: (one) => `<div class="os-person">${frappe.ui.avatar.html({ label: one.full_name, image: one.user_image, size: "sm" })}
						<div><div class="os-person-name">${esc(one.full_name || one.name)}${one.enabled ? "" : ` ${frappe.ui.badge.html({ label: __("Off"), theme: "gray" })}`}</div>
						<div class="one-shell-quiet">${esc(one.name)}</div></div></div>`,
				},
				{
					label: __("Apps"),
					render: (one) => {
						const held = new Set(data.apps.map((app) => one.access[app.name]));
						if (held.size === 1 && !held.has("None")) {
							const [level] = held;
							return frappe.ui.badge.html({ label: __("Every app · {0}", [levels[level]]), theme: level === "Manager" ? "blue" : "gray" });
						}
						return (
							data.apps
								.filter((app) => one.access[app.name] !== "None")
							.map((app) => frappe.ui.badge.html({ label: `${app.name} · ${levels[one.access[app.name]]}`, theme: one.access[app.name] === "Manager" ? "blue" : "gray" }))
								.join(" ") || `<span class="one-shell-quiet">${esc(__("The five everybody has"))}</span>`
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

	// One person, drawn as a docview: their name after People in the
	// breadcrumb, where they stand in the pill, a Select per app with its mark
	// and the Administrator switch saved from the page head against the User
	// as it was loaded, frappe's form sidebar with their photo and links, and
	// what an administrator does when somebody leaves as the page's Actions.
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
					label: __("Send a Password Reset"),
					group: __("Actions"),
					action: async () => {
						await frappe.xcall(Settings.API + "send_reset", { user: one.name });
						done(__("Sent. They get a mail to choose a new password."));
					},
				}
			);
		}
		if (!one.me && one.enabled && !one.joined) {
			actions.push({
				label: __("Invite Again"),
				group: __("Actions"),
				action: async () => {
					await frappe.xcall(Settings.API + "invite_again", { user: one.name });
					done(__("Sent. The earlier link no longer works."));
				},
			});
		}
		if (!one.me) {
			actions.push(
				one.enabled
					? {
							label: __("Turn Off"),
							group: __("Actions"),
							action: () =>
								frappe.confirm(__("Turn {0} off? They are signed out now and cannot sign in. Everything they made stays.", [esc(name)]), async () => {
									await frappe.xcall(Settings.API + "set_enabled", { user: one.name, on: 0 });
									this.refresh({ fresh: true });
								}),
					  }
					: {
							label: __("Turn On"),
							group: __("Actions"),
							action: async () => {
								await frappe.xcall(Settings.API + "set_enabled", { user: one.name, on: 1 });
								this.refresh({ fresh: true });
							},
					  }
			);
		}
		const status = !one.enabled
			? { label: __("Off"), colour: "gray" }
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
						html: one.employee ? `<a class="one-record-link" href="${frappe.utils.get_form_link("Employee", one.employee)}">${esc(__("Their employee record"))}</a>` : "",
					},
				],
				meta: [one.last_active ? __("Last active {0}", [frappe.datetime.prettyDate(one.last_active)]) : one.joined ? __("Not active lately") : __("Has not joined yet")],
			}),
			actions,
		});
		const apps = data.apps.map((app) => `app_${app.icon}`);
		const rows = [
			{ heading: __("What They Can Use"), note: __("Everybody has One, OneCloud, OneMail, OneTask and OneCalendar. A manager also sets the app up and sees everything in it.") },
			...Settings.pairs(apps),
			{ stack: ["admin"] },
			{ heading: __("Where They Are Signed In") },
			{
				html: one.me
					? `<div class="one-shell-quiet">${esc(__("You. Your own are on your Sign-in page."))}</div>`
					: '<div data-list="places"></div>',
			},
			...(one.recent.length ? [{ heading: __("Last Sign-ins") }, { html: '<div data-list="recent"></div>' }] : []),
		];
		const $card = this.form(data, { rows });
		Settings.marks($card, data.apps);
		// Frappe's table, as on the Sign-in page, under the record's own parts.
		if (!one.me) {
			onedesk.shell.table($card.find('[data-list="places"]'), {
				rows: one.sessions,
				page_size: 10,
				icon: "monitor-smartphone",
				empty: one.joined ? __("Signed in nowhere.") : __("Invited, and not joined yet."),
				columns: Settings.session_columns(),
			});
		}
		onedesk.shell.table($card.find('[data-list="recent"]'), { rows: one.recent, columns: Settings.signin_columns() });
	}

	// Each app's mark before its name, on a field that picks what somebody
	// may do in it.
	static marks($wrapper, apps) {
		for (const app of apps) {
			$wrapper.find(`.frappe-control[data-fieldname="app_${app.icon}"] .control-label`).first().prepend(`<span class="os-app-mark">${frappe.utils.icon(app.icon, "sm")}</span>`);
		}
	}

	// Fieldnames two to a row, for Editor.form's rows.
	static pairs(names) {
		const rows = [];
		for (let at = 0; at < names.length; at += 2) rows.push([names[at], names[at + 1] || ""]);
		return rows;
	}

	// Fields in two columns, the first taking the odd one: frappe's Column
	// Break, so the dialog reads down each column rather than in rows.
	static two_columns(list, field) {
		const half = Math.ceil(list.length / 2);
		return list.flatMap((one, at) => [...(at === half ? [{ fieldtype: "Column Break" }] : []), field(one, at)]);
	}

	// A new person, with the apps they get, in one step.
	invite_dialog(data) {
		const levels = data.levels.map((level) => ({ value: level.value, label: level.label }));
		const dialog = new frappe.ui.Dialog({
			title: __("Invite Somebody"),
			fields: [
				{ fieldname: "email", fieldtype: "Data", options: "Email", label: __("Email"), reqd: 1 },
				{ fieldtype: "Column Break" },
				{ fieldname: "first_name", fieldtype: "Data", label: __("First Name"), reqd: 1 },
				{ fieldname: "last_name", fieldtype: "Data", label: __("Last Name") },
				{ fieldtype: "Section Break", label: __("What They Can Use"), description: __("Everybody has One, OneCloud, OneMail, OneTask and OneCalendar.") },
				...Settings.two_columns(data.apps, (app) => ({ fieldname: `app_${app.icon}`, fieldtype: "Select", label: app.name, options: levels, default: "None" })),
			],
			primary_action_label: __("Invite"),
			primary_action: async (values) => {
				const access = Object.fromEntries(data.apps.map((app) => [app.name, values[`app_${app.icon}`]]));
				const said = await frappe.xcall(Settings.API + "invite", { email: values.email, first_name: values.first_name, last_name: values.last_name, access });
				dialog.hide();
				frappe.show_alert({ message: __("Invited. They get a mail to set their password."), indicator: "green" });
				this.data = said;
				this.$content.empty();
				this.draw_people(said);
			},
		});
		Settings.marks(dialog.$wrapper, data.apps);
		dialog.show();
	}

	// The workspace's account, drawn as a record: where it stands in the pill
	// and, when money or a lost connection is the news, a sentence above
	// everything; the plan and the credits as its parts; how old the copy is
	// in the side. Buying is the page's primary action.
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
						// Frappe's own sidebar list, as a form's links are.
						html: `<ul class="list-unstyled sidebar-menu">${[
							["/desk/workspace-settings?section=people", __("People")],
							["/desk/onecloud", __("OneCloud")],
							["/desk/query-report/AI Credits", __("What Used the Credits")],
						]
							.map(([href, label]) => `<li><a class="one-record-link" href="${esc(href)}">${esc(label)}</a></li>`)
							.join("")}</ul>`,
					},
				],
				meta: [account.last_heard ? __("As of {0}", [frappe.datetime.prettyDate(account.last_heard)]) : __("Not heard from the account yet")],
			}),
			actions: [
				{ label: __("Storage, Database or Seats"), action: () => this.add_to_plan(data), group: __("Add") },
				{ label: __("OneAI Credits"), action: () => this.buy_credits(), group: __("Add") },
				{ label: __("Payment Method"), action: () => this.payment_portal() },
				{ label: __("Check Again"), action: () => this.check_again() },
			],
		});
		const facts = (rows) =>
			`<dl class="os-facts">${rows
				.filter(([, value]) => value)
				.map(([label, value]) => `<dt>${esc(label)}</dt><dd>${value}</dd>`)
				.join("")}</dl>`;
		const seats = account.seats ? __("{0} of {1} used", [data.used, account.seats]) : __("{0} used, no limit", [data.used]);
		// Storage and database as frappe-ui's bar, orange from nine tenths and
		// red over, each leading to where the room is taken.
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
		const add_ons = (data.add_ons || [])
			.map(
				(one) => `<div class="one-shell-row" data-add-on="${esc(one.offering)}">
					<div class="one-shell-row-main"><div class="one-shell-row-title">${esc(one.quantity > 1 ? __("{0} × {1}", [one.quantity, one.label]) : one.label)}</div>
					<div class="one-shell-row-sub">${esc(__("{0} a month", [money(one.amount * (one.quantity || 1))]))}</div></div>
					<div class="one-shell-row-actions">${onedesk.shell.button(one.quantity > 1 ? __("Remove One") : __("Remove"), { "data-drop": "1" }, "ghost")}</div>
				</div>`
			)
			.join("");
		const expiring = account.credits_expiring
			? esc(__("{0} on {1}", [number(account.credits_expiring), frappe.datetime.str_to_user(account.credits_expires_on)]))
			: "";
		this.$content.html(
			(data.said ? `<div class="one-record-news">${frappe.ui.alert.html({ title: data.said.text, theme: data.said.colour === "red" ? "red" : "yellow" })}</div>` : "") +
				onedesk.shell.section(
					__("Plan"),
					facts([
						[__("Plan"), esc(account.plan || "")],
						[__("A Month"), account.monthly ? esc(money(account.monthly)) : ""],
						[__("Seats"), `<a href="/desk/workspace-settings?section=people">${esc(seats)}</a>`],
					]) +
						(storage ? `<a class="os-bar" href="/desk/onecloud">${storage}</a>` : "") +
						(database ? `<div class="os-bar">${database}</div>` : "") +
						(add_ons ? `<div class="os-add-ons"><div class="one-shell-section-title"><span>${esc(__("Added to the Plan"))}</span></div>${add_ons}</div>` : "")
				) +
				onedesk.shell.section(
					__("Invoices"),
					'<div data-list="invoices"><div class="one-shell-quiet">' + esc(__("Asking for them…")) + "</div></div>",
					__("What One has charged the workspace. Each opens Stripe's own copy; Add to OneBook makes it a draft bill in your books.")
				) +
				onedesk.shell.section(
					__("OneAI Credits"),
					facts([
						[__("Left"), esc(number(account.credits_balance))],
						[__("Held"), account.credits_held ? esc(number(account.credits_held)) : ""],
						[__("Used in the Last 30 Days"), account.credits_month ? esc(number(account.credits_month)) : ""],
						[__("Expiring"), expiring],
					]),
					__("OneAI is paid for with credits. The plan's monthly credits are used first, and the ones you buy never expire.")
				) +
				onedesk.shell.section(
					__("Ledger"),
					data.ledger ? '<div data-list="ledger"></div>' : `<div class="one-shell-quiet">${esc(__("The account could not be reached for the ledger just now."))}</div>`,
					__("The last {0} days: what came in, and what OneAI used each day. Click a day to see who and what used it.", [data.ledger_days])
				)
		);
		this.draw_invoices(this.$content.find('[data-list="invoices"]'));
		// One at a time: 2 × 1 GB becomes 1 × 1 GB, the last one comes off.
		this.$content.find("[data-add-on] [data-drop]").on("click", (event) => {
			const key = $(event.currentTarget).closest("[data-add-on]").attr("data-add-on");
			const kept = Object.fromEntries((data.add_ons || []).map((one) => [one.offering, one.quantity]));
			const one = (data.add_ons || []).find((row) => row.offering === key);
			kept[key] = (kept[key] || 1) - 1;
			frappe.confirm(
				__("Take one {0} off the plan? It saves {1} a month, and what it gave the workspace goes with it.", [
					one ? one.label : key,
					money(one ? one.amount : 0),
				]),
				() => this.take(account.plan_key, kept)
			);
		});
		// The account's ledger as frappe's table, as every list of ours is.
		if (data.ledger) {
			// A day of a few small calls is a fraction of a credit, which rounds to nothing.
			const amount = (value, sign) =>
				value ? `<span class="${sign === "+" ? "text-success" : ""}">${sign}${esc(format_number(value, null, value < 10 ? 2 : 0))}</span>` : "";
			onedesk.shell.table(this.$content.find('[data-list="ledger"]'), {
				rows: data.ledger,
				page_size: 15,
				icon: "coins",
				empty: __("Nothing came in or went out in that time."),
				columns: [
					{ label: __("Date"), render: (one) => esc(frappe.datetime.str_to_user(one.on)) },
					{ label: __("What"), fieldname: "what" },
					{ label: __("In"), render: (one) => amount(one.came, "+") },
					{ label: __("Out"), render: (one) => amount(one.went, "−") },
				],
				open: (one) => one.day && frappe.set_route("query-report", "AI Credits", { from_date: one.day, to_date: one.day, by: "Person" }),
			});
		}
	}

	// The workspace's Stripe invoices, asked for after the page is drawn so
	// the page does not wait on Stripe. Each opens Stripe's own page; one not
	// yet in this workspace's books can be added as a draft bill (one/bills.py).
	async draw_invoices($into) {
		const esc = frappe.utils.escape_html;
		let said;
		try {
			said = await frappe.xcall("onedesk.one.bills.invoices");
		} catch (e) {
			return $into.html(`<div class="one-shell-quiet">${esc(__("The invoices could not be fetched just now."))}</div>`);
		}
		const themes = { paid: "green", open: "orange", uncollectible: "red", void: "gray" };
		const states = { paid: __("Paid"), open: __("Due"), uncollectible: __("Unpaid"), void: __("Void") };
		const list = await onedesk.shell.table($into.empty(), {
			rows: said.invoices || [],
			page_size: 12,
			icon: "receipt",
			empty: __("No invoices yet."),
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
		// The button is inside a row that opens Stripe's page: it acts, and the row does not.
		$into.on("click", "[data-book]", async (event) => {
			event.stopPropagation();
			const bill = await frappe.xcall("onedesk.one.bills.to_books", { invoice: $(event.currentTarget).attr("data-book") });
			frappe.show_alert({ message: __("Added to OneBook as a draft bill."), indicator: "green" });
			frappe.set_route("Form", "Purchase Invoice", bill);
		});
		$into.on("click", "a[target=_blank]", (event) => event.stopPropagation());
		return list;
	}

	// Stripe's billing portal, in a new tab: the card, the billing address, old receipts.
	async payment_portal() {
		const said = await frappe.xcall("onedesk.one.bills.payment_portal");
		if (said && said.url) window.open(said.url, "_blank", "noopener");
	}

	// Make the plan this with exactly these add-ons (one_admin/billing.py),
	// then draw what the account says now.
	async take(plan, extras, label = null) {
		await frappe.xcall("onedesk.one.account.plans_take", { plan, extras, label });
		frappe.show_alert({ message: __("The plan was changed."), indicator: "green" });
		this.refresh({ fresh: true });
	}

	// Every plan side by side, the current one marked, and what moving to one
	// costs a month against now. The add-ons stay.
	async change_plan() {
		const said = await frappe.xcall("onedesk.one.account.plans_offered");
		const esc = frappe.utils.escape_html;
		const money = (value) => format_currency(value || 0, said.currency, 0);
		const gb = (value) => (value == null ? __("Unlimited") : __("{0} GB", [format_number(value, null, 0)]));
		const table = `<table class="table table-bordered os-plans"><thead><tr>
			<th>${esc(__("Plan"))}</th><th>${esc(__("Seats"))}</th><th>${esc(__("Storage"))}</th><th>${esc(__("Database"))}</th><th>${esc(__("Credits a Month"))}</th><th>${esc(__("A Month"))}</th>
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
					label: __("Move To"),
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

	// An add-on and how many, and what that costs a month. When the plan above
	// would give the same for less, it says so and offers that instead: the
	// calculator's one job on this side (one_admin/plans.py, quote).
	async add_to_plan(data) {
		const account = data.account || {};
		const said = await frappe.xcall("onedesk.one.account.plans_offered");
		const esc = frappe.utils.escape_html;
		const money = (value) => format_currency(value || 0, said.currency, 0);
		const sold = said.add_ons_sold || [];
		if (!sold.length) return frappe.msgprint(__("There is nothing to add just now."));
		const dialog = new frappe.ui.Dialog({
			title: __("Add to the Plan"),
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
				{ fieldname: "count", fieldtype: "Int", label: __("How Many"), reqd: 1, default: 1, change: () => show() },
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
			// What the workspace would have with it, and whether a plan gives that for less.
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
						  })}<div class="one-shell-actions">${onedesk.shell.button(__("Move to {0} Instead", [better.label]), { "data-better": better.plan }, "subtle")}</div></div>`
						: "")
			);
			dialog.fields_dict.said.$wrapper.find("[data-better]").on("click", async () => {
				dialog.hide();
				// The plan and exactly the add-ons it needs, in place of what is there.
				await this.take(better.plan, Object.fromEntries(better.extras.map((one) => [one.offering, one.count])), better.label);
			});
		}, 250);
		dialog.show();
		show();
	}

	// Ask the account now rather than tonight, and draw what it said.
	async check_again() {
		await frappe.xcall("onedesk.one.account.check_again");
		this.refresh({ fresh: true });
	}

	// A pack from the account's price list, then Stripe in a new tab. The
	// credit arrives when Stripe says the money moved, so the page asks again
	// when the reader comes back to it.
	async buy_credits() {
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

	// Where the workspace opens: the address One gives it, which always works,
	// and the customer's own, each once its DNS points here (one/account.py,
	// one_admin/domains.py). Add a Domain is the page's action.
	draw_domains(data) {
		const esc = frappe.utils.escape_html;
		const target = data.target || "";
		const rows = data.domains || [];
		const given = rows.find((one) => one.given);
		const primary = rows.find((one) => one.primary) || given;
		this.page.set_primary_action(__("Add a Domain"), () => this.add_domain(target), "plus");
		this.page.add_inner_button(__("Check Again"), async () => {
			await frappe.xcall("onedesk.one.account.domains_refresh");
			this.refresh();
		});
		// The record each of their own domains still needs, or an example one.
		const waiting = rows.filter((one) => !one.given && one.status !== "Active").map((one) => one.domain);
		this.$content.html(
			onedesk.shell.section(
				__("Addresses"),
				`<div data-list="domains"></div>${
					primary
						? `<div class="one-shell-quiet one-shell-note">${esc(
								__("{0} is the main address: sign-in, invitations and every link in mail use it.", [primary.domain])
						  )}</div>`
						: ""
				}`,
				__("Where the workspace opens in a browser. {0} always works; your own domain works once its DNS points here. Email addresses do not change.", [
					given ? given.domain : "",
				])
			) +
				(target
					? onedesk.shell.section(
							__("The DNS Record"),
							Settings.dns_records(waiting.length ? waiting : [null], target) + Settings.dns_note(waiting),
							waiting.length
								? __("Make this where your domain's DNS is kept. It works a few minutes after the record is right.")
								: __("What a domain of your own needs, where its DNS is kept.")
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
				? __("Waiting for the DNS record below. It works a few minutes after the record is right.")
				: __("Not working. Check the DNS record below, then remove the domain and add it again.");
		onedesk.shell.table(this.$content.find('[data-list="domains"]'), {
			rows,
			icon: "globe",
			empty: __("No domains yet."),
			columns: [
				{
					label: __("Domain"),
					render: (one) =>
						`<div>${esc(one.domain)} ${one.given ? frappe.ui.badge.html({ label: __("Given by One"), theme: "gray" }) : ""}</div>${
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
			frappe.confirm(__("Make {0} the main address? Sign-in, invitations and every link in mail will use it.", [esc(domain)]), async () => {
				await frappe.xcall("onedesk.one.account.domain_primary", { domain });
				this.refresh();
			});
		});
		this.$content.on("click", "[data-drop]", (event) => {
			const domain = of(event);
			frappe.confirm(__("Stop opening the workspace at {0}?", [esc(domain)]), async () => {
				await frappe.xcall("onedesk.one.account.domain_drop", { domain });
				this.refresh();
			});
		});
	}

	// The CNAME record each name needs, drawn as a DNS provider lists one:
	// type, name and value, each value with Copy. `null` is an example row.
	static dns_records(names, target) {
		const esc = frappe.utils.escape_html;
		const copy = (value) =>
			`<button type="button" class="os-dns-copy" data-copy="${esc(value)}" title="${esc(__("Copy"))}" aria-label="${esc(__("Copy"))}">${frappe.utils.icon("copy", "sm")}</button>`;
		const rows = names
			.map(
				(name) => `<tr>
					<td><span class="os-dns-value">CNAME</span></td>
					<td>${name ? `<span class="os-dns-value">${esc(name)}</span>${copy(name)}` : `<span class="text-muted">${esc(__("Your domain, such as office.example.com"))}</span>`}</td>
					<td><span class="os-dns-value">${esc(target)}</span>${copy(target)}</td>
				</tr>`
			)
			.join("");
		return `<table class="os-dns"><thead><tr><th>${esc(__("Type"))}</th><th>${esc(__("Name"))}</th><th>${esc(__("Value"))}</th></tr></thead><tbody>${rows}</tbody></table>`;
	}

	// Said only when it applies: a bare domain (acme.com) can take a CNAME
	// only where the DNS provider flattens it.
	static dns_note(names) {
		const bare = names.filter((name) => name && name.split(".").length === 2);
		if (!bare.length) return "";
		return `<div class="one-shell-quiet os-dns-lead">${frappe.utils.escape_html(
			__("{0} is a bare domain. It works only if your DNS provider allows a CNAME there, which some call ALIAS. If it does not, add www.{0} here instead and have your registrar redirect {0} to it.", [bare[0]])
		)}</div>`;
	}

	// The domain and the record it needs, together. Adding does not wait on
	// the DNS: the domain waits, and works a few minutes after the record does.
	add_domain(target) {
		const dialog = new frappe.ui.Dialog({
			title: __("Add a Domain"),
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
				frappe.show_alert({ message: __("Added. It works a few minutes after the DNS record is right."), indicator: "green" });
				this.refresh();
			},
		});
		const draw = () => {
			const name = (dialog.get_value("domain") || "").trim().toLowerCase() || null;
			dialog.fields_dict.record.$wrapper.html(
				`<div class="one-shell-quiet os-dns-lead">${frappe.utils.escape_html(__("Make this record where the domain's DNS is kept."))}</div>${Settings.dns_records(
					[name],
					target
				)}${Settings.dns_note([name])}`
			);
		};
		draw();
		dialog.$wrapper.on("click", "[data-copy]", (event) => frappe.utils.copy_to_clipboard($(event.currentTarget).attr("data-copy")));
		dialog.show();
	}

	// OneAI's actions: what each does, for which product, the model it runs
	// on (its maker's logo and name) and what it used in the last thirty
	// days. A row opens it: the model, what is added to it, and Try It.
	draw_oneai(data) {
		const esc = frappe.utils.escape_html;
		const params = frappe.utils.get_query_params();
		const only = params.product || null;
		const rows = (data.actions || []).filter((one) => !only || one.product === only);
		this.page.add_inner_button(__("Knowledge"), () => frappe.set_route("List", "AI Knowledge"));
		this.page.add_inner_button(__("What Used the Credits"), () => frappe.set_route("query-report", "AI Credits", { by: "Action" }));
		const note = only
			? __("{0}'s actions only.", [only])
			: __("Each thing OneAI does, and the model it runs on. Default is what One picked. Click one to change it.");
		this.$content.html(
			onedesk.shell.section(
				__("Actions"),
				`${only ? `<div class="one-shell-note"><a class="one-record-link" data-all>${esc(__("Show every action"))}</a></div>` : ""}<div data-list="actions"></div>`,
				note
			)
		);
		this.$content.find("[data-all]").on("click", () => {
			frappe.set_route("workspace-settings", { section: "oneai" });
			this.open("oneai");
		});
		onedesk.shell.table(this.$content.find('[data-list="actions"]'), {
			rows,
			page_size: 50,
			icon: "sparkles",
			empty: __("No actions are switched on."),
			columns: [
				{
					label: __("Action"),
					render: (one) =>
						`<div class="os-ai-action"><span>${esc(one.label)}</span>${Settings.product_badge(one.product)}</div>${
							one.about ? `<div class="one-shell-quiet">${esc(one.about)}</div>` : ""
						}`,
				},
				{ label: __("Model"), render: (one) => Settings.model_html(Settings.model_of(data.catalogue, one)) },
				{
					label: __("Last 30 Days"),
					render: (one) =>
						one.calls
							? `<span title="${esc(__("{0} calls", [one.calls]))}">${esc(__("{0} credits", [format_number(one.credits, null, one.credits < 10 ? 2 : 0)]))}</span>`
							: `<span class="text-muted">${esc(__("Not used"))}</span>`,
				},
			],
			open: (one) => this.action_dialog(one, data.catalogue),
		});
		if (params.action) {
			const one = rows.find((row) => row.name === params.action);
			if (one) this.action_dialog(one, data.catalogue);
		}
	}

	// The model an action runs on: what it chose, else the catalogue's
	// default for what it needs. `chosen` says which.
	static model_of(catalogue, one) {
		const offered = (catalogue || {})[one.capability] || [];
		const picked = one.model && offered.find((m) => m.name === one.model);
		const fallback = offered.find((m) => m.default);
		if (picked) return { ...picked, chosen: true };
		if (one.model) return { name: one.model, label: one.model, chosen: true, gone: true };
		return fallback ? { ...fallback, chosen: false } : null;
	}

	// The product an action works for, as a badge with its mark.
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

	// One action, changed where it is listed: its model, what is added to it,
	// Try It and Use the Default. Saved against when it was opened, as a
	// desk form is.
	action_dialog(one, catalogue) {
		const esc = frappe.utils.escape_html;
		const offered = (catalogue || {})[one.capability] || [];
		const fallback = offered.find((m) => m.default);
		const options = [
			{ value: "", label: fallback ? __("Default: {0}", [fallback.label]) : __("Default") },
			...offered.map((m) => ({ value: m.name, label: `${m.label} · ${m.maker}` })),
		];
		const describe = (name) => {
			const m = offered.find((x) => x.name === name) || fallback;
			if (!m) return "";
			const cost =
				m.read != null && m.written != null
					? __("About {0} credits per 1,000 words it reads, and {1} per 1,000 it writes.", [format_number(m.read, null, 2), format_number(m.written, null, 2)])
					: __("Priced per use rather than per word.");
			return `<div class="os-ai-picked">${Settings.model_html({ ...m, chosen: true })}<div class="one-shell-quiet">${esc(
				__("Made by {0}, run by {1}.", [m.maker, m.company])
			)} ${esc(cost)}</div></div>`;
		};
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
				{
					fieldname: "extra",
					fieldtype: "Small Text",
					label: __("Added Instructions"),
					default: one.extra || "",
					description: __("Added to what {0} already does, for everybody who uses it. It never replaces it.", [one.label]),
				},
			],
			primary_action_label: __("Save"),
			primary_action: async (values) => {
				await frappe.xcall("onedesk.one_ai.run.set_action", {
					action: one.name,
					model: values.model || "",
					extra: values.extra || "",
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
			dialog.add_custom_action(__("Use the Default"), () =>
				frappe.confirm(__("Run {0} on the default model with nothing added?", [esc(one.label)]), async () => {
					await frappe.xcall("onedesk.one_ai.run.reset_action", { action: one.name });
					dialog.hide();
					this.refresh();
				})
			);
		}
		dialog.show();
	}

	// Runs the action once as the dialog stands, saved or not. It costs
	// credits like any call, and says so before it runs.
	try_action(one, model, extra) {
		const esc = frappe.utils.escape_html;
		const asking = new frappe.ui.Dialog({
			title: __("Try {0}", [one.label]),
			fields: [
				{ fieldname: "warn", fieldtype: "HTML", options: `<div class="one-shell-quiet">${esc(__("This runs it once, as it stands in the dialog, and uses the workspace's credits like any other use."))}</div>` },
				{ fieldname: "text", fieldtype: "Small Text", label: __("Text"), reqd: 1 },
				{ fieldname: "said", fieldtype: "HTML" },
			],
			primary_action_label: __("Run"),
			primary_action: async (values) => {
				const where = asking.fields_dict.said.$wrapper;
				where.html(`<div class="one-shell-quiet">${esc(__("Asking…"))}</div>`);
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

	// OneIntake's settings in four parts, each a heading and what it decides,
	// under the month: what arrived, what OneAI handled and what waits, each
	// opening the inbox where it is.
	draw_intake(data) {
		const esc = frappe.utils.escape_html;
		const month = data.month || {};
		const inbox = (box) => `/desk/intake?box=${box}&everyone=1`;
		const fact = (value, label, href) =>
			`<a class="os-intake-fact" href="${esc(href)}"><span class="os-intake-number">${esc(format_number(value || 0, null, 0))}</span><span class="one-shell-quiet">${esc(label)}</span></a>`;
		const facts = `<div class="os-intake-facts">${[
			fact(month.arrived, __("Arrived"), inbox("done")),
			fact(month.handled, __("Handled by OneAI"), inbox("done")),
			fact(month.needed, __("Needed a Person"), inbox("waiting")),
			fact(month.waiting, __("Waiting Now"), inbox("waiting")),
			fact(month.undone, __("Undone"), inbox("done")),
		].join("")}</div>`;
		this.$content.append(onedesk.shell.section(__("This Month"), facts, __("For everybody in the workspace. Each number opens the inbox.")));
		this.$content.append(
			onedesk.shell.section(
				__("Where OneAI Reads"),
				`<div class="os-intake-list" data-list="mailboxes"></div><div class="os-intake-list" data-list="folders"></div>`,
				__("New mail in these mailboxes and new files in these folders are read. Starting one is for whoever holds it, since OneAI then acts as them; an administrator can stop any.")
			)
		);
		const links = (pairs) =>
			`<div class="one-shell-quiet os-intake-links">${pairs
				.map(([href, label]) => `<a class="one-record-link" href="${esc(href)}">${esc(label)}</a>`)
				.join(" · ")}</div>`;
		const marks = data.marks || {};
		this.form(data, {
			rows: [
				{ heading: __("What Is Read"), note: __("Besides the mailboxes and folders above.") },
				{ stack: ["records"] },
				["most_pages", "_"],
				{ heading: __("How Sure OneAI Must Be"), note: __("Anything OneAI is less sure of than this percentage waits for a person.") },
				["floor", "_"],
				{ stack: ["audit"] },
				{ heading: __("Filing") },
				{ stack: ["keep_in_place"] },
				["quiet_minutes", "_"],
				{ heading: __("OneBook"), note: __("What OneAI may do with bills and invoices it reads."), mark: marks.OneBook },
				{ stack: ["household", "submit_einvoices"] },
				{ html: links([["/desk/ready-to-submit", __("Ready to Submit")], ["/desk/query-report/Spending", __("Spending")]]) },
				...((data.hr || []).length
					? [
							{ heading: __("OneHR"), note: __("What OneAI does by itself when something arrives in OneHR. Each uses credits."), mark: marks.OneHR },
							{ stack: data.hr },
							{ html: links([["/desk/hr-settings", __("Interview recording and how long audio is kept are in HR Settings")]]) },
					  ]
					: []),
			],
		});
		this.draw_intake_sources(data);
		// What OneIntake's reading runs on is set with the rest of OneAI's actions.
		this.page.add_inner_button(__("Models"), () => frappe.set_route("workspace-settings", { section: "oneai", product: "OneIntake" }));
	}

	// The mailboxes and folders OneAI reads, as lists. Turning one on is its
	// holder's consent, since OneAI then acts as them; an administrator may
	// stop any (one_intake/switches.py).
	draw_intake_sources(data) {
		const esc = frappe.utils.escape_html;
		const reading = (on) => frappe.ui.badge.html({ label: on ? __("Reading") : __("Off"), theme: on ? "green" : "gray" });
		const again = () => this.refresh();
		const marks = data.marks || {};
		onedesk.shell.table(this.$content.find('[data-list="mailboxes"]'), {
			title: __("Mailboxes"),
			mark: marks.OneMail,
			rows: data.mailboxes || [],
			page_size: 10,
			icon: "mail",
			empty: __("No mailboxes yet."),
			columns: [
				{ label: __("Mailbox"), fieldname: "email" },
				{ label: __("Read by OneAI"), render: (one) => reading(one.on) },
				{ label: __("On Behalf Of"), render: (one) => esc(one.for || "") },
			],
			open: (one) => {
				if (one.on)
					return frappe.confirm(__("Stop OneAI reading new mail in {0}?", [esc(one.email)]), async () => {
						await frappe.xcall("onedesk.one_intake.switches.set_mailbox", { account: one.name, on: 0 });
						again();
					});
				if (!one.mine) return frappe.msgprint(__("Only somebody who holds {0} can let OneAI read it, because OneAI then acts as them.", [esc(one.email)]));
				frappe.confirm(
					__("OneAI will read new mail in {0} and its attachments, file them and act on them on your behalf. Scans and photos are read with OneAI credits.", [`<b>${esc(one.email)}</b>`]),
					async () => {
						await frappe.xcall("onedesk.one_intake.switches.set_mailbox", { account: one.name, on: 1 });
						again();
					}
				);
			},
		});
		onedesk.shell.table(this.$content.find('[data-list="folders"]'), {
			title: __("Folders"),
			mark: marks.OneCloud,
			rows: data.folders || [],
			page_size: 10,
			icon: "folder",
			empty: __("OneAI reads no folders yet."),
			columns: [
				{ label: __("Folder"), render: (one) => esc(one.path.replace(/^Home\//, "")) },
				{ label: __("On Behalf Of"), render: (one) => esc(one.for || "") },
			],
			actions: onedesk.shell.button(__("Add a Folder"), { "data-add-folder": "1" }, "subtle", "plus"),
			open: (one) =>
				frappe.confirm(__("Stop OneAI reading new files in {0} and the folders inside it?", [esc(one.path)]), async () => {
					await frappe.xcall("onedesk.one_intake.switches.set_folder", { folder: one.name, on: 0 });
					again();
				}),
		});
		this.$content.on("click", "[data-add-folder]", () => {
			const dialog = new frappe.ui.Dialog({
				title: __("Add a Folder"),
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
						options: `<div class="one-shell-quiet">${esc(
							__("OneAI will read new files in it and the folders inside it, file them and act on them on your behalf. Scans and photos are read with OneAI credits.")
						)}</div>`,
					},
				],
				primary_action_label: __("Read It"),
				primary_action: async (values) => {
					await frappe.xcall("onedesk.one_intake.switches.set_folder", { folder: values.folder, on: 1 });
					dialog.hide();
					again();
				},
			});
			dialog.show();
		});
	}

	// The holiday list in force today, edited here: its day off, its country
	// and its public holidays. Saving it is what OneHR, OneCalendar and
	// Intake's deadlines all read (one/holidays.py). Next year's list is made
	// from this one, and opened here with ?list=.
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
							__("It is in force for everybody from today, or from its first day if it starts later: leave, attendance, check-ins, the calendar and deadlines.")
						)}</div>`,
					},
				],
				primary_action_label: __("Use It"),
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
			frappe.show_alert({ message: __("{0} is ready and starts on its first day.", [name]), indicator: "green" });
			open_list(name);
		};
		if (data.empty) {
			this.$content.append(
				onedesk.shell.section(__("Holidays"), onedesk.shell.empty(__("No holiday list yet"), __("Choose one, and it is in force for everybody.")))
			);
			this.page.add_inner_button(__("Use Another List"), use_another);
			return;
		}
		const list = data.list;
		const day = (value) => frappe.datetime.str_to_user(value);
		if (list.in_force && !data.next && list.days_left <= 90) {
			const $make = $(onedesk.shell.button(__("Make Next Year's List"), {}, "ghost")).on("click", next_year);
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
						description: __("Until then {0} is in force.", [data.now]),
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
			fact(day(list.to_date), list.days_left >= 0 ? __("Last Day, in {0} days", [list.days_left]) : __("Last Day, passed")),
			...(data.elsewhere ? [fact(data.elsewhere, __("People on Their Own List"), "/desk/holiday-list-assignment?applicable_for=Employee&docstatus=1")] : []),
		].join("")}</div>`;
		this.$content.append(
			onedesk.shell.section(list.name, facts, __("{0} to {1}. Leave, attendance, check-ins, the calendar and deadlines all count around these days.", [day(list.from_date), day(list.to_date)]))
		);
		this.form(data, {
			rows: [
				{ heading: __("Days Off"), note: __("The days nobody works, every week of the list.") },
				{ stack: ["weekly_offs"] },
				{ heading: __("Public Holidays"), note: __("Add a day, change its name or remove it, then save.") },
				["country", "subdivision"],
				{ html: onedesk.shell.button(__("Add the Country's Public Holidays"), { "data-local": "1" }, "subtle", "plus") },
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
			frappe.show_alert({ message: added.length ? __("{0} holidays added. Save to keep them.", [added.length]) : __("Every one of them is already in the list."), indicator: "blue" });
		});
		if (list.in_force && data.next) this.page.add_inner_button(__("Next Year's List"), () => open_list(data.next));
		else if (list.in_force) this.page.add_inner_button(__("Make Next Year's List"), next_year);
		this.page.add_inner_button(__("Use Another List"), use_another);
	}

	// ---------------------------------------------------------------- notifications

	// Every notification One sends, by the app that sends it, or the one that
	// is open. Frappe's own (mentions, assignments, shares) are listed so the
	// page is the whole answer, but their text is frappe's and not ours to edit.
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
				? frappe.ui.badge.html({ label: __("Mailed by {0}", [one.mailed_by]), theme: "gray" })
				: one.outside
				? frappe.ui.badge.html({ label: __("Mailed Outside"), theme: "gray" })
				: one.always
				? frappe.ui.badge.html({ label: __("Always Mailed"), theme: "gray" })
				: channel(__("Email"), one.email, one.email_default) + " " + channel(__("Push"), one.push, one.push_default);
		const open_rule = (name) => frappe.set_route("workspace-settings", { section: this.key, rule: name });
		this.$content.html(
			`<div class="one-shell-section one-shell-note one-shell-quiet">${esc(
				__("What One tells people. Open one to change what it says and whether it may also be mailed or pushed. Blue is on for new people, and each person can change their own.")
			)}</div>
			<div class="one-shell-section" data-list="rules"></div>
			<div class="one-shell-section" data-list="types"></div>`
		);
		// The workspace's own rules, then everything One sends: frappe's table,
		// as every list of records is, each opening its own page.
		onedesk.shell.table(this.$content.find('[data-list="rules"]'), {
			title: __("Rules"),
			note: __("The workspace's own notifications: when something happens to a record, tell somebody."),
			rows: data.rules || [],
			icon: "bell-plus",
			empty: __("No rules yet."),
			open: (one) => open_rule(one.name),
			actions:
				onedesk.shell.button(__("Ask OneAI for One"), { "data-rule-ai": "1" }, "ghost", "sparkles") +
				onedesk.shell.button(__("New Rule"), { "data-rule-new": "1" }, "subtle", "plus"),
			columns: [
				{ label: __("Rule"), fieldname: "name" },
				{ label: __("What It Does"), render: (one) => `<span class="one-shell-quiet">${esc(one.said || "")}</span>` },
				{ label: "", render: (one) => (one.enabled ? "" : frappe.ui.badge.html({ label: __("Off"), theme: "gray" })) },
			],
		});
		onedesk.shell.table(this.$content.find('[data-list="types"]'), {
			title: __("What One Sends"),
			rows: data.apps.flatMap((group) => group.types.map((one) => ({ ...one, app: group.app, mark: group.mark }))),
			page_size: 100,
			icon: "bell",
			none: __("Nothing One sends is called that."),
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
					render: (one) => `<span class="os-app">${one.mark ? `<span class="os-app-mark">${frappe.utils.icon(one.mark, "sm")}</span>` : ""}${esc(one.app)}</span>`,
				},
				{ label: __("Channels"), render: channels },
				{ label: "", render: state },
			],
		});
		this.$content.on("click", "[data-rule-new]", () => open_rule("new"));
		this.$content.on("click", "[data-rule-ai]", () =>
			onedesk.oneai.open({ ask: __("Help me set up a notification rule. Ask me what should happen and who should be told, then suggest the rule.") })
		);
	}

	// One type, edited as a form is: its text and its channels, saved from the
	// page head against the record as it was loaded. The preview renders the
	// text as it will be sent, with each slot shown where its value goes.
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
						? __("{0} mails this itself, in its own words. Send This is the same switch as the one in its settings.", [type.mailed_by])
						: __("{0} mails this itself, in its own words, whenever it happens. It is listed so you can see everything the workspace sends.", [type.mailed_by])
				)}</div>`,
			});
		} else if (type.upstream) {
			rows.push(
				{
					html: `<div class="one-shell-quiet">${esc(
						type.rule
							? __("It is {0}'s own rule, {1}, so it says what {0} wrote.", [type.upstream, type.rule])
							: __("It says what {0} wrote.", [type.upstream])
					)}</div>`,
				},
				{ heading: __("Channels"), note: __("The bell is always on. These are what people may add to it, and what a new person starts with.") },
				["one_allow_email", "one_allow_push"],
				["one_email_default", "one_push_default"]
			);
		} else if (type.ours) {
			rows.push(
				{ heading: __("What It Says"), note: __("Left as it came, it is sent in each reader's own language. Once you change it, it is sent as you wrote it.") },
				["one_subject"],
				["one_message"],
				{ html: `${slots ? `<div class="one-shell-quiet os-slots">${__("It can use {0}", [slots])}</div>` : ""}${preview}` }
			);
			if (type.always) {
				rows.push(
					{ heading: __("Channels"), note: __("Its mail is always sent, so people can answer it by replying. The bell has it too, and push is theirs to choose.") },
					["one_allow_push", "one_push_default"]
				);
			} else if (!type.outside) {
				rows.push(
					{ heading: __("Channels"), note: __("The bell is always on. These are what people may add to it, and what a new person starts with.") },
					["one_allow_email", "one_allow_push"],
					["one_email_default", "one_push_default"]
				);
			} else {
				rows.push({ html: `<div class="one-shell-quiet">${esc(__("Mailed to addresses outside the workspace, so nobody chooses a channel for it."))}</div>` });
			}
		}
		const rewrite = () =>
			onedesk.oneai.open({
				ask: __(
					'Rewrite the text of the "{0}" notification so it is short, plain and friendly, and keeps every slot it uses. Suggest it as a change I can apply.',
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
					{ label: __("Who Gets It"), html: type.to ? `<div>${esc(type.to)}</div>` : "" },
				],
			}),
			actions:
				type.ours && !type.upstream
					? [
							{ label: __("Rewrite with OneAI"), action: rewrite },
							{ label: __("Back to the Default Text"), action: reset, group: __("Actions") },
					  ]
					: [],
		});
		const $card = this.form(data, { rows });
		const draw = frappe.utils.debounce(() => this.preview(type.name, $card), 400);
		// The preview follows the text; form() already keeps "Not Saved".
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
		// Rendered by the server from the administrator's own text, with every
		// value escaped and each slot a chip we drew: the one place this page
		// puts HTML it did not build itself.
		$card.find(".os-preview-subject").html(said.subject || "");
		$card.find(".os-preview-message").html(said.message || "");
		const wrong = [said.subject_wrong, said.message_wrong].filter(Boolean);
		$card.find(".os-preview-wrong").html(wrong.length ? frappe.ui.alert.html({ title: wrong.join(" "), theme: "red" }) : "");
	}

	// A rule of the workspace's, as a form: frappe's own Notification, held to
	// what a workspace rule may do (one/rules.py). The condition is frappe's
	// own filter editor; the fields it offers follow what the rule watches.
	draw_rule(data) {
		const esc = frappe.utils.escape_html;
		const rule = data.rule;
		const remove = () =>
			frappe.confirm(__("Delete the rule {0}? Nobody is told by it again.", [rule.name]), async () => {
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
				sub: esc(__("A rule of the workspace's")),
				groups: [{ label: __("What It Does"), html: rule.said ? `<div>${esc(rule.said)}</div>` : "" }],
			}),
			actions: rule.new ? [] : [{ label: __("Delete"), action: remove, group: __("Actions") }],
		});
		const rows = [
			["enabled"],
			...(rule.new ? [["rule_name"]] : []),
			{ heading: __("What It Watches") },
			["document_type", "event"],
			["date_changed", "days_in_advance"],
			["value_changed"],
			{ html: `<div class="os-filter-label">${esc(__("Only When"))}</div><div class="os-filters"></div>` },
			{ heading: __("Who Is Told"), note: __("Only people who can open the record are told.") },
			["roles"],
			["person_field", "send_to_all_assignees"],
			{ heading: __("What It Says") },
			["subject"],
			["message"],
			{ heading: __("Channels"), note: __("The bell is always on. These are what people may add to it, and what a new person starts with.") },
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
			if (!doctype) return $filters.html(`<div class="one-shell-quiet">${esc(__("Choose the kind of record first."))}</div>`);
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
		// Only what the person may read, and records in their own right.
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
		// A new rule, once saved, is opened under its own name.
		if (!rule.new && this.record === "rule:new") frappe.set_route("workspace-settings", { section: this.key, rule: rule.name });
	}
};
