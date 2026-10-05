// New Project, by kind: frappe's quick entry for Project, asking only what the
// kind needs. Picking a kind is the first thing; its fields follow. For Fixed
// Price, the contract is made with it (one_project/kinds.py `make`).
frappe.provide("onedesk.project");

// A project opens on its page (one_project/page/project_view), at its own
// address: /desk/project/<name>. The form is the same address with ?edit=1,
// for every field the page doesn't show, and is still where a new one is made.
{
	const standard = frappe.router.convert_to_standard_route.bind(frappe.router);
	frappe.router.convert_to_standard_route = async (route) => {
		const found = await standard(route);
		// The address says it; carried on, it would open the next project's form too.
		if (frappe.route_options) delete frappe.route_options.edit;
		const [view, doctype, name] = found || [];
		if (view !== "Form" || doctype !== "Project" || !name || name.startsWith("new-project")) return found;
		if (new URLSearchParams(window.location.search).has("edit")) return found;
		return ["project-view", name];
	};
}

onedesk.project.KINDS = () => [
	{
		value: "Fixed Price",
		icon: "file-text",
		said: frappe.boot.one_retention
			? __("An agreed price, billed as the work gets done. Subcontracts, retention and a budget.")
			: __("An agreed price, billed as the work gets done. Subcontracts and a budget."),
	},
	{ value: "Time and Materials", icon: "clock", said: __("Billed by the hour at agreed rates, plus what's bought for it.") },
	{ value: "Retainer", icon: "repeat", said: __("A monthly fee for a set number of hours.") },
	{ value: "Internal", icon: "building-2", said: __("No customer. A budget and the work.") },
];

// A step of the New Project dialog: frappe's Slide, inside a dialog rather than
// the setup wizard's page, so without the wizard's theme button.
onedesk.project.Step = class Step extends frappe.ui.Slide {
	attach_toggle_theme_btn() {}
};

