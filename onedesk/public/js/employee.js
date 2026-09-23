frappe.provide("onedesk.employee");

// A record should say where somebody is before it says what they are linked to.
//
// None of this is a new tab. The state replaces the title's pill, the quarter
// and the numbers go in the dashboard band above the tabs, and the two things
// you actually do to a person go in the sidebar. Every seam is frappe's own —
// `set_indicator`, `dashboard.set_headline`, `sidebar.add_user_action` — so the
// record stays a record.

onedesk.employee.paint = (frm, data) => {
	frm.page.set_indicator(data.state.label, data.state.colour);
	const band = onedesk.employee.band(data);
	if (band) frm.dashboard.set_headline(band, null, true);
	else frm.dashboard.clear_headline();
};

// One band under the title, on every tab: a quarter of attendance on the left,
// and on the right the handful of numbers somebody opens this record to read.
// `add_indicator` was the first try and it is the wrong place — its stats area
// lives inside the dashboard, which v17 renders on the Connections tab, so the
// numbers were only ever visible on the one tab that already lists everything.
onedesk.employee.band = (data) => {
	const stats = onedesk.employee.stats(data);
	const heat = onedesk.employee.heat(data.days);
	if (!heat && !stats.length) return "";
	// The legend is a third child rather than part of the chart: seven keys in
	// a row are wider than four months of squares, so inside the left column it
	// either shouldered the numbers off the edge or wrapped to three lines and
	// stretched the band to fit. Across the foot it is one line with room over.
	return `<div class="one-band">` +
		(heat ? heat.months : "") +
		`<div class="one-stats">${stats.join("")}</div>` +
		(heat ? heat.legend : "") +
		`</div>`;
};

//: What a square can mean, in the order the legend reads them. Five are
//: Attendance's own statuses; late is its two flags on an otherwise present
//: day, and holiday is the list rather than the record.
onedesk.employee.MARKS = () => ({
	present: __("Present"),
	wfh: __("From home"),
	late: __("Late"),
	half: __("Half day"),
	leave: __("On leave"),
	absent: __("Absent"),
	holiday: __("Holiday"),
});

