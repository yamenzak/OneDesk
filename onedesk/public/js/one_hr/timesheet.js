frappe.provide("onedesk.timesheet");

frappe.ui.form.on("Timesheet", {
	refresh(frm) {
		frm.remove_custom_button(__("Start Timer"));
		frm.remove_custom_button(__("Resume Timer"));
		if (frm.doc.docstatus !== 0) return;

		const open = running(frm);
		const label = open ? __("Resume Timer") : __("Start Timer");
		frm.add_custom_button(label, () => onedesk.timesheet.timer(frm, open));
		frm.change_custom_button_type(label, null, "primary");
	},
});

frappe.ui.form.on("Timesheet Detail", {
	async project(frm, cdt, cdn) {
		const row = locals[cdt][cdn];
		if (!row.project || row.is_billable) return;
		const { message } = await frappe.call("onedesk.one_project.hours.billed_hourly", { project: row.project });
		if (message) frappe.model.set_value(cdt, cdn, "is_billable", 1);
	},
});

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
				description: __("The timer says so when it runs past this, if it is set."),
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
			${frappe.ui.button.html({ label: row ? __("Resume") : __("Start"), variant: "solid", css_class: "btn-go" })}
			${frappe.ui.button.html({ label: __("Complete"), variant: "solid", css_class: "btn-stop", attrs: { style: "display:none" } })}
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
	const since = () =>
		Math.max(moment(frappe.datetime.system_datetime()).diff(moment(row.from_time), "seconds"), 0);

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
			from_time: frappe.datetime.system_datetime(),
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
			to_time: frappe.datetime.system_datetime(),
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
