// The band of answers under a record's title, on every tab. Shared by the
// Employee record and a lead's and a deal's page; the CSS is `.one-band` in
// desk.css. Label over value, which is the desk's own way of putting a number
// on screen.
frappe.provide("onedesk.band");

onedesk.band.stat = (label, value, route, tone) => {
	const inner = `<span class="one-stat-label">${frappe.utils.escape_html(label)}</span>` +
		`<span class="one-stat-value">${frappe.utils.escape_html(String(value))}</span>`;
	const cls = `one-stat${tone ? " one-stat-" + tone : ""}`;
	return route
		? `<a class="${cls}" href="${route}">${inner}</a>`
		: `<span class="${cls}">${inner}</span>`;
};

// A band that is only numbers, with no chart beside them.
onedesk.band.show = (frm, stats) => {
	if (!stats.length) return frm.dashboard.clear_headline();
	frm.dashboard.set_headline(
		`<div class="one-band one-band-plain"><div class="one-stats">${stats.join("")}</div></div>`,
		null,
		true,
	);
};
