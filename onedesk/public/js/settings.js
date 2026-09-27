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
	static WIDE = ["people"];

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
	}

	async show() {
		if (!this.said) this.said = await frappe.xcall(Settings.API + "sections");
		const mine = this.said.sections.filter((one) => one.group === this.group_name);
		const params = frappe.utils.get_query_params();
		const found = mine.find((one) => one.key === params.section) || mine[0];
		// A notification type is ?type=, a workspace rule ?rule= (or ?rule=new).
		if (found) this.open(found.key, { record: params.type || (params.rule ? `rule:${params.rule}` : null) });
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
		// The router names the page after show; the section's name wins.
		onedesk.shell.name(section.label);
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

		const shown = data.sessions.slice(0, 10);
		const more = data.sessions.length - shown.length;
		const places = onedesk.shell.section(
			__("Where You Are Signed In"),
			shown
				.map((one) =>
					row(
						`${esc(one.device)}${one.here ? " " + frappe.ui.badge.html({ label: __("This One"), theme: "blue" }) : ""}`,
						esc([one.address, __("last used {0}", [when(one.last_used)])].filter(Boolean).join(" · ")),
						one.here ? "" : onedesk.shell.button(__("Sign Out"), { "data-sign-out": one.key }, "ghost", "log-out")
					)
				)
				.join("") +
				(more > 0 ? `<div class="one-shell-quiet one-shell-note">${esc(__("And {0} more.", [more]))}</div>` : "") +
				(data.sessions.length > 1
					? `<div class="one-shell-actions">${onedesk.shell.button(__("Sign Out Everywhere Else"), { "data-elsewhere": "1" }, "subtle", "log-out")}</div>`
					: "")
		);

		const recent = data.recent.length
			? onedesk.shell.section(
					__("Recent Sign-ins"),
					data.recent
						.map((one) =>
							row(
								esc(frappe.datetime.str_to_user(one.on)),
								esc(one.address),
								one.failed ? frappe.ui.badge.html({ label: __("Failed"), theme: "red" }) : ""
							)
						)
						.join(""),
					__("A failed sign-in you did not make is somebody trying your password. Change it.")
			  )
			: "";

		this.$content.html(intro + password + passkey + places + recent);
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
		this.$content.find("[data-sign-out]").on("click", async (event) => {
			await frappe.xcall("onedesk.one.signin.sign_out", { key_of: $(event.currentTarget).attr("data-sign-out") });
			frappe.show_alert({ message: __("Signed out there."), indicator: "green" });
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
		await frappe.require("embedded_list.bundle.js");
		const remembered = new frappe.ui.EmbeddedList({
			wrapper: this.$content.find('[data-list="remembered"]'),
			title: esc(__("Remembered")),
			description: esc(__("Click one to change it.")),
			show_search: facts.length > 5,
			empty_icon: "brain",
			empty_message: __("Nothing yet. Tell OneAI to remember something, or add it here."),
			no_match_message: __("No memory says that."),
			get_data: () => Promise.resolve(facts),
			on_row_click: (one) => this.memory_dialog(one),
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
		remembered.refresh();
		// Everything at once is the header's quiet second action, asking first.
		if (facts.length > 1) {
			remembered.$header.find(".embedded-list-header-actions").append(
				frappe.ui.button.html({ label: __("Forget Everything"), variant: "ghost", theme: "red", attrs: { "data-forget-all": "1" } })
			);
			remembered.$header.find("[data-forget-all]").on("click", () =>
				frappe.confirm(__("Forget everything OneAI remembers about you?"), async () => redraw(await frappe.xcall(Settings.API + "forget_all")))
			);
		}
		if (knowledge.length) {
			new frappe.ui.EmbeddedList({
				wrapper: this.$content.find('[data-list="workspace"]'),
				title: esc(__("From Your Workspace")),
				description: esc(__("Written by your workspace's administrators for everybody. OneAI uses it when it helps you; they change it.")),
				show_search: knowledge.length > 5,
				get_data: () => Promise.resolve(knowledge),
				columns: [
					{ label: __("Title"), fieldname: "title" },
					{ label: __("Used On"), render: (one) => esc(one.applies_to || __("Everything")) },
				],
			}).refresh();
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
	// row opens the person (person_dialog), as a list row opens its record.
	async draw_people(data) {
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
		await frappe.require("embedded_list.bundle.js");
		new frappe.ui.EmbeddedList({
			wrapper: this.$content.find('[data-list="people"]'),
			title: esc(__("People")),
			description: esc(__("Click somebody to change what they can use, or to sign them out.")),
			show_search: data.people.length > 5,
			empty_message: __("Nobody yet. Invite somebody."),
			no_match_message: __("Nobody by that name."),
			get_data: () => Promise.resolve(data.people.map((one) => ({ ...one, search: `${one.full_name} ${one.name}` }))),
			on_row_click: (one) => this.person_dialog(one.name),
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
		}).refresh();
	}

	// One person: a Select per app and an Administrator switch, saved
	// together against the User as it was loaded; where they are signed in
	// and their last sign-ins; and in the footer, what an administrator does
	// when somebody leaves.
	async person_dialog(user) {
		const esc = frappe.utils.escape_html;
		const one = await frappe.xcall(Settings.API + "person", { user });
		const people = this.data;
		const levels = people.levels.map((level) => ({ value: level.value, label: level.label }));
		const SHOWN = 5;
		const signed = one.sessions.length
			? one.sessions
					.slice(0, SHOWN)
					.map((at) => `<div class="os-place"><div>${esc(at.device)}</div><div class="one-shell-quiet">${esc([at.address, frappe.datetime.prettyDate(at.last_used)].filter(Boolean).join(" · "))}</div></div>`)
					.join("") +
			  (one.sessions.length > SHOWN ? `<div class="os-place one-shell-quiet">${esc(__("And {0} more.", [one.sessions.length - SHOWN]))}</div>` : "")
			: `<div class="one-shell-quiet">${esc(one.me ? __("You. Your own are on your Sign-in page.") : __("Signed in nowhere."))}</div>`;
		const recent = one.recent
			.map(
				(at) =>
					`<div class="os-place"><div class="${at.failed ? "text-danger" : ""}">${esc(at.failed ? __("Failed") : __("Signed in"))}</div><div class="one-shell-quiet">${esc(
						[at.address, frappe.datetime.prettyDate(at.on)].filter(Boolean).join(" · ")
					)}</div></div>`
			)
			.join("");
		const about = [
			one.employee ? `<a href="${frappe.utils.get_form_link("Employee", one.employee)}">${esc(__("Their employee record"))}</a>` : "",
			esc(one.last_active ? __("Last active {0}.", [frappe.datetime.prettyDate(one.last_active)]) : __("Never signed in.")),
			one.enabled ? "" : esc(__("Turned off: they cannot sign in.")),
		]
			.filter(Boolean)
			.join(" · ");
		const dialog = new frappe.ui.Dialog({
			title: one.full_name || one.name,
			size: "large",
			fields: [
				{ fieldname: "about", fieldtype: "HTML", options: `<div class="one-shell-quiet">${esc(one.name)} · ${about}</div>` },
				{ fieldtype: "Section Break", label: __("What They Can Use"), description: __("Everybody has One, OneCloud, OneMail, OneTask and OneCalendar.") },
				...Settings.two_columns(people.apps, (app, at) => ({ fieldname: `app_${at}`, fieldtype: "Select", label: app.name, options: levels })),
				{ fieldtype: "Section Break" },
				{
					fieldname: "admin",
					fieldtype: "Switch",
					label: __("Administrator"),
					description: __("Opens Workspace settings: people, the plan, domains and OneAI. The other administrators are told."),
					default: one.admin ? 1 : 0,
				},
				{ fieldtype: "Section Break", label: __("Where They Are Signed In") },
				{ fieldname: "signed", fieldtype: "HTML", options: signed },
				...(recent ? [{ fieldtype: "Section Break", label: __("Last Sign-ins") }, { fieldname: "recent", fieldtype: "HTML", options: recent }] : []),
			],
			primary_action_label: __("Save"),
			primary_action: async (values) => {
				const access = Object.fromEntries(people.apps.map((app, at) => [app.name, values[`app_${at}`]]));
				try {
					const said = await frappe.xcall(Settings.API + "save_person", { user, access, admin: values.admin ? 1 : 0, modified: one.modified });
					dialog.hide();
					frappe.show_alert({ message: __("Saved."), indicator: "green" });
					this.data = said;
					this.$content.empty();
					this.draw_people(said);
				} catch (e) {
					// frappe has said why (the last administrator, or changed since).
				}
			},
		});
		const again = (said) => {
			dialog.hide();
			this.data = said;
			this.$content.empty();
			this.draw_people(said);
		};
		const actions = [];
		if (!one.me) {
			actions.push(
				one.enabled
					? frappe.ui.button({
							label: __("Turn Off"),
							variant: "ghost",
							theme: "red",
							icon: "power",
							onclick: () =>
								frappe.confirm(__("Turn {0} off? They are signed out now and cannot sign in. Everything they made stays.", [esc(one.full_name || one.name)]), async () =>
									again(await frappe.xcall(Settings.API + "set_enabled", { user, on: 0 }))
								),
					  })
					: frappe.ui.button({ label: __("Turn On"), variant: "ghost", icon: "power", onclick: async () => again(await frappe.xcall(Settings.API + "set_enabled", { user, on: 1 })) })
			);
			if (one.enabled) {
				actions.push(
					frappe.ui.button({
						label: __("Sign Out Everywhere"),
						variant: "ghost",
						icon: "log-out",
						onclick: () =>
							frappe.confirm(__("Sign {0} out on every device?", [esc(one.full_name || one.name)]), async () => {
								await frappe.xcall(Settings.API + "sign_out_everywhere", { user });
								dialog.hide();
								frappe.show_alert({ message: __("Signed out everywhere."), indicator: "green" });
							}),
					}),
					frappe.ui.button({
						label: __("Send a Password Reset"),
						variant: "ghost",
						icon: "key-round",
						onclick: async () => {
							await frappe.xcall(Settings.API + "send_reset", { user });
							frappe.show_alert({ message: __("Sent. They get a mail to choose a new password."), indicator: "green" });
						},
					})
				);
			}
		}
		dialog.custom_actions.append(...actions);
		// Not as defaults: frappe reads a default of "User" as the person
		// signed in (model.get_default_value).
		dialog.set_values(Object.fromEntries(people.apps.map((app, at) => [`app_${at}`, one.access[app.name]])));
		dialog.show();
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
				...Settings.two_columns(data.apps, (app, at) => ({ fieldname: `app_${at}`, fieldtype: "Select", label: app.name, options: levels, default: "None" })),
			],
			primary_action_label: __("Invite"),
			primary_action: async (values) => {
				const access = Object.fromEntries(data.apps.map((app, at) => [app.name, values[`app_${at}`]]));
				const said = await frappe.xcall(Settings.API + "invite", { email: values.email, first_name: values.first_name, last_name: values.last_name, access });
				dialog.hide();
				frappe.show_alert({ message: __("Invited. They get a mail to set their password."), indicator: "green" });
				this.data = said;
				this.$content.empty();
				this.draw_people(said);
			},
		});
		dialog.show();
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
			onedesk.shell.section(__("Plan"), `<dl class="os-facts">${facts}</dl>${storage ? `<div class="os-bar">${storage}</div>` : ""}`) +
				onedesk.shell.section(
					__("OneAI Credits"),
					`<dl class="os-facts">${credits}</dl><div class="one-shell-quiet one-shell-note">${esc(data.month || "")}</div>
					<div class="one-shell-actions">${onedesk.shell.button(__("Buy Credits"), { "data-buy": "1" }, "solid", "credit-card")}${onedesk.shell.button(__("See What Used Them"), { "data-used": "1" }, "ghost")}</div>`
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
				return `<div class="one-shell-row" data-domain="${esc(one.domain)}">
					<div class="one-shell-row-main"><div class="one-shell-row-title">${esc(one.domain)}</div><div class="one-shell-row-sub">
						${status ? frappe.ui.badge.html({ label: __(status), theme }) : ""}
						${one.primary ? frappe.ui.badge.html({ label: __("Primary"), theme: "blue" }) : ""}
						${(one.provided || one.given) ? frappe.ui.badge.html({ label: __("Ours"), theme: "gray" }) : ""}
					</div>${one.said ? `<div class="one-shell-quiet">${esc(one.said)}</div>` : ""}</div>
					<div class="one-shell-row-actions">
						${!one.primary && status === "Active" ? onedesk.shell.button(__("Make Primary"), { "data-primary": "1" }, "ghost") : ""}
						${!(one.provided || one.given) ? onedesk.shell.button(__("Remove"), { "data-drop": "1" }, "ghost", null, "red") : ""}
					</div>
				</div>`;
			})
			.join("");
		this.$content.html(
			onedesk.shell.section(
				__("Addresses"),
				(rows || onedesk.shell.empty(__("No domains yet."))) +
					`<div class="one-shell-actions">${onedesk.shell.button(__("Add a Domain"), { "data-add": "1" }, "solid", "plus")}${onedesk.shell.button(__("Check Again"), { "data-refresh": "1" }, "ghost", "refresh-cw")}</div>`,
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
				(one) => `<div class="one-shell-row" data-action="${esc(one.name)}">
				<div class="one-shell-row-main"><div class="one-shell-row-title">${esc(one.label)}</div>${one.about ? `<div class="one-shell-quiet">${esc(one.about)}</div>` : ""}</div>
				<div class="one-shell-row-actions">${frappe.ui.badge.html({ label: one.model || __("Default"), theme: one.model ? "violet" : "gray" })}
				${onedesk.shell.button(__("Change"), { "data-change": "1" }, "ghost")}</div>
			</div>`
			)
			.join("");
		this.$content.html(
			onedesk.shell.section(
				__("What Runs on Which Model"),
				rows,
				__("Each thing OneAI does can run on a model you choose, and be told something more. Default is what One picked.")
			) +
				onedesk.shell.section(
					__("Knowledge"),
					`<div class="one-shell-row"><div class="one-shell-row-main">${esc(__("{0} notes OneAI reads before it answers", [data.knowledge || 0]))}</div>
				<div class="one-shell-row-actions">${onedesk.shell.button(__("Open"), { "data-knowledge": "1" }, "ghost", "external-link")}</div></div>`
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
		this.form(data, { before: data.month ? `<div class="one-shell-note">${frappe.ui.badge.html({ label: data.month, theme: "violet" })}</div>` : "" });
	}

	draw_holidays(data) {
		const esc = frappe.utils.escape_html;
		const coming = (data.coming || [])
			.map((one) => `<div class="one-shell-row"><div class="one-shell-row-main">${esc(one.what || "")}</div><div class="one-shell-quiet">${frappe.datetime.str_to_user(one.date)}</div></div>`)
			.join("");
		const $card = $(
			onedesk.shell.section(
				__("The Workspace's Holidays"),
				`<div class="one-shell-form"></div><div class="one-shell-actions"></div></div><div class="one-shell-section"><div class="one-shell-section-title">${__("Coming Up")}</div>${
					coming || onedesk.shell.empty(__("None in the list."))
				}`,
				__("Days nobody works. Deadlines, leave and check-ins count around them.")
			)
		).appendTo(this.$content);
		this.group = new frappe.ui.FieldGroup({
			fields: [{ fieldname: "holiday_list", fieldtype: "Select", label: __("Holiday List"), options: ["", ...(data.lists || [])], default: data.chosen }],
			body: $card.find(".one-shell-form")[0],
		});
		this.group.make();
		this.saves(() => Settings.every(this.group, ["holiday_list"]), $card);
		$card.find(".one-shell-actions").html(
			(data.chosen ? onedesk.shell.button(__("Open the List"), { "data-open": "1" }, "ghost", "external-link") : "") +
				onedesk.shell.button(__("New List"), { "data-new": "1" }, "ghost", "plus")
		);
		$card.find("[data-open]").on("click", () => frappe.set_route("Form", "Holiday List", data.chosen));
		$card.find("[data-new]").on("click", () => frappe.new_doc("Holiday List"));
	}

	// ---------------------------------------------------------------- notifications

	// Every notification One sends, by the app that sends it, or the one that
	// is open. Frappe's own (mentions, assignments, shares) are listed so the
	// page is the whole answer, but their text is frappe's and not ours to edit.
	draw_notification_types(data) {
		if (data.rule) return this.draw_rule(data);
		if (data.type) return this.draw_notification_type(data);
		const esc = frappe.utils.escape_html;
		// Who it goes to, on its own line: the sentence above says when.
		const to = (one) => (one.to ? `<div class="one-shell-quiet os-to">${frappe.utils.icon("users", "xs")}${esc(one.to)}</div>` : "");
		const channel = (label, allowed, on) => (allowed ? frappe.ui.badge.html({ label, theme: on ? "blue" : "gray" }) : "");
		const row = (one) => {
			const badges = one.ours
				? [
						one.enabled ? "" : frappe.ui.badge.html({ label: __("Off"), theme: "gray" }),
						one.edited ? frappe.ui.badge.html({ label: __("Edited"), theme: "violet" }) : "",
						one.mailed_by
							? frappe.ui.badge.html({ label: __("Mailed by {0}", [one.mailed_by]), theme: "gray" })
							: one.outside
							? frappe.ui.badge.html({ label: __("Mailed Outside"), theme: "gray" })
							: one.always
							? frappe.ui.badge.html({ label: __("Always Mailed"), theme: "gray" })
							: channel(__("Email"), one.email, one.email_default) + channel(__("Push"), one.push, one.push_default),
				  ].join(" ")
				: "";
			return `<div class="one-shell-row ${one.ours ? "one-shell-row-link" : ""}" ${one.ours ? `data-type="${esc(one.name)}" tabindex="0"` : ""}>
				<div class="one-shell-row-main"><div class="one-shell-row-title">${esc(one.label)}</div>${
					one.about ? `<div class="one-shell-quiet">${esc(one.about)}</div>${to(one)}` : one.ours ? "" : `<div class="one-shell-quiet">${esc(__("Written by frappe. Each person chooses whether it is also mailed."))}</div>`
				}</div>
				<div class="one-shell-row-actions">${badges}${one.ours ? `<span class="one-shell-chevron">${frappe.utils.icon("chevron-right", "sm")}</span>` : ""}</div>
			</div>`;
		};
		const rule = (one) => `<div class="one-shell-row one-shell-row-link" data-rule="${esc(one.name)}" tabindex="0">
				<div class="one-shell-row-main"><div class="one-shell-row-title">${esc(one.name)}</div><div class="one-shell-quiet">${esc(one.said)}</div></div>
				<div class="one-shell-row-actions">${one.enabled ? "" : frappe.ui.badge.html({ label: __("Off"), theme: "gray" })}<span class="one-shell-chevron">${frappe.utils.icon("chevron-right", "sm")}</span></div>
			</div>`;
		this.$content.html(
			`<div class="one-shell-section one-shell-note one-shell-quiet">${esc(
				__("What One tells people. Open one to change what it says and whether it may also be mailed or pushed. Blue is on for new people, and each person can change their own.")
			)}</div>` +
				onedesk.shell.section(
					__("Rules"),
					((data.rules || []).map(rule).join("") || onedesk.shell.empty(__("No rules yet."))) +
						`<div class="one-shell-actions">${onedesk.shell.button(__("New Rule"), { "data-rule-new": "1" }, "subtle", "plus")}${onedesk.shell.button(__("Ask OneAI for One"), { "data-rule-ai": "1" }, "ghost", "sparkles")}</div>`,
					__("The workspace's own notifications: when something happens to a record, tell somebody.")
				) +
				data.apps.map((group) => onedesk.shell.section(group.app || __("Across One"), group.types.map(row).join(""))).join("")
		);
		const go = (event) => frappe.set_route("workspace-settings", { section: this.key, type: $(event.currentTarget).attr("data-type") });
		this.$content.find("[data-type]").on("click", go).on("keydown", (event) => event.key === "Enter" && go(event));
		const open_rule = (name) => frappe.set_route("workspace-settings", { section: this.key, rule: name });
		this.$content.find("[data-rule]").on("click", (event) => open_rule($(event.currentTarget).attr("data-rule")));
		this.$content.find("[data-rule]").on("keydown", (event) => event.key === "Enter" && open_rule($(event.currentTarget).attr("data-rule")));
		this.$content.find("[data-rule-new]").on("click", () => open_rule("new"));
		this.$content.find("[data-rule-ai]").on("click", () =>
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
		const head = `<div class="os-type-head">
			<div class="os-type-back">${onedesk.shell.button(__("All Notifications"), { "data-back": "1" }, "ghost", "arrow-left")}</div>
			<div class="os-who-name">${esc(type.label)}</div>
			${type.about ? `<div class="one-shell-quiet">${esc(type.about)}</div>` : ""}
			${type.to ? `<div class="one-shell-quiet os-to">${frappe.utils.icon("users", "xs")}${esc(type.to)}</div>` : ""}
			${
				type.ours && !type.upstream
					? `<div class="os-who-actions">${onedesk.shell.button(__("Rewrite with OneAI"), { "data-rewrite": "1" }, "subtle", "sparkles")}${onedesk.shell.button(
							__("Back to the Default Text"),
							{ "data-reset": "1" },
							"ghost",
							"rotate-ccw"
					  )}</div>`
					: ""
			}
		</div>`;
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
		const $card = this.form(data, { before: head, rows });
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
		$card.find("[data-back]").on("click", () => frappe.set_route("workspace-settings", { section: this.key }));
		$card.find("[data-reset]").on("click", async () => {
			await this.group.set_values({ one_subject: type.default_subject, one_message: type.default_message });
			this.check();
			this.preview(type.name, $card);
		});
		$card.find("[data-rewrite]").on("click", () =>
			onedesk.oneai.open({
				ask: __(
					'Rewrite the text of the "{0}" notification so it is short, plain and friendly, and keeps every slot it uses. Suggest it as a change I can apply.',
					[type.label]
				),
			})
		);
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
		const head = `<div class="os-type-head">
			<div class="os-type-back">${onedesk.shell.button(__("All Notifications"), { "data-back": "1" }, "ghost", "arrow-left")}</div>
			<div class="os-who-name">${esc(rule.new ? __("New Rule") : rule.name)}</div>
			${rule.said ? `<div class="one-shell-quiet">${esc(rule.said)}</div>` : ""}
			${rule.new ? "" : `<div class="os-who-actions">${onedesk.shell.button(__("Delete"), { "data-delete": "1" }, "ghost", "trash-2", "red")}</div>`}
		</div>`;
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
		const $card = this.form(data, { before: head, rows });
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
		$card.find("[data-back]").on("click", () => frappe.set_route("workspace-settings", { section: this.key }));
		$card.find("[data-delete]").on("click", () =>
			frappe.confirm(__("Delete the rule {0}? Nobody is told by it again.", [rule.name]), async () => {
				await frappe.xcall(Settings.API + "delete_rule", { name: rule.name });
				frappe.set_route("workspace-settings", { section: this.key });
			})
		);
		// A new rule, once saved, is opened under its own name.
		if (!rule.new && this.record === "rule:new") frappe.set_route("workspace-settings", { section: this.key, rule: rule.name });
	}
};
