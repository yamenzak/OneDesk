frappe.provide("onedesk.employee");

// Five answers, each carrying the doctype it came from so the links survive.
// Drawn with frappe's own primitives rather than a framework: this is a panel on
// a desk form, and a build step for it would be the heaviest thing in the app.
onedesk.employee.render = (frm, wrapper) => {
	frappe.call({
		method: "onedesk.one_hr.employee.overview",
		args: { employee: frm.doc.name },
	}).then(({ message }) => {
		if (message) wrapper.innerHTML = onedesk.employee.markup(message);
	});
};

onedesk.employee.markup = (data) => [
	onedesk.employee.today(data.today, data.awaiting),
	onedesk.employee.leave(data.leave),
	onedesk.employee.pay(data.pay, data.tenure),
].join("");

onedesk.employee.card = (title, body, route) => `
	<section class="one-card">
		<header>
			<h4>${frappe.utils.escape_html(title)}</h4>
			${route ? `<a href="${route}">${__("Open")}</a>` : ""}
		</header>
		${body}
	</section>`;

onedesk.employee.today = (today, awaiting) => {
	const lines = [];
	if (today.checkin) {
		lines.push(onedesk.employee.line(
			today.checkin.log_type === "OUT" ? __("Last out") : __("Last in"),
			frappe.datetime.comment_when(today.checkin.time, true),
			`/desk/employee-checkin/${encodeURIComponent(today.checkin.name)}`,
		));
	} else {
		lines.push(onedesk.employee.line(__("Check-in"), __("Nothing recorded")));
	}
	lines.push(onedesk.employee.line(
		__("Today"),
		today.holiday
			? __("Holiday")
			: (today.attendance ? today.attendance.status : __("Not marked")),
		today.attendance ? `/desk/attendance/${encodeURIComponent(today.attendance.name)}` : null,
	));
	for (const row of awaiting) {
		lines.push(onedesk.employee.line(
			__("Waiting on an approver"),
			`${row.count} ${__(row.doctype)}`,
			`/desk/${frappe.router.slug(row.doctype)}?employee=${encodeURIComponent(
				cur_frm.doc.name)}`,
		));
	}
	return onedesk.employee.card(__("Where they are"), lines.join(""));
};

onedesk.employee.leave = (rows) => {
	if (!rows.length) {
		return onedesk.employee.card(__("Leave"),
			onedesk.employee.line(__("Allocations"), __("None for this period")));
	}
	const body = rows.map((row) => `
		<div class="one-leave">
			<span class="one-leave-left">${row.left}</span>
			<span class="one-leave-type">${frappe.utils.escape_html(row.type)}</span>
			<span class="one-leave-of">${__("of {0} taken {1}", [row.allocated, row.taken])}</span>
		</div>`).join("");
	return onedesk.employee.card(__("Leave left"), body,
		`/desk/leave-application?employee=${encodeURIComponent(cur_frm.doc.name)}`);
};

onedesk.employee.pay = (pay, tenure) => {
	const lines = [];
	if (pay) {
		lines.push(onedesk.employee.line(__("Paid under"), pay.salary_structure,
			`/desk/salary-structure-assignment/${encodeURIComponent(pay.name)}`));
		lines.push(onedesk.employee.line(__("Base"),
			format_currency(pay.base, pay.currency)));
		if (pay.next_payday) {
			lines.push(onedesk.employee.line(__("Next period from"),
				frappe.datetime.str_to_user(pay.next_payday)));
		}
	} else {
		lines.push(onedesk.employee.line(__("Paid under"), __("No salary structure assigned")));
	}
	if (tenure.joined) {
		lines.push(onedesk.employee.line(__("Here since"),
			`${frappe.datetime.str_to_user(tenure.joined)} · ${
				__("{0} days", [tenure.days])}`));
	}
	if (tenure.reports_to) {
		lines.push(onedesk.employee.line(__("Reports to"), tenure.reports_to,
			`/desk/employee/${encodeURIComponent(tenure.reports_to)}`));
	}
	return onedesk.employee.card(__("Pay and tenure"), lines.join(""));
};

onedesk.employee.line = (label, value, route) => `
	<div class="one-line">
		<span class="one-line-label">${frappe.utils.escape_html(label)}</span>
		<span class="one-line-value">${
			route
				? `<a href="${route}">${frappe.utils.escape_html(String(value))}</a>`
				: frappe.utils.escape_html(String(value))
		}</span>
	</div>`;

frappe.ui.form.on("Employee", {
	refresh(frm) {
		const field = frm.get_field("one_overview");
		if (!frm.doc.name || frm.is_new() || !field) return;
		field.$wrapper.empty();
		const wrapper = $('<div class="one-overview">').appendTo(field.$wrapper)[0];
		onedesk.employee.render(frm, wrapper);
	},
});
