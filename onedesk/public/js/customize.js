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
			if (!this.data || data.doctype !== this.doctype || data.token === this.data.token || this.saving) return;
			if (this.dirty) this.conflict();
			else if (this.$content && this.$content.is(":visible")) this.refresh();
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
			this.$content.html(onedesk.shell.empty(__("Open a form, then Customize from its menu."), "", { icon: "settings-2" }));
			return;
		}
		try {
			this.data = await frappe.xcall(Customize.API + "load", { doctype: this.doctype });
		} catch (e) {
			this.$content.html(frappe.ui.alert.html({ title: __("This form cannot be customized here."), theme: "red" }));
			return;
		}
		this.$content.empty();
		this.draw(this.data);
	}

	saver(values) {
		return { method: Customize.API + "save", args: { doctype: this.doctype, values, token: this.data.token } };
	}

	redraw(said) {
		this.data = said;
		this.draw(said);
	}

	draw(data) {
		onedesk.shell.name(__("Customize {0}", [data.label]), { route: `customize/${encodeURIComponent(data.doctype)}` });
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
					{ heading: __("Above the Fields"), note: declared || __("The numbers under the title, the buttons, and fields of the records this one links to.") },
					{ stack: ["band"] },
					{ stack: ["verbs"] },
					{ stack: ["linked"] },
					{ heading: __("Connections and Buttons") },
					{ stack: ["links"] },
					{ stack: ["actions"] },
				],
			}
		);
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
