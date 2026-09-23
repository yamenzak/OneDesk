// A task's due date reads as a day, and red once it has passed on a task still
// to do. ERPNext's Expected End Date is a Datetime, so every list and board
// card said "25-09-2026 00:00:00"; the time is shown only when one was set.
// Lateness is read off the date rather than a status — one_project/board.py says
// why Overdue is not one.
//
// On the docfield rather than the list's formatters, because the board draws
// its cards through frappe.format, which reads `df.formatter` and nothing else.
(() => {
	const DONE = ["Completed", "Cancelled", "Template"];
	const due = frappe.meta.get_docfield("Task", "exp_end_date");
	if (!due) return;
	due.formatter = (value, df, options, doc) => {
		if (!value) return "";
		const [day, time] = frappe.datetime.convert_to_user_tz(value).split(" ");
		const shown = frappe.datetime.str_to_user(day) + (time && !time.startsWith("00:00") ? ` ${time.slice(0, 5)}` : "");
		const late = doc && !DONE.includes(doc.status) && day < frappe.datetime.get_today();
		return late ? `<span class="text-danger">${shown}</span>` : shown;
	};
})();
