frappe.provide("onedesk.mail");

// OneMail's settings, in frappe's own settings dialog (frappe.ui.SettingsDialog),
// opened from Settings at the foot of OneMail's rail. Mailboxes is everyone's:
// each mailbox they hold, opened into its own tabs (signature, out-of-office
// reply, users, connection, rules). Setup, Shared Mailboxes, System Mailboxes,
// Organization Mailboxes, Private Mailboxes and Mail Templates are a Workspace
// Administrator's: the company's domains and the mailboxes the workspace
// receives and sends from by default, who reads and sends from each shared
// mailbox, the address the workspace gives each person and whether it sends,
// everybody's mailboxes at the company's domains, which private mailboxes
// people may connect, and the templates. Roles is an administrator's: OneMail's role
// builder (public/js/role_matrix.js). Wording follows docs/WORDING.md. Every change is
// a call to one_mail/holders.py, connect.py and rules.py, or one_mail/mail_templates.py.
onedesk.mail.settings = (tab) => {
	const H = "onedesk.one_mail.holders.";
	const { esc, saved, heading, heading_with, row, glyph, chevron, empty, fields, button, buttons, remove, view, track, header_switch, switched } =
		onedesk.module_settings.kit;
	// What the reader's role lets them do across the workspace's mail
	// (one/boot.py `one_mail_may`, one_mail/abilities.py).
	const can = frappe.boot.one_mail_may || {};

	// Whose a mailbox is: the workspace's, a team's, the address the workspace
	// gives a person (System), a person's at a company domain (Organization),
	// or a person's own elsewhere, such as Gmail (Private).
	const kind_of = (box) =>
		box.workspace
			? __("Workspace")
			: box.shared
			? __("Shared")
			: box.hosted
			? __("System")
			: box.private
			? __("Private")
			: __("Organization");
	const icon_of = (box) =>
		box.workspace ? "building-2" : box.shared ? "users" : box.hosted ? "at-sign" : box.private ? "lock" : "building";

	const disconnect = (account, email, done) =>
		frappe.confirm(__("Disconnect {0}? Mail already synced is kept.", [esc(email)]), async () => {
			await frappe.xcall("onedesk.one_mail.connect.disconnect", { account });
			done();
		});

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
			const $list = $(`<div class="one-set-list"></div>`).appendTo(panel.body.empty());
			if (!boxes.length) $list.append(empty(__("No mailboxes")));
			boxes.forEach((box) => {
				const said = [kind_of(box), box.sends ? __("Read and Send") : __("Read Only")];
				if (box.sends && box.signed) said.push(box.signed);
				const day = (value) => frappe.datetime.str_to_user(value);
				if (box.covering_until) said.push(__("Covering until {0}", [day(box.covering_until)]));
				else if (box.away?.leave) said.push(__("On Leave until {0}", [day(box.away.until)]));
				else if (box.away) said.push(box.away.until ? __("Out of Office until {0}", [day(box.away.until)]) : __("Out of Office"));
				else if (box.replies) said.push(__("Auto Reply On"));
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
	// frappe's settings do. A shared mailbox's settings are an
	// administrator's (holders.may_manage).
	const R = "onedesk.one_mail.rules.";
	const managed = __("Your role doesn't allow changing this.");

	// A signature is shown as a mail client shows it: on white, whatever the
	// theme. The frame grows to what it holds.
	const framed = (html) =>
		$(`<iframe class="oms-signature-frame" sandbox="allow-same-origin" tabindex="-1" aria-hidden="true"></iframe>`)
			.attr("srcdoc", `<style>body{margin:0;padding:20px 24px;background:#fff}</style>${html}`)
			.on("load", function () {
				this.style.height = `${this.contentDocument.body.scrollHeight}px`;
			});

	// Each style's card is a sketch of it: bars for lines of text, a square
	// for the logo, in the company's colour where the style uses it.
	const sketch = (preset, colour) => {
		const at = (x, y, w, h, kind = "", look = "") =>
			`<i class="oms-sketch-bit ${kind}" style="left:${x}px;top:${y}px;width:${w}px;height:${h}px;${look}"></i>`;
		const bar = (x, y, w) => at(x, y, w, 3, "oms-sketch-text");
		const name = (x, y, w = 22) => at(x, y, w, 4, "oms-sketch-name");
		const branded = (x, y, w, h, look = "") => at(x, y, w, h, "", `background:${colour};${look}`);
		const lines = (x, y) => name(x, y) + bar(x, y + 8, 30) + bar(x, y + 14, 24);
		const drawn = {
			simple: lines(10, 9),
			beside: branded(8, 13, 10, 10) + branded(22, 9, 1, 18) + lines(27, 9),
			above: branded(10, 4, 8, 8) + lines(10, 15),
			accent: branded(8, 8, 2, 20) + branded(14, 9, 22, 4) + bar(14, 17, 30) + bar(14, 23, 24),
			line: name(6, 16, 12) + bar(21, 16.5, 10) + bar(34, 16.5, 10) + bar(47, 16.5, 7),
			tinted: branded(5, 5, 50, 26, "opacity:0.12") + lines(11, 10),
		}[preset];
		return drawn
			? `<span class="oms-sketch" aria-hidden="true">${drawn}</span>`
			: `<span class="oms-sketch oms-sketch-custom">${frappe.utils.icon("pencil", "sm")}</span>`;
	};

	// A signature is a style drawn from the person and the company, showing
	// what is ticked, or Custom: written by hand and never redrawn. The big
	// frame shows the chosen style, or the one under the pointer.
	const SIGN = "onedesk.one_mail.signatures.";
	const signature_tab = (box) => {
		let state = null;
		let was = "";
		const now = (panel) =>
			JSON.stringify([
				panel.get_value("sender_name") || "",
				state.preset,
				state.preset ? state.shown : [],
				state.preset ? "" : panel.get_value("custom") || "",
			]);
		const dirty = (panel) => panel.$header.find(".one-set-save").toggleClass("hide", now(panel) === was);
		const html_of = (preset) => (state.presets.find((one) => one.preset === preset) || {}).html;
		const show = (panel, preset = state.preset) => {
			const $look = panel.fieldgroup.get_field("look").$wrapper.empty();
			panel.fieldgroup.set_df_property("custom", "hidden", !!state.preset);
			if (preset) $look.append($(`<div class="oms-signature"></div>`).append(framed(html_of(preset))));
		};
		const cards = (panel) => {
			const $row = $(`<div class="oms-styles" role="radiogroup"></div>`).attr("aria-label", __("Style"));
			const card = (preset, label) =>
				$(`<button type="button" class="oms-style" role="radio"></button>`)
					.toggleClass("oms-style--chosen", state.preset === preset)
					.attr("aria-checked", state.preset === preset)
					.html(`${sketch(preset, state.colour)}<span class="oms-style-name">${esc(label)}</span>`)
					.on("mouseenter focus", () => preset && state.preset && show(panel, preset))
					.on("mouseleave blur", () => state.preset && show(panel))
					.on("click", () => {
						// Custom starts from Simple's lines, the one style the editor
						// can hold without flattening it.
						if (!preset && state.preset && !panel.get_value("custom"))
							panel.fieldgroup.set_value("custom", html_of("simple"));
						state.preset = preset;
						cards(panel);
						shows(panel);
						show(panel);
						dirty(panel);
					});
			for (const one of state.presets) $row.append(card(one.preset, one.label));
			$row.append(card("", __("Custom")));
			panel.fieldgroup.get_field("styles").$wrapper.empty().append($row);
		};
		const shows = (panel) => {
			const $wrapper = panel.fieldgroup.get_field("shows").$wrapper.empty();
			if (!state.preset) return;
			const $chips = $(`<div class="oms-chips"></div>`);
			for (const one of state.shows.filter((show) => show.has)) {
				const on = state.shown.includes(one.key);
				$(`<button type="button" class="oms-chip"></button>`)
					.toggleClass("oms-chip--on", on)
					.attr("aria-pressed", on)
					.html(`${on ? frappe.utils.icon("check", "xs") : ""}<span>${esc(one.label)}</span>`)
					.on("click", async () => {
						state.shown = on ? state.shown.filter((key) => key !== one.key) : [...state.shown, one.key];
						shows(panel);
						const drawn = await frappe.xcall(SIGN + "presets_of", { account: box.name, show: JSON.stringify(state.shown) });
						state.presets = drawn.presets;
						show(panel);
						dirty(panel);
					})
					.appendTo($chips);
			}
			$wrapper.append(`<div class="one-set-label">${esc(__("Show"))}</div>`).append($chips);
		};
		return {
			id: "signature",
			label: __("Signature"),
			icon: "signature",
			title: __("Signature"),
			description: box.may_sign
				? __("Added to every email sent from this mailbox.")
				: !box.sends
				? __("Requires Send access.")
				: __("Added to every email sent from this mailbox. Your role doesn't allow changing it."),
			actions: box.may_sign
				? [
						{
							label: __("Save"),
							variant: "solid",
							class: "one-set-save",
							click: async (panel) => {
								await frappe.xcall(SIGN + "set_preset", {
									account: box.name,
									preset: state.preset,
									show: JSON.stringify(state.shown),
									signature: panel.get_value("custom") || "",
									sender_name: panel.get_value("sender_name") || "",
								});
								saved();
								was = now(panel);
								dirty(panel);
							},
						},
				  ]
				: [],
			async render(panel) {
				if (!box.may_sign && !box.sends) return;
				const view = panel.shown;
				state = await frappe.xcall(SIGN + "presets_of", { account: box.name });
				if (view !== panel.shown) return;
				// Whoever may not change it still sees what goes out under their mail.
				if (!box.may_sign) {
					const $body = panel.body.empty();
					const $list = $(`<div class="one-set-list"></div>`).appendTo($body);
					const name = state.sender_name || state.default_sender_name || "—";
					row({ lead: "", title: __("Sender Name"), end: `<span class="one-set-value">${esc(name)}</span>` }).appendTo($list);
					const html = state.preset ? html_of(state.preset) : state.signature;
					$body.append(html ? $(`<div class="oms-signature"></div>`).append(framed(html)) : empty(__("No signature")));
					return;
				}
				panel.add_fields([
					{
						fieldname: "sender_name",
						fieldtype: "Data",
						label: __("Sender Name"),
						default: state.sender_name,
						placeholder: state.default_sender_name || __("The writer's name"),
						description: __("Shown with the address on every email sent from this mailbox, or the default name if empty."),
					},
					{ fieldname: "look", fieldtype: "HTML" },
					{ fieldname: "custom", fieldtype: "Text Editor", default: state.preset ? "" : state.signature, hidden: !!state.preset },
					{ fieldname: "styles", fieldtype: "HTML" },
					{ fieldname: "shows", fieldtype: "HTML" },
				]);
				cards(panel);
				shows(panel);
				show(panel);
				panel.$header.find(".one-set-save").addClass("hide");
				setTimeout(() => {
					was = now(panel);
					dirty(panel);
				}, 600);
				panel.fieldgroup.get_field("custom").df.change = () => dirty(panel);
				panel.fieldgroup.get_field("sender_name").df.change = () => dirty(panel);
				panel.body.off("input.oms-signature").on("input.oms-signature", () => dirty(panel));
			},
		};
	};

	// A person's out-of-office, on any mailbox of their own: dates, who it
	// answers, the message (the standard one until it is
	// changed) and the reply as a sender gets it. Approved leave answers on
	// its own, said at the top whether or not the switch is on.
	const away_tab = (box) => {
		let standard = "";
		const values = (panel) => {
			const said = panel.get_values() || {};
			const message = (said.message || "").trim();
			return {
				account: box.name,
				from_date: said.from_date || null,
				until: said.until || null,
				to: said.to || "Everyone",
				message: message === standard.trim() ? "" : message,
			};
		};
		let waiting = null;
		const preview = (panel) => {
			clearTimeout(waiting);
			waiting = setTimeout(async () => {
				const said = values(panel);
				const drawn = await frappe.xcall(R + "away_preview", { account: box.name, message: panel.get_value("message") || "" });
				const untouched = !(panel.get_value("message") || "").trim() || panel.get_value("message").trim() === standard.trim();
				standard = drawn.default;
				if (untouched && panel.get_value("message") !== standard) panel.fieldgroup.set_value("message", standard);
				panel.fieldgroup
					.get_field("preview")
					.$wrapper.empty()
					.append(`<div class="one-set-label">${esc(__("What They Get"))}</div>`)
					.append($(`<div class="oms-signature"></div>`).append(framed(drawn.html)));
			}, 300);
		};
		const note = (away) => {
			if (away.leave_until) {
				const words = [__("You're on approved leave until {0}. Replies go out on their own, saying you're back on {1}.", [frappe.datetime.str_to_user(away.leave_until), frappe.datetime.str_to_user(away.leave_back)])];
				if (away.covering) words.push(__("They name {0} for anything urgent.", [away.covering.name]));
				return words.join(" ");
			}
			return __("While you're on approved leave, replies go out on their own until you're back, with the Away Message from your leave request.");
		};
		return {
			id: "away",
			label: __("Out of Office"),
			icon: "plane",
			title: __("Out of Office"),
			description: box.may.away ? __("Each sender gets it once every 4 days. Never sent to mailing lists or automatic mail.") : "",
			actions: box.may.away
				? [
						{
							label: __("Save"),
							variant: "solid",
							class: "one-set-save",
							click: async (panel) => {
								await frappe.xcall(R + "set_away", { ...values(panel), away: panel.on.get_value() ? 1 : 0 });
								saved();
								panel.clean();
							},
						},
				  ]
				: [],
			async render(panel) {
				const view = panel.shown;
				const away = (await frappe.xcall(R + "away_of", { account: box.name })) || {};
				if (view !== panel.shown) return;
				// The leave note sits between the heading and the fields, so it
				// shows whether the switch is on or off.
				panel.$header.siblings(".oms-leave").remove();
				onedesk.alert({ text: note(away) }).addClass("one-set-alert oms-leave").insertAfter(panel.$header);
				if (!box.may.away) return;
				panel.add_fields([
					{ fieldname: "from_date", fieldtype: "Date", label: __("From"), default: away.one_away_from, description: __("Leave empty to start now.") },
					{ fieldtype: "Column Break" },
					{ fieldname: "until", fieldtype: "Date", label: __("Until"), default: away.one_away_until, description: __("Leave empty to keep it on until you turn it off.") },
					{ fieldtype: "Section Break" },
					{
						fieldname: "to",
						fieldtype: "Select",
						label: __("Sent To"),
						default: away.one_away_to || "Everyone",
						options: [
							{ value: "Everyone", label: __("Everyone") },
							{ value: "Workspace", label: __("Workspace Only") },
							{ value: "Contacts", label: __("Workspace and Contacts") },
						],
					},
					{ fieldtype: "Section Break" },
					{ fieldname: "message", fieldtype: "Small Text", label: __("Message"), default: away.one_away_message || "" },
					{ fieldname: "preview", fieldtype: "HTML" },
				]);
				track(panel);
				panel.body.off("input.oms-away").on("input.oms-away", "textarea", () => preview(panel));
				preview(panel);
				panel.on = header_switch(panel, away.one_away, async (on) => {
					await frappe.xcall(R + "set_away", { ...values(panel), away: on });
					panel.clean();
				});
			},
		};
	};

	// How far OneAI may go with this mailbox (one_mail/gate.py). Off reaches
	// everything that reads mail, the OneAI panel included.
	const G = "onedesk.one_mail.gate.";
	// What OneIntake does with a mailbox's mail, each its own switch, by the
	// level it starts at (one_mail/gate.py JOBS).
	const NOT_READ = "Not Read";
	const LEVELS = [
		[NOT_READ, __("Not Read")],
		["Sort Only", __("Sorted")],
		["Read and File", __("Read and Filed")],
		["Read, File and Act", __("Read, Filed and Acted On")],
	];
	const JOBS = [
		{
			level: "Sort Only",
			title: __("Sorting"),
			note: __("Automation rules that ask OneAI need this level."),
			jobs: [
				["junk", __("Move Junk and Phishing"), __("Phishing also alerts the mailbox's users.")],
				["newsletters", __("Move Newsletters and Ads"), __("Creates a Newsletters folder if there is none.")],
			],
		},
		{
			level: "Read and File",
			title: __("Filing"),
			jobs: [
				["link", __("Link Messages to Records"), __("Shows the message on each record's timeline.")],
				["attach", __("Attach Files to Records"), __("Payslips and IDs are only attached to the Employee.")],
				["tidy", __("Rename and Tag Files"), __("Also splits a scan of several letters into one file each.")],
			],
		},
		{
			level: "Read, File and Act",
			title: __("Actions"),
			note: __("Changes OneAI is unsure of wait for approval in OneIntake."),
			jobs: [
				["parties", __("Create Customers and Suppliers"), __("Also Leads and Job Applicants, for unknown senders.")],
				["contacts", __("Create and Update Contacts"), __("For the sender and everyone in To and Cc.")],
				["enrich", __("Update Tax ID, Website and Phone"), __("Fills empty fields. A different value waits for approval in OneIntake.")],
				["tasks", __("Create Tasks"), __("Includes follow-ups promised in sent mail.")],
				["events", __("Create Events"), ""],
				["money", __("Draft Invoices, Orders and Payments"), __("Saved as drafts in Ready to Submit. A bill asking to be paid to a new IBAN is held.")],
				["hr", __("File Employee Documents"), __("IDs, certificates, leave, resignations and expense claims.")],
				["projects", __("Post Site Logs"), __("Saved as a Project Update.")],
				["agent", __("Other Actions"), __("Comments, and records of other types.")],
			],
		},
	];
	const LEVEL_SAYS = {
		[NOT_READ]: __("OneAI does not read new mail."),
		"Sort Only": __("Moves junk and newsletters out of the Inbox."),
		"Read and File": __("Also links each message and its files to its records."),
		"Read, File and Act": __("Also creates the records and tasks a message asks for."),
	};
	const at = (level) => LEVELS.findIndex((one) => one[0] === level);
	const credits = (said) => {
		const used = format_number(said.used, null, said.used % 1 ? 2 : 0);
		if (!said.limit) return `<div class="oms-meter-said">${esc(__("{0} credits used this month. There is no limit.", [used]))}</div>`;
		const share = Math.min(100, Math.round((said.used / said.limit) * 100));
		return `<div class="oms-meter${share >= 90 ? " oms-meter-full" : ""}" role="meter" aria-valuemin="0" aria-valuemax="${said.limit}" aria-valuenow="${said.used}"><span style="width: ${share}%"></span></div>
			<div class="oms-meter-said">${esc(__("{0} of {1} credits used this month.", [used, format_number(said.limit, null, 0)]))}</div>`;
	};

	const oneai_tab = (box) => ({
		id: "oneai",
		label: __("OneAI"),
		icon: "oneai",
		title: __("OneAI"),
		description: box.may.ai
			? __("What OneAI does with new mail on its own. It never mails anyone outside the workspace. If disabled, OneAI can't read this mailbox.")
			: __("What OneAI does with new mail in this mailbox. Your role doesn't allow changing it."),
		actions: box.may.ai
			? [
					{
						label: __("Save"),
						variant: "solid",
						class: "one-set-save",
						click: async (panel) => {
							const values = panel.get_values();
							if (!values) return;
							const save = async () => {
								const reads = values.mail !== NOT_READ;
								panel.said = await frappe.xcall(G + "set_settings", {
									account: box.name,
									reads: reads ? 1 : 0,
									level: reads ? values.mail : undefined,
									attachments: values.attachments ? 1 : 0,
									limit: values.limit || 0,
									skips: JOBS.flatMap((group) => group.jobs.map((job) => job[0])).filter((key) => !values[`job_${key}`]),
								});
								saved();
								panel.clean();
							};
							const stops = values.mail === NOT_READ && panel.said?.reads ? panel.said.asks || [] : [];
							if (!stops.length) return save();
							frappe.confirm(
								__("Set New Mail to Not Read? {0} will stop running.", [stops.map(esc).join(", ")]),
								save
							);
						},
					},
			  ]
			: [],
		async render(panel) {
			const said = (panel.said = await frappe.xcall(G + "settings_of", { account: box.name }));
			if (!said.ai) {
				panel.set_header({ title: __("OneAI"), description: __("OneAI is turned off for this workspace in Apps.") });
				return;
			}
			if (!said.may_manage) {
				const $list = $(`<div class="one-set-list"></div>`).appendTo(panel.body.empty());
				const value = (title, said_value) =>
					row({ lead: "", title, end: `<span class="one-set-value">${esc(said_value)}</span>` }).appendTo($list);
				value(__("OneAI"), said.on ? __("On") : __("Off"));
				if (!said.on) return;
				const level = said.reads ? said.level : NOT_READ;
				value(__("New Mail"), (LEVELS.find((one) => one[0] === level) || [])[1] || level);
				if (said.reads) value(__("Read Attachments"), said.attachments ? __("Yes") : __("No"));
				return;
			}
			const reading = (level) => `eval:doc.mail && doc.mail !== "${NOT_READ}"` + (level ? ` && ${at(level)} <= ${JSON.stringify(LEVELS.map((one) => one[0]))}.indexOf(doc.mail)` : "");
			const fields = [
				...(box.connected && !box.shared
					? [
							{
								fieldname: "own",
								fieldtype: "HTML",
								options: onedesk.alert({
									text: __("This is your own mailbox. If OneAI reads it, it files and acts on this mail in the workspace, with your permissions."),
									colour: "orange",
								})
									.addClass("one-set-alert")
									.prop("outerHTML"),
							},
					  ]
					: []),
				{
					fieldname: "mail",
					fieldtype: "Select",
					label: __("New Mail"),
					options: LEVELS.map(([value, label]) => ({ value, label })),
					default: said.reads ? said.level : NOT_READ,
					change: () => levelled(panel),
					description: LEVEL_SAYS[said.reads ? said.level : NOT_READ],
				},
				{
					fieldname: "attachments",
					fieldtype: "Switch",
					label: __("Read Attachments"),
					default: said.attachments,
					depends_on: reading(),
					description: __("Also reads attached PDFs, scans and photos, which uses the most credits."),
				},
			];
			JOBS.forEach((group) => {
				fields.push(
					{ fieldname: `group_${at(group.level)}`, fieldtype: "Section Break", label: group.title, depends_on: reading() },
					{
						fieldname: `about_${at(group.level)}`,
						fieldtype: "HTML",
						options: `<p class="oms-group-about">${group.note ? `${esc(group.note)} ` : ""}<span class="oms-later">${esc(
							__("Requires New Mail set to {0}.", [LEVELS[at(group.level)][1]])
						)}</span></p>`,
					}
				);
				group.jobs.forEach(([key, label, about]) =>
					fields.push({
						fieldname: `job_${key}`,
						fieldtype: "Switch",
						label,
						description: about,
						default: said.skips.includes(key) ? 0 : 1,
					})
				);
			});
			fields.push(
				{ fieldname: "credits_break", fieldtype: "Section Break", label: __("Credits"), depends_on: reading() },
				{ fieldname: "used", fieldtype: "HTML", options: credits(said) },
				{
					fieldname: "limit",
					fieldtype: "Int",
					label: __("Monthly Credit Limit"),
					default: said.limit || "",
					description: __("OneAI stops reading new mail for the rest of the month once this is used, with no limit if empty."),
				}
			);
			panel.add_fields(fields);
			levelled(panel);
			track(panel);
			panel.on = header_switch(panel, said.on, async (on) => {
				await frappe.xcall(G + "set_settings", { account: box.name, on });
				panel.clean();
			});
		},
	});

	// A job past the level New Mail is set to stays in view, greyed and
	// out of reach, with its group saying which level brings it.
	const levelled = (panel) => {
		const level = panel.fieldgroup.get_value("mail");
		const now = at(level);
		const mail = panel.fieldgroup.get_field("mail");
		const runs_as = panel.said?.reads && panel.said.for && level !== NOT_READ ? " " + __("Runs with {0}'s permissions.", [panel.said.for]) : "";
		mail.$wrapper.find(".help-box").text((LEVEL_SAYS[level] || "") + runs_as);
		JOBS.forEach((group) => {
			const later = at(group.level) > now;
			panel.fieldgroup.get_field(`about_${at(group.level)}`).$wrapper.find(".oms-later").toggle(later);
			group.jobs.forEach(([key]) => {
				const field = panel.fieldgroup.get_field(`job_${key}`);
				field.$wrapper.toggleClass("oms-job-later", later);
				field.$input && field.$input.prop("disabled", later);
			});
		});
	};

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
			panel.set_header({ title: __("Users"), description: users_said(one_box) });
			const $add = $(`<div class="one-set-add one-set-add-top"></div>`).appendTo(panel.body);
			const pick = frappe.ui.form.make_control({
				df: {
					fieldtype: "Link",
					fieldname: "user",
					options: "User",
					placeholder: __("Select User"),
					get_query: () => ({
						filters: { user_type: "System User", enabled: 1, name: ["not in", one_box.people.map((one) => one.user)] },
					}),
				},
				parent: $(`<span class="one-set-add-pick"></span>`).appendTo($add),
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
			const $list = $(`<div class="one-set-list"></div>`).appendTo(panel.body);
			if (!one_box.people.length) $list.append(empty(__("No users")));
			// Beyond reading and sending, what each person may change in this
			// one mailbox (holders.give, a share of it).
			const labelled = Object.fromEntries((said.abilities || []).map((one) => [one.key, one.label]));
			const may_sub = (one) => (one.may.length ? __("Can change {0}", [one.may.map((key) => labelled[key]).join(", ")]) : one.user);
			const choose = (one, $row) => {
				const open = (said.abilities || []).filter((ability) => !one.covered.includes(ability.key));
				const covered = (said.abilities || []).filter((ability) => one.covered.includes(ability.key));
				const dialog = new frappe.ui.Dialog({
					title: __("Access for {0}", [one.name]),
					fields: [
						{
							fieldname: "where",
							fieldtype: "HTML",
							options: `<p class="text-muted small">${esc(
								covered.length
									? __("Only in {0}. Their role already allows {1}.", [box.email, covered.map((ability) => ability.label).join(", ")])
									: __("Only in {0}.", [box.email])
							)}</p>`,
						},
						{
							fieldname: "keys",
							fieldtype: "MultiCheck",
							columns: 2,
							options: open.map((ability) => ({ label: ability.label, value: ability.key, checked: one.may.includes(ability.key) })),
						},
					],
					primary_action_label: __("Save"),
					primary_action: async ({ keys }) => {
						one.may = await frappe.xcall(H + "give", { account: box.name, user: one.user, keys: keys || [] });
						$row.find(".one-set-sub").text(may_sub(one));
						dialog.hide();
						saved();
					},
				});
				dialog.show();
			};
			one_box.people.forEach((one) => {
				const $row = row({ lead: frappe.ui.avatar.html({ label: one.name, size: "md" }), title: one.name, sub: esc(may_sub(one)) }).appendTo($list);
				$row.find(".one-set-title").append(" ", frappe.ui.badge.html({ label: one.role, theme: "gray" }));
				const $end = $row.find(".one-set-end");
				const everything = (said.abilities || []).every((ability) => one.covered.includes(ability.key));
				const $access = button({ label: __("Edit Access"), variant: "outline", size: "sm" }).appendTo($end);
				if (everything) $access.prop("disabled", true).attr("title", __("Their role already allows everything here."));
				else $access.on("click", () => choose(one, $row));
				const send = frappe.ui.form.make_control({
					df: { fieldtype: "Switch", fieldname: "sends", label: __("Send"), read_only: !one_box.enable_outgoing },
					parent: $(`<span class="one-set-switch"></span>`).appendTo($end),
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

	// A connected mailbox: where it reads and sends from and when mail was
	// last checked; Reconnect asks for the password again.
	const connection_tab = (box, from) => ({
		id: "connection",
		label: __("Connection"),
		icon: "plug",
		title: __("Connection"),
		description: box.error ? __("Disconnected. {0}", [box.error]) : __("Connected"),
		actions: [
			{ label: __("Disconnect"), theme: "red", click: () => disconnect(box.name, box.email, () => home(from)) },
			{ label: __("Reconnect"), variant: "solid", click: () => reconnect(box, from) },
		],
		async render(panel) {
			const said = await frappe.xcall("onedesk.one_mail.connect.connection_of", { account: box.name });
			const $list = $(`<div class="one-set-list"></div>`).appendTo(panel.body.empty());
			[
				[__("Incoming Server"), said.incoming || "—"],
				[__("Outgoing Server"), said.outgoing || __("Not sending")],
				[__("Last Checked"), said.checked ? frappe.datetime.prettyDate(said.checked) : __("Not yet")],
			].forEach(([title, value]) => row({ lead: "", title, end: `<span class="one-set-value">${esc(value)}</span>` }).appendTo($list));
		},
	});
	const reconnect = (box, from) => {
		const dialog = new frappe.ui.Dialog({
			title: __("Reconnect {0}", [box.email]),
			fields: [
				{ fieldname: "password", fieldtype: "Password", label: __("Password"), reqd: 1, description: __("Gmail and Outlook require an app password.") },
				{ fieldname: "login", fieldtype: "Data", label: __("Login ID"), description: __("Leave empty to use the email address.") },
			],
			primary_action_label: __("Reconnect"),
			primary_action: async (values) => {
				await frappe.xcall("onedesk.one_mail.connect.reconnect", { account: box.name, ...values });
				dialog.hide();
				saved();
				open(box.name, from, "connection");
			},
		});
		dialog.show();
	};

	// A mailbox's rules, in the order they run, each opened in the tab as
	// steps (public/js/one_mail/rule_builder.js; rules.py: rules_of_mailbox,
	// save_rule, enable_rule, delete_rule, decide_rule). Whoever manages the
	// mailbox changes them; the person a workspace address is issued to
	// asks, and a Mail Manager approves.
	const builder_files = ["/assets/onedesk/js/one_mail/rule_builder.js", "/assets/onedesk/css/one_mail/rule_builder.css"];
	const rules_tab = (box) => ({
		id: "rules",
		label: __("Automation"),
		icon: "workflow",
		title: __("Automation"),
		description: box.may.rules
			? __("Rules you write, run in order on each new message. They come before what OneAI does.")
			: box.hosted && !box.shared
			? __("Rules you write, run in order on each new message. A rule you ask for runs once a Mail Manager approves it.")
			: managed,
		actions:
			box.may.rules || (box.hosted && !box.shared)
				? [
						{
							label: box.may.rules ? __("New Rule") : __("Request Rule"),
							icon: "plus",
							click: (panel) => starters_view(panel, box),
						},
				  ]
				: [],
		async render(panel) {
			const was = panel.shown;
			const said = await frappe.xcall(R + "rules_of_mailbox", { account: box.name });
			if (panel.shown !== was) return;
			panel.said = said;
			if (!said.may) return;
			const $list = $(`<div class="one-set-list"></div>`).appendTo(panel.body.empty());
			if (!said.rules.length) $list.append(empty(__("No rules")));
			said.rules.forEach((rule) => {
				const $end = row({
					lead: glyph("list-filter"),
					title: rule.title || __("Mail Rule"),
					sub: esc([rule.when, rule.then].filter(Boolean).join(" → ")),
					end: chevron(),
					open: () => rule_view(panel, box, rule),
				})
					.appendTo($list)
					.find(".one-set-end");
				if (rule.requested_by) {
					$end.prepend(frappe.ui.badge.html({ label: __("Waiting for Approval"), theme: "orange" }));
					return;
				}
				if (rule.needs_ai && rule.enabled && !said.reads)
					$end.prepend(
						$(frappe.ui.badge.html({ label: __("Not Running"), theme: "gray" })).attr(
							"title",
							__("New Mail is set to Not Read in the OneAI tab.")
						)
					);
				if (!said.manages) return;
				const on = frappe.ui.form.make_control({
					df: { fieldtype: "Switch", fieldname: "enabled", label: "" },
					parent: $(`<span class="one-set-switch one-set-head-switch"></span>`).prependTo($end),
					render_input: true,
				});
				on.set_value(rule.enabled ? 1 : 0);
				on.$input.attr("aria-label", __("Enabled"));
				on.$input.on("change", async () => {
					await frappe.xcall(R + "enable_rule", { name: rule.name, enabled: on.get_value() ? 1 : 0 });
					saved();
				});
			});
		},
	});

	// What the builder offers in this mailbox: its folders and people, and
	// whether OneAI may read it.
	const context_of = async (panel, box) => {
		const said = panel.said || (await frappe.xcall(R + "rules_of_mailbox", { account: box.name }));
		return {
			email: box.email,
			folders: said.folders || [],
			people: said.people || [],
			ai: !!said.ai,
			reads: !!said.reads,
			to_oneai: box.may.ai ? () => dialog.activate("oneai") : null,
		};
	};

	// A new rule starts from one of the examples, in groups, or from nothing.
	const starters_view = async (panel, box) => {
		await frappe.require(builder_files);
		const context = await context_of(panel, box);
		view(panel, {
			title: box.may.rules ? __("New Mail Rule") : __("Request Mail Rule"),
			description: __("Start from one of these, and change anything."),
			render: (shown) => {
				const groups = {};
				for (const one of onedesk.rules.starters(context)) {
					if (!groups[one.group]) {
						if (one.group) $(`<div class="rb-starters-group"></div>`).text(one.group).appendTo(shown.body);
						groups[one.group] = $(`<div class="rb-starters"></div>`).appendTo(shown.body);
					}
					$(`<button type="button" class="rb-starter"></button>`)
						.html(
							`<span class="rb-starter-title">${frappe.utils.icon(one.icon, "sm")}<span class="rb-starter-name">${esc(one.title)}</span>${
								onedesk.rules.uses_ai(one.rule.steps) ? onedesk.oneai.tag("OneAI") : ""
							}</span><span class="rb-starter-about">${esc(one.about)}</span>`
						)
						.on("click", () => rule_view(panel, box, null, one.rule))
						.appendTo(groups[one.group]);
				}
			},
		});
	};

	// One rule as steps, in the tab.
	const rule_view = async (panel, box, rule, starter = null) => {
		await frappe.require(builder_files);
		const context = await context_of(panel, box);
		let built = null;
		const save = async () => {
			await frappe.xcall(R + "save_rule", { account: box.name, values: built.value(), name: rule ? rule.name : null });
			saved();
			panel.refresh();
		};
		const decide = (approve) => async () => {
			await frappe.xcall(R + "decide_rule", { name: rule.name, approve: approve ? 1 : 0 });
			saved();
			panel.refresh();
		};
		const asking = !box.may.rules;
		const actions = [{ label: asking ? __("Send Request") : __("Save"), variant: "solid", click: save }];
		if (rule && rule.requested_by && box.may.rules) {
			actions.splice(0, 1, { label: __("Decline"), theme: "red", click: decide(false) }, { label: __("Approve"), variant: "solid", click: decide(true) });
		}
		if (rule && (asking ? rule.requested_by : !rule.requested_by)) {
			actions.unshift({
				label: __("Delete"),
				theme: "red",
				click: () =>
					frappe.confirm(__("Delete this rule?"), async () => {
						await frappe.xcall(R + "delete_rule", { name: rule.name });
						panel.refresh();
					}),
			});
		}
		view(panel, {
			title: rule ? rule.title || __("Mail Rule") : asking ? __("Request Mail Rule") : __("New Mail Rule"),
			description:
				rule && rule.requested_by
					? __("{0} asked for this rule. It runs once approved.", [rule.requested_by_name || rule.requested_by])
					: undefined,
			actions,
			render: (shown) => {
				built = onedesk.rules.builder($(`<div></div>`).appendTo(shown.body), rule || starter || { title: "", steps: [] }, context);
			},
		});
	};

	// `focus` is the tab to open on: signature, away, auto, users or connection.
	const open = async (name, from = "mailboxes", focus = null) => {
		const box = await frappe.xcall(H + "mailbox", { account: name });
		const items = [];
		if (box.sends || box.may_sign) items.push(signature_tab(box));
		if (!box.shared && !box.covering_until) items.push(away_tab(box));
		items.push(oneai_tab(box));
		if (box.shared && box.may.holders) items.push(users_tab(box, from));
		if (box.connected && box.may_reconnect) items.push(connection_tab(box, from));
		items.push(rules_tab(box));
		// One mailbox is an AccountCenter, its address under the name.
		dialog.center = { center: "account", label: box.email, icon: icon_of(box) };
		dialog.reset(
			[{ items: [{ id: "back", label: __("All Mailboxes"), icon: "arrow-left", render() {} }] }, { items }],
			items.some((one) => one.id === focus) ? focus : items[0].id
		);
		dialog.$wrapper
			.find('.settings-dialog-tab-item[data-tab-id="back"]')
			.off("click")
			.on("click", () => home(from));
	};
	const home = (tab) => {
		dialog.center = null;
		dialog.reset(dialog.home, tab);
	};

	// What a person may connect, from Private Mailboxes (boot.one_mail_private).
	const can_connect = () => {
		const { on, domains } = frappe.boot.one_mail_private || { on: 1, domains: [] };
		if (!on) return __("Your organization address. Private mailboxes are turned off in this workspace.");
		if (domains.length) return __("Your organization address, or a private one at {0}.", [domains.map((one) => "@" + one).join(", ")]);
		return __("Your organization address, or a private one such as Gmail.");
	};

	// Connecting an IMAP mailbox: the user's own from Mailboxes, the
	// workspace's from Shared Mailboxes, which then opens its users.
	const connect = (panel, { shared = false } = {}) => {
		let form = null;
		view(panel, {
			title: shared ? __("Connect Shared Mailbox") : __("Connect Mailbox"),
			description: shared ? __("A workspace address such as sales@. Add its users after connecting.") : can_connect(),
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
				// Only needed when the server isn't found on its own, and never at a
				// company domain an administrator set up (frappe.boot.one_mail_domains).
				form.sections_dict.server?.collapse(true);
				const known = () =>
					(frappe.boot.one_mail_domains || []).includes((form.get_value("email") || "").split("@")[1]?.toLowerCase());
				form.fields_dict.email.df.onchange = () => {
					const company = known();
					form.sections_dict.server?.wrapper.toggleClass("hide", company);
					form.set_df_property("password", "description", company ? "" : __("Gmail and Outlook require an app password."));
				};
			},
		});
	};

	// An organization mailbox connected by an administrator for somebody, at a company
	// domain, so it is theirs without their typing anything (connect.connect_for).
	const connect_for = (panel) => {
		let form = null;
		view(panel, {
			title: __("Connect Organization Mailbox"),
			description: __("It appears in their mailboxes once connected."),
			actions: [
				{
					label: __("Connect"),
					variant: "solid",
					click: async () => {
						const values = form.get_values();
						if (!values) return;
						const $go = panel.$header.find(".settings-dialog-panel-actions button").prop("disabled", true);
						try {
							await frappe.xcall("onedesk.one_mail.connect.connect_for", values);
							frappe.show_alert({ message: __("Mailbox connected"), indicator: "green" });
							panel.refresh();
						} finally {
							$go.prop("disabled", false);
						}
					},
				},
			],
			render: (shown) => {
				form = fields($(`<div></div>`).appendTo(shown.body), [
					{
						fieldname: "user",
						fieldtype: "Link",
						options: "User",
						label: __("User"),
						reqd: 1,
						get_query: () => ({ filters: { user_type: "System User", enabled: 1 } }),
						onchange: async () => {
							const user = form.get_value("user");
							const email = user ? await frappe.db.get_value("User", user, "email").then((r) => r.message?.email) : "";
							const domain = (email || "").split("@")[1];
							if (domain && (frappe.boot.one_mail_domains || []).includes(domain) && !form.get_value("email"))
								form.set_value("email", email);
						},
					},
					{ fieldname: "email", fieldtype: "Data", options: "Email", label: __("Email Address"), reqd: 1 },
					{ fieldname: "password", fieldtype: "Password", label: __("Password"), reqd: 1 },
					{ fieldname: "sends", fieldtype: "Switch", label: __("Enable Outgoing"), default: 1 },
				]);
			},
		});
	};

	// ── Setup ───────────────────────────────────────────────────────────────
	// The company's domains and their servers (connect.add_domain), so people
	// connect a mailbox at one with its password alone, and the workspace's
	// Default Incoming and Default Outgoing (holders.set_defaults).
	// Notifications keep One's own sender.
	const C = "onedesk.one_mail.connect.";
	const setup = {
		id: "setup",
		label: __("Setup"),
		icon: "sliders-horizontal",
		title: __("Setup"),
		async render(panel) {
			const was_shown = panel.shown;
			const [said, domains] = await Promise.all([frappe.xcall(H + "shared"), frappe.xcall(C + "domains")]);
			if (panel.shown !== was_shown) return;
			panel.set_header({
				title: __("Setup"),
				description: said.system_sender ? __("Notifications are sent from {0}.", [said.system_sender]) : "",
			});
			const $body = panel.body.empty();
			const top = heading_with(__("Company Domains"), __("People connect a mailbox at these with its password alone."));
			top.$row.appendTo($body);
			button({ label: __("Add Domain"), variant: "outline", size: "sm" })
				.on("click", () => add_domain(panel))
				.appendTo(top.$end);
			const $list = $(`<div class="one-set-list"></div>`).appendTo($body);
			if (!domains.length) $list.append(empty(__("No company domains")));
			domains.forEach((one) => {
				const $row = row({
					lead: glyph("globe"),
					title: one.domain_name,
					sub: esc([one.email_server, one.smtp_server].filter(Boolean).join(" · ")),
				}).appendTo($list);
				remove(() =>
					frappe.confirm(__("Remove {0}? Mailboxes already connected at it keep working.", [esc(one.domain_name)]), async () => {
						await frappe.xcall(C + "remove_domain", { domain: one.domain_name });
						panel.refresh();
					})
				).appendTo($row.find(".one-set-end"));
			});
			if ((said.mailboxes || []).length) {
				$body.append(heading(__("Defaults")));
				draw_defaults($body, said, () => panel.refresh());
			}
		},
	};
	const add_domain = (panel) => {
		let form = null;
		view(panel, {
			title: __("Add Domain"),
			description: __("Found from the domain, so change them only if they're wrong."),
			actions: [
				{
					label: __("Save"),
					variant: "solid",
					click: async () => {
						const values = form.get_values();
						if (!values) return;
						const $go = panel.$header.find(".settings-dialog-panel-actions button").prop("disabled", true);
						try {
							await frappe.xcall(C + "add_domain", values);
							frappe.boot.one_mail_domains = [...new Set([...(frappe.boot.one_mail_domains || []), values.domain.toLowerCase()])];
							saved();
							panel.refresh();
						} finally {
							$go.prop("disabled", false);
						}
					},
				},
			],
			render: (shown) => {
				form = fields($(`<div></div>`).appendTo(shown.body), [
					{
						fieldname: "domain",
						fieldtype: "Data",
						label: __("Domain"),
						reqd: 1,
						placeholder: "yourcompany.com",
						onchange: async () => {
							const domain = form.get_value("domain");
							if (!domain) return;
							const found = await frappe.xcall(C + "servers_for", { domain });
							for (const key of ["email_server", "incoming_port", "smtp_server", "smtp_port"]) form.set_value(key, found[key]);
						},
					},
					{ fieldtype: "Section Break", fieldname: "servers", label: __("Servers"), collapsible: 1 },
					{ fieldname: "email_server", fieldtype: "Data", label: __("IMAP Server"), reqd: 1 },
					{ fieldname: "incoming_port", fieldtype: "Int", label: __("IMAP Port"), default: 993 },
					{ fieldtype: "Column Break" },
					{ fieldname: "smtp_server", fieldtype: "Data", label: __("SMTP Server"), reqd: 1 },
					{ fieldname: "smtp_port", fieldtype: "Int", label: __("SMTP Port"), default: 587 },
				]);
				// Found from the domain, so out of the way unless they're wrong.
				form.sections_dict.servers?.collapse(true);
			},
		});
	};
	const draw_defaults = ($body, said, again) => {
		const boxes = said.mailboxes || [];
		const incoming = boxes.find((one) => one.workspace);
		const outgoing = boxes.find((one) => one.sends_default);
		const group = fields($(`<div class="oms-defaults"></div>`).appendTo($body), [
			{
				fieldname: "incoming",
				fieldtype: "Select",
				label: __("Default Incoming"),
				options: boxes.map((one) => one.email_id).join("\n"),
				default: incoming ? incoming.email_id : "",
				description: __("Replies to notifications arrive in this mailbox."),
			},
			{ fieldtype: "Column Break" },
			{
				fieldname: "outgoing",
				fieldtype: "Select",
				label: __("Default Outgoing"),
				options: ["", ...boxes.filter((one) => one.enable_outgoing).map((one) => one.email_id)].join("\n"),
				default: outgoing ? outgoing.email_id : "",
				description: __("New mail is sent from this mailbox unless the writer picks another."),
			},
		]);
		const named = (email) => (boxes.find((one) => one.email_id === email) || {}).name;
		const was = { incoming: incoming && incoming.name, outgoing: outgoing && outgoing.name };
		for (const key of ["incoming", "outgoing"]) {
			group.fields_dict[key].df.onchange = async () => {
				const value = named(group.get_value(key));
				if (!value || value === was[key]) return;
				was[key] = value;
				await frappe.xcall(H + "set_defaults", { [key]: value });
				saved();
				again();
			};
		}
	};

	// ── Shared Mailboxes ────────────────────────────────────────────────────
	const shared = {
		id: "shared",
		label: __("Shared Mailboxes"),
		icon: "users",
		title: __("Shared Mailboxes"),
		description: __("Mailboxes a team reads together, such as sales@."),
		actions: can.connect_shared
			? [
					{
						label: __("Connect Shared Mailbox"),
						icon: "plus",
						click: (panel) => connect(panel, { shared: true }),
					},
			  ]
			: [],
		async render(panel) {
			const was = panel.shown;
			const said = await frappe.xcall(H + "shared");
			if (panel.shown !== was) return;
			const $body = panel.body.empty();
			const $list = $(`<div class="one-set-list"></div>`).appendTo($body);
			if (!(said.mailboxes || []).length) $list.append(empty(__("No shared mailboxes")));
			(said.mailboxes || []).forEach((box) => {
				const sends = box.people.filter((one) => one.sends).length;
				$list.append(
					row({
						lead: glyph(box.workspace ? "building-2" : "users"),
						title: box.email_id,
						sub: esc(
							[
								...(box.workspace || box.sends_default
									? [box.workspace && __("Default Incoming"), box.sends_default && __("Default Outgoing")].filter(Boolean)
									: [__("Shared")]),
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

	// A person's row in System and Organization Mailboxes, opened to set a
	// signature, a sender name or an away reply for them.
	const person_row = (one, from) =>
		row({
			lead: frappe.ui.avatar.html({ label: one.full_name, size: "md" }),
			title: one.full_name,
			sub: esc(one.email),
			end: chevron(),
			open: () => open(one.name, from),
		});

	// ── System Mailboxes ────────────────────────────────────────────────────
	// The address the workspace gives each person (holders.addresses_of_people,
	// issued), and whether it sends: by default for new people
	// (set_personal_sends) and one by one (set_sends).
	const system = {
		id: "system",
		label: __("System Mailboxes"),
		icon: "at-sign",
		title: __("System Mailboxes"),
		description: __("Addresses the workspace gives each person."),
		async render(panel) {
			const was = panel.shown;
			const [said, listed] = await Promise.all([
				can.policy ? frappe.xcall(H + "shared") : null,
				frappe.xcall(H + "addresses_of_people"),
			]);
			if (panel.shown !== was) return;
			const $body = panel.body.empty();
			if (said) {
				switched(
					$body,
					__("Send From New Addresses"),
					__("Each new user gets an address such as {0}. If disabled, it only receives mail.", [
						`name.${said.slug || "workspace"}@${said.mail_domain}`,
					]),
					said.personal_sends,
					(on) => frappe.xcall(H + "set_personal_sends", { on })
				);
				$body.append(heading(__("Mailboxes")));
			}
			const issued = (listed || []).filter((one) => one.issued);
			const $list = $(`<div class="one-set-list"></div>`).appendTo($body);
			if (!issued.length) $list.append(empty(__("No mailboxes")));
			issued.forEach((one) => {
				const $row = person_row(one, "system").appendTo($list);
				if (!said) return;
				const send = frappe.ui.form.make_control({
					df: { fieldtype: "Switch", fieldname: "sends", label: __("Send") },
					parent: $(`<span class="one-set-switch"></span>`).prependTo($row.find(".one-set-end")),
					render_input: true,
				});
				send.set_value(one.sends);
				send.$input.on("change", async () => {
					await frappe.xcall(H + "set_sends", { account: one.name, on: send.get_value() ? 1 : 0 });
					saved();
				});
			});
		},
	};

	// ── Organization Mailboxes ──────────────────────────────────────────────
	// Mailboxes people hold at the company's own domains, connected by them or
	// for them by an administrator (connect.connect_for).
	const organization = {
		id: "organization",
		label: __("Organization Mailboxes"),
		icon: "building",
		title: __("Organization Mailboxes"),
		description: __("Mailboxes people hold at the company's domains."),
		actions: can.policy
			? [{ label: __("Connect Organization Mailbox"), icon: "plus", click: (panel) => connect_for(panel) }]
			: [],
		async render(panel) {
			const was = panel.shown;
			const listed = (await frappe.xcall(H + "addresses_of_people")) || [];
			if (panel.shown !== was) return;
			const connected = listed.filter((one) => !one.issued);
			const $list = $(`<div class="one-set-list"></div>`).appendTo(panel.body.empty());
			if (!connected.length) $list.append(empty(__("No organization mailboxes")));
			connected.forEach((one) => person_row(one, "organization").appendTo($list));
		},
	};

	// ── Private Mailboxes ───────────────────────────────────────────────────
	// Mailboxes people connect for themselves outside the company's domains,
	// such as Gmail. Only their owner opens or changes one (holders.may).
	const private_tab = {
		id: "private",
		label: __("Private Mailboxes"),
		icon: "lock",
		title: __("Private Mailboxes"),
		description: __("Mailboxes people connect at any other domain, such as Gmail, which only the person who connected one can open."),
		async render(panel) {
			const was = panel.shown;
			const said = await frappe.xcall(H + "shared");
			if (panel.shown !== was) return;
			const $body = panel.body.empty();
			const $top = heading_with(__("Allowed Domains"), __("Leave empty to allow any domain.")).$row.appendTo($body);
			let domains = said.allowed_domains || [];
			const $list = $(`<div class="one-set-list"></div>`).appendTo($body);
			const save = async (next) => {
				domains = await frappe.xcall(H + "set_allowed_domains", { domains: next });
				draw();
			};
			const draw = () => {
				$list.empty();
				if (!domains.length) $list.append(empty(__("Any domain")));
				domains.forEach((one) => {
					const $row = row({ lead: glyph("globe"), title: "@" + one }).appendTo($list);
					remove(() => save(domains.filter((other) => other !== one))).appendTo($row.find(".one-set-end"));
				});
			};
			draw();
			const $add = $(`<div class="one-set-add"></div>`).appendTo($top.find(".one-set-heading-end"));
			const typed = frappe.ui.form.make_control({
				df: { fieldtype: "Data", fieldname: "domain", placeholder: "gmail.com" },
				parent: $(`<span class="one-set-add-pick"></span>`).appendTo($add),
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
			header_switch(panel, said.external, (on) => frappe.xcall(H + "set_external", { on }));
		},
	};

	// ── Mail Templates ──────────────────────────────────────────────────────
	// One opens in place, as everything else here does (onedesk.mail_templates
	// in doctype_settings.js draws its fields and saves it). One a setting still
	// sends, such as HR Settings' leave approval, says so and can't be deleted.
	const template = async (panel, name) => {
		const doc = name ? await frappe.db.get_doc("Email Template", name) : null;
		const using = name ? ((await frappe.xcall("onedesk.one_mail.mail_templates.templates")) || []).find((one) => one.name === name)?.used_by || [] : [];
		let form = null;
		const actions = [];
		if (doc && !using.length)
			actions.push({ label: __("Delete"), theme: "red", click: () => onedesk.mail_templates.remove(name, () => panel.refresh()) });
		actions.push({ label: __("Preview"), click: () => onedesk.mail_templates.preview(form, name) });
		actions.push({
			label: __("Save"),
			variant: "solid",
			click: async () => {
				const values = form.get_values();
				if (!values) return;
				await onedesk.mail_templates.save(name, doc, values);
				form.one_slash_close && form.one_slash_close();
				panel.refresh();
			},
		});
		view(panel, {
			title: name || __("New Mail Template"),
			description: using.length ? __("Used by {0}.", [using.join(", ")]) : "",
			actions,
			render: (shown) => {
				form = fields($(`<div></div>`).appendTo(shown.body), onedesk.mail_templates.fields(name, doc));
				Promise.resolve(doc && form.set_values(doc)).then(() => onedesk.mail_templates.slash(form));
			},
		});
	};
	const templates = {
		id: "templates",
		label: __("Mail Templates"),
		icon: "mails",
		title: __("Mail Templates"),
		description: __("Emails people start from when they write."),
		actions: [{ label: __("New Mail Template"), icon: "plus", click: (panel) => template(panel, null) }],
		async render(panel) {
			const was = panel.shown;
			const rows = (await frappe.xcall("onedesk.one_mail.mail_templates.templates")) || [];
			if (panel.shown !== was) return;
			const $body = panel.body.empty();
			const search = frappe.ui.form.make_control({
				df: { fieldtype: "Data", fieldname: "search", placeholder: __("Search") },
				parent: $(`<div class="one-set-search"></div>`).appendTo($body),
				render_input: true,
			});
			const $list = $(`<div class="one-set-list"></div>`).appendTo($body);
			if (!rows.length) $list.append(empty(__("No mail templates")));
			const $none = $(empty(__("No matches"))).addClass("hide").appendTo($list);
			search.$input.on("input", () => {
				const words = search.$input.val().trim().toLowerCase();
				let shown = 0;
				$list.children(".one-set-row").each((_, el) => {
					const match = !words || el.dataset.find.includes(words);
					$(el).toggleClass("hide", !match);
					shown += match ? 1 : 0;
				});
				$none.toggleClass("hide", !rows.length || shown > 0);
			});
			rows.forEach((one) => {
				// The subject only where it says more than the name.
				const said = [one.subject !== one.name ? one.subject : "", one.label || __("All Record Types")];
				if ((one.default_for || []).length) said.push(__("Default for {0}", [one.default_for.join(", ")]));
				const $row = row({
					lead: glyph("mail"),
					title: one.name,
					sub: esc(said.filter(Boolean).join(" · ")),
					end: chevron(),
					open: () => template(panel, one.name),
				}).attr("data-find", [one.name, one.subject, one.label, ...(one.default_for || []), ...one.used_by].join(" ").toLowerCase());
				for (const setting of one.used_by)
					$row.find(".one-set-title").append(" ", frappe.ui.badge.html({ label: __("Used by {0}", [setting]), theme: "gray" }));
				$list.append($row);
			});
		},
	};

	// ── Roles ───────────────────────────────────────────────────────────────
	const role_files = ["/assets/onedesk/js/role_matrix.js", "/assets/onedesk/css/role_matrix.css"];
	const roles = {
		id: "roles",
		label: __("Roles"),
		icon: "shield-check",
		title: __("Roles"),
		description: __("What each role can do in OneMail, given to people on their page in People."),
		actions: [
			{
				label: __("Show Roles"),
				icon: "eye",
				click: async (panel) => {
					await frappe.require(role_files);
					onedesk.roles.pick(panel, "OneMail");
				},
			},
			{
				label: __("New Role"),
				icon: "plus",
				click: async (panel) => {
					await frappe.require(role_files);
					onedesk.roles.create(panel, "OneMail");
				},
			},
		],
		async render(panel) {
			await frappe.require(role_files);
			onedesk.roles.draw(panel, "OneMail");
		},
	};

	// Each workspace tab asks what the reader's role allows
	// (onedesk.module_settings.open leaves out what it doesn't).
	setup.needs = "policy";
	shared.needs = ["connect_shared", "holders", "others"];
	system.needs = ["policy", "others"];
	organization.needs = ["policy", "others"];
	private_tab.needs = "policy";
	templates.needs = "templates";
	roles.needs = "roles";
	const tabs = [
		{ group: __("Your Mail"), items: [mailboxes] },
		{ group: __("Workspace"), items: [setup, shared, system, organization, private_tab, templates, roles] },
	];
	// `connect` and `connect-shared` open a tab on its Connect view, and
	// `mailbox:<name>[:signature|away]` on one mailbox.
	const [opening, named, focus] = String(tab || "").split(":");
	const joining = { connect: "mailboxes", "connect-shared": can.connect_shared ? "shared" : "mailboxes", mailbox: "mailboxes" }[opening];
	const dialog = onedesk.module_settings.open({ module: "OneMail", may: can, tabs, default_tab: joining || tab });
	dialog.$wrapper.addClass("oms");
	dialog.show();
	if (opening === "mailbox") open(named, "mailboxes", focus);
	else if (joining) connect(dialog.get_panel(joining), { shared: joining === "shared" });
	return dialog;
};
