// One's ControlCenter (docs/ONE.md): the workspace's own settings, a tab
// each, for its administrators (one/control.py). Each module's ControlCenter is
// opened by name from links and the rail (`onedesk.control_centers`).
frappe.provide("onedesk.one_control");
frappe.provide("onedesk.control_centers");

onedesk.OneSection = class OneSection extends onedesk.CenterSection {
	static API = "onedesk.one.control.";
	static HERE = "one";
	static LABEL = "ControlCenter";

	// The workspace's own settings, a tab each (one/control.py HOLDS). Every
	// field is System Settings', Company's or Global Defaults' own, and each
	// tab saves only its own.
	draw_company(data) {
		const esc = frappe.utils.escape_html;
		const facts = [
			[__("Workspace"), data.name],
			// The company is named only where it differs from the workspace.
			[__("Company"), data.company !== data.name ? data.company : ""],
			[__("Country"), data.country ? __(data.country) : ""],
			[__("Currency"), data.currency],
		]
			.filter(([, value]) => value)
			.map(([label, value]) => `<dt>${esc(label)}</dt><dd>${esc(value)}</dd>`)
			.join("");
		const $card = this.form(data, {
			rows: [
				{ heading: __("Company"), note: __("The currency can't change once there are transactions.") },
				{ html: `<dl class="os-facts os-facts-apart">${facts}</dl>` },
				{ heading: __("Contact") },
				["phone_no", "email"],
				["website", "tax_id"],
				{ heading: __("Address") },
				["address_line1", "address_line2"],
				["city", "state"],
				["pincode", ""],
				["email_footer_address", ""],
				// Apart from the fields, and red, so nobody presses it on the way to Save.
				{
					html: `<div class="os-danger">
						<div class="os-danger-text">
							<div class="os-danger-title">${frappe.utils.escape_html(__("Start Again"))}</div>
							<div class="os-danger-sub">${frappe.utils.escape_html(
								__("Deletes every sale, purchase, stock move, project, payslip, lead and asset. Customers, items, people and settings stay.")
							)}</div>
						</div>
						${onedesk.shell.button(__("Delete All Transactions"), { "data-start-again": "1" }, "outline", "trash-2", "red")}
					</div>`,
				},
			],
		});
		// An address is four or five lines; frappe sizes the box for a paragraph.
		$card.find('[data-fieldname="email_footer_address"] textarea').css("height", "7.5rem");
		$card.on("click", "[data-start-again]", () =>
			frappe.confirm(__("Every sale, purchase, stock move, project, payslip, lead and asset is deleted. This can't be undone."), () =>
				frappe
					.call({ method: "onedesk.one.start_again.start", type: "POST", freeze: true })
					.then((r) => frappe.set_route("Form", "Transaction Deletion Record", r.message))
			)
		);
	}

	draw_branding(data) {
		this.form(data, { rows: [["company_logo", "one_brand_colour"], ["one_frame_colour", ""]] });
	}

	draw_formats(data) {
		const on = (value) => (cint(value) ? [__("On"), "green"] : [__("Off"), "gray"]);
		const $card = this.tiled(data, {
			before: [
				["language", "time_zone"],
				["date_format", "time_format"],
				["number_format", "first_day_of_the_week"],
				{ html: `<div class="one-shell-quiet os-reads" data-reads="1"></div>` },
			],
			tiles: [
				["rounded", __("Rounded Totals"), "hash", ["one_rounded_total"]],
				["words", __("Totals in Words"), "type", ["one_in_words"]],
				["symbol", __("Currency Symbol"), "coins", ["one_currency_symbol"]],
			],
			after: [{ html: '<div class="os-sample" data-sample="1"></div>' }],
			unlabelled: ["one_rounded_total", "one_in_words", "one_currency_symbol"],
			css: "os-tiles-three",
			states: (values) => ({
				rounded: on(values.one_rounded_total),
				words: on(values.one_in_words),
				symbol: cint(values.one_currency_symbol) ? [__("Shown"), "green"] : [__("Hidden"), "gray"],
			}),
		});
		const esc = frappe.utils.escape_html;
		const reads = () => {
			const values = this.values();
			const now = values.time_zone && moment.tz && moment.tz.zone(values.time_zone) ? moment().tz(values.time_zone) : moment();
			const date = now.format((values.date_format || "dd-mm-yyyy").toUpperCase());
			const time = now.format(values.time_format || "HH:mm:ss");
			const number = format_number(1234567.89, values.number_format, 2);
			$card.find("[data-reads]").text(__("Preview: {0}", [`${date} ${time}, ${number}`]));
			// The foot of a sale as it will read: the three switches at work.
			const currency = data.currency || "";
			const amount = (value) => {
				const figure = format_number(value, values.number_format, 2);
				return !cint(values.one_currency_symbol) || !currency ? figure : `${currency} ${figure}`;
			};
			const rows = [[__("Grand Total"), amount(1234.56)]];
			if (cint(values.one_rounded_total)) rows.push([__("Rounded Total"), amount(1235)]);
			$card.find("[data-sample]").html(
				`<div class="os-sample-label">${esc(__("A Sale's Total"))}</div>
				<dl class="os-sample-rows">${rows.map(([label, value]) => `<dt>${esc(label)}</dt><dd>${esc(value)}</dd>`).join("")}</dl>${
					cint(values.one_in_words)
						? `<div class="os-sample-words">${esc(
								__("In Words: {0}", [__("{0} One Thousand Two Hundred Thirty-Five Only", [currency]).trim()])
						  )}</div>`
						: ""
				}`
			);
		};
		this.ready.then(reads);
		$card.on("change input", "select, input", () => setTimeout(reads));
	}

	// Settings as tiles, drawn to Sign-in's standard in AccountCenter: a grey
	// icon, the name and a badge saying where it stands (`states`, redrawn as
	// they change), the fields under it, and no label on a field that only
	// repeats the tile's name (`unlabelled`). `before` and `after` are rows
	// around them.
	tiled(data, { tiles, states, unlabelled = [], before = [], after = [], css = "" }) {
		const $card = this.form(data, {
			rows: [
				...before,
				...tiles.flatMap(([key, heading, mark, stack]) => [{ heading, mark }, { row: { stack }, css: `os-tile os-tile-${key}` }]),
				...after,
			],
		}).addClass(`os-tiles ${css}`);
		for (const name of unlabelled) $card.find(`[data-fieldname="${name}"]`).addClass("os-unlabelled");
		const badges = () => {
			for (const [key, [label, theme]] of Object.entries(states(this.values()))) {
				const $head = $card.find(`.os-tile-${key} .section-head`).first();
				$head.find(".os-tile-state").remove();
				$head.append(`<span class="os-tile-state">${frappe.ui.badge.html({ label, theme })}</span>`);
			}
		};
		this.ready.then(badges);
		$card.on("change input", "select, input", () => setTimeout(badges));
		return $card;
	}

	// The label a Select field shows for its value.
	chosen(name) {
		const field = this.group.fields_dict[name];
		const value = String(this.values()[name] ?? "");
		const options = (field && field.df.options) || [];
		const option = Array.isArray(options) ? options.find((one) => String(one.value) === value) : null;
		return option ? option.label : value;
	}

	draw_signin(data) {
		const on = (value) => (cint(value) ? [__("On"), "green"] : [__("Off"), "gray"]);
		this.tiled(data, {
			tiles: [
				["two_factor", __("Two-Factor"), "smartphone", ["one_two_factor", "two_factor_method"]],
				["passkeys", __("Passkeys"), "fingerprint-pattern", ["one_login_with_passkey"]],
				["email_link", __("Email Link"), "mail", ["login_with_email_link"]],
				["passwords", __("Passwords"), "key-round", ["one_password", "force_user_to_reset_password"]],
				["sessions", __("Sessions"), "clock", ["session_expiry", "deny_multiple_sessions"]],
				["lockout", __("Lockout"), "lock", ["allow_consecutive_login_attempts", "allow_login_after_fail"]],
			],
			unlabelled: ["one_two_factor", "one_login_with_passkey", "login_with_email_link", "one_password"],
			states: (values) => ({
				two_factor: values.one_two_factor && values.one_two_factor !== "off" ? [this.chosen("one_two_factor"), "green"] : [__("Off"), "gray"],
				passkeys: on(values.one_login_with_passkey),
				email_link: on(values.login_with_email_link),
				passwords: values.one_password ? [this.chosen("one_password"), "green"] : [__("Any password"), "orange"],
				sessions: [this.chosen("session_expiry"), "gray"],
				lockout: [__("After {0}", [values.allow_consecutive_login_attempts || 0]), "gray"],
			}),
		});
	}

	draw_sharing(data) {
		this.form(data, { rows: [{ stack: ["one_calendar_links", "one_record_sharing"] }] });
	}
};

