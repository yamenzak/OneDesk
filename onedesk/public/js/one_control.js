// One's ControlCenter (docs/ONE.md): the workspace's own settings, General,
// for its administrators (one/control.py). Each module's ControlCenter is
// opened by name from links and the rail (`onedesk.control_centers`).
frappe.provide("onedesk.one_control");
frappe.provide("onedesk.control_centers");

onedesk.OneSection = class OneSection extends onedesk.CenterSection {
	static API = "onedesk.one.control.";
	static HERE = "one";
	static LABEL = "ControlCenter";

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
};

onedesk.one_control.open = async ({ at = null } = {}) => {
	// Somebody who doesn't administer the workspace has their own account.
	if (!frappe.boot.one_administers) return onedesk.account_center.open();
	const said = await frappe.xcall(onedesk.OneSection.API + "sections_of");
	const about = { general: __("The company, its contact details and branding, formats, sign-in and sharing.") };
	const dialog = onedesk.module_settings.open({
		module: "One",
		tabs: [{ group: null, items: said.sections.map((one) => onedesk.center_section.tab(onedesk.OneSection, { id: one.key, label: one.label, icon: one.icon, about: about[one.key] })) }],
		default_tab: at,
		center: { center: "settings", label: __("Your Workspace"), icon: "building-2" },
		expand: false,
	});
	dialog.show();
	return dialog;
};

onedesk.control_centers.One = onedesk.one_control.open;
