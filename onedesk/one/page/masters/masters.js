// Masters: the short lists records pick their values from, in one place
// (one/masters.py). The kinds down the left, grouped by where they are used;
// the chosen kind's values beside them in frappe's EmbeddedList. Add is the
// page head's primary action; a value opens in frappe's dialog with the kind's
// own fields, as quick entry draws them, and how many records use it. Every
// write is frappe's own (insert, save, rename_doc, delete), so its permission
// checks and its refusal to remove a value in use are the ones that apply.

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
		this.listen();
	}

	// A value added, changed or removed anywhere (another person, a OneAI
	// card, frappe's form) draws the open list and the counts again.
	listen() {
		const again = frappe.utils.debounce(() => this.load(), 800);
		frappe.realtime.on("list_update", (data) => {
			if (data && this.kind && data.doctype === this.kind.doctype && this.panes.values.is(":visible")) again();
		});
	}

	// Told of changes to the open kind only.
	watch() {
		if (this.watched === this.kind.doctype) return;
		if (this.watched) frappe.realtime.doctype_unsubscribe(this.watched);
		this.watched = this.kind.doctype;
		frappe.realtime.doctype_subscribe(this.watched);
	}

	async load() {
		this.kinds = await frappe.xcall(`${Masters.API}kinds`);
		const asked = frappe.utils.get_url_arg("type");
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
			history.replaceState(null, "", `${location.pathname}?type=${encodeURIComponent(this.kind.doctype)}`);
			this.draw_kinds();
			// On a phone the panes stack, so the chosen list is brought into view.
			this.draw_values().then(() => {
				if (!window.matchMedia("(max-width: 767px)").matches) return;
				requestAnimationFrame(() => this.panes.values[0].scrollIntoView({ block: "start" }));
			});
			// An open OneAI panel is told which list is open now.
			if (onedesk.oneai && onedesk.oneai.panel) onedesk.oneai.panel.moved(onedesk.oneai.where());
		});
	}

	async draw_values() {
		const esc = frappe.utils.escape_html;
		const kind = this.kind;
		this.page.clear_primary_action();
		if (!kind) return this.panes.values.empty();
		onedesk.shell.name(__("Masters"));
		this.watch();
		if (kind.create) this.page.set_primary_action(__("Add {0}", [kind.one]), () => this.open(null), "plus");
		const rows = await frappe.xcall(`${Masters.API}values`, { doctype: kind.doctype });
		// The name, then what frappe's own list of the kind shows beside it.
		const columns = [
			{ label: __("Name"), render: (one) => esc(__(one.label || one.name)) },
			...kind.columns.map((df) => ({ label: df.label, render: (one) => frappe.format(one[df.fieldname], df, { inline: true }) })),
		];
		const $main = $(`<div class="one-masters-main"></div>`);
		this.panes.values.empty().append($main);
		await onedesk.shell.table($main, {
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

	// A value in frappe's dialog, with the kind's own fields as quick entry
	// draws them (a unit's symbol and whether it is whole, an item group's
	// parent), the name first. What a dialog can't hold, a department's
	// approvers, is in frappe's form behind Edit Full Form.
	async open(one) {
		const kind = this.kind;
		await frappe.model.with_doctype(kind.doctype);
		const doc = one ? await frappe.xcall("frappe.client.get", { doctype: kind.doctype, name: one.name }) : null;
		const fields = this.fields(kind, doc);
		const dialog = new frappe.ui.Dialog({
			title: one ? __(one.label || one.name) : __("New {0}", [kind.one]),
			fields: [...fields, { fieldname: "__used", fieldtype: "HTML", options: one ? onedesk.shell.quiet("&nbsp;") : "" }],
			primary_action_label: __("Save"),
			primary_action: () => this.save(dialog, kind, doc, fields),
		});
		if (doc) {
			if (kind.tables) {
				dialog.add_custom_action(__("Edit Full Form"), () => {
					dialog.hide();
					frappe.set_route("Form", kind.doctype, doc.name);
				});
			}
			this.removable(dialog, kind, doc.name, one.label);
			frappe.xcall(`${Masters.API}used`, { doctype: kind.doctype, name: doc.name }).then((count) => {
				dialog.fields_dict.__used.$wrapper.html(
					onedesk.shell.quiet(
						count > 1 ? __("Used on {0} records", [count]) : count ? __("Used on 1 record") : __("Not used on any record")
					)
				);
			});
		}
		dialog.show();
	}

	// The kind's fields from frappe's meta: every one with a value, but a
	// tree's bookkeeping, the company, and tables. The name comes first; a
	// kind named as it is asked to be (Lead Sources) gets a Name field.
	fields(kind, doc) {
		const kept = new Set(["lft", "rgt", "old_parent", "company"]);
		const shown = frappe.meta
			.get_docfields(kind.doctype)
			.filter((df) => !df.hidden && !kept.has(df.fieldname) && !frappe.model.no_value_type.includes(df.fieldtype))
			.map((df) => ({ ...df, default: doc ? doc[df.fieldname] : df.default }));
		const at = shown.findIndex((df) => df.fieldname === kind.name_field);
		const name = at >= 0 ? shown.splice(at, 1)[0] : { fieldname: "__newname", fieldtype: "Data", label: __("Name"), default: doc ? doc.name : "" };
		Object.assign(name, { reqd: 1, read_only: doc && !kind.rename ? 1 : 0 });
		return [name, ...shown];
	}

	// Save: a new value through masters.add; a changed name through frappe's
	// rename, then the rest through frappe.client.save against `modified`.
	async save(dialog, kind, doc, fields) {
		const values = dialog.get_values();
		if (!values) return;
		const name_field = fields[0].fieldname;
		if (!doc) {
			await frappe.xcall(`${Masters.API}add`, { doctype: kind.doctype, values });
			frappe.show_alert({ message: __("Saved"), indicator: "green" });
		} else {
			let name = doc.name;
			const was = name_field === "__newname" ? doc.name : doc[name_field];
			if (values[name_field] !== was) {
				// frappe says it was renamed.
				name = await frappe.xcall(`${Masters.API}rename`, { doctype: kind.doctype, name, value: values[name_field] });
			}
			const changed = {};
			for (const df of fields.slice(1)) {
				if (df.read_only) continue;
				const value = values[df.fieldname] ?? null;
				if (String(value ?? "") !== String(doc[df.fieldname] ?? "")) changed[df.fieldname] = value;
			}
			if (Object.keys(changed).length) {
				const fresh = name === doc.name ? doc : await frappe.xcall("frappe.client.get", { doctype: kind.doctype, name });
				await frappe.xcall("frappe.client.save", { doc: { ...fresh, ...changed } });
				frappe.show_alert({ message: __("Saved"), indicator: "green" });
			}
		}
		dialog.hide();
		this.again();
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
};
