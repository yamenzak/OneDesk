// A project's page (docs/PROJECT-PAGE.md): the page head with what can be done
// to it, its name and who it's for, the four figures its kind leads with,
// and the tabs. Everything shown comes from one call, one_project/view.py
// `said`, read as the reader. The form stays, under Edit Details, for every
// field the page doesn't show.
//
// The page follows the record as a form does, through the shell's Editor:
// it listens on the project's room and draws again when it's saved, and when
// its money moves (`one_project_money`). Nothing on it is edited here.

frappe.provide("onedesk");

onedesk.ProjectPage = class ProjectPage {
	// What each card is called, by the key view.py gives it.
	static CARDS = () => ({
		contract: __("Contract"),
		cost: __("Cost"),
		forecast: __("Forecast Margin"),
		done: __("Done"),
		hours: __("Hours This Month"),
		unbilled: __("Not Invoiced Yet"),
		fee: __("Monthly Fee"),
		invoiced: __("Invoiced"),
		budget: __("Budget Used"),
		spent: __("Spent"),
		due: __("Due"),
	});

	static HEALTH = { "On Track": "green", "At Risk": "orange", "Off Track": "red" };
	static STATUS = { Open: "blue", Completed: "green", Cancelled: "gray" };

	constructor(page) {
		this.page = page;
		this.$body = onedesk.shell.body(page.$shell, { wide: true }).addClass("one-pp");
		this.follow = new onedesk.shell.Editor(page);
		this.follow.$content = this.$body;
		this.follow.refresh = () => this.shown() && this.load();
		frappe.realtime.on("one_project_money", (data) => {
			if (data.project === this.name && this.shown()) this.load();
		});
	}

	shown() {
		return frappe.get_route()[0] === "project-view";
	}

	show(name) {
		if (!name) return frappe.set_route("List", "Project");
		if (name !== this.name) {
			this.name = name;
			this.said = null;
			this.$body.html(onedesk.shell.quiet(__("Loading…")));
		}
		this.load();
	}

	async load() {
		const name = this.name;
		const said = await frappe.xcall("onedesk.one_project.view.said", { project: name });
		if (name !== this.name) return;
		this.said = said;
		this.draw();
		this.follow.hear([{ doctype: "Project", name: said.name, modified: said.modified }]);
	}

	// The project as the shared actions take it (project_actions.js).
	get frm() {
		const said = this.said;
		return {
			doctype: "Project",
			doc: { name: said.name, project_name: said.title, customer: said.customer },
			reload_doc: () => this.load(),
		};
	}

	draw() {
		const said = this.said;
		onedesk.shell.trail(__("Projects"), "/desk/project", said.title);
		this.draw_head();
		const tab = this.tabs && this.tabs.get_active ? this.tabs.get_active() : 0;
		this.$body.empty().append(this.title_line(), this.figures());
		this.tabs = new frappe.ui.Tabs({
			tabs: said.tabs.map((key) => ({ label: this.tab_label(key), content: () => this.tab(key) })),
			active: Math.min(tab || 0, said.tabs.length - 1),
			css_class: "one-pp-tabs",
		});
		this.$body.append(this.tabs.$el);
	}

	tab_label(key) {
		return { overview: __("Overview") }[key] || key;
	}

	tab(key) {
		return { overview: () => this.overview() }[key]();
	}

	// The page head: the status as frappe's indicator, Board and Schedule,
	// the rest under the menu, and the kind's main action.
	draw_head() {
		const said = this.said;
		const page = this.page;
		const frm = this.frm;
		page.set_indicator(__(said.status), onedesk.ProjectPage.STATUS[said.status] || "gray");
		page.clear_inner_toolbar();
		page.clear_menu();
		page.clear_primary_action();
		if (frappe.model.can_read("Task")) {
			page.add_inner_button(__("Board"), () => onedesk.project.board(frm));
			page.add_inner_button(__("Schedule"), () => onedesk.project.plan(frm));
		}
		const main = this.main_action();
		if (main) page.set_primary_action(main.label, main.action);
		page.add_menu_item(__("Edit Details"), () => frappe.set_route(`/desk/project/${encodeURIComponent(said.name)}?edit=1`));
		if (main?.key !== "post") page.add_menu_item(__("Post Update"), () => onedesk.project.post(frm));
		if (said.customer && frappe.model.can_create("Sales Invoice") && main?.key !== "invoice_time" && said.kind !== "Fixed Price") {
			page.add_menu_item(__("Invoice Time"), () => onedesk.project.invoice_time(frm));
		}
		if (said.customer && frappe.model.can_create("Quotation")) {
			page.add_menu_item(__("Quote Extra Work"), () =>
				frappe.new_doc("Quotation", { project: said.name, one_extra_work: 1, quotation_to: "Customer", party_name: said.customer })
			);
		}
		if (said.can_write) page.add_menu_item(__("Group Under New Project"), () => onedesk.project.group(frm));
		if (frappe.model.can_create("Project Template")) page.add_menu_item(__("Save as Template"), () => onedesk.project.save_as(frm));
	}

	// What a project of this kind is mostly opened to do.
	main_action() {
		const said = this.said;
		const frm = this.frm;
		if (said.kind === "Fixed Price" && said.contract && frappe.model.can_create("Sales Invoice")) {
			return {
				key: "bill",
				label: __("Bill Progress"),
				action: () => onedesk.progress.ask({ doctype: "Sales Order", doc: { name: said.contract } }),
			};
		}
		if (said.kind === "Time and Materials" && said.customer && frappe.model.can_create("Sales Invoice")) {
			return { key: "invoice_time", label: __("Invoice Time"), action: () => onedesk.project.invoice_time(frm) };
		}
		return { key: "post", label: __("Post Update"), action: () => onedesk.project.post(frm) };
	}

	// The name, its kind and health, then who it's for, when, and who runs it;
	// the team on the right.
	title_line() {
		const said = this.said;
		const esc = frappe.utils.escape_html;
		const badges = [frappe.ui.badge.html({ label: __(said.kind) })];
		if (said.health) badges.push(frappe.ui.badge.html({ label: __(said.health), theme: onedesk.ProjectPage.HEALTH[said.health] }));
		const dates = [said.starts, said.ends].filter(Boolean).map((one) => frappe.datetime.str_to_user(one));
		const sub = [
			said.parent ? `<a href="/desk/project/${encodeURIComponent(said.parent)}">${esc(said.parent_title || said.parent)}</a>` : "",
			said.customer ? `<a href="/desk/customer/${encodeURIComponent(said.customer)}">${esc(said.customer_name || said.customer)}</a>` : "",
			dates.length ? esc(dates.join(" – ")) : "",
			said.manager_name ? esc(said.manager_name) : "",
		].filter(Boolean);
		const $line = $(`<div class="one-pp-title">
			<div class="one-pp-name">
				<h1>${esc(said.title)}</h1>${badges.join("")}
				${sub.length ? `<div class="one-pp-sub">${sub.join('<span class="one-pp-sep">·</span>')}</div>` : ""}
			</div>
			<div class="one-pp-team"></div>
		</div>`);
		if (said.team.length) $line.find(".one-pp-team").append(frappe.avatar_group(said.team, 5, { align: "right" }));
		return $line;
	}

	money(value) {
		return onedesk.shell.ltr(format_currency(value, this.said.currency, 0));
	}

	// "Invoiced {0}" and its figures, each part of a note joined by a dot.
	note_money(parts) {
		const esc = frappe.utils.escape_html;
		return parts
			.map(([said, values]) => esc(said).replace(/\{(\d+)\}/g, (_, i) => esc(this.money(values[Number(i)]))))
			.join(" · ");
	}

	// The kind's four figures, as the desk puts a figure on screen
	// (band.js): its name over its value, a line under it, and how far it is
	// to a whole.
	figures() {
		const esc = frappe.utils.escape_html;
		const names = onedesk.ProjectPage.CARDS();
		const value = (card) => {
			if (card.money !== undefined) return this.money(card.money);
			if (card.hours !== undefined) return __("{0} h", [format_number(card.hours, null, card.hours % 1 ? 1 : 0)]);
			if (card.date) return card.value ? frappe.datetime.str_to_user(card.value) : "–";
			return card.value ?? "–";
		};
		const figures = this.said.cards.map((card) =>
			onedesk.band.stat(names[card.key] || card.key, value(card), null, card.tone, {
				note: card.note ? esc(card.note) : card.note_money ? this.note_money(card.note_money) : "",
				meter: card.bar !== undefined && card.bar !== null ? { value: card.bar, of: 100 } : null,
			})
		);
		return $(`<div class="one-pp-figures">${figures.join("")}</div>`);
	}

	// Overview: what's going on, on the left; what it is, on the right.
	overview() {
		const said = this.said;
		const view = said.overview;
		const $tab = $(`<div class="one-pp-overview"><div class="one-pp-main"></div><div class="one-pp-aside"></div></div>`);
		const $main = $tab.find(".one-pp-main");
		const $aside = $tab.find(".one-pp-aside");
		if (view.milestones && view.milestones.length) $main.append(this.milestones(view.milestones));
		if (view.weekly) $main.append(this.weekly(view.weekly));
		if (view.activities && view.activities.length) $main.append(this.activities(view.activities));
		$main.append(this.needs(view.needs));
		if (view.update) $main.append(this.update(view.update));
		$aside.append(this.about(view));
		if (view.sub_projects.length) $aside.append(this.sub_projects(view.sub_projects));
		if (view.subcontracts && view.subcontracts.length) $aside.append(this.subcontracts(view.subcontracts));
		if (view.people && view.people.length) $aside.append(this.people(view.people));
		return $tab[0];
	}

	section(title, body, aside = "") {
		return onedesk.shell.section(title, body, null, aside ? `<span class="one-pp-count">${frappe.utils.escape_html(aside)}</span>` : "");
	}

	milestones(rows) {
		const esc = frappe.utils.escape_html;
		const next = rows.find((one) => !one.done);
		const line = rows
			.map(
				(one) => `<a class="one-pp-milestone${one.done ? " is-done" : ""}${one === next ? " is-next" : ""}" href="/desk/task/${encodeURIComponent(one.name)}">
					<span class="one-pp-milestone-dot"></span>
					<span class="one-pp-milestone-name">${esc(one.subject)}</span>
					<span class="one-pp-milestone-due">${one.due ? esc(frappe.datetime.str_to_user(one.due)) : ""}</span>
				</a>`
			)
			.join("");
		return this.section(__("Milestones"), `<div class="one-pp-milestones">${line}</div>`);
	}

	weekly(weekly) {
		const $section = $(this.section(__("Hours by Week"), `<div class="one-pp-chart"></div>`, __("{0} h", [format_number(weekly.total, null, 1)])));
		// Drawn once it's on screen and has a width, as frappe-charts needs.
		const el = $section.find(".one-pp-chart")[0];
		const draw = () =>
			el.isConnected && el.offsetWidth
				? onedesk.band.chart(el, { kind: "bar", label: __("Hours"), labels: weekly.labels, values: weekly.values })
				: requestAnimationFrame(draw);
		requestAnimationFrame(draw);
		return $section;
	}

	activities(rows) {
		const esc = frappe.utils.escape_html;
		return this.table(__("By Activity"), {
			rows,
			columns: [
				{ label: __("Activity"), fieldname: "activity" },
				{ label: __("Hours"), render: (one) => esc(format_number(one.hours, null, 1)) },
				{ label: __("Amount"), render: (one) => (one.amount ? esc(this.money(one.amount)) : "") },
			],
		}, __("This month"));
	}

	// A list of records on the page: the shell's table, frappe's EmbeddedList.
	// It sits in a section of its own, under the section's heading.
	table(title, options, aside = "") {
		const $section = $(this.section(title, `<div class="one-pp-list"></div>`, aside));
		onedesk.shell.table($section.find(".one-pp-list"), { page_size: 10, ...options });
		return $section;
	}

	// What wants somebody now, each opening where it's dealt with.
	needs(rows) {
		const esc = frappe.utils.escape_html;
		return this.table(__("Needs You"), {
			rows,
			icon: "circle-check",
			empty: __("Nothing needs you"),
			columns: [
				{
					label: __("What"),
					render: (one) =>
						`<span class="one-pp-dot is-${esc(one.tone)}"></span>${esc(one.text)}` +
						[one.dim, one.late ? __("{0} days late", [one.late]) : ""]
							.filter(Boolean)
							.map((said) => ` <span class="one-pp-dim">· ${esc(said)}</span>`)
							.join(""),
				},
				{ label: __("Amount"), render: (one) => (one.money !== undefined && one.money !== null ? esc(this.money(one.money)) : "") },
			],
			open: (one) => {
				if (one.route) frappe.set_route(one.route);
				else if (one.action === "invoice_time") onedesk.project.invoice_time(this.frm);
			},
		});
	}

	update(one) {
		const esc = frappe.utils.escape_html;
		return this.section(
			__("Latest Update"),
			`<div class="one-pp-update"><div class="one-pp-update-by"><span>${esc(one.by)}</span><span class="one-pp-dim">${esc(
				frappe.datetime.str_to_user(one.on)
			)}</span></div><div>${esc(one.said)}</div></div>`
		);
	}

	about(view) {
		const said = this.said;
		const esc = frappe.utils.escape_html;
		const link = (doctype, name, label) =>
			`<a href="/desk/${frappe.router.slug(doctype)}/${encodeURIComponent(name)}">${esc(label || name)}</a>`;
		const rows = [
			[__("Kind"), esc(__(said.kind))],
			said.customer ? [__("Customer"), link("Customer", said.customer, said.customer_name)] : null,
			said.manager ? [__("Manager"), esc(said.manager_name || said.manager)] : null,
			said.contract ? [__("Contract"), link("Sales Order", said.contract)] : null,
			view.retention && view.retention.one_retention
				? [
						__("Retention"),
						esc(
							view.retention.one_retention_due
								? __("{0}% until {1}", [view.retention.one_retention, frappe.datetime.str_to_user(view.retention.one_retention_due)])
								: __("{0}%", [view.retention.one_retention])
						),
				  ]
				: null,
			said.starts ? [__("Starts"), esc(frappe.datetime.str_to_user(said.starts))] : null,
			said.ends ? [__("Ends"), esc(frappe.datetime.str_to_user(said.ends))] : null,
			said.parent ? [__("Part Of"), link("Project", said.parent, said.parent_title)] : null,
		].filter(Boolean);
		return this.section(
			__("About"),
			`<dl class="one-pp-about">${rows.map(([label, value]) => `<dt>${esc(label)}</dt><dd>${value}</dd>`).join("")}</dl>`
		);
	}

	sub_projects(rows) {
		return this.table(__("Sub-projects"), {
			rows,
			columns: [
				{ label: __("Project"), render: (one) => frappe.utils.escape_html(one.title || one.name) },
				{ label: __("Done"), render: (one) => (one.status === "Completed" ? __("Completed") : `${one.share}%`) },
			],
			open: (one) => frappe.set_route("project", one.name),
		});
	}

	// Each subcontract: how far it's billed, what it's for, retention held
	// and what's left to bill. A row opens the order.
	subcontracts(rows) {
		const esc = frappe.utils.escape_html;
		const billed = (one) => (one.ordered ? Math.round((100 * one.billed) / one.ordered) : 0);
		return this.table(__("Subcontracts"), {
			rows,
			columns: [
				{
					label: __("Supplier"),
					render: (one) => esc(one.supplier),
				},
				{ label: __("Billed"), render: (one) => (billed(one) >= 100 ? __("Billed") : `${billed(one)}%`) },
				{ label: __("Ordered"), render: (one) => esc(this.money(one.ordered)) },
				{ label: __("Left"), render: (one) => esc(this.money(one.left)) },
			],
			open: (one) => frappe.set_route(one.route),
		});
	}

	people(rows) {
		const esc = frappe.utils.escape_html;
		return this.table(__("Who Logged Time"), {
			rows,
			columns: [
				{ label: __("Person"), render: (one) => `${frappe.avatar(one.user, "avatar-xs")} ${esc(one.name)}` },
				{ label: __("Hours"), render: (one) => esc(format_number(one.hours, null, 1)) },
			],
		}, __("This month"));
	}
};
