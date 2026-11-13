// An event's subject is its name in the list, and when it starts says more
// than its ID, so the ID column and box go and Starts On is a column
// (one_calendar/custom/event.json). An open event is upcoming business, not
// a fault: blue, as frappe colours what is under way.
frappe.listview_settings["Event"] = {
	...frappe.listview_settings["Event"],
	hide_name_column: true,
	hide_name_filter: true,
	get_indicator(doc) {
		const colour = { Open: "blue", Completed: "green", Closed: "gray", Cancelled: "red" }[doc.status] || "gray";
		return [__(doc.status), colour, `status,=,${doc.status}`];
	},
};
