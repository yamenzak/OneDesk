frappe.provide("onedesk.setup");

frappe.setup.on("before_load", function () {
	const done = frappe.boot.setup_wizard_completed_apps || [];
	if (done.includes("onedesk")) return;

	const at = frappe.setup.slides.findIndex((slide) => slide.name === "persona");
	if (at >= 0) frappe.setup.slides.splice(at, 1, ...onedesk.setup.slides);
	else onedesk.setup.slides.map(frappe.setup.add_slide);
});

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
				description: __("Added to this year's holiday list with your country's public holidays."),
			},
		],
	},
];