// Pictures: where a record's picture comes from. First the optional services
// (Gravatar, Google's logos), switched with TrustCenter's own agreement
// (onedesk.trust.switch); then, for each record type, its avatar, which opens
// every style drawn from one of its own names to pick from (one/avatars.py).
// None is frappe's letters. Each is saved as it is picked.
onedesk.OneSection.prototype.draw_pictures = function (data) {
	const esc = frappe.utils.escape_html;
	const svg = (markup) => `data:image/svg+xml;utf8,${encodeURIComponent(markup)}`;
	const $card = $(`<div class="one-shell-section"></div>`).appendTo(this.$content);

	// Headings as the form tabs draw theirs (frappe's section head), so this
	// tab reads like the others.
	const head = (title, sub) =>
		$(`<div class="form-section one-shell-part os-plain-part"><div class="section-head">${esc(title)}</div><div class="section-description">${esc(sub)}</div></div>`).appendTo($card);

	// From the Web: the two optional services, a tile each as Sign-in's ways
	// in are drawn, switched with TrustCenter's own agreement.
	head(__("From the Web"), __("Pictures people and organisations already have elsewhere."));
	const $services = $(`<div class="os-ways"></div>`).appendTo($card);
	for (const one of data.services) {
		const $tile = $(`<div class="os-way">
			<div class="os-way-head"><span class="os-way-icon">${frappe.utils.icon(one.key === "logos" ? "building-2" : "circle-user", "md")}</span>
			<span class="os-way-title">${esc(one.title)}</span><span class="os-way-state"></span></div>
			<div class="os-way-row"><div class="os-way-text">${esc(one.does)}</div><div class="os-way-actions"></div></div>
		</div>`).appendTo($services);
		const state = (on) => $tile.find(".os-way-state").html(frappe.ui.badge.html(on ? { label: __("On"), theme: "green" } : { label: __("Off"), theme: "gray" }));
		const control = frappe.ui.form.make_control({
			df: { fieldtype: "Switch", fieldname: one.key, label: "" },
			parent: $(`<span class="one-set-switch"></span>`).appendTo($tile.find(".os-way-actions")),
			render_input: true,
		});
		control.set_value(one.on ? 1 : 0);
		state(one.on);
		control.$input.attr("aria-label", one.title).prop("disabled", !data.may_bind);
		control.$input.on("change", async () => {
			const on = control.get_value() ? 1 : 0;
			if (!(await onedesk.trust.switch(one, on))) control.set_value(on ? 0 : 1);
			state(control.get_value());
		});
	}

	head(__("Drawn"), __("Records with no picture get one, drawn on your workspace."));
	const $grid = $(`<div class="os-picture-cards"></div>`).appendTo($card);
	const galleries = {};
	for (const kind of data.kinds) {
		const $card_ = $(`<button type="button" class="os-picture-card" aria-haspopup="true"></button>`)
			.attr("aria-label", __("Pick a Picture for {0}", [kind.label]))
			.appendTo($grid);
		const draw = () =>
			$card_.html(
				frappe.ui.avatar.html({
					image: kind.style && galleries[kind.doctype] ? svg(galleries[kind.doctype][kind.style]) : undefined,
					label: kind.label,
					size: "2xl",
					theme: "auto",
				}) +
					`<span class="os-picture-card-title">${esc(kind.label)}</span>` +
					`<span class="os-picture-card-sub">${esc(kind.style ? kind.title : __("Letters"))}</span>`
			);
		draw();
		const pick = async (style, popover) => {
			popover.close();
			await frappe.xcall("onedesk.one.avatars.pick", { doctype: kind.doctype, style: style || "" });
			kind.style = style;
			kind.title = (data.styles.find((one) => one.key === style) || {}).title;
			draw();
			frappe.show_alert({ message: __("Saved"), indicator: "green" });
		};
		const popover = new frappe.ui.Popover({
			trigger: $card_,
			css_class: "os-pictures-panel",
			content: () => {
				const $panel = $(`<div class="os-pictures-grid" role="listbox"></div>`);
				const option = (style, title, html) =>
					$(`<button type="button" class="os-pictures-option" role="option"></button>`)
						.attr({ title, "aria-label": title, "aria-selected": (kind.style || "") === style ? "true" : "false" })
						.html(html)
						.on("click", () => pick(style, popover));
				option("", __("None, the Letters"), frappe.ui.avatar.html({ label: kind.label, size: "lg", theme: "auto" })).appendTo($panel);
				const fill = (drawn) => {
					for (const one of data.styles) {
						const title = one.creator ? `${one.title} (${one.creator})` : one.title;
						option(one.key, title, frappe.ui.avatar.html({ image: svg(drawn[one.key]), label: kind.label, size: "lg" })).appendTo($panel);
					}
				};
				if (galleries[kind.doctype]) fill(galleries[kind.doctype]);
				else frappe.xcall("onedesk.one.avatars.gallery", { doctype: kind.doctype }).then((drawn) => fill((galleries[kind.doctype] = drawn)));
				return $panel;
			},
		});
		if (kind.style) frappe.xcall("onedesk.one.avatars.gallery", { doctype: kind.doctype }).then((drawn) => ((galleries[kind.doctype] = drawn), draw()));
	}
};

