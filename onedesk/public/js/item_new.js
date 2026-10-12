// New Item, by kind: frappe's quick entry for Item, in three steps on frappe's
// Slides as New Project is (project_new.js). What the thing is comes first, then
// its name, group and unit, then what that kind needs: prices and supplier, where
// it is kept and when to order more, its asset category, or the sizes and colours
// it comes in. The server sets ERPNext's own fields from the answers
// (one_inventory/kinds.py `make`).
frappe.provide("onedesk.item");

onedesk.item.KINDS = () => [
	{ value: "Stock", label: __("Kept in Stock"), icon: "package", said: __("Counted in a warehouse.") },
	{ value: "Service", label: __("Service"), icon: "wrench", said: __("Work or a charge, never stocked.") },
	{ value: "Equipment", label: __("Equipment"), icon: "truck", said: __("Owned and used, like a van or a laptop.") },
	{ value: "Versions", label: __("Sizes or Colours"), icon: "layers", said: __("One product in several versions.") },
];

frappe.ui.form.ItemQuickEntryForm = class ItemQuickEntryForm extends frappe.ui.form.QuickEntryForm {
	is_quick_entry() {
		return true;
	}

	render_dialog() {
		this.title = __("New Item");
		this.size = "large";
		this.fields = [{ fieldtype: "HTML", fieldname: "steps" }];
		super.make();
		this.$wrapper.addClass("one-new-project");
		this.kind = null;
		frappe.xcall("onedesk.one_inventory.kinds.defaults").then((said) => {
			this.said = said;
			this.make_steps();
		});
	}

	make_steps() {
		const said = this.said;
		const doc = this.doc || {};
		const kind = (want) => `eval:${JSON.stringify(want)}.includes(doc.kind)`;
		const details = [
			{ fieldtype: "Data", fieldname: "kind", hidden: 1 },
			{ fieldtype: "Data", fieldname: "title", label: __("Name"), reqd: 1, default: doc.item_name },
			{
				fieldtype: "Data",
				fieldname: "code",
				label: __("Code"),
				reqd: said.by_code ? 1 : 0,
				hidden: said.by_code ? 0 : 1,
			},
			{ fieldtype: "Link", fieldname: "group", label: __("Group"), options: "Item Group", reqd: 1, default: doc.item_group },
			{ fieldtype: "Link", fieldname: "unit", label: __("Unit"), options: "UOM", reqd: 1, default: doc.stock_uom || said.unit },
			{
				fieldtype: "Select",
				fieldname: "measured_by",
				label: __("Sold by Size"),
				options: [
					{ value: "No", label: __("No") },
					{ value: "Length", label: __("Length") },
					{ value: "Area", label: __("Area") },
				],
				default: "No",
				depends_on: kind(["Stock", "Versions", "Service"]),
			},
			{
				fieldtype: "Float",
				fieldname: "per_unit",
				label: __("Metres in One Unit"),
				depends_on: `eval:doc.measured_by == "Length" && doc.unit != "Meter"`,
				mandatory_depends_on: `eval:doc.measured_by == "Length" && doc.unit != "Meter"`,
			},
			{
				fieldtype: "Float",
				fieldname: "per_unit_area",
				label: __("Square Metres in One Unit"),
				depends_on: `eval:doc.measured_by == "Area" && doc.unit != "Square Meter"`,
				mandatory_depends_on: `eval:doc.measured_by == "Area" && doc.unit != "Square Meter"`,
			},
			{ fieldtype: "Column Break" },
			{ fieldtype: "Attach Image", fieldname: "image", label: __("Picture") },
			{ fieldtype: "Small Text", fieldname: "description", label: __("Description") },
		];
		const versions = Object.entries(said.attributes || {}).map(([attribute, values]) => ({
			fieldtype: "MultiSelectList",
			fieldname: `v_${frappe.scrub(attribute)}`,
			label: __(attribute),
			options: values,
		}));
		// Selling on the left, and where it comes from on the right, each switch
		// opening the fields it needs underneath it. Ordering more when low is
		// its own part.
		const sells = ["Stock", "Service", "Versions"];
		const more = [
			{ fieldtype: "Data", fieldname: "kind", hidden: 1 },
			{ fieldtype: "Section Break" },
			{ fieldtype: "Column Break", label: __("Selling"), depends_on: kind(sells) },
			{ fieldtype: "Switch", fieldname: "sold", label: __("Sold to Customers") },
			{ fieldtype: "Currency", fieldname: "selling_price", label: __("Selling Price"), options: "currency", depends_on: "eval:doc.sold" },
			{ fieldtype: "Column Break", label: __("Buying and Making") },
			{ fieldtype: "Switch", fieldname: "bought", label: __("Bought from Suppliers"), default: 1 },
			{ fieldtype: "Currency", fieldname: "buying_price", label: __("Buying Price"), options: "currency", depends_on: "eval:doc.bought && doc.kind != 'Versions'" },
			{ fieldtype: "Link", fieldname: "supplier", label: __("Usual Supplier"), options: "Supplier", depends_on: "eval:doc.bought" },
			{ fieldtype: "Switch", fieldname: "made_here", label: __("Made in Our Workshop"), depends_on: kind(["Stock", "Versions"]) },
			{ fieldtype: "Section Break", depends_on: kind(["Stock"]) },
			{ fieldtype: "Switch", fieldname: "reorder", label: __("Order More When Low") },
			{ fieldtype: "Column Break" },
			{ fieldtype: "Section Break", depends_on: `eval:doc.reorder && doc.kind == "Stock"` },
			{ fieldtype: "Float", fieldname: "reorder_level", label: __("Order More Below"), mandatory_depends_on: "eval:doc.reorder" },
			{ fieldtype: "Column Break" },
			{ fieldtype: "Float", fieldname: "reorder_qty", label: __("Order This Many") },
			{ fieldtype: "Section Break", depends_on: kind(["Stock"]) },
			{ fieldtype: "Link", fieldname: "warehouse", label: __("Kept In"), options: "Warehouse" },
			{ fieldtype: "Column Break" },
			{ fieldtype: "Float", fieldname: "opening_stock", label: __("On Hand Now") },
			{ fieldtype: "Section Break", depends_on: kind(["Equipment"]) },
			{
				fieldtype: "Link",
				fieldname: "asset_category",
				label: __("Asset Category"),
				options: "Asset Category",
				mandatory_depends_on: kind(["Equipment"]),
			},
			{ fieldtype: "Column Break" },
			{ fieldtype: "Section Break", label: __("Comes In"), depends_on: kind(["Versions"]), description: __("Each combination becomes its own item.") },
			...versions,
			{ fieldtype: "Data", fieldname: "currency", hidden: 1, default: said.currency },
		];
		// What goes into one of it: its first bill of materials, a step only
		// something made here has (`follow_made`).
		this.made_from = {
			name: "made",
			title: __("Made From"),
			fields: [
				{ fieldtype: "HTML", fieldname: "note" },
				{
					fieldtype: "Table",
					fieldname: "materials",
					label: __("Materials"),
					in_place_edit: true,
					data: [],
					fields: [
						{ fieldtype: "Link", fieldname: "item_code", label: __("Material"), options: "Item", in_list_view: 1, reqd: 1, columns: 6 },
						{ fieldtype: "Float", fieldname: "qty", label: __("Quantity"), in_list_view: 1, reqd: 1, columns: 2 },
						{ fieldtype: "Data", fieldname: "uom", label: __("Unit"), in_list_view: 1, read_only: 1, columns: 2 },
					],
				},
			],
			onload: (step) => {
				const [, details] = Object.values(this.slides.slide_dict);
				const unit = details.get_value("unit") || this.said.unit;
				const table = step.get_field("materials");
				// "Per Meter", but "per unit" for a unit that is counted.
				frappe.db.get_value("UOM", unit, "must_be_whole_number").then(({ message }) => {
					const said = message?.must_be_whole_number ? __("Quantities per unit") : __("Quantities per {0}", [__(unit)]);
					step.get_field("note").$wrapper.html(`<p class="text-muted">${frappe.utils.escape_html(said)}</p>`);
				});
				const code = details.get_value("code") || "";
				for (const material of table.df.fields.filter((df) => df.fieldname === "item_code")) {
					material.get_query = () => ({ filters: { disabled: 0, has_variants: 0, is_fixed_asset: 0, name: ["!=", code] } });
				}
				// Each material's name and unit: ERPNext shows an item link as
				// "code: name" when the row has its name, and the unit says what
				// the quantity counts.
				const named = async () => {
					const rows = (table.grid.df.data || []).filter((row) => row.item_code && !row.uom);
					if (!rows.length) return;
					const found = await frappe.xcall("frappe.client.get_list", {
						doctype: "Item",
						filters: { name: ["in", rows.map((row) => row.item_code)] },
						fields: ["name", "item_name", "stock_uom"],
					});
					for (const row of rows) {
						const one = found.find((item) => item.name === row.item_code);
						if (one) Object.assign(row, { item_name: one.item_name, uom: one.stock_uom });
					}
					table.grid.refresh();
				};
				table.grid.wrapper.on("change awesomplete-selectcomplete", "input", () => setTimeout(named, 300));
				// Hundreds of parts come from a list, not one row at a time.
				$(frappe.ui.button.html({ label: __("Add from a List"), size: "sm", css_class: "one-from-list" }))
					.insertAfter(table.grid.wrapper.find(".grid-add-row"))
					.on("click", () => this.from_list(table));
			},
		};
		const steps = this.get_field("steps").$wrapper;
		this.slides = new frappe.ui.Slides({
			parent: steps,
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
						step.get_field("group").get_query = () => ({ filters: { is_group: 0 } });
						// The code follows the name until somebody types one.
						let typed = false;
						step.get_field("code").df.onchange = () => (typed = Boolean(step.get_value("code")));
						step.get_field("title").df.onchange = () => {
							if (!typed) step.form.set_value("code", onedesk.item.code_from(step.get_value("title"))).then(() => (typed = false));
						};
						step.get_field("measured_by").df.onchange = () => this.follow_measure(step);
						step.get_field("unit").df.onchange = () => this.follow_unit(step);
						this.follow_kind(step);
					},
				},
				{
					name: "more",
					title: __("Buying, Selling and Stock"),
					fields: more,
					onload: (step) => {
						step.get_field("warehouse").get_query = () => ({ filters: { is_group: 0, disabled: 0 } });
						if (said.warehouse) step.form.set_value("warehouse", said.warehouse);
						step.get_field("made_here").df.onchange = () => this.follow_made(step);
						this.follow_kind(step);
					},
				},
			],
		});
		this.slides.$footer.hide();
		onedesk.project.steps_in_footer(this);
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

	// A step's fields say what its kind needs, and a kind starts in its group,
	// sold or not, as most things of that kind are.
	follow_kind(step) {
		if (!step?.form || !this.kind) return;
		const was = step.get_value("kind");
		step.form.set_value("kind", this.kind).then(() => step.form.refresh_dependency());
		if (was === this.kind) return;
		if (step.name === "details") {
			const group = (this.said.groups || {})[this.kind];
			if (group) step.form.set_value("group", group);
		}
		if (step.name === "more") {
			step.form.set_value("sold", this.kind === "Equipment" ? 0 : 1);
			// Only stock can be made here, so a service or equipment is bought.
			const made = ["Stock", "Versions"].includes(this.kind);
			$(step.form.wrapper).find(".column-label").eq(1).text(made ? __("Buying and Making") : __("Buying"));
			this.follow_made(step);
		}
	}

	// Add from a List: a parts list pasted or uploaded, read and matched to the
	// items there are, shown before anything is saved, then added to the table
	// with the missing parts made stock items (one_inventory/parts.py).
	from_list(table) {
		const esc = frappe.utils.escape_html;
		const counted = (qty) => format_number(qty, null, Number.isInteger(qty) ? 0 : 3);
		let found = null;
		let dialog = null;
		const act = async (values) => {
			if (found) {
				const rows = await frappe.xcall("onedesk.one_inventory.parts.add", { parts: found.parts });
				table.grid.df.data = (table.grid.df.data || []).filter((row) => row.item_code).concat(rows);
				table.grid.refresh();
				dialog.hide();
				frappe.show_alert({ message: __("{0} parts added", [rows.length]), indicator: "green" });
				return;
			}
			if (!values.file && !values.text) {
				frappe.msgprint(__("Upload a list or paste one."));
				return;
			}
			found = await frappe.xcall("onedesk.one_inventory.parts.read", { text: values.text, file_url: values.file });
			const rows = found.parts
				.map(
					(one) =>
						`<tr><td>${esc(one.item || one.code || "")}</td><td>${esc(one.item_name || "")}${one.note ? `<div class="text-muted small">${esc(one.note)}</div>` : ""}</td>` +
						`<td class="text-right">${esc(counted(one.qty))}</td><td>${esc(__(one.uom || ""))}</td>` +
						`<td>${one.new ? `<span class="indicator-pill blue">${esc(__("New"))}</span>` : `<span class="indicator-pill green">${esc(__("In Items"))}</span>`}</td></tr>`
				)
				.join("");
			dialog.fields_dict.file.$wrapper.hide();
			dialog.fields_dict.text.$wrapper.hide();
			dialog.fields_dict.found.$wrapper.html(
				`<p>${esc(found.new ? __("{0} parts, {1} new", [found.parts.length, found.new]) : __("{0} parts, none new", [found.parts.length]))}</p>` +
					`<table class="table table-sm"><thead><tr><th>${esc(__("Part"))}</th><th>${esc(__("Name"))}</th><th class="text-right">${esc(__("Quantity"))}</th><th>${esc(__("Unit"))}</th><th></th></tr></thead><tbody>${rows}</tbody></table>`
			);
			dialog.set_primary_action(__("Add {0} Parts", [found.parts.length]), act);
		};
		dialog = new frappe.ui.Dialog({
			title: __("Add from a List"),
			size: "large",
			fields: [
				{ fieldtype: "Attach", fieldname: "file", label: __("Parts List"), description: __("A spreadsheet or CSV file") },
				{ fieldtype: "Small Text", fieldname: "text", label: __("Or Paste It"), description: __("Code, name, quantity and unit, one part per row") },
				{ fieldtype: "HTML", fieldname: "found" },
			],
			primary_action_label: __("Read List"),
			primary_action: act,
		});
		dialog.show();
	}

	// Something made here has a fourth step for what it is made from.
	// Length or Area counts the item in metres or square metres, unless
	// it is kept in a unit of its own (a sheet), which then says its size.
	follow_measure(details) {
		const by = details.get_value("measured_by");
		const unit = { Length: "Meter", Area: "Square Meter" }[by];
		const was = details.get_value("unit");
		if (unit && [this.said.unit, "Meter", "Square Meter"].includes(was)) details.form.set_value("unit", unit);
		if (!unit && ["Meter", "Square Meter"].includes(was)) details.form.set_value("unit", this.said.unit);
	}

	// A unit that is a length or an area sells the item by it, as saving the
	// item would (measure.py follows_unit).
	follow_unit(details) {
		const unit = details.get_value("unit");
		if (!unit || details.get_value("measured_by") !== "No") return;
		frappe.xcall("onedesk.one_inventory.measure.unit_is", { uom: unit }).then((kind) => {
			if (kind && details.get_value("unit") === unit) details.form.set_value("measured_by", kind);
		});
	}

	follow_made(step) {
		const slides = this.slides;
		const want = ["Stock", "Versions"].includes(this.kind) && Boolean(step.get_value("made_here"));
		const has = slides.slides.length === 4;
		if (want && !has) {
			slides.slides.push(this.made_from);
			slides.setup();
		} else if (!want && has) {
			slides.slides.pop();
		}
		slides.render_progress_dots();
		this.set_buttons();
	}

	set_buttons() {
		const at = this.slides?.current_id || 0;
		const last = this.slides && at === this.slides.slides.length - 1;
		this.get_secondary_btn().toggle(at > 0);
		this.set_primary_action(last ? __("Add Item") : __("Next"), () => (last ? this.create() : this.go(1)));
		this.get_primary_btn().toggle(at > 0 || Boolean(this.kind));
	}

	go(by) {
		const slides = this.slides;
		const step = slides.current_slide;
		if (by > 0 && step.form && step.name !== "kind" && !step.fulfil()) return;
		if (by > 0) step.done = true;
		slides.show_slide(slides.current_id + by);
	}

	draw_kinds(step) {
		const esc = frappe.utils.escape_html;
		const $kinds = step.get_field("kinds").$wrapper;
		const draw = () => {
			$kinds.html(
				`<div class="one-kinds" role="radiogroup" aria-label="${esc(__("Kind"))}">` +
					onedesk.item
						.KINDS()
						.map(
							(one) =>
								`<button type="button" class="one-kind${one.value === this.kind ? " on" : ""}" role="radio" aria-checked="${one.value === this.kind}" data-kind="${esc(one.value)}">` +
								`<span class="one-kind-icon">${frappe.utils.icon(one.icon, "sm")}</span>` +
								`<span class="one-kind-name">${esc(one.label)}</span>` +
								`<span class="one-kind-said">${esc(one.said)}</span></button>`
						)
						.join("") +
					`</div>`
			);
			$kinds.find("[data-kind]").on("click", (e) => {
				this.kind = e.currentTarget.dataset.kind;
				draw();
				for (const one of [this.slides.slide_dict[1], this.slides.slide_dict[2]]) this.follow_kind(one);
				this.go(1);
			});
		};
		draw();
	}

	async create() {
		const [, details, more] = Object.values(this.slides.slide_dict);
		const made = this.slides.slides.length === 4 ? this.slides.slide_dict[3] : null;
		if (!more.fulfil() || (made && !made.fulfil()) || this.working) return;
		const values = { ...details.values, ...more.values, kind: this.kind, code: details.get_value("code") };
		values.materials = made ? (made.get_value("materials") || []).filter((one) => one.item_code && one.qty > 0).map(({ item_code, qty }) => ({ item_code, qty })) : [];
		values.versions = {};
		for (const attribute of Object.keys(this.said.attributes || {})) {
			const chosen = more.get_value(`v_${frappe.scrub(attribute)}`) || [];
			if (chosen.length) values.versions[attribute] = chosen;
		}
		if (this.kind === "Versions" && !Object.keys(values.versions).length) {
			frappe.msgprint(__("Pick at least one size or colour."));
			return;
		}
		this.working = true;
		try {
			const name = await frappe.xcall("onedesk.one_inventory.kinds.make", { values });
			this.hide();
			frappe.show_alert({ message: __("{0} added", [frappe.utils.escape_html(values.title)]), indicator: "green" });
			if (this.after_insert) this.after_insert(await frappe.db.get_doc("Item", name));
			else {
				// Something made here opens where its bill of materials is added.
				if (values.made_here) frappe.route_options = { view: "making" };
				frappe.set_route("Form", "Item", name);
			}
		} finally {
			this.working = false;
		}
	}
};

// An item code from its name, as kinds.py `code_from` makes it.
onedesk.item.code_from = (name) =>
	(String(name || "").match(/[A-Za-z0-9]+/g) || [])
		.slice(0, 3)
		.map((word) => word.toUpperCase())
		.join("-");
