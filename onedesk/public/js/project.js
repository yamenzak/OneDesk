

frappe.ui.form.on("Project", {
	setup(frm) {
		frm.tasks_sort = { sort_by: "lft", sort_order: "asc" };
		const theirs = frm.events.render_tasks;
		frm.events.render_tasks = (frm) => {
			const pending = theirs(frm);
			pending.then((list) => list && onedesk.project.by_milestone(frm, list));
			return pending;
		};
	},
	before_save(frm) {
		return onedesk.project.closing(frm);
	},
	on_tab_change(frm) {
		if (!frm.is_new()) onedesk.project.parts(frm);
	},
	refresh(frm) {
		frm.toggle_display(Object.keys(onedesk.project.PARTS), !frm.is_new());
		frm.toggle_display(["users", "one_contacts"], frm.is_new());
		if (frm.is_new()) return;
		onedesk.project.parts(frm);
		onedesk.project.vet_comments(frm);
		onedesk.project.members_in_sidebar(frm);
		if (frappe.model.can_read("Task")) {
			frm.remove_custom_button(__("Kanban Board"), __("View"));
			frm.add_custom_button(__("Board"), () => onedesk.project.board(frm));
		}
		onedesk.record_calendar(frm);
		if (frappe.model.can_read("Task")) {
			frm.remove_custom_button(__("Gantt Chart"), __("View"));
			frm.add_custom_button(__("Schedule"), () => onedesk.project.plan(frm));
		}
		if (frm.perm[0] && frm.perm[0].write) {
			frm.add_custom_button(__("Group Under New Project"), () => onedesk.project.group(frm), __("Actions"));
		}
		if (frm.doc.customer && frappe.model.can_create("Quotation")) {
			frm.add_custom_button(
				__("Quote Extra Work"),
				() =>
					frappe.new_doc("Quotation", {
						project: frm.doc.name,
						one_extra_work: 1,
						quotation_to: "Customer",
						party_name: frm.doc.customer,
					}),
				__("Actions")
			);
		}
		if (frappe.model.can_create("Task") && frappe.model.can_read("Project Template")) {
			frm.add_custom_button(__("Add from Template"), () => onedesk.project.add_template(frm.doc.name, () => frm.reload_doc()), __("Actions"));
		}
		if (frappe.model.can_create("Project Template")) {
			frm.add_custom_button(__("Save as Template"), () => onedesk.project.save_as(frm), __("Actions"));
		}
		if (frm.perm[0] && frm.perm[0].write) {
			frm.add_custom_button(__("Ask for Updates"), () => onedesk.project.ask_updates(frm.doc.name, () => frm.reload_doc()), __("Actions"));
		}
		frm.one_status_was = frm.doc.status;
		onedesk.project.main(frm);
		frappe.realtime.off("one_project_money");
		frappe.realtime.on("one_project_money", (data) => {
			if (cur_frm !== frm || data.project !== frm.doc.name || frm.is_dirty()) return;
			frm.reload_doc();
		});
	},
});

frappe.provide("onedesk.project");

