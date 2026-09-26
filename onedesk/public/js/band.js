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
	// A time since is sent as the moment and said here, the way the desk says
	// every other: "yesterday", "3 days ago".
	// `short` says it the way the clock does ("5 d").
	const said = () =>
		extra.short
			? $("<div>").html(frappe.datetime.comment_when(extra.when, true)).text()
			: frappe.datetime.prettyDate(extra.when);
	const when = (text) => (extra.when ? String(text).replace("{when}", said()) : String(text));
	const inner =
		`<span class="one-stat-label">${esc(when(label))}</span>` +
		`<span class="one-stat-value">${esc(when(value))}</span>` +
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
	// A heat map of named days (a person's quarter) is laid out as it always
	// was: the months, the numbers beside them, and the key across the foot.
	const heat = charts.find((chart) => chart.kind === "heat");
	if (heat) {
		const drawn = onedesk.band.heat(heat.days);
		// The legend is a third child rather than part of the chart: seven keys
		// in a row are wider than four months of squares, so inside the left
		// column it either shouldered the numbers off the edge or wrapped to
		// three lines and stretched the band to fit. Across the foot it is one
		// line with room over.
		frm.dashboard.set_headline(
			`<div class="one-band">` +
				(drawn ? drawn.months : "") +
				`<div class="one-stats">${stats.join("")}</div>` +
				(drawn ? drawn.legend : "") +
				`</div>`,
			null,
			true
		);
		return;
	}
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

//: What a square can mean, in the order the legend reads them. Five are
//: Attendance's own statuses; late is its two flags on an otherwise present
//: day, and holiday is the list rather than the record.
onedesk.band.MARKS = () => ({
	present: __("Present"),
	wfh: __("From home"),
	late: __("Late"),
	half: __("Half day"),
	leave: __("On leave"),
	absent: __("Absent"),
	holiday: __("Holiday"),
});

// `frappe.Chart` ships a heatmap and it is the wrong instrument: it ramps a
// *count* through five shades of one hue and labels the scale Less→More, where
// a day here is one of seven named states and absent is not more than present.
// So the geometry is frappe-charts' to the pixel — a ten pixel square, a two
// pixel gutter, a three pixel radius, a month to a block, the month's name
// above it — and only what the colours mean is ours.
onedesk.band.heat = (days) => {
	if (!days || !days.length) return "";

	const marks = onedesk.band.MARKS();
	const seen = new Set();
	const months = [];

	days.forEach((day, i) => {
		const month = moment(day.date);
		if (!months.length || month.date() === 1) {
			// The server hands back one run that starts on a week boundary, so a
			// day's row is its place in that run: no weekday arithmetic here, and
			// a month opens with blanks down to the weekday it starts on.
			months.push({ name: month.format("MMM"), cells: new Array(i % 7).fill("") });
		}
		seen.add(day.mark);
		months[months.length - 1].cells.push(onedesk.band.square(day, marks));
	});

	const blocks = months.map((month) =>
		`<div class="one-heat-month"><div class="one-heat-name">${month.name}</div>` +
		`<div class="one-heat-grid">${month.cells
			.map((cell) => cell || `<span class="one-day one-day-blank"></span>`)
			.join("")}</div></div>`);

	const legend = Object.keys(marks)
		.filter((mark) => seen.has(mark))
		.map((mark) => `<span class="one-key one-key-${mark}">${marks[mark]}</span>`);

	return {
		months: `<div class="one-heat-months">${blocks.join("")}</div>`,
		legend: `<div class="one-heat-legend">${legend.join("")}</div>`,
	};
};

onedesk.band.square = (day, marks) => {
	const said = frappe.utils.escape_html(onedesk.band.said(day, marks).join(" · "));
	const cls = `one-day one-day-${day.mark}`;
	return day.doc
		? `<a class="${cls}" title="${said}" href="/desk/attendance/${
			encodeURIComponent(day.doc)}"></a>`
		: `<span class="${cls}" title="${said}"></span>`;
};

// Everything the day knows, in the order somebody would say it out loud.
onedesk.band.said = (day, marks) => {
	const said = [frappe.datetime.str_to_user(day.date), marks[day.mark] || __("Not marked")];
	if (day.holiday) said.push(day.holiday);
	if (day.leave_type) said.push(day.leave_type);
	if (day.late && day.early) said.push(__("in late, left early"));
	else if (day.late) said.push(__("in late"));
	else if (day.early) said.push(__("left early"));
	if (day.hours) said.push(__("{0} hours", [day.hours]));
	if (day.shift) said.push(day.shift);
	return said;
};
