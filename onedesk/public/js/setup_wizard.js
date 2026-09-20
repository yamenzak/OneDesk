frappe.provide("onedesk.setup");

frappe.setup.on("before_load", function () {
	const done = frappe.boot.setup_wizard_completed_apps || [];
	if (done.includes("onedesk")) return;
	onedesk.setup.slides.map(frappe.setup.add_slide);
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
];
