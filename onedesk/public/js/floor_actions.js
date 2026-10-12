// What the Shop Floor (one_inventory/page/floor) does to a job card, each
// through ERPNext's own calls, asked in frappe's own dialogs as ERPNext's
// Shop Floor asks them (manufacturing/page/shop_floor): who starts it and
// when, how many were made and lost when a session ends, and the quality
// check a step must pass before it is closed. `done` reads the page again.
frappe.provide("onedesk.floor");

const FLOOR = "erpnext.manufacturing.page.shop_floor.shop_floor";

// Start, pause and resume run the job card's own methods, as ERPNext's
// workstation does (workstation.update_job_card).
onedesk.floor.run = (job_card, method, data = {}) =>
	frappe.xcall("erpnext.manufacturing.doctype.workstation.workstation.update_job_card", {
		job_card,
		method,
		start_time: data.start_time || "",
		employees: data.employees || [],
		end_time: data.end_time || "",
	});

onedesk.floor.start = (job_card, employee, done) => {
	const dialog = new frappe.ui.Dialog({
		title: __("Start {0}", [job_card]),
		fields: [
			{ fieldtype: "Datetime", fieldname: "start_time", label: __("Started At"), default: frappe.datetime.now_datetime(), reqd: 1 },
			{
				fieldtype: "Table",
				fieldname: "employees",
				label: __("Who Is On It"),
				cannot_add_rows: false,
				in_place_edit: true,
				data: employee ? [{ employee }] : [],
				fields: [{ fieldtype: "Link", fieldname: "employee", options: "Employee", label: __("Employee"), in_list_view: 1 }],
			},
		],
		primary_action_label: __("Start"),
		primary_action: async (values) => {
			dialog.hide();
			await onedesk.floor.run(job_card, "start_timer", { start_time: values.start_time, employees: (values.employees || []).filter((one) => one.employee) });
			done?.();
		},
	});
	dialog.show();
};

onedesk.floor.pause = async (job_card, done) => {
	await onedesk.floor.run(job_card, "pause_job", { end_time: frappe.datetime.now_datetime() });
	done?.();
};

onedesk.floor.resume = async (job_card, done) => {
	await onedesk.floor.run(job_card, "resume_job", { start_time: frappe.datetime.now_datetime() });
	done?.();
};

// The end of a session: how many were made and lost, then either carry on
// later or close the step. Closing a step that must pass a quality check
// asks for it first, as ERPNext's job card does on submit.
onedesk.floor.record = (step, done) => {
	const left = Math.max(flt(step.for_quantity) - flt(step.done) - flt(step.loss), 0);
	const payload = (values) => ({
		job_card: step.name,
		qty: flt(values.qty),
		for_quantity: flt(step.for_quantity),
		pending_qty: Math.max(left - flt(values.qty) - flt(values.loss), 0),
		process_loss_qty: flt(values.loss),
		end_time: values.end_time,
	});
	const dialog = new frappe.ui.Dialog({
		title: __("Record {0}", [__(step.operation)]),
		fields: [
			{ fieldtype: "Float", fieldname: "qty", label: __("How Many Made"), default: left, reqd: 1, description: __("{0} of {1} still to make", [left, step.for_quantity]) },
			{ fieldtype: "Float", fieldname: "loss", label: __("How Many Lost"), default: 0 },
			{ fieldtype: "Datetime", fieldname: "end_time", label: __("Ended At"), default: frappe.datetime.now_datetime(), reqd: 1 },
		],
		primary_action_label: __("Close Step"),
		primary_action: (values) => {
			if (!(flt(values.qty) > 0)) return frappe.msgprint(__("Quantity must be greater than zero."));
			dialog.hide();
			const close = async () => {
				const r = await frappe.xcall(`${FLOOR}.complete_and_submit`, payload(values));
				done?.();
				if (r?.finished_good) onedesk.floor.offer_entry(step.name);
			};
			if (step.qc?.required && step.qc.status !== "Accepted") onedesk.floor.check(step, close);
			else close();
		},
		secondary_action_label: __("Carry On Later"),
		secondary_action: async () => {
			const values = dialog.get_values();
			if (!values) return;
			if (!(flt(values.qty) > 0)) return frappe.msgprint(__("Quantity must be greater than zero."));
			dialog.hide();
			await frappe.xcall(`${FLOOR}.save_and_continue`, payload(values));
			done?.();
		},
	});
	dialog.show();
};

