// Masters: the short lists records pick their values from, in one place
// (one/masters.py). The kinds down the left, grouped by where they are used;
// the chosen kind's values beside them in frappe's EmbeddedList. Add is the
// page head's primary action; a value opens in frappe's dialog to rename or
// remove it, with how many records use it. Every write is frappe's own
// (insert, rename_doc, delete), so its permission checks and its refusal to
// remove a value in use are the ones that apply.

frappe.pages["masters"].on_page_load = (wrapper) => {
	const page = onedesk.shell.page(wrapper, __("Masters"));
	wrapper.masters = new onedesk.Masters(page);
};

frappe.pages["masters"].on_page_show = (wrapper) => wrapper.masters && wrapper.masters.load();

frappe.provide("onedesk");

onedesk.Masters = class Masters {
	static API = "onedesk.one.masters.";

	// The groups' names as the page says them.
	static GROUPS = { Shared: __("Shared") };

	constructor(page) {
		this.page = page;
		this.panes = onedesk.shell.panes(page.$shell, [{ key: "kinds", width: 260 }, { key: "values" }]);
	}

	async load() {
		this.kinds = await frappe.xcall(`${Masters.API}kinds`);
		const asked = frappe.utils.get_url_arg("kind");
		const kept = this.kind && this.kinds.find((one) => one.doctype === this.kind.doctype);
		this.kind = this.kinds.find((one) => one.doctype === asked) || kept || this.kinds[0];
		this.draw_kinds();
		await this.draw_values();
	}

	// The kinds as a sidebar, as OneMail's folders and OneTask's views, under
	// their group's name.
	draw_kinds() {
		const esc = frappe.utils.escape_html;
		const groups = [...new Set(this.kinds.map((one) => one.group))];
		const html = groups
			.map((group) => {
				const kinds = this.kinds
					.filter((one) => one.group === group)
					.map((one) => {
						const on = this.kind && one.doctype === this.kind.doctype;
						return `<button class="one-masters-kind${on ? " one-masters-on" : ""}" data-kind="${esc(one.doctype)}" ${on ? 'aria-current="page"' : ""}>
							<span class="one-masters-label">${esc(one.label)}</span><span class="one-masters-count">${one.count}</span>
						</button>`;
					})
					.join("");
				return `<div class="one-masters-group">${esc(Masters.GROUPS[group] || group)}</div>${kinds}`;
			})
			.join("");
		this.panes.kinds.html(
			html ? `<nav class="one-masters-side" aria-label="${__("Masters")}">${html}</nav>` : onedesk.shell.empty(__("No masters"), null, { icon: "database" })
		);
		this.panes.kinds.find("[data-kind]").on("click", (event) => {
			this.kind = this.kinds.find((one) => one.doctype === event.currentTarget.dataset.kind);
			history.replaceState(null, "", `${location.pathname}?kind=${encodeURIComponent(this.kind.doctype)}`);
			this.draw_kinds();
			this.draw_values();
		});
	}

	async draw_values() {
		const esc = frappe.utils.escape_html;
		const kind = this.kind;
		this.page.clear_primary_action();
		if (!kind) return this.panes.values.empty();
		onedesk.shell.name(__("Masters"));
		if (kind.create) this.page.set_primary_action(__("Add"), () => this.open(null), "plus");
		const rows = await frappe.xcall(`${Masters.API}values`, { doctype: kind.doctype });
		const columns = [
			{
				label: __("Name"),
				render: (one) =>
					esc(__(one.label || one.name)) + (one.is_default ? " " + frappe.ui.badge.html({ label: __("Default"), theme: "blue" }) : ""),
			},
		];
		if (kind.doctype === "Print Heading") columns.push({ label: __("Description"), fieldname: "description" });
		const $main = $(`<div class="one-masters-main"></div>`);
		this.panes.values.empty().append($main);
		onedesk.shell.table($main, {
			title: kind.label,
			rows,
			page_size: 100,
			icon: "list",
			empty: __("Nothing here yet"),
			none: __("No matches"),
			open: (one) => this.open(one),
			columns,
		});
	}

	again() {
		this.load();
	}

	// A value: its name, how many records use it, and Remove. The two kinds with
	// more to them have dialogs of their own.
	async open(one) {
		const kind = this.kind;
		if (kind.doctype === "Print Heading") return this.print_heading(one);
		if (kind.doctype === "Address Template") return this.address_template(one);
		const editable = !one || kind.rename;
		const dialog = new frappe.ui.Dialog({
			title: one ? __(one.label || one.name) : __("Add to {0}", [kind.label]),
			fields: [
				{ fieldname: "value", fieldtype: "Data", label: __("Name"), reqd: 1, default: one ? one.label || one.name : "", read_only: !editable },
				{ fieldname: "used", fieldtype: "HTML", options: one ? onedesk.shell.quiet("&nbsp;") : "" },
			],
			primary_action_label: editable ? __("Save") : null,
			primary_action: editable
				? async ({ value }) => {
						dialog.hide();
						if (!one) {
							await frappe.xcall(`${Masters.API}add`, { doctype: kind.doctype, value });
							frappe.show_alert({ message: __("Saved"), indicator: "green" });
						} else if (value !== (one.label || one.name)) {
							// frappe says it was renamed.
							await frappe.xcall(`${Masters.API}rename`, { doctype: kind.doctype, name: one.name, value });
						}
						this.again();
				  }
				: null,
		});
		if (one) {
			this.removable(dialog, kind, one.name, one.label);
			frappe.xcall(`${Masters.API}used`, { doctype: kind.doctype, name: one.name }).then((count) => {
				dialog.fields_dict.used.$wrapper.html(
					onedesk.shell.quiet(count ? __("Used on {0} records", [count]) : __("Not used on any record"))
				);
			});
		}
		dialog.show();
	}

	// Remove, beside a dialog's Save, with frappe's own confirmation. Frappe
	// refuses a value records still use, and says which.
	removable(dialog, kind, name, label) {
		if (!kind.delete) return;
		dialog.set_secondary_action_label(__("Remove"));
		dialog.set_secondary_action(() =>
			frappe.confirm(__("Remove {0}?", [__(label || name)]), async () => {
				await frappe.xcall("frappe.client.delete", { doctype: kind.doctype, name });
				dialog.hide();
				frappe.show_alert({ message: __("Removed"), indicator: "green" });
				this.again();
			})
		);
	}

	// A print heading: what a printed page says above a document.
	print_heading(one) {
		const kind = this.kind;
		const dialog = new frappe.ui.Dialog({
			title: one ? one.name : __("New Print Heading"),
			fields: [
				{ fieldname: "print_heading", fieldtype: "Data", label: __("Heading"), reqd: 1, default: one ? one.name : "", read_only: !!one && !kind.rename },
				{ fieldname: "description", fieldtype: "Small Text", label: __("Description"), default: one ? one.description : "" },
			],
			primary_action_label: __("Save"),
			primary_action: async (values) => {
				if (!one) {
					await frappe.xcall("frappe.client.insert", { doc: { doctype: "Print Heading", ...values } });
				} else {
					let name = one.name;
					if (values.print_heading !== one.name) {
						name = await frappe.xcall("frappe.client.rename_doc", { doctype: "Print Heading", old_name: one.name, new_name: values.print_heading });
					}
					if ((values.description || "") !== (one.description || "")) {
						const doc = await frappe.xcall("frappe.client.get", { doctype: "Print Heading", name });
						await frappe.xcall("frappe.client.save", { doc: { ...doc, description: values.description } });
					}
				}
				dialog.hide();
				frappe.show_alert({ message: __("Saved"), indicator: "green" });
				this.again();
			},
		});
		if (one) this.removable(dialog, kind, one.name);
		dialog.show();
	}

	// An address template: the country it is for, whether it is the default, and
	// the template, which names the address's fields (one/masters.py holds it).
	address_template(one) {
		const kind = this.kind;
		const dialog = new frappe.ui.Dialog({
			title: one ? __(one.country) : __("New Address Template"),
			size: "large",
			fields: [
				{ fieldname: "country", fieldtype: "Link", options: "Country", label: __("Country"), reqd: 1, default: one ? one.country : "", read_only: !!one },
				{ fieldname: "is_default", fieldtype: "Check", label: __("Default"), default: one ? one.is_default : 0 },
				{ fieldname: "template", fieldtype: "Code", options: "Jinja", label: __("Template"), reqd: 1, default: one ? one.template : "" },
			],
			primary_action_label: __("Save"),
			primary_action: async (values) => {
				const doc = one
					? { doctype: "Address Template", name: one.name, modified: one.modified, ...values }
					: { doctype: "Address Template", ...values };
				await frappe.xcall(one ? "frappe.client.save" : "frappe.client.insert", { doc });
				dialog.hide();
				frappe.show_alert({ message: __("Saved"), indicator: "green" });
				this.again();
			},
		});
		if (one) this.removable(dialog, kind, one.name);
		dialog.show();
	}
};
