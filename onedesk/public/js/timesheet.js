// The timer, on one clock, resuming only what has not ended.
//
// ERPNext's has two faults and they compound. It offers Resume for any row whose
// Completed box is unticked and whose From Time is past — which is every row
// anybody typed by hand, since nothing ticks Completed when you enter a block
// yourself — and on Complete it writes `to_time = now` over the end time that
// was already there. And its two clocks disagree: it stamps times with
// `frappe.datetime.get_datetime_as_string()`, which is `moment()` on the
// operator's own machine, while it measures elapsed time against
// `frappe.datetime.now_datetime()`, which is the site's timezone. On this site
// (Asia/Dubai, container in UTC) Complete wrote 20:40 against a start of 23:59
// and the save died on "To Time cannot be before From Time"; four hours the
// other way it would have silently banked four hours nobody worked.
//
// So this is ours rather than a wrapper around theirs. Every stamp is
// `frappe.datetime.now_datetime()`, and the only row it will resume is one with
// a start and no end.
frappe.provide("onedesk.timesheet");

frappe.ui.form.on("Timesheet", {
	refresh(frm) {
		frm.remove_custom_button(__("Start Timer"));
		frm.remove_custom_button(__("Resume Timer"));
		if (frm.doc.docstatus !== 0) return;

		const open = running(frm);
		frm.add_custom_button(open ? __("Resume Timer") : __("Start Timer"), () =>
			onedesk.timesheet.timer(frm, open),
		).addClass("btn-primary");
	},
});

// A row with an end time is finished, whatever its Completed box says.
function running(frm) {
	return (frm.doc.time_logs || []).find((row) => row.from_time && !row.to_time);
}

onedesk.timesheet.timer = (frm, row) => {
	const dialog = new frappe.ui.Dialog({
		title: row ? __("Resume Timer") : __("Start Timer"),
		fields: [
			{
				fieldtype: "Link",
				fieldname: "activity_type",
				label: __("Activity Type"),
				options: "Activity Type",
				reqd: 1,
			},
			{ fieldtype: "Link", fieldname: "project", label: __("Project"), options: "Project" },
			{ fieldtype: "Link", fieldname: "task", label: __("Task"), options: "Task" },
			{
				fieldtype: "Float",
				fieldname: "expected_hours",
				label: __("Expected Hrs"),
				description: __("Optional. The timer says so when it runs past this."),
			},
			{ fieldtype: "Section Break" },
			{ fieldtype: "HTML", fieldname: "clock" },
		],
	});

	dialog.set_values(
		row
			? {
					activity_type: row.activity_type,
					project: row.project,
					task: row.task,
					expected_hours: row.expected_hours,
				}
			: { project: frm.doc.parent_project },
	);
	dialog.get_field("clock").$wrapper.append(`
		<div class="stopwatch" style="text-align:center; font-size: 2rem; font-variant-numeric: tabular-nums;">00:00:00</div>
		<div class="text-center" style="margin-top: var(--margin-md)">
			<button class="btn btn-primary btn-go">${row ? __("Resume") : __("Start")}</button>
			<button class="btn btn-primary btn-stop" style="display:none">${__("Complete")}</button>
		</div>
	`);

	run(frm, dialog, row);
	dialog.show();
};

function run(frm, dialog, row) {
	const $clock = dialog.$wrapper.find(".stopwatch");
	const $go = dialog.$wrapper.find(".btn-go");
	const $stop = dialog.$wrapper.find(".btn-stop");
	let ticking = null;
	let told = false;

	// Elapsed is always derived from the row's own start against the site's
	// clock, never counted up from zero: a dialog closed and reopened, or a
	// page reloaded, must not lose the time in between.
	const since = () =>
		Math.max(moment(frappe.datetime.now_datetime()).diff(moment(row.from_time), "seconds"), 0);

	function show() {
		const seconds = since();
		$clock.text(
			[seconds / 3600, (seconds % 3600) / 60, seconds % 60]
				.map((part) => String(Math.floor(part)).padStart(2, "0"))
				.join(":"),
		);
		const expected = dialog.get_value("expected_hours");
		if (!told && expected > 0 && seconds >= expected * 3600) {
			told = true;
			frappe.show_alert({ message: __("Past the expected hours."), indicator: "orange" });
		}
	}

	function tick() {
		show();
		ticking = setInterval(show, 1000);
		$go.hide();
		$stop.show();
	}

	if (row) tick();

	$go.on("click", () => {
		const said = dialog.get_values();
		if (!said) return;
		row = frappe.model.add_child(frm.doc, "Timesheet Detail", "time_logs");
		Object.assign(row, said, {
			from_time: frappe.datetime.now_datetime(),
			completed: 0,
		});
		frm.refresh_field("time_logs");
		frm.save();
		tick();
	});

	$stop.on("click", () => {
		const said = dialog.get_values();
		if (!said) return;
		Object.assign(row, said, {
			to_time: frappe.datetime.now_datetime(),
			completed: 1,
		});
		clearInterval(ticking);
		dialog.hide();
		frm.refresh_field("time_logs");
		frm.dirty();
		frm.save();
	});

	dialog.onhide = () => clearInterval(ticking);
}