onedesk.one_control.open = async ({ at = null } = {}) => {
	// Somebody who doesn't administer the workspace has their own account.
	if (!frappe.boot.one_administers) return onedesk.account_center.open();
	const said = await frappe.xcall(onedesk.OneSection.API + "sections_of");
	const about = {
		company: __("The company, how to reach it and its address."),
		branding: __("The logo and colours on letter heads and around every screen."),
		formats: __("Language, time zone, how dates and numbers read, and amounts."),
		signin: __("How people sign in to the workspace, and for how long."),
		sharing: __("What people may share outside their own access."),
		pictures: __("Pictures of contacts, customers and others, from the web or drawn for those with none."),
	};
	const dialog = onedesk.module_settings.open({
		module: "One",
		tabs: [{ group: null, items: said.sections.map((one) => onedesk.center_section.tab(onedesk.OneSection, { id: one.key, label: one.label, icon: one.icon, about: about[one.key] })) }],
		default_tab: at,
		center: { center: "settings", label: __("Your Workspace"), icon: "building-2" },
	});
	dialog.show();
	return dialog;
};

onedesk.control_centers.One = onedesk.one_control.open;

// One's foot (docs/READY.md, mechanism 5): Settings, Help and the version
// at the foot of One's rail, on whichever of its screens is open. They are
// frappe's desk pages, so the window draws it (module_foot) rather than an
// island's windowModuleFoot.
$(document).on("page-change", () =>
	setTimeout(() => {
		const sidebar = frappe.app && frappe.app.sidebar;
		const win = onedesk.window.current();
		if (!win || win.$foot_action || !sidebar || sidebar.current_module !== "One") return;
		win.module_foot({ module: "One", settings: () => onedesk.one_control.open() });
		onedesk.window.nav.place();
	}, 0)
);
