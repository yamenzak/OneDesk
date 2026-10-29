// A stage's outcome in the colour it means: frappe guesses a colour from the
// word, and guessed Open red.
const OUTCOME = { Open: "blue", "On Hold": "orange", Won: "green", Lost: "gray" };

frappe.listview_settings["Sales Stage"] = Object.assign(frappe.listview_settings["Sales Stage"] || {}, {
	formatters: {
		one_outcome(value) {
			if (!value) return "";
			return `<span class="indicator-pill ${OUTCOME[value] || "gray"}"><span>${__(value)}</span></span>`;
		},
	},
});
