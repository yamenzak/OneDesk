(() => {
	const Chart = frappe.widget && frappe.widget.widget_factory && frappe.widget.widget_factory.chart;
	if (!Chart || Chart.prototype.one_colors) return;
	Chart.prototype.one_colors = true;
	const style = getComputedStyle(document.documentElement);
	const hue = (name) => style.getPropertyValue(`--surface-${name || "gray"}-5`).trim();

	const args = Chart.prototype.get_chart_args;
	Chart.prototype.get_chart_args = function () {
		const built = args.call(this);
		const named = built.one_colors;
		delete built.one_colors;
		const labels = (built.data && built.data.labels) || [];
		if (named && labels.length) {
			built.colors = labels.map((label) => hue(named[label]));
			built.data = { ...built.data, labels: labels.map((label) => __(label)) };
		}
		return built;
	};
})();
