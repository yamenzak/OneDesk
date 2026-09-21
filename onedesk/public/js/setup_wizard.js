frappe.provide("onedesk.setup");

frappe.setup.on("before_load", function () {
	const done = frappe.boot.setup_wizard_completed_apps || [];
	if (done.includes("onedesk")) return;

	// erpnext's "persona" slide asks four required questions and offers
	// Accounting/Manufacturing/Stock, and `capture_user_persona` only sends the
	// answers to their analytics. Nothing in setup reads them, so it is replaced
	// rather than added to — the same splice hrms uses for an HR-only site.
	const at = frappe.setup.slides.findIndex((slide) => slide.name === "persona");
	if (at >= 0) frappe.setup.slides.splice(at, 1, ...onedesk.setup.slides);
	else onedesk.setup.slides.map(frappe.setup.add_slide);
});

onedesk.setup.slides = [
	{
		name: "onedesk_look",
		title: __("How should One look?"),
		help: __("You can change this later from your own settings."),
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
	// Four answers that are really one, asked once. They set the standard day,
	// this year's holidays, and the shift that turns check-ins into attendance.
	// A workspace that is never asked gets a Sunday marked absent, every hour of
	// a shiftless day counted as overtime, and an attendance list that stays
	// empty without saying why. See one_hr/setup.py.
	{
		name: "onedesk_working_day",
		title: __("When do people work?"),
		help: __("One shift and one holiday list to start with. Both can be changed, and more added, later."),
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
				label: __("Weekly Off"),
				fieldtype: "Select",
				options: [
					"Sunday",
					"Monday",
					"Tuesday",
					"Wednesday",
					"Thursday",
					"Friday",
					"Saturday",
				].join("\n"),
				default: "Sunday",
				reqd: 1,
				description: __(
					"This day and your country's public holidays become this year's holiday list."
				),
			},
		],
	},
];