onedesk.project.by_milestone = (frm, list) => {
	const $actions = frm.get_field("tasks_html").$wrapper.find(".embedded-list-header-actions");
	frm.tasks_done ??= false;
	list.get_page = ({ start, page_length, txt }) =>
		frappe.xcall("erpnext.projects.doctype.project.project.get_project_tasks", {
			project: frm.doc.name,
			...frm.tasks_sort,
			start,
			page_length,
			txt,
			done: frm.tasks_done ? 1 : 0,
		});
	list.on_row_click = (row) =>
		frappe.is_mobile()
			? frappe.set_route("Form", "Task", row.name)
			: frappe.require("side_panel.bundle.js").then(() => frappe.ui.get_side_panel().open("Task", row.name));
	new frappe.ui.SortSelector({
		parent: $actions,
		doctype: "Task",
		args: {
			sort_by: frm.tasks_sort.sort_by,
			sort_order: frm.tasks_sort.sort_order,
			options: [
				{ fieldname: "lft", label: __("Milestone") },
				{ fieldname: "creation", label: __("Created On") },
				{ fieldname: "modified", label: __("Last Updated On") },
				...list.columns.filter((column) => column.fieldname).map(({ fieldname, label }) => ({ fieldname, label })),
			],
		},
		onchange: (sort_by, sort_order) => {
			frm.tasks_sort = { sort_by, sort_order };
			list.refresh();
		},
	}).wrapper.insertAfter($actions.find("[data-action='search']"));
	const $done = $(
		frappe.ui.button.html({ label: __("Completed"), icon: "circle-check", variant: frm.tasks_done ? "subtle" : "ghost", attrs: { "aria-pressed": String(frm.tasks_done) } })
	).insertBefore($actions.find("[data-action='add-row']").first().length ? $actions.find("[data-action='add-row']").first() : $actions.children().last());
	$done.attr("title", __("Show Completed Tasks")).on("click", () => {
		frm.tasks_done = !frm.tasks_done;
		frappe.ui.button.dress($done, { variant: frm.tasks_done ? "subtle" : "ghost" });
		$done.attr("aria-pressed", String(frm.tasks_done));
		list.refresh();
	});
	const dress = () => {
		const by = frm.tasks_sort.sort_by;
		const $rows = list.$wrapper.find("tbody tr[data-row-idx]");
		list.$wrapper.find("tbody tr.one-row-heading").remove();
		$rows.each((_i, tr) => {
			const row = list.data[tr.dataset.rowIdx] || {};
			tr.classList.toggle("one-row-group", by === "lft" && !!row.is_group);
			tr.classList.toggle("one-row-child", by === "lft" && !row.is_group && !!row.parent_task);
		});
		const group = onedesk.project.TASK_GROUPS[by];
		if (!group) return;
		const keys = list.data.map((row) => group(row));
		const width = list.columns.length + (list.show_index ? 1 : 0);
		let was = null;
		$rows.each((_i, tr) => {
			const key = keys[tr.dataset.rowIdx];
			if (key === was) return;
			was = key;
			const count = keys.filter((one) => one === key).length;
			$(`<tr class="one-row-heading"><td colspan="${width}"><span></span><span class="one-row-count"></span></td></tr>`)
				.find("span:first").text(key).end()
				.find(".one-row-count").text(count).end()
				.insertBefore(tr);
		});
	};
	list.after_render = dress;
	const more = list.render_more.bind(list);
	list.render_more = () => {
		more();
		dress();
	};
	list.refresh();
};

onedesk.project.TASK_GROUPS = {
	status: (row) => __(row.status || "Open"),
	priority: (row) => __(row.priority || "Low"),
	exp_end_date: (row) => {
		if (!row.exp_end_date) return __("No End Date");
		const days = frappe.datetime.get_day_diff(row.exp_end_date, frappe.datetime.get_today());
		return days < 0 ? __("Late") : days <= 7 ? __("Next 7 Days") : __("Later");
	},
};

onedesk.project.said = (frm) => {
	const shared = (frm.one_project_said ||= {});
	if (shared.name !== frm.doc.name || Date.now() - shared.at > 1500) {
		shared.name = frm.doc.name;
		shared.at = Date.now();
		shared.got = frappe.xcall("onedesk.one_project.view.said", { project: frm.doc.name });
	}
	return shared.got;
};