// A step that makes a part of its own is closed with what it made received
// into stock, as ERPNext's Shop Floor offers after it.
onedesk.floor.offer_entry = (job_card) =>
	frappe.confirm(__("Receive what {0} made into stock?", [job_card]), () => onedesk.floor.entry(job_card));

onedesk.floor.entry = async (job_card) => {
	const r = await frappe.xcall(`${FLOOR}.make_manufacture_stock_entry`, { job_card });
	if (r?.name) frappe.set_route("Form", "Stock Entry", r.name);
};

// The materials a step still has to take, moved to it in a stock entry made
// by the job card's own mapper.
onedesk.floor.move = async (job_card) => {
	const doc = await frappe.xcall("erpnext.manufacturing.doctype.job_card.job_card.make_stock_entry", { source_name: job_card });
	const [made] = frappe.model.sync(doc);
	frappe.set_route("Form", made.doctype, made.name);
};

// A step's quality check: each of its template's readings, a measure for a
// number and Accepted or Rejected for the rest, submitted as ERPNext's
// in-process Quality Inspection.
onedesk.floor.check = async (step, then) => {
	const said = await frappe.xcall(`${FLOOR}.get_quality_inspection_checklist`, { job_card: step.name });
	if (!said?.parameters?.length) return then?.();
	const fields = said.parameters.flatMap((one, i) =>
		one.numeric || one.formula_based_criteria
			? [{ fieldtype: "Float", fieldname: `p${i}`, label: one.specification, reqd: 1, description: one.min_value || one.max_value ? __("From {0} to {1}", [one.min_value, one.max_value]) : "" }]
			: [{ fieldtype: "Select", fieldname: `p${i}`, label: one.specification, options: ["Accepted", "Rejected"], default: "Accepted", reqd: 1, description: one.value || "" }]
	);
	const dialog = new frappe.ui.Dialog({
		title: __("Check {0}", [__(step.operation)]),
		fields,
		primary_action_label: __("Record Check"),
		primary_action: async (values) => {
			dialog.hide();
			const readings = said.parameters.map((one, i) =>
				one.numeric || one.formula_based_criteria
					? { specification: one.specification, reading_value: values[`p${i}`] }
					: { specification: one.specification, status: values[`p${i}`] }
			);
			const r = await frappe.xcall(`${FLOOR}.submit_quality_inspection`, { job_card: step.name, readings: JSON.stringify(readings) });
			if (r?.status === "Rejected") frappe.msgprint(__("The check was rejected, so the step stays open."));
			else then?.();
		},
	});
	dialog.show();
};

// A step's work instructions, written on its operation. frappe cleans the
// text editor's HTML when it is saved, so it is shown as it is.
onedesk.floor.instructions = (step) =>
	frappe.msgprint({ title: __(step.operation), message: step.instructions.work_instruction, wide: true });

// A step whose sessions are all recorded is closed as ERPNext's Shop Floor
// closes it, its quality check first when it must pass one.
onedesk.floor.close = (step, done) => {
	const close = () =>
		frappe.confirm(__("Close {0}? Nothing more can be recorded on it.", [__(step.operation)]), async () => {
			await frappe.xcall(`${FLOOR}.submit_job_card`, { job_card: step.name });
			done?.();
		});
	if (step.qc?.required && step.qc.status !== "Accepted") onedesk.floor.check(step, close);
	else close();
};
