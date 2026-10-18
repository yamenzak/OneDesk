frappe.provide("onedesk.check");

onedesk.check.report = ({ method, ask }) => {
	let island = null;
	let report = null;
	const fix = (key) => {
		const call = (values) =>
			frappe.xcall(method, { key, ...values }).then(() => {
				frappe.ui.toast({ message: __("Fixed"), type: "success" });
				report.refresh();
			});
		if (!(ask && ask(key, call))) call({});
	};
	return {
		filters: [],
		onload(page) {
			report = page;
			page.page.wrapper.addClass("one-check");
		},
		after_datatable_render() {
			const rows = (frappe.query_report?.data || []).filter((one) => one && one.check);
			const props = { rows, onFix: fix };
			if (island) return island.update(props);
			const $host = $('<div class="one-check-host"></div>').prependTo(report.page.main);
			island = frappe.ui.mount_island("onedesk.check", $host[0], props);
		},
	};
};
