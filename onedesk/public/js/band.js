frappe.provide("onedesk.band");

onedesk.band.stat = (label, value, route, tone, extra = {}) => {
	const esc = frappe.utils.escape_html;
	if (extra.steps) return onedesk.band.steps(extra.steps);
	const said = () =>
		extra.short
			? $("<div>").html(frappe.datetime.comment_when(extra.when, true)).text()
			: frappe.datetime.prettyDate(extra.when);
	const when = (text) => (extra.when ? String(text).replace("{when}", said()) : String(text));
	const inner =
		`<span class="one-stat-label">${esc(when(label))}</span>` +
		`<span class="one-stat-value">${esc(onedesk.shell.ltr(when(value)))}</span>` +
		onedesk.band.delta(extra.delta) +
		(extra.note ? `<span class="one-stat-note">${extra.note}</span>` : "") +
		onedesk.band.meter(extra.meter);
	const cls = `one-stat${tone ? " one-stat-" + tone : ""}`;
	return route ? `<a class="${cls}" href="${route}">${inner}</a>` : `<span class="${cls}">${inner}</span>`;
};

onedesk.band.steps = (steps) => {
	const esc = frappe.utils.escape_html;
	const ICON = { done: "check", now: "dot", late: "alert-circle", next: "dot" };
	return (
		`<ol class="one-steps">` +
		steps
			.map(
				(step) =>
					`<li class="one-step one-step-${esc(step.state)}">` +
					`<span class="one-step-mark">${step.state === "done" || step.state === "late" ? frappe.utils.icon(ICON[step.state], "xs") : ""}</span>` +
					`<span class="one-step-text"><span class="one-step-label">${esc(step.label)}</span>` +
					`<span class="one-step-note">${esc(step.note || "")}</span></span></li>`
			)
			.join("") +
		`</ol>`
	);
};

onedesk.band.delta = (delta) => {
	if (!delta || delta.change === null || delta.change === undefined || !isFinite(delta.change)) return "";
	const change = Number(delta.change);
	if (!change) return "";
	const up = change > 0;
	const good = delta.better === "down" ? !up : up;
	const size = Math.abs(change) >= 1000 ? __("999+") : format_number(Math.abs(change), null, 0);
	return (
		`<span class="one-stat-delta ${good ? "green-stat" : "red-stat"}">` +
		`<span class="indicator-pill-round ${good ? "green" : "red"}">${frappe.utils.icon(up ? "arrow-up-right" : "arrow-down-right", "xs")}</span>` +
		`<span>${frappe.utils.escape_html(`${size}% ${delta.against || ""}`.trim())}</span></span>`
	);
};

onedesk.band.meter = (meter) => {
	if (!meter || !meter.of) return "";
	const share = Math.max(0, Math.min(100, (100 * Number(meter.value || 0)) / Number(meter.of)));
	return (
		`<span class="one-stat-meter" role="progressbar" aria-valuemin="0" aria-valuemax="100" aria-valuenow="${Math.round(share)}">` +
		`<span style="width: ${share}%"></span></span>`
	);
};

onedesk.band.show = (frm, stats, charts = []) => {
	if (!stats.length && !charts.length) return frm.dashboard.clear_headline();
	frm.layout.message.children(".form-message:has(.one-band)").remove();
	const heat = charts.find((chart) => chart.kind === "heat");
	if (heat) {
		const drawn = onedesk.band.heat(heat.days);
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
	const $band = frm.layout.message.find(".one-band").last();
	charts.forEach((chart, i) => onedesk.band.chart($band.find(`#one-chart-${key}-${i} .one-chart-body`)[0], chart));
};

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
	const axis = (value) =>
		Math.abs(value) >= 1000 ? frappe.utils.format_chart_axis_number(value) : String(Math.round(value * 10) / 10);
	const options = {
		type: chart.kind,
		height: 132,
		animate: 0,
		disableEntryAnimation: 1,
		showLegend: 0,
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
	frappe.utils.set_space_label_ratio(options);
	return new frappe.Chart(el, options);
};

onedesk.band.MARKS = () => ({
	present: __("Present"),
	wfh: __("From home"),
	late: __("Late"),
	half: __("Half day"),
	leave: __("On leave"),
	absent: __("Absent"),
	holiday: __("Holiday"),
});

onedesk.band.heat = (days) => {
	if (!days || !days.length) return "";

	const marks = onedesk.band.MARKS();
	const seen = new Set();
	const months = [];

	days.forEach((day, i) => {
		const month = moment(day.date);
		if (!months.length || month.date() === 1) {
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
