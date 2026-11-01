// Review stamps in the bottom bar, on a dev site only (one_interface/stamps.py):
// Island on a page an island still draws, and Passed, with its day, on a
// screen the final passthrough has finished. A customer never sees one.
frappe.provide("onedesk.interface");

onedesk.interface.stamp = (win, { key, icon, label, tone = "gray" }) => {
	if (!win || !win.$status) return;
	win.$status.find(`.one-stamp[data-stamp="${key}"]`).remove();
	if (!(frappe.boot.one_stamps || {}).dev) return;
	const $stamp = $(`<span class="one-stamp" data-stamp="${key}" data-tone="${tone}"></span>`).append(frappe.utils.icon(icon, "xs"));
	$("<span></span>").text(label).appendTo($stamp);
	win.$status.prop("hidden", false).append($stamp);
};

// A screen as stamps.py names it: a record's and a list's by their doctype,
// a report's, a tree's and a print's by theirs, any other page by its route.
onedesk.interface.screen = (route = frappe.get_route()) => {
	const [first, second] = route || [];
	if (!first) return "";
	return ["Form", "List", "Tree", "Report", "query-report", "print"].includes(first) && second ? `${first}/${second}` : String(first);
};

$(document).on("page-change", () => {
	if (!(frappe.boot.one_stamps || {}).dev) return;
	// after the page has drawn its window
	setTimeout(() => {
		const win = onedesk.interface.current();
		const said = ((frappe.boot.one_stamps || {}).passed || {})[onedesk.interface.screen()];
		if (!win) return;
		if (!said) return win.$status.find('.one-stamp[data-stamp="passed"]').remove();
		onedesk.interface.stamp(win, { key: "passed", icon: "badge-check", label: __("Passed {0}", [frappe.datetime.str_to_user(said.on)]), tone: "green" });
	}, 300);
});
