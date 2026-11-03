frappe.provide("onedesk.setup");

frappe.setup.on("before_load", function () {
	const done = frappe.boot.setup_wizard_completed_apps || [];
	if (done.includes("onedesk")) return;

	frappe.setup.utils.load_prefilled_data = onedesk.setup.prefilled;

	// erpnext's slides may be added before ours or after, by load order:
	// either way its persona slide goes and ours follow its organization.
	const added = frappe.setup.slides.some((slide) => slide.name === "organization");
	const slides = added ? frappe.setup.slides : !done.includes("erpnext") && window.erpnext?.setup?.slides_settings;
	if (!slides) return onedesk.setup.all().map(frappe.setup.add_slide);
	const persona = slides.findIndex((slide) => slide.name === "persona");
	if (persona >= 0) slides.splice(persona, 1);
	const organization = slides.find((slide) => slide.name === "organization");
	if (organization && !organization.one_standard_first) onedesk.setup.standard_first(organization);
	if (slides.some((slide) => slide.name === onedesk.setup.slides[0].name)) return;
	slides.splice(slides.indexOf(organization) + 1, 0, ...onedesk.setup.all());
});

// Ours, then each module's steps with fields, decided when the wizard is
// built (one/setup_steps.py for_wizard).
onedesk.setup.all = () => [...onedesk.setup.slides, ...(frappe.boot.one_setup_wizard || [])];

// frappe reads System Settings for the first slide, which only the platform's
// own role may and nobody on a workspace holds; boot carries the same values.
onedesk.setup.prefilled = function (slide, callback) {
	const said = frappe.boot.sysdefaults || {};
	frappe.wizard.values.currency = said.currency;
	frappe.wizard.values.country = said.country;
	frappe.wizard.values.timezone = said.time_zone;
	frappe.wizard.values.language = frappe.wizard.values.language || said.language;
	callback(slide);
};

// The Standard chart first, so it is the one picked: no national chart has
// both payroll accounts (docs/ACCOUNTS.md).
onedesk.setup.standard_first = function (slide) {
	slide.one_standard_first = true;
	const chart = slide.fields.find((df) => df.fieldname === "chart_of_accounts");
	if (chart) {
		chart.description = __(
			"Standard works for payroll in every country. Pick your country's chart only if your accountant files from it."
		);
	}
	slide.load_chart_of_accounts = function (me) {
		const country = frappe.wizard.values.country || frappe.defaults.get_default("country");
		if (!country) return;
		frappe.call({
			method: "erpnext.accounts.doctype.account.chart_of_accounts.chart_of_accounts.get_charts_for_country",
			args: { country: country, with_standard: true },
			callback: (r) => {
				if (!r.message) return;
				const charts = ["Standard", ...r.message.filter((one) => one !== "Standard")];
				me.get_input("chart_of_accounts").empty().add_options(charts);
				me.get_field("chart_of_accounts").set_value("Standard");
			},
		});
	};
};

onedesk.setup.WEEK = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"];

onedesk.setup.slides = [
	{
		name: "onedesk_look",
		title: __("How should One look?"),
		help: __("You can change this later in your settings."),
		fields: [
			{
				fieldname: "onedesk_theme",
				label: __("Appearance"),
				fieldtype: "Select",
				options: ["Automatic", "Light", "Dark"].join("\n"),
				default: "Automatic",
				reqd: 1,
			},
		],
	},
	{
		name: "onedesk_working_day",
		title: __("When do people work?"),
		before_show: function () {
			if (this.one_days_off_set) return;
			this.one_days_off_set = true;
			const weekends = frappe.boot.one_weekends || {};
			const days = weekends[frappe.wizard.values.country] || ["Saturday", "Sunday"];
			const field = this.get_field("onedesk_weekly_off");
			field.selected_options = [...days];
			field.select_options(field.selected_options);
		},
		help: __("Sets your first shift and holiday list. You can change both later."),
		fields: [
			{
				fieldname: "onedesk_day_starts",
				label: __("Day Starts"),
				fieldtype: "Time",
				default: "09:00:00",
				reqd: 1,
			},
			{ fieldtype: "Column Break" },
			{
				fieldname: "onedesk_day_ends",
				label: __("Day Ends"),
				fieldtype: "Time",
				default: "17:00:00",
				reqd: 1,
			},
			{ fieldtype: "Section Break" },
			{
				fieldname: "onedesk_weekly_off",
				label: __("Days Off"),
				fieldtype: "MultiCheck",
				options: onedesk.setup.WEEK.map((day) => ({ label: __(day), value: day })),
				sort_options: false,
				columns: 4,
				description: __("Added to this year's holiday list with your country's public holidays."),
			},
		],
	},
];

// On a dev site, the wizard's first screen offers the demo company beside
// Get Started (one_demo/start.py): it is built in the background, and One
// opens when it is done.
if (frappe.boot.one_dev && frappe.setup.SetupWizard && !frappe.setup.SetupWizard.prototype.one_demo_offered) {
	const make_intro = frappe.setup.SetupWizard.prototype.make_intro;
	frappe.setup.SetupWizard.prototype.one_demo_offered = true;
	frappe.setup.SetupWizard.prototype.make_intro = function () {
		make_intro.call(this);
		frappe.ui
			.button({ label: __("Load the Demo Company"), variant: "ghost", css_class: "mt-2", onclick: onedesk.setup.load_demo })
			.appendTo(this.$intro);
	};
}

onedesk.setup.load_demo = function () {
	const dialog = new frappe.ui.Dialog({
		title: __("Load the Demo Company"),
		fields: [
			{
				fieldtype: "HTML",
				options: `<p>${__("This workspace becomes the demo company. Set up your own in a new workspace.")}</p>`,
			},
			{
				fieldname: "password",
				fieldtype: "Password",
				label: __("Password"),
				reqd: 1,
				description: __("Everyone in the demo company signs in with it. The owner is {0}.", ["wsadmin@one.test"]),
			},
		],
		primary_action_label: __("Load"),
		primary_action: async ({ password }) => {
			await frappe.xcall("onedesk.one_demo.start.start", { password });
			dialog.hide();
			onedesk.setup.follow_demo();
		},
	});
	dialog.show();
};

onedesk.setup.follow_demo = async function () {
	const said = await frappe.xcall("onedesk.one_demo.start.progress");
	if (said.built) {
		frappe.hide_progress();
		window.location.href = "/desk";
		return;
	}
	if (said.failed) {
		frappe.hide_progress();
		frappe.msgprint(__("The demo company could not be built. The error is in the Error Log."));
		return;
	}
	frappe.show_progress(__("Building the Demo Company"), said.done, said.of, __("{0} of {1} steps", [said.done, said.of]));
	setTimeout(onedesk.setup.follow_demo, 3000);
};
