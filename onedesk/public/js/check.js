// A check report: each row is something that will fail on first use, whether
// it is Ready, To Do or Suggested, and a Fix where there is one. The Books,
// Storage and Inventory Checks are all this (one_book/ready.py,
// one_storage/ready.py, one_inventory/ready.py). `ask(key, call)` asks for
// what a fix needs and returns true, or returns false for one needing nothing.
frappe.provide("onedesk.check");

onedesk.check.report = ({ method, ask }) => {
	let island = null;
	let report = null;
	// A Fix: asks for what it needs, if anything, then reads the report again.
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
		// The rows drawn as a checklist (frontend/src/check), modelled on
		// Shopify's setup guide, in place of frappe's grid, whose row numbers,
		// filter hint and run time say nothing to somebody setting up.
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