// `frappe.Chart` ships a heatmap and it is the wrong instrument: it ramps a
// *count* through five shades of one hue and labels the scale Less→More, where
// a day here is one of seven named states and absent is not more than present.
// So the geometry is frappe-charts' to the pixel — a ten pixel square, a two
// pixel gutter, a three pixel radius, a month to a block, the month's name
// above it — and only what the colours mean is ours.
onedesk.employee.heat = (days) => {
	if (!days || !days.length) return "";

	const marks = onedesk.employee.MARKS();
	const seen = new Set();
	const months = [];

	days.forEach((day, i) => {
		const month = moment(day.date);
		if (!months.length || month.date() === 1) {
			// The server hands back one run that starts on a week boundary, so a
			// day's row is its place in that run: no weekday arithmetic here, and
			// a month opens with blanks down to the weekday it starts on.
			months.push({ name: month.format("MMM"), cells: new Array(i % 7).fill("") });
		}
		seen.add(day.mark);
		months[months.length - 1].cells.push(onedesk.employee.square(day, marks));
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

onedesk.employee.square = (day, marks) => {
	const said = frappe.utils.escape_html(onedesk.employee.said(day, marks).join(" · "));
	const cls = `one-day one-day-${day.mark}`;
	return day.doc
		? `<a class="${cls}" title="${said}" href="/desk/attendance/${
			encodeURIComponent(day.doc)}"></a>`
		: `<span class="${cls}" title="${said}"></span>`;
};

// Everything the day knows, in the order somebody would say it out loud.
onedesk.employee.said = (day, marks) => {
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

// A pill each was the first try: seven outlines in a row read as seven controls
// rather than as one paragraph of numbers. See public/js/band.js.
//: What a standing is worth saying about it, by the band the server put it in.
//: Only "low" and "watch" get a colour: a number that is fine is a number
//: nobody has to look at, and painting it green would make the good case the
//: loud one.
onedesk.employee.STANDING_TONE = { low: "alarm", watch: "waiting", good: null };

onedesk.employee.stats = (data) => {
	const stats = [];

	// First, beside the quarter it is worked out from. It is the one number
	// here about whether the check-ins themselves can be believed, which is a
	// different question from how many of them there were.
	if (data.standing) {
		stats.push(onedesk.band.stat(
			__("Standing"),
			data.standing.score,
			`/desk/clock-attempt?employee=${encodeURIComponent(cur_frm.doc.name)}`,
			onedesk.employee.STANDING_TONE[data.standing.band],
		));
	}

	if (data.today.checkin) {
		stats.push(onedesk.band.stat(
			data.today.checkin.log_type === "OUT" ? __("Out") : __("In"),
			onedesk.clock.when(data.today.checkin.time),
			`/desk/employee-checkin/${encodeURIComponent(data.today.checkin.name)}`,
		));
	}

	for (const row of data.leave) {
		stats.push(onedesk.band.stat(
			row.type.replace(/ Leave$/, ""),
			__("{0} left", [row.left]),
			`/desk/leave-application?employee=${encodeURIComponent(cur_frm.doc.name)}`,
			row.left > 0 ? null : "quiet",
		));
	}

	for (const row of data.awaiting) {
		stats.push(onedesk.band.stat(
			__(row.doctype),
			__("{0} awaiting", [row.count]),
			`/desk/${frappe.router.slug(row.doctype)}?employee=${
				encodeURIComponent(cur_frm.doc.name)}`,
			"waiting",
		));
	}

	// What of the company's they hold, only when they hold something. See
	// one_inventory/custody.py.
	if (data.equipment) {
		stats.push(onedesk.band.stat(__("Equipment"), __("{0} held", [data.equipment]),
			`/desk/asset?custodian=${encodeURIComponent(cur_frm.doc.name)}`));
	}

	// Date of Joining is a field on the Overview tab two centimetres away, and
	// six stats fill the grid's two rows exactly where seven left one adrift.
	if (data.pay && data.pay.salary_structure) {
		stats.push(onedesk.band.stat(__("Paid under"), data.pay.salary_structure,
			`/desk/salary-structure-assignment/${encodeURIComponent(data.pay.name)}`));
	}

	return stats;
};

//: What you can do to a person from their own page, and the doctype that says
//: whether you may. Each one prefills `employee`, so it is self-service on your
//: own record and on somebody's behalf on theirs — which is the same control,
//: because a `User Permission` decides whose record you can open at all.
onedesk.employee.ACTIONS = [
	["Leave Application", __("Apply for Leave")],
	["Expense Claim", __("Claim an Expense")],
	// What somebody is paid is a Salary Structure Assignment, not the CTC field
	// on this record, and the only route to one was Connections. `can_create`
	// is the gate: an employee reading their own page does not have it.
	["Salary Structure Assignment", __("Assign a Salary Structure")],
];

// HR's one click when somebody's phone changes. Offered only where there is a
// credential to retire and only to somebody who may write one, so an ordinary
// reader of a colleague's record never sees it.
onedesk.employee.passkey = (frm, data) => {
	if (!data.passkey || !frappe.model.can_write("Clock Device")) return;
	frm.sidebar.add_user_action(__("Reset Passkey"), () => {
		frappe.confirm(
			__("{0} will register a new passkey on their next check-in. The old one is retired, not deleted.", [
				frm.doc.employee_name,
			]),
			() =>
				frappe
					.xcall("onedesk.one_hr.passkey.reset", { employee: frm.doc.name })
					.then(() => {
						frappe.show_alert({ message: __("Passkey reset"), indicator: "green" });
						frm.refresh();
					})
		);
	});
};

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

	// Not a new doctype: overtime is written onto the day that was worked, so
	// the action opens the same dialog the Attendance record offers.
	if (frappe.model.can_write("Attendance")) {
		frm.sidebar.add_user_action(__("Record Overtime"), () =>
			onedesk.overtime.ask({ employee: frm.doc.name }),
		);
	}
};

frappe.ui.form.on("Employee", {
	refresh(frm) {
		if (!frm.doc.name || frm.is_new()) return;
		onedesk.employee.actions(frm);
		onedesk.record_calendar(frm);
		frappe.call({
			method: "onedesk.one_hr.employee.overview",
			args: { employee: frm.doc.name },
		}).then(({ message }) => {
			if (message && frm.doc.name === cur_frm?.doc?.name) {
				onedesk.employee.paint(frm, message);
				onedesk.employee.passkey(frm, message);
			}
		});
	},
});