// New Project in three steps, on frappe's Slides: the kind, what that kind
// needs, then the dates and who runs it. The dialog's own buttons move between
// them; Slides keeps the steps, their dots and what each one holds.
frappe.ui.form.ProjectQuickEntryForm = class ProjectQuickEntryForm extends frappe.ui.form.QuickEntryForm {
	is_quick_entry() {
		return true;
	}

	render_dialog() {
		const doc = this.doc || {};
		const kind = (want) => `eval:${JSON.stringify(want)}.includes(doc.kind)`;
		this.kind = doc.one_kind || null;
		this.title = doc.one_parent ? __("New Sub-project") : __("New Project");
		this.size = "large";
		this.fields = [{ fieldtype: "HTML", fieldname: "steps" }];
		super.make();
		this.$wrapper.addClass("one-new-project");

		const details = [
			{ fieldtype: "Data", fieldname: "kind", hidden: 1 },
			{ fieldtype: "Link", fieldname: "parent", options: "Project", hidden: 1, default: doc.one_parent },
			{ fieldtype: "Data", fieldname: "title", label: __("Name"), reqd: 1, default: doc.project_name },
			{ fieldtype: "Column Break" },
			{
				fieldtype: "Link",
				fieldname: "client",
				label: __("Customer"),
				options: "Customer",
				default: doc.customer,
				depends_on: kind(["Fixed Price", "Time and Materials", "Retainer"]),
				mandatory_depends_on: kind(["Fixed Price", "Time and Materials", "Retainer"]),
			},
			// The contract and the fee are agreed in the customer's own currency.
			{ fieldtype: "Link", fieldname: "currency", options: "Currency", hidden: 1 },
			{ fieldtype: "Section Break", depends_on: kind(["Fixed Price"]) },
			{ fieldtype: "Currency", fieldname: "contract", label: __("Contract Value"), options: "currency" },
			{
				fieldtype: "Link",
				fieldname: "item",
				label: __("Bill As"),
				options: "Item",
				depends_on: "eval:doc.contract",
				mandatory_depends_on: "eval:doc.contract",
			},
			{ fieldtype: "Column Break" },
			{ fieldtype: "Percent", fieldname: "retention", label: __("Retention"), hidden: !frappe.boot.one_retention },
			{
				fieldtype: "Date",
				fieldname: "retention_due",
				label: __("Retention Due"),
				depends_on: "eval:doc.retention",
				mandatory_depends_on: "eval:doc.retention",
			},
			{
				fieldtype: "Percent",
				fieldname: "retention_handover",
				label: __("Released at Handover"),
				description: __("Share of the retention"),
				depends_on: "eval:doc.retention",
			},
			{ fieldtype: "Section Break", depends_on: kind(["Time and Materials", "Internal"]) },
			{ fieldtype: "Currency", fieldname: "budget", label: __("Budget") },
			{ fieldtype: "Column Break" },
			{ fieldtype: "Section Break", depends_on: kind(["Retainer"]) },
			{ fieldtype: "Currency", fieldname: "monthly_fee", label: __("Monthly Fee"), options: "currency" },
			{ fieldtype: "Column Break" },
			{ fieldtype: "Float", fieldname: "monthly_hours", label: __("Hours a Month") },
		];
		const plan = [
			{ fieldtype: "Data", fieldname: "kind", hidden: 1 },
			{ fieldtype: "Date", fieldname: "starts", label: __("Starts"), default: doc.expected_start_date },
			{ fieldtype: "Link", fieldname: "manager", label: __("Manager"), options: "User" },
			{ fieldtype: "Column Break" },
			// A retainer runs month to month, so it has a start and no end.
			{
				fieldtype: "Date",
				fieldname: "ends",
				label: __("Ends"),
				default: doc.expected_end_date,
				depends_on: kind(["Fixed Price", "Time and Materials", "Internal"]),
			},
			{ fieldtype: "Link", fieldname: "template", label: __("Template"), options: "Project Template" },
			// How its time is counted, apart from how it's paid for (one_project/hours.py).
			{ fieldtype: "Section Break" },
			{
				fieldtype: "Select",
				fieldname: "time",
				label: __("Time"),
				options: [
					{ value: "Timesheets", label: __("Timesheets") },
					{ value: "Attendance on Site", label: __("Attendance on Site") },
					{ value: "Not Tracked", label: __("Not Tracked") },
				],
				reqd: 1,
			},
			{ fieldtype: "Column Break" },
			{
				fieldtype: "Link",
				fieldname: "site",
				label: __("Site"),
				options: "Shift Location",
				depends_on: "eval:doc.time == 'Attendance on Site'",
				mandatory_depends_on: "eval:doc.time == 'Attendance on Site'",
			},
		];
		const said = frappe.xcall("onedesk.one_project.kinds.defaults");

		this.slides = new frappe.ui.Slides({
			parent: this.get_field("steps").$wrapper,
			slide_class: onedesk.project.Step,
			unidirectional: 1,
			done_state: 1,
			slides: [
				{ name: "kind", title: __("Kind"), fields: [{ fieldtype: "HTML", fieldname: "kinds" }], onload: (step) => this.draw_kinds(step) },
				{
					name: "details",
					title: __("Details"),
					fields: details,
					onload: (step) => {
						// frappe applies mandatory_depends_on in a dialog's fields only.
						step.form.is_dialog = true;
						// Slide copies its fields as JSON, which drops a function.
						step.get_field("item").get_query = () => ({
							filters: { is_sales_item: 1, disabled: 0, is_stock_item: 0 },
						});
						step.form.set_value("kind", this.kind).then(() => step.form.refresh_dependency());
						said.then((found) => {
							if (!step.get_value("item") && found.item) step.form.set_value("item", found.item);
						});
						// The contract and the fee are in the currency the customer is billed in.
						const billed = (customer) =>
							frappe
								.xcall("onedesk.one_project.kinds.defaults", { customer })
								.then((found) => step.form.set_value("currency", found.currency || frappe.defaults.get_default("currency")));
						step.get_field("client").df.onchange = () => billed(step.get_value("client"));
						billed(step.get_value("client"));
					},
				},
				{
					name: "plan",
					title: __("Plan"),
					fields: plan,
					onload: (step) => {
						step.form.set_value("kind", this.kind).then(() => step.form.refresh_dependency());
						step.form.is_dialog = true;
						said.then((found) => {
							if (!step.get_value("manager")) step.form.set_value("manager", found.user);
							if (!step.get_value("time")) step.form.set_value("time", found.time || "Timesheets");
						});
					},
				},
			],
		});
		this.slides.$footer.hide();
		this.slides.refresh = ((refresh) => (id) => {
			refresh.call(this.slides, id);
			this.set_buttons();
		})(this.slides.refresh);

		this.set_secondary_action_label(__("Previous"));
		this.set_secondary_action(() => this.go(-1));
		this.onhide = () => (frappe.quick_entry = null);
		this.set_buttons();
		this.show();
		if (this.init_callback) this.init_callback(this);
	}

	// Previous on every step but the first; Next, then Create Project on the last.
	set_buttons() {
		const at = this.slides.current_id || 0;
		const last = at === this.slides.slides.length - 1;
		this.get_secondary_btn().toggle(at > 0);
		// The first step has nothing to press but a card.
		this.$wrapper.find(".modal-footer").toggle(at > 0 || Boolean(this.kind));
		this.set_primary_action(last ? __("Create Project") : __("Next"), () => (last ? this.create() : this.go(1)));
		// The kind is picked by its card, which moves on.
		this.get_primary_btn().toggle(at > 0 || Boolean(this.kind));
	}

	// Forward only once this step's own fields are filled in; back any time.
	go(by) {
		const slides = this.slides;
		const step = slides.current_slide;
		if (by > 0 && step.form && step.name !== "kind" && !step.set_values()) return;
		if (by > 0) step.done = true;
		slides.show_slide(slides.current_id + by);
	}

	// The kinds as cards. Picking one shows its fields on the next step.
	draw_kinds(step) {
		const esc = frappe.utils.escape_html;
		const $kinds = step.get_field("kinds").$wrapper;
		const draw = () => {
			$kinds.html(
				`<div class="one-kinds" role="radiogroup" aria-label="${esc(__("Kind"))}">` +
					onedesk.project
						.KINDS()
						.map(
							(one) =>
								`<button type="button" class="one-kind${one.value === this.kind ? " on" : ""}" role="radio" aria-checked="${one.value === this.kind}" data-kind="${esc(one.value)}">` +
								`<span class="one-kind-icon">${frappe.utils.icon(one.icon, "sm")}</span>` +
								`<span class="one-kind-name">${esc(__(one.value))}</span>` +
								`<span class="one-kind-said">${esc(one.said)}</span></button>`
						)
						.join("") +
					`</div>`
			);
			$kinds.find("[data-kind]").on("click", (e) => {
				this.kind = e.currentTarget.dataset.kind;
				draw();
				// The steps after this one ask for what the kind needs.
				for (const step of [this.slides.slide_dict[1], this.slides.slide_dict[2]]) {
					if (step.made) step.form.set_value("kind", this.kind).then(() => step.form.refresh_dependency());
				}
				this.go(1);
			});
		};
		draw();
	}

	async create() {
		const [, details, plan] = Object.values(this.slides.slide_dict);
		if (!plan.set_values() || this.working) return;
		// Hidden fields are not among the values frappe's form returns.
		const values = { ...details.values, ...plan.values, kind: this.kind, parent: details.get_value("parent") };
		// An end typed before the kind became Retainer is not one it has.
		if (this.kind === "Retainer") delete values.ends;
		this.working = true;
		try {
			const name = await frappe.xcall("onedesk.one_project.kinds.make", { values });
			this.hide();
			frappe.show_alert({ message: __("{0} created", [frappe.utils.escape_html(values.title)]), indicator: "green" });
			if (this.after_insert) this.after_insert(await frappe.db.get_doc("Project", name));
			else frappe.set_route("Form", "Project", name);
		} finally {
			this.working = false;
		}
	}
};
