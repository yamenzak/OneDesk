frappe.query_reports["Ready to Submit"] = {
	filters: [],
	get_datatable_options(options) {
		return Object.assign(options, { checkboxColumn: true });
	},
	formatter(value, row, column, data, default_formatter) {
		value = default_formatter(value, row, column, data);
		if (!data) return value;
		if (column.fieldname === "state") return frappe.ui.badge.html({ label: data.state, theme: data.ready ? "green" : "orange", size: "sm" });
		if (column.fieldname === "document" && data.route) return `<a href="${encodeURI(data.route)}">${value}</a>`;
		return value;
	},
	onload(report) {
		report.page.set_primary_action(__("Submit"), () => submit(report), "check-check");
	},
};

function submit(report) {
	const names = report.get_checked_items().filter((one) => one.ready).map((one) => [one.doctype, one.name]);
	if (!names.length) return frappe.show_alert({ message: __("Tick the ready drafts to submit"), indicator: "orange" });
	frappe.confirm(__("Submit {0} drafts?", [names.length]), async () => {
		const said = await frappe.xcall("onedesk.one_intake.drafts.submit_all", { names });
		if (said.failed.length) {
			frappe.msgprint({
				title: __("Some Drafts Not Submitted"),
				message: said.failed.map((one) => `<div>${frappe.utils.escape_html(one.name)}: ${frappe.utils.escape_html(one.why)}</div>`).join(""),
			});
		} else {
			frappe.show_alert({ message: __("{0} submitted", [said.done.length]), indicator: "green" });
		}
		report.refresh();
	});
}
