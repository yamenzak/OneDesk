// A form, customized by the workspace (one/customize.py, docs/SHELL.md
// decision 6), read here and changed by OneAI: every part is one of frappe's
// tables of what the workspace added or changed, and Add a Field asks OneAI,
// whose card writes what the page used to (one/ai.py customize). A form with
// no form named opens the Custom Fields list. It redraws when anybody changes the form.
frappe.provide("onedesk");

onedesk.Customize = class Customize extends onedesk.shell.Editor {
	static API = "onedesk.one.customize.";

	constructor(page) {
		super(page);
		this.$section = page.$shell;
		// This form's customizations changed: a OneAI card approved, a
		// Reset, or another administrator. The page reads them again.
		frappe.realtime.on("one_customized", (data) => {
			if (!this.data || data.doctype !== this.doctype || data.token === this.data.token) return;
			if (this.$content && this.$content.is(":visible")) this.refresh();
		});
		// An extension made, turned on or off, or deleted: the list's counts
		// and the form's Extensions change with it, edits kept.
		frappe.realtime.on("list_update", async (data) => {
			if (data.doctype !== "Extension" || !this.doctype || !this.$content || !this.$content.is(":visible")) return;
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
		// No form named: the list of every custom field is frappe's own
		// (Workspace Field, OneStudio's Custom Fields).
		if (!this.doctype) {
			frappe.set_route("List", "Workspace Field");
			return;
		}
		try {
			[this.data, this.extensions] = await Promise.all([
				frappe.xcall(Customize.API + "load", { doctype: this.doctype }),
				frappe.xcall("onedesk.one_studio.forms.extensions", { doctype: this.doctype }),
			]);
		} catch (e) {
			this.$content.html(frappe.ui.alert.html({ title: __("This form can't be customized."), theme: "red" }));
			return;
		}
		this.$content.empty();
		this.draw(this.data);
	}

	redraw(said) {
		this.data = said;
		this.$content.empty();
		this.draw(said);
	}

	// What the workspace changed about the form, read here and changed by
	// OneAI: each part is one of frappe's tables, and a part with nothing in
	// it is not drawn, but for the fields added, which says how to add one.
	draw(data) {
		// "Custom Fields / Customer": one form under the Custom Fields list,
		// as the rail says; the form's own list is Open on the menu.
		onedesk.shell.trail(__("Custom Fields"), "/desk/workspace-field", data.label);
		this.menu(data);
		const esc = frappe.utils.escape_html;
		const badge = (label, theme = "gray") => frappe.ui.badge.html({ label, theme });
		const ask = (text) => onedesk.oneai.open({ ask: text });
		const parts = {};
		for (const key of ["added", "changed", "above", "connections", "extensions"]) {
			parts[key] = $('<div class="one-shell-section"></div>').appendTo(this.$content);
		}
		const drawn = new Set(["added", "extensions"]);

		// The fields added here, and the forms each was carried to.
		const rules = (one) =>
			[
				one.came_with ? badge(__("Standard Field"), "blue") : "",
				one.reqd ? badge(__("Required"), "orange") : "",
				one.unique ? badge(__("Unique")) : "",
				one.in_list_view ? badge(__("In List View")) : "",
				one.read_only ? badge(__("Read Only")) : "",
				one.default ? badge(__("Default {0}", [one.default])) : "",
				one.depends_on ? badge(__("Depends On")) : "",
				one.fetch_from ? badge(__("Fetched From {0}", [one.fetch_from.split(".")[0]])) : "",
				one.non_negative ? badge(__("Non Negative")) : "",
				one.length ? badge(__("Length {0}", [one.length])) : "",
			]
				.filter(Boolean)
				.join(" ");
		onedesk.shell.table(parts.added, {
			title: __("Custom Fields"),
			note: __("Ask OneAI to add or change a field."),
			rows: data.added || [],
			icon: "text-cursor-input",
			empty: __("No custom fields"),
			actions: onedesk.oneai.button(__("Add Field"), __("I want to add a field to {0}.", [data.label])),
			open: (one) => ask(__("I want to change the field {0} on {1}.", [one.label, data.label])),
			columns: [
				{
					label: __("Field"),
					render: (one) => `${esc(one.label)}${one.description ? `<div class="one-shell-quiet">${esc(one.description)}</div>` : ""}`,
				},
				{ label: __("Type"), render: (one) => esc(__(one.fieldtype)) + (one.options ? ` <span class="one-shell-quiet">${esc(one.options.split("\n").join(", "))}</span>` : "") },
				{ label: __("Properties"), render: rules },
				{ label: __("Also Added To"), render: (one) => esc((one.also_on || []).map((form) => __(form)).join(", ")) },
			],
		});

		// What was changed about the fields the form came with.
		const said = {
			label: (value) => __("Renamed to {0}", [value]),
			hidden: (value) => (+value ? __("Hidden") : __("Shown")),
			reqd: (value) => (+value ? __("Required") : __("Optional")),
			in_list_view: (value) => (+value ? __("In List View") : __("Not in List View")),
			in_standard_filter: (value) => (+value ? __("In Filters") : __("Not in Filters")),
			bold: () => __("Bold"),
			read_only: (value) => (+value ? __("Read Only") : __("Editable")),
			default: (value) => __("Default {0}", [value]),
			description: () => __("Description Changed"),
			depends_on: () => __("Depends On"),
		};
		if ((data.changed || []).length) {
			drawn.add("changed");
			onedesk.shell.table(parts.changed, {
				title: __("Changed Fields"),
				rows: data.changed,
				icon: "pencil",
				open: (one) => ask(__("I want to change the field {0} on {1}.", [one.label, data.label])),
				columns: [
					{ label: __("Field"), render: (one) => esc(one.label) },
					{
						label: __("Changes"),
						render: (one) => one.changes.map((change) => badge((said[change.property] || (() => __(change.property)))(change.value))).join(" "),
					},
				],
			});
		}

		// The workspace's own rows above the fields.
		const above = [
			...data.values.band.map((one) => ({ kind: __("Number"), label: one.label, detail: __(one.source || "") })),
			...data.values.verbs.map((one) => ({ kind: __("Button"), label: one.label || one.verb, detail: one.verb })),
			...data.values.charts.map((one) => ({ kind: __("Chart"), label: one.label || one.chart, detail: one.chart })),
			...data.values.linked.map((one) => ({ kind: __("Linked Section"), label: one.label, detail: one.link_field })),
		];
		if (above.length) {
			drawn.add("above");
			onedesk.shell.table(parts.above, {
				title: __("Form Header"),
				rows: above,
				icon: "layout-panel-top",
				columns: [
					{ label: __("Type"), render: (one) => esc(one.kind) },
					{ label: __("Label"), render: (one) => esc(one.label || "") },
					{ label: __("Source"), render: (one) => `<span class="one-shell-quiet">${esc(one.detail || "")}</span>` },
				],
			});
		}

		// Connections, and buttons that open somewhere.
		const joined = [
			...data.values.links.map((one) => ({ kind: __("Connection"), label: __(one.link_doctype), detail: one.link_fieldname })),
			...data.values.actions.map((one) => ({ kind: __("Shortcut"), label: one.label, detail: one.action })),
		];
		if (joined.length) {
			drawn.add("connections");
			onedesk.shell.table(parts.connections, {
				title: __("Connections and Buttons"),
				rows: joined,
				icon: "link",
				columns: [
					{ label: __("Type"), render: (one) => esc(one.kind) },
					{ label: __("Label"), render: (one) => esc(one.label || "") },
					{ label: __("Field"), render: (one) => `<span class="one-shell-quiet">${esc(one.detail || "")}</span>` },
				],
			});
		}

		parts.extensions.addClass("one-customize-extensions");
		this.ran(data);
		for (const [key, $part] of Object.entries(parts)) if (!drawn.has(key)) $part.remove();
	}

	// The extensions on this form (one_studio/forms.py), in one of frappe's
	// tables: what each does, and whether it is on. A row opens it.
	ran(data) {
		const $into = this.$content.find(".one-customize-extensions").empty();
		if (!$into.length) return;
		const esc = frappe.utils.escape_html;
		onedesk.shell.table($into, {
			title: __("Extensions"),
			rows: this.extensions || [],
			icon: "code",
			empty: __("No extensions"),
			open: (one) => frappe.set_route("Form", "Extension", one.name),
			columns: [
				{ label: __("Extension"), render: (one) => esc(one.title) },
				{ label: __("Description"), render: (one) => esc(one.explanation || "") },
				{ label: __("When"), render: (one) => esc([__(one.runs), one.event ? __(one.event) : ""].filter(Boolean).join(" · ")) },
				{ label: __("Status"), render: (one) => frappe.ui.badge.html({ label: one.enabled ? __("On") : __("Off"), theme: one.enabled ? "green" : "gray" }) },
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
			frappe.confirm(__("Reset {0}? This removes all custom fields and changes.", [data.label]), async () => {
				const said = await frappe.xcall(Customize.API + "reset", { doctype: data.doctype });
				frappe.show_alert({ message: __("{0} reset", [data.label]), indicator: "green" });
				this.redraw(said);
			})
		);
	}
};
