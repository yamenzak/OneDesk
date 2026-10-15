// A chart's colours follow what each slice or bar is, not where it falls.
//
// A Group By chart lists its groups by count, largest first, and frappe paints
// them from the start of its colour list, so On Track was green only while it
// had the most projects. A standard chart may name a colour per label under
// `one_colors` in its Custom Options; the colours are then set from its labels
// each time it draws, and the labels, which are the field's own values, are
// shown in the reader's language. A colour is one of frappe-ui's hues, read
// off its token as the chart draws, so it follows the theme; frappe-charts
// paints SVG attributes, which take no var().
//
// A pie or donut so coloured has its legend drawn under it as a row that
// wraps: frappe-charts puts each legend item 150 px from the last and one more
// on a row than fits, so "Time and Materials" ran into the next item and the
// fourth went past the edge.
(() => {
	const Chart = frappe.widget && frappe.widget.widget_factory && frappe.widget.widget_factory.chart;
	if (!Chart || Chart.prototype.one_colors) return;
	Chart.prototype.one_colors = true;
	const ROUND = ["pie", "donut", "percentage"];
	const style = getComputedStyle(document.documentElement);
	const hue = (name) => style.getPropertyValue(`--surface-${name || "gray"}-5`).trim();

	const args = Chart.prototype.get_chart_args;
	Chart.prototype.get_chart_args = function () {
		const built = args.call(this);
		const named = built.one_colors;
		delete built.one_colors;
		const labels = (built.data && built.data.labels) || [];
		this.one_legend = null;
		if (named && labels.length) {
			built.colors = labels.map((label) => hue(named[label]));
			built.data = { ...built.data, labels: labels.map((label) => __(label)) };
			if (ROUND.includes(built.type)) {
				built.showLegend = 0;
				const values = (built.data.datasets && built.data.datasets[0] && built.data.datasets[0].values) || [];
				this.one_legend = built.data.labels.map((label, i) => [label, values[i], built.colors[i]]);
			}
		}
		return built;
	};

	const render = Chart.prototype.render;
	Chart.prototype.render = async function () {
		await render.call(this);
		this.body.find(".one-chart-legend").remove();
		if (!this.one_legend || !this.chart_wrapper.is(":visible")) return;
		const legend = $('<div class="one-chart-legend"></div>');
		for (const [label, value, colour] of this.one_legend) {
			$('<span class="one-chart-legend-item"></span>')
				.append($('<span class="one-chart-legend-dot"></span>').css("background", colour))
				.append($("<span></span>").text(label))
				.append($('<span class="one-chart-legend-count"></span>').text(value))
				.appendTo(legend);
		}
		legend.insertAfter(this.chart_wrapper);
	};
})();
