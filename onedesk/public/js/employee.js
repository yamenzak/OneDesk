frappe.provide("onedesk.employee");

// A record should say where somebody is before it says what they are linked to.
//
// None of this is a new tab. The state replaces the title's pill, the numbers go
// in the dashboard band above the tabs where the heatmap already lives, and the
// two things you actually do to a person go in the sidebar. Every one of those
// is frappe's own — `set_indicator`, `dashboard.add_indicator`,
// `sidebar.add_user_action` — so the record stays a record.

onedesk.employee.paint = (frm, data) => {
	frm.page.set_indicator(data.state.label, data.state.colour);
	const band = onedesk.employee.band(data);
	if (band) frm.dashboard.set_headline(band, null, true);
	else frm.dashboard.clear_headline();
};

// One band under the title, on every tab. `add_indicator` was the first try and
// it is the wrong place: its stats area lives inside the dashboard, which v17
// renders on the Connections tab, so the numbers were only ever visible on the
// one tab that already lists everything.
onedesk.employee.band = (data) => {
	const chips = [];

	if (data.today.checkin) {
		chips.push(onedesk.employee.chip(
			data.today.checkin.log_type === "OUT" ? __("Out") : __("In"),
			onedesk.employee.when(data.today.checkin.time),
			`/desk/employee-checkin/${encodeURIComponent(data.today.checkin.name)}`,
		));
	}

	for (const row of data.leave) {
		chips.push(onedesk.employee.chip(
			row.type.replace(/ Leave$/, ""),
			__("{0} left", [row.left]),
			`/desk/leave-application?employee=${encodeURIComponent(cur_frm.doc.name)}`,
			row.left > 0 ? null : "spent",
		));
	}

	for (const row of data.awaiting) {
		chips.push(onedesk.employee.chip(
			__(row.doctype),
			__("{0} awaiting", [row.count]),
			`/desk/${frappe.router.slug(row.doctype)}?employee=${
				encodeURIComponent(cur_frm.doc.name)}`,
			"waiting",
		));
	}

	if (data.pay && data.pay.salary_structure) {
		chips.push(onedesk.employee.chip(__("Paid under"), data.pay.salary_structure,
			`/desk/salary-structure-assignment/${encodeURIComponent(data.pay.name)}`));
	}

	if (data.tenure.joined) {
		chips.push(onedesk.employee.chip(__("Here since"),
			frappe.datetime.str_to_user(data.tenure.joined)));
	}

	return chips.length ? `<div class="one-band">${chips.join("")}</div>` : "";
};

// `comment_when` answers in markup, and a chip escapes what it is given, so the
// span would print itself. The words are what we want, not the tooltip around
// them.
onedesk.employee.when = (stamp) =>
	$("<div>").html(frappe.datetime.comment_when(stamp, true)).text();

onedesk.employee.chip = (label, value, route, tone) => {
	const inner = `<span class="one-chip-label">${frappe.utils.escape_html(label)}</span>` +
		`<span class="one-chip-value">${frappe.utils.escape_html(String(value))}</span>`;
	const cls = `one-chip${tone ? " one-chip-" + tone : ""}`;
	return route
		? `<a class="${cls}" href="${route}">${inner}</a>`
		: `<span class="${cls}">${inner}</span>`;
};

//: What you can do to a person from their own page, and the doctype that says
//: whether you may. Each one prefills `employee`, so it is self-service on your
//: own record and on somebody's behalf on theirs — which is the same control,
//: because a `User Permission` decides whose record you can open at all.
onedesk.employee.ACTIONS = [
	["Employee Checkin", __("Record a check-in")],
	["Leave Application", __("Apply for leave")],
	["Expense Claim", __("Claim an expense")],
];

onedesk.employee.actions = (frm) => {
	frm.sidebar.clear_user_actions();
	// A person who has left is not applying for anything.
	if (frm.doc.status !== "Active") return;

	for (const [doctype, label] of onedesk.employee.ACTIONS) {
		if (!frappe.model.can_create(doctype)) continue;
		frm.sidebar.add_user_action(label, () => {
			frappe.new_doc(doctype, { employee: frm.doc.name });
		});
	}
};

frappe.ui.form.on("Employee", {
	refresh(frm) {
		if (!frm.doc.name || frm.is_new()) return;
		onedesk.employee.actions(frm);
		frappe.call({
			method: "onedesk.one_hr.employee.overview",
			args: { employee: frm.doc.name },
		}).then(({ message }) => {
			if (message && frm.doc.name === cur_frm?.doc?.name) {
				onedesk.employee.paint(frm, message);
			}
		});
	},
});
