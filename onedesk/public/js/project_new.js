// New Project, by kind: frappe's quick entry for Project, asking only what the
// kind needs. Picking a kind is the first thing; its fields follow. For Fixed
// Price, the contract is made with it (one_project/kinds.py `make`).
frappe.provide("onedesk.project");

onedesk.project.KINDS = () => [
	{
		value: "Fixed Price",
		icon: "file-text",
		said: __("An agreed price, billed as the work gets done. Subcontracts, retention and a budget."),
	},
	{ value: "Time and Materials", icon: "clock", said: __("Billed by the hour at agreed rates, plus what's bought for it.") },
	{ value: "Retainer", icon: "repeat", said: __("A monthly fee for a set number of hours.") },
	{ value: "Internal", icon: "building-2", said: __("No customer. A budget and the work.") },
];

frappe.ui.form.ProjectQuickEntryForm = class ProjectQuickEntryForm extends frappe.ui.form.QuickEntryForm {
	is_quick_entry() {
		return true;
	}

	render_dialog() {
		const doc = this.doc || {};
		const kind = (want) => `eval:${JSON.stringify(want)}.includes(doc.kind)`;
		this.title = __("New Project");
		this.size = "large";
		this.fields = [
			{ fieldtype: "HTML", fieldname: "kinds" },
			{ fieldtype: "Data", fieldname: "kind", hidden: 1, default: doc.one_kind || "Fixed Price" },
			{ fieldtype: "Link", fieldname: "parent", options: "Project", hidden: 1, default: doc.one_parent },
			{ fieldtype: "Section Break" },
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
			{ fieldtype: "Section Break", depends_on: kind(["Fixed Price"]) },
			{ fieldtype: "Currency", fieldname: "contract", label: __("Contract Value") },
			{
				fieldtype: "Link",
				fieldname: "item",
				label: __("Bill As"),
				options: "Item",
				depends_on: "eval:doc.contract",
				mandatory_depends_on: "eval:doc.contract",
				get_query: () => ({ filters: { is_sales_item: 1, disabled: 0, is_stock_item: 0 } }),
			},
			{ fieldtype: "Column Break" },
			{ fieldtype: "Percent", fieldname: "retention", label: __("Retention") },
			{
				fieldtype: "Date",
				fieldname: "retention_due",
				label: __("Retention Due"),
				depends_on: "eval:doc.retention",
				mandatory_depends_on: "eval:doc.retention",
			},
			{ fieldtype: "Section Break", depends_on: kind(["Time and Materials", "Internal"]) },
			{ fieldtype: "Currency", fieldname: "budget", label: __("Budget") },
			{ fieldtype: "Column Break" },
			{ fieldtype: "Section Break", depends_on: kind(["Retainer"]) },
			{ fieldtype: "Currency", fieldname: "monthly_fee", label: __("Monthly Fee") },
			{ fieldtype: "Column Break" },
			{ fieldtype: "Float", fieldname: "monthly_hours", label: __("Hours a Month") },
			{ fieldtype: "Section Break" },
			{ fieldtype: "Date", fieldname: "starts", label: __("Starts"), default: doc.expected_start_date },
			{ fieldtype: "Link", fieldname: "manager", label: __("Manager"), options: "User" },
			{ fieldtype: "Column Break" },
			{ fieldtype: "Date", fieldname: "ends", label: __("Ends"), default: doc.expected_end_date },
			{ fieldtype: "Link", fieldname: "template", label: __("Template"), options: "Project Template" },
		];
		super.make();
		this.$wrapper.addClass("one-new-project");
		this.set_primary_action(__("Create Project"), () => this.create());
		this.onhide = () => (frappe.quick_entry = null);
		this.draw_kinds();
		this.show();
		this.refresh_dependency();
		frappe.xcall("onedesk.one_project.kinds.defaults").then((said) => {
			if (!this.get_value("item") && said.item) this.set_value("item", said.item);
			if (!this.get_value("manager")) this.set_value("manager", said.user);
		});
		if (this.init_callback) this.init_callback(this);
	}

	// The kinds as cards: one is picked, and its fields show below.
	draw_kinds() {
		const esc = frappe.utils.escape_html;
		const $kinds = this.get_field("kinds").$wrapper;
		const draw = () => {
			const on = this.get_value("kind");
			$kinds.html(
				`<div class="one-kinds" role="radiogroup" aria-label="${esc(__("Kind"))}">` +
					onedesk.project
						.KINDS()
						.map(
							(one) =>
								`<button type="button" class="one-kind${one.value === on ? " on" : ""}" role="radio" aria-checked="${one.value === on}" data-kind="${esc(one.value)}">` +
								`<span class="one-kind-icon">${frappe.utils.icon(one.icon, "sm")}</span>` +
								`<span class="one-kind-name">${esc(__(one.value))}</span>` +
								`<span class="one-kind-said">${esc(one.said)}</span></button>`
						)
						.join("") +
					`</div>`
			);
			$kinds.find("[data-kind]").on("click", (e) => {
				this.set_value("kind", e.currentTarget.dataset.kind).then(() => {
					draw();
					this.refresh_dependency();
				});
			});
		};
		draw();
	}

	async create() {
		const values = this.get_values();
		if (!values || this.working) return;
		// Hidden fields are not among the values frappe's dialog returns.
		values.kind = this.get_value("kind");
		values.parent = this.get_value("parent");
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
