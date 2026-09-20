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
];