onedesk.project.main = async (frm) => {
	const s = await onedesk.project.said(frm);
	if (s.name !== frm.doc.name || frm.doc.status === "Cancelled") return;
	const can = (doctype) => frappe.model.can_create(doctype);
	const verb = (label, action) => frm.add_custom_button(label, action);
	if (s.kind === "Fixed Price" && !s.contract && s.quotation?.count === 1 && can("Sales Order")) verb(__("Make Order"), () => onedesk.project.order_quote(s.quotation));
	else if (s.kind === "Fixed Price" && !s.contract && !s.quotation && s.can_write && s.customer && can("Sales Order")) verb(__("Add Contract"), () => onedesk.project.add_contract(frm));
	else if (s.kind === "Fixed Price" && s.contract && can("Sales Invoice"))
		verb(__("Bill Progress"), () => onedesk.project.bill_progress(s.orders, s.contract, s.currency, s.overview?.billing?.billable?.share));
	else if (s.kind === "Time and Materials" && s.customer && can("Sales Invoice")) verb(__("Invoice Time"), () => onedesk.project.invoice_time(frm));
	else if (s.kind === "Retainer" && s.customer && can("Sales Invoice")) verb(__("Invoice Month"), () => onedesk.project.invoice_month(frm));
	else return onedesk.project.asked(frm, true);
	onedesk.project.asked(frm, false);
};

onedesk.project.closing = async (frm) => {
	const status = frm.doc.status;
	if (frm.is_new() || status === frm.one_status_was || !["Completed", "Cancelled"].includes(status)) return;
	const open = await frappe.xcall("onedesk.one_project.status.ask", { project: frm.doc.name });
	if (!open.tasks && !open.projects) return;
	frappe.validated = false;
	const parts = [
		open.tasks && (open.tasks === 1 ? __("1 open task") : __("{0} open tasks", [open.tasks])),
		open.projects && (open.projects === 1 ? __("1 open sub-project") : __("{0} open sub-projects", [open.projects])),
	].filter(Boolean);
	const title = frappe.utils.escape_html(frm.doc.project_name);
	const said = status === "Completed" ? __("{0} still has {1}. Complete them too?", [title, frappe.utils.comma_and(parts)]) : __("{0} still has {1}. Cancel them too?", [title, frappe.utils.comma_and(parts)]);
	frappe.confirm(said, async () => {
		await frappe.xcall("onedesk.one_project.status.change", { project: frm.doc.name, status, close: 1 });
		frm.reload_doc();
	});
};

onedesk.project.vet_comments = (frm) => {
	const box = frm.comment_box;
	if (!box || box.one_vetted) return;
	box.one_vetted = true;
	const send = box.on_submit;
	box.on_submit = async (comment) => {
		const said = await frappe.xcall("onedesk.one_project.members.unseen", { project: frm.doc.name, content: comment });
		if (said.people.length && said.can_add) {
			const names = frappe.utils.comma_and(said.people.map((one) => one.name));
			const add = await new Promise((resolve) =>
				frappe.confirm(__("{0} can't see this project. Add them to it?", [names]), () => resolve(true), () => resolve(false), __("Add to Project"), __("Comment Only"))
			);
			if (add) await frappe.xcall("onedesk.one_project.members.let_in", { project: frm.doc.name, users: said.people.map((one) => one.user) });
		}
		send(comment);
	};
};

onedesk.project.PARTS = { one_overview_part: "overview", one_money_part: "money", one_time_part: "time", one_suppliers_part: "suppliers", one_team_part: "team" };

onedesk.project.parts = (frm) => {
	for (const [fieldname, part] of Object.entries(onedesk.project.PARTS)) {
		const field = frm.fields_dict[fieldname];
		if (!field) continue;
		const props = { project: frm.doc.name, part, field: fieldname, frm };
		if (field.one_island) {
			field.one_island.update(props);
			continue;
		}
		if (field.tab && !field.tab.is_active()) continue;
		field.$wrapper.empty();
		field.one_island = frappe.ui.mount_island("onedesk.project_part", field.$wrapper[0], props);
	}
};

onedesk.project.asked = async (frm, first) => {
	const waiting = await frappe.xcall("onedesk.one_project.updates.asked", { project: frm.doc.name });
	if (frm.doc.name !== cur_frm?.doc?.name) return;
	if (waiting) frm.set_intro(__("Your update on this project is asked for today."), "blue");
	if (waiting || first) {
		frm.add_custom_button(__("Post Update"), () => onedesk.project.post(frm));
	} else {
		frm.add_custom_button(__("Post Update"), () => onedesk.project.post(frm), __("Actions"));
	}
};

