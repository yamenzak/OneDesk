// Which palette answers. The desk owns light/dark through data-theme; this is
// the second dimension, and it is set before first paint so nothing flashes.
frappe.provide("onedesk.theme");

onedesk.theme.DEFAULT = "one";

onedesk.theme.apply = function (name) {
	document.documentElement.setAttribute("data-one-theme", name || onedesk.theme.DEFAULT);
};

onedesk.theme.apply(onedesk.theme.DEFAULT);
