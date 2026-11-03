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
			const classic = !frappe.ui.chart || !frappe.ui.chart.is_classic || frappe.ui.chart.is_classic(built);
			if (ROUND.includes(built.type) && classic) {
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
