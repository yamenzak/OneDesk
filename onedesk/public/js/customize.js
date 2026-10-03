// A form, customized by the workspace (one/customize.py, docs/SHELL.md
// decision 6). The page is the shell's Editor, so it is a record's page in
// all but name: dirty against what loaded, a warning before leaving, Save in
// the head with Ctrl+S, and a save refused when somebody else saved first.
// Every part is frappe's own: FieldGroup, and its grids for the tables.
frappe.provide("onedesk");

onedesk.Customize = class Customize extends onedesk.shell.Editor {
	static API = "onedesk.one.customize.";

	constructor(page) {
		super(page);
		this.$section = page.$shell;
		// Somebody else changed this form's customizations: another
		// administrator, or a OneAI card approved. Untouched, the page
		// reloads; with changes in it, it says so and keeps them.
		frappe.realtime.on("one_customized", (data) => {
			if (!this.doctype) return this.listed();
			if (!this.data || data.doctype !== this.doctype || data.token === this.data.token || this.saving) return;
			if (this.dirty) this.conflict();
			else if (this.$content && this.$content.is(":visible")) this.refresh();
		});
		// An extension made, turned on or off, or deleted: the list's counts
		// and the form's Extensions change with it, edits kept.
		frappe.realtime.on("list_update", async (data) => {
			if (data.doctype !== "Extension" || !this.$content || !this.$content.is(":visible")) return;
			if (!this.doctype) return this.listed();
			this.extensions = await frappe.xcall("onedesk.one_studio.forms.extensions", { doctype: this.doctype });
			this.ran(this.data);
		});
	}

	show() {
		const doctype = frappe.get_route()[1];
		if (doctype === this.doctype && this.data) return;
		this.doctype = doctype;
		this.refresh({ fresh: true });
	}

	async refresh() {
		this.unsaved();
		this.$content = onedesk.shell.body(this.$section, { wide: true });
		if (!this.doctype) {
			this.forms();
			return;
		}
		try {
			[this.data, this.extensions] = await Promise.all([
				frappe.xcall(Customize.API + "load", { doctype: this.doctype }),
				frappe.xcall("onedesk.one_studio.forms.extensions", { doctype: this.doctype }),
			]);
		} catch (e) {
			this.$content.html(frappe.ui.alert.html({ title: __("This form cannot be customized here."), theme: "red" }));
			return;
		}
		this.$content.empty();
		this.draw(this.data);
	}

	// The list again, as it was searched, when it is the one showing.
	listed() {
		if (this.doctype || !this.$content || !this.$content.is(":visible")) return;
		const query = this.$content.find(".embedded-list-search").val();
		this.forms().then((list) => query && list.$wrapper.find(".embedded-list-search").val(query).trigger("input"));
	}

	// No form named: every form the administrator may customize, in one of
	// frappe's tables, the ones the workspace has changed first, then by app
	// (one_studio/forms.py). A row opens the form's Customize page.
	async forms() {
		this.data = null;
		this.$content = onedesk.shell.body(this.$section);
		this.page.set_title(__("Forms"));
		onedesk.shell.trail(__("OneStudio"), "/desk/extension", __("Forms"));
		const rows = await frappe.xcall("onedesk.one_studio.forms.forms");
		this.$content.empty();
		const esc = frappe.utils.escape_html;
		const count = (n, label) => (n ? frappe.ui.badge.html({ label, theme: "blue" }) : "");
		return onedesk.shell.table($("<div>").appendTo(this.$content), {
			note: __("Every form you may change, the ones changed here first. Open one to customize it."),
			rows,
			icon: "file-text",
			page_size: 50,
			empty: __("There is no form you may change."),
			none: __("No form by that name."),
			open: (one) => frappe.set_route("customize", one.doctype),
			columns: [
				{ label: __("Form"), render: (one) => esc(one.label) },
				{ label: __("App"), render: (one) => esc(one.app) },
				{ label: __("Changes"), render: (one) => count(one.changes, one.changes === 1 ? __("1 change") : __("{0} changes", [one.changes])) },
				{ label: __("Extensions"), render: (one) => count(one.extensions, one.extensions === 1 ? __("1 extension") : __("{0} extensions", [one.extensions])) },
			],
		});
	}

	saver(values) {
		return { method: Customize.API + "save", args: { doctype: this.doctype, values, token: this.data.token } };
	}

	redraw(said) {
		this.data = said;
		this.draw(said);
	}

	draw(data) {
		// "Forms / Customer": one form under the Forms list, as the rail says;
		// the form's own list is Open on the menu.
		onedesk.shell.trail(__("Forms"), "/desk/customize", data.label);
		this.menu(data);
		const table = (fieldname, label, description, fields, rows) => ({
			fieldtype: "Table",
			fieldname,
			label,
			description,
			fields,
			data: rows.map((row) => ({ ...row })),
			in_place_edit: true,
		});
		const select = (options, extra = {}) => ({ fieldtype: "Select", options: ["", ...options].join("\n"), ...extra });
		const kinds = [...new Set([...data.choices.kinds, ...data.values.fields.map((one) => one.fieldtype)])];
		const fields = [
			table(
				"fields",
				__("Fields"),
				__("In the order the form shows them; drag a row to move it. A field the record came with may be hidden, not removed."),
				[
					{ fieldtype: "Data", fieldname: "label", label: __("Label"), in_list_view: 1, columns: 3 },
					{
						...select(kinds),
						fieldname: "fieldtype",
						label: __("Kind"),
						in_list_view: 1,
						columns: 2,
						read_only_depends_on: "eval:doc.fieldname && !doc.mine",
					},
					{ fieldtype: "Data", fieldname: "options", label: __("Choices or Form"), in_list_view: 1, columns: 2, read_only_depends_on: "eval:doc.fieldname && !doc.mine" },
					{ fieldtype: "Check", fieldname: "hidden", label: __("Hidden"), in_list_view: 1, columns: 1 },
					{ fieldtype: "Check", fieldname: "reqd", label: __("Required"), in_list_view: 1, columns: 1 },
					{ fieldtype: "Check", fieldname: "in_list_view", label: __("In the List"), in_list_view: 1, columns: 1 },
					{ fieldtype: "Data", fieldname: "fieldname", label: __("Name"), read_only: 1 },
					{ fieldtype: "Check", fieldname: "mine", label: __("Made Here"), read_only: 1 },
				],
				data.values.fields
			),
			table(
				"band",
				__("Numbers Under the Title"),
				__("Each is a field, a field of a linked record, a count or a sum, or a measure a module keeps."),
				[
					{ fieldtype: "Data", fieldname: "label", label: __("Label"), in_list_view: 1, columns: 2, reqd: 1 },
					{ ...select(["Field", "Linked Field", "Count", "Sum", "Measure"]), fieldname: "source", label: __("Value"), in_list_view: 1, columns: 2, reqd: 1 },
					{ ...select(data.choices.fields), fieldname: "field", label: __("Field"), in_list_view: 1, columns: 2 },
					{ ...select(data.choices.measures), fieldname: "measure", label: __("Measure"), in_list_view: 1, columns: 2 },
					{ ...select(["quiet", "waiting", "alarm"]), fieldname: "tone", label: __("Tone"), in_list_view: 1, columns: 1 },
					{ ...select(data.choices.links), fieldname: "link_field", label: __("Through") },
					{ fieldtype: "Link", options: "DocType", fieldname: "of_doctype", label: __("Of") },
					{ fieldtype: "Data", fieldname: "filters", label: __("Counting") },
					{ fieldtype: "Data", fieldname: "shown_when", label: __("Shown When") },
					{ fieldtype: "Data", fieldname: "route", label: __("Leads To") },
					{ fieldtype: "Check", fieldname: "hide_empty", label: __("Hide When Empty") },
				],
				data.values.band
			),
			table(
				"verbs",
				__("Buttons That Do Something"),
				__("What a module offers to do to this record. Each shows only when it can be done."),
				[
					{ ...select(data.choices.verbs), fieldname: "verb", label: __("Verb"), in_list_view: 1, columns: 4, reqd: 1 },
					{ fieldtype: "Data", fieldname: "label", label: __("Label"), in_list_view: 1, columns: 4 },
					{ fieldtype: "Check", fieldname: "primary", label: __("Primary"), in_list_view: 1, columns: 2 },
				],
				data.values.verbs
			),
			table(
				"charts",
				__("Charts Beside the Numbers"),
				__("What a module draws of this record, such as a customer's billing month by month."),
				[
					{ ...select(data.choices.charts), fieldname: "chart", label: __("Chart"), in_list_view: 1, columns: 5, reqd: 1 },
					{ fieldtype: "Data", fieldname: "label", label: __("Label"), in_list_view: 1, columns: 5 },
				],
				data.values.charts
			),
			table(
				"linked",
				__("Linked Sections"),
				__("Fields of a record this one links to, edited here and saved in the same save."),
				[
					{ fieldtype: "Data", fieldname: "label", label: __("Heading"), in_list_view: 1, columns: 2, reqd: 1 },
					{ ...select(data.choices.links), fieldname: "link_field", label: __("Through"), in_list_view: 1, columns: 2, reqd: 1 },
					{ fieldtype: "Small Text", fieldname: "fields", label: __("Fields"), in_list_view: 1, columns: 4, reqd: 1 },
					{ ...select(data.choices.fields), fieldname: "placed_in", label: __("In the Tab Of"), in_list_view: 1, columns: 2 },
				],
				data.values.linked
			),
			table(
				"links",
				__("Connections"),
				__("Records of another form that link to this one, listed under Connections."),
				[
					{ fieldtype: "Link", options: "DocType", fieldname: "link_doctype", label: __("Form"), in_list_view: 1, columns: 4, reqd: 1 },
					{ fieldtype: "Data", fieldname: "link_fieldname", label: __("Its Link Field"), in_list_view: 1, columns: 3, reqd: 1 },
					{ fieldtype: "Data", fieldname: "group", label: __("Group"), in_list_view: 1, columns: 3 },
				],
				data.values.links
			),
			table(
				"actions",
				__("Buttons That Go Somewhere"),
				__("A place in the desk to open from this record, as a route."),
				[
					{ fieldtype: "Data", fieldname: "label", label: __("Label"), in_list_view: 1, columns: 3, reqd: 1 },
					{ fieldtype: "Data", fieldname: "action", label: __("Goes To"), in_list_view: 1, columns: 4, reqd: 1 },
					{ fieldtype: "Data", fieldname: "group", label: __("Group"), in_list_view: 1, columns: 3 },
				],
				data.values.actions
			),
		];
		const declared = data.declared
			? __("{0} of what shows above the fields comes with the form, from {1}, and stays as it is.", [data.declared, data.declared_by || __("a module")])
			: "";
		this.form(
			{ fields, values: {} },
			{
				rows: [
					{ stack: ["fields"] },
					{ heading: __("Above the Fields"), note: declared || __("The numbers and charts under the title, the buttons, and fields of the records this one links to.") },
					{ stack: ["band"] },
					{ stack: ["verbs"] },
					{ stack: ["charts"] },
					{ stack: ["linked"] },
					{ heading: __("Connections and Buttons") },
					{ stack: ["links"] },
					{ stack: ["actions"] },
					{ heading: __("Extensions"), note: __("What runs on this form, written by OneAI and turned on in OneStudio › Extensions. Read here; changed there.") },
					{ html: '<div class="one-customize-extensions"></div>' },
				],
			}
		);
		this.ran(data);
	}

	// The extensions on this form (one_studio/forms.py), in one of frappe's
	// tables: what each does, and whether it is on. A row opens it.
	ran(data) {
		const $into = this.$content.find(".one-customize-extensions").empty();
		if (!$into.length) return;
		const esc = frappe.utils.escape_html;
		onedesk.shell.table($into, {
			rows: this.extensions || [],
			icon: "code",
			empty: __("Nothing runs on {0}", [data.label]),
			open: (one) => frappe.set_route("Form", "Extension", one.name),
			columns: [
				{ label: __("Extension"), render: (one) => esc(one.title) },
				{ label: __("What It Does"), render: (one) => esc(one.explanation || "") },
				{ label: __("When"), render: (one) => esc([__(one.runs), one.event ? __(one.event) : ""].filter(Boolean).join(" · ")) },
				{ label: __("On"), render: (one) => frappe.ui.badge.html({ label: one.enabled ? __("On") : __("Off"), theme: one.enabled ? "green" : "gray" }) },
			],
		});
	}

	menu(data) {
		this.page.clear_menu();
		this.page.add_menu_item(__("Open {0}", [data.label]), () => frappe.set_route("List", data.doctype));
		this.page.add_menu_item(__("Export"), async () => {
			const said = await frappe.xcall(Customize.API + "export", { doctype: data.doctype });
			const blob = new Blob([JSON.stringify(said, null, 1)], { type: "application/json" });
			const link = Object.assign(document.createElement("a"), {
				href: URL.createObjectURL(blob),
				download: `${frappe.scrub(data.doctype)}-customized.json`,
			});
			link.click();
			URL.revokeObjectURL(link.href);
		});
		this.page.add_menu_item(__("Reset"), () =>
			frappe.confirm(__("Take back everything this workspace changed about {0}?", [data.label]), async () => {
				const said = await frappe.xcall(Customize.API + "reset", { doctype: data.doctype });
				frappe.show_alert({ message: __("{0} is as it came.", [data.label]), indicator: "green" });
				this.set_dirty(false);
				this.$content.empty();
				this.redraw(said);
			})
		);
	}
};
