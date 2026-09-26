// The band of answers under a record's title, on every tab. Shared by every
// Record Head (head.js), the Employee record and a lead's, a deal's and a
// project's page; the CSS is `.one-band` in desk.css.
//
// A number is a metric card: its label over its value, as the desk puts a
// number on screen, then how it changed, the way frappe's Number Card says it
// (a round pill with an arrow, then "12% since last year"), and how far it is
// to a whole, the way frappe-ui's Progress draws it. A chart beside the
// numbers is frappe's own `frappe.Chart`, as a Dashboard Chart or a report's
// chart is, in one hue.
frappe.provide("onedesk.band");

onedesk.band.stat = (label, value, route, tone, extra = {}) => {
	const esc = frappe.utils.escape_html;
	const inner =
		`<span class="one-stat-label">${esc(label)}</span>` +
		`<span class="one-stat-value">${esc(String(value))}</span>` +
		onedesk.band.delta(extra.delta) +
		onedesk.band.meter(extra.meter);
	const cls = `one-stat${tone ? " one-stat-" + tone : ""}`;
	return route ? `<a class="${cls}" href="${route}">${inner}</a>` : `<span class="${cls}">${inner}</span>`;
};

// How a number changed against the period before. `better` says which way is
// good news: more billed is, more owed is not. A number that did not move
// says nothing, as the Number Card leaves out a stat of nought.
onedesk.band.delta = (delta) => {
	if (!delta || delta.change === null || delta.change === undefined || !isFinite(delta.change)) return "";
	const change = Number(delta.change);
	if (!change) return "";
	const up = change > 0;
	const good = delta.better === "down" ? !up : up;
	const size = Math.abs(change) >= 1000 ? __("over 999") : format_number(Math.abs(change), null, 0);
	return (
		`<span class="one-stat-delta ${good ? "green-stat" : "red-stat"}">` +
		`<span class="indicator-pill-round ${good ? "green" : "red"}">${frappe.utils.icon(up ? "arrow-up-right" : "arrow-down-right", "xs")}</span>` +
		`<span>${frappe.utils.escape_html(`${size}% ${delta.against || ""}`.trim())}</span></span>`
	);
};

// A part of a whole: frappe-ui's Progress, medium, as a line under the value.
onedesk.band.meter = (meter) => {
	if (!meter || !meter.of) return "";
	const share = Math.max(0, Math.min(100, (100 * Number(meter.value || 0)) / Number(meter.of)));
	return (
		`<span class="one-stat-meter" role="progressbar" aria-valuemin="0" aria-valuemax="100" aria-valuenow="${Math.round(share)}">` +
		`<span style="width: ${share}%"></span></span>`
	);
};

// The band: charts on the left if there are any, numbers on the right.
onedesk.band.show = (frm, stats, charts = []) => {
	if (!stats.length && !charts.length) return frm.dashboard.clear_headline();
	// A band replaces the one before it: set_headline appends.
	frm.layout.message.children(".form-message:has(.one-band)").remove();
	const key = frappe.scrub(frm.doctype);
	frm.dashboard.set_headline(
		`<div class="one-band ${charts.length ? "one-band-charted" : "one-band-plain"}">` +
			(charts.length
				? `<div class="one-band-charts">${charts.map((chart, i) => onedesk.band.panel(chart, `${key}-${i}`)).join("")}</div>`
				: "") +
			`<div class="one-stats">${stats.join("")}</div></div>`,
		null,
		true
	);
	// Into the band just drawn, never a copy of an earlier one still leaving.
	const $band = frm.layout.message.find(".one-band").last();
	charts.forEach((chart, i) => onedesk.band.chart($band.find(`#one-chart-${key}-${i} .one-chart-body`)[0], chart));
};

// A chart's panel: what it is and what it adds up to, over the chart. The
// one figure it is about (this invoice's month) keeps the hue and the rest go
// grey, which is the whole of the emphasis.
onedesk.band.panel = (chart, key) => {
	const esc = frappe.utils.escape_html;
	const id = `one-chart-${key}`;
	const marked = Number.isInteger(chart.marked)
		? `<style>#${id} rect.bar:not([data-point-index="${chart.marked}"]) { fill: var(--one-chart-context) !important; }</style>`
		: "";
	const head =
		`<span class="one-stat-label">${esc(chart.label)}</span>` +
		(chart.said ? `<span class="one-chart-said">${esc(chart.said)}</span>` : "");
	return (
		`<div class="one-band-chart" id="${id}">${marked}` +
		(chart.route ? `<a class="one-chart-head" href="${chart.route}">${head}</a>` : `<div class="one-chart-head">${head}</div>`) +
		`<div class="one-chart-body"></div></div>`
	);
};

// The hue a single series is drawn in: the desk's own blue, the step of it
// that reads on this theme's surface (checked for contrast on both).
onedesk.band.hue = () => {
	const style = getComputedStyle(document.documentElement);
	const dark = document.documentElement.getAttribute("data-theme") === "dark";
	return (style.getPropertyValue(dark ? "--blue-400" : "--blue-500") || "").trim() || "blue";
};

onedesk.band.chart = (el, chart) => {
	if (!el) return null;
	const said = chart.currency
		? (value) => format_currency(value, chart.currency, 0)
		: (value) => format_number(value, null, Number.isInteger(value) ? 0 : 1);
	// Thousands shortened as frappe's dashboards shorten them; a count under a
	// thousand as the whole number it is, not "200.00".
	const axis = (value) =>
		Math.abs(value) >= 1000 ? frappe.utils.format_chart_axis_number(value) : String(Math.round(value * 10) / 10);
	const options = {
		type: chart.kind,
		height: 132,
		// No entry animation: a band drawn again mid-animation kept its bars
		// at nought, and a figure that grows in is decoration.
		animate: 0,
		disableEntryAnimation: 1,
		showLegend: 0,
		// Copies: frappe-charts works on the arrays it is given in place, and a
		// band drawn again from the same head would have drawn noughts.
		data: { labels: [...chart.labels], datasets: [{ name: chart.label, values: [...chart.values] }] },
		colors: [onedesk.band.hue()],
		axisOptions: {
			xIsSeries: 1,
			xAxisMode: "tick",
			yAxisMode: "span",
			shortenYAxisNumbers: 1,
			numberFormatter: axis,
		},
		barOptions: { spaceRatio: 0.45 },
		lineOptions: { regionFill: 1, hideDots: chart.values.length > 12 ? 1 : 0, dotSize: 4 },
		tooltipOptions: { formatTooltipY: said },
	};
	// frappe's own: more than ten labels get less room each.
	frappe.utils.set_space_label_ratio(options);
	return new frappe.Chart(el, options);
};
