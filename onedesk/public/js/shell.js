// The shell every page of ours is built in (docs/SHELL.md). A page composes
// these parts rather than drawing its own, so every page of One looks like one
// product and like the desk it sits in:
//
// - the head is frappe's page head: the title, the breadcrumb, the indicator,
//   Save as the primary action with Ctrl+S, the buttons and the menu;
// - the body is a column (the desk form's width) or wide (a table's width);
// - a section is a heading, a note and what is under it, divided from the
//   next by a rule, never boxed;
// - a row, an empty state, a quiet line, one of each;
// - the Editor is a record edited as a desk form is: dirty against what
//   loaded, a warning before leaving, saved against `modified`, and told on
//   `doc_update` when somebody else changes it.
//
// Every part is frappe's first (point 9 of docs/PASSOVER.md): espresso's
// button, badge and alert drawn as frappe-ui draws them, FieldGroup for
// fields, the page head for actions. What is here is only what frappe has not.

frappe.provide("onedesk.shell");

$.extend(onedesk.shell, {
	// A page of ours: frappe's app page, with the shell's frame in its main area.
	page(wrapper, title) {
		const page = frappe.ui.make_app_page({ parent: wrapper, title, single_column: true });
		page.$shell = $(`<section class="one-shell"></section>`).appendTo(page.main);
		return page;
	},

	// The body: a column in the middle of the page, as a desk form and
	// frappe-ui's settings pages are, or wide where a table needs the room.
	// Drawing one replaces what the frame held.
	body($shell, { wide = false } = {}) {
		$shell.html(`<div class="one-shell-body">${onedesk.shell.quiet(__("Loading…"))}</div>`);
		return $shell.find(".one-shell-body").toggleClass("one-shell-wide", !!wide);
	},

	// The page head is a breadcrumb in v17, so a page's name goes there, and
	// to the browser tab.
	name(label) {
		frappe.breadcrumbs.add({ type: "Custom", label: frappe.utils.escape_html(label), route: frappe.get_route_str() });
		frappe.utils.set_title(label);
		// OneAI's panel names where the reader is by the page's title, which the
		// router's change came before; tell it again now that it is right.
		if (onedesk.oneai && onedesk.oneai.panel) onedesk.oneai.panel.moved(onedesk.oneai.where());
	},

	button(label, attrs = {}, variant = "subtle", icon = null, theme = null) {
		return frappe.ui.button.html({ label, attrs, variant, icon, theme: theme || undefined });
	},

	// One part of a page: a heading and what it holds, divided from the next
	// by a rule, the way a record's sections are.
	section(title, body, note) {
		const esc = frappe.utils.escape_html;
		return `<div class="one-shell-section">${title ? `<div class="one-shell-section-title">${esc(title)}</div>` : ""}${
			note ? `<div class="one-shell-quiet one-shell-note">${esc(note)}</div>` : ""
		}${body}</div>`;
	},

	// A row: what it is, a quiet line under it, and its actions on the right.
	// `link` makes the whole row the target, with frappe-ui's list-row hover.
	row({ title = "", sub = "", quiet = "", actions = "", link = null, css = "" } = {}) {
		const esc = frappe.utils.escape_html;
		const attrs = link ? Object.entries(link).map(([key, value]) => ` ${key}="${esc(value)}"`).join("") + ' tabindex="0"' : "";
		return `<div class="one-shell-row${link ? " one-shell-row-link" : ""}${css ? ` ${css}` : ""}"${attrs}>
			<div class="one-shell-row-main">${title ? `<div class="one-shell-row-title">${title}</div>` : ""}${
				sub ? `<div class="one-shell-row-sub">${sub}</div>` : ""
			}${quiet ? `<div class="one-shell-quiet">${quiet}</div>` : ""}</div>
			<div class="one-shell-row-actions">${actions}${link ? `<span class="one-shell-chevron">${frappe.utils.icon("chevron-right", "sm")}</span>` : ""}</div>
		</div>`;
	},

	actions(html) {
		return `<div class="one-shell-actions">${html}</div>`;
	},

	empty(title, description) {
		const esc = frappe.utils.escape_html;
		return `<div class="one-shell-empty"><div class="one-shell-empty-title">${esc(title)}</div>${
			description ? `<div class="one-shell-quiet">${esc(description)}</div>` : ""
		}</div>`;
	},

	quiet(text) {
		return `<div class="one-shell-quiet">${frappe.utils.escape_html(text)}</div>`;
	},
});

// A record edited on a page of ours, as a desk form edits one (form.js,
// model.js). A page extends it and says three things: what to call to save
// (`saver`), how to draw what came back (`redraw`), and how to open the record
// again (`refresh`). `this.$content` is the body the form is drawn in.
onedesk.shell.Editor = class Editor {
	constructor(page) {
		this.page = page;
		this.opened = [];
		this.leaving = (event) => {
			event.preventDefault();
			return (event.returnValue = "There are unsaved changes, are you sure you want to exit?");
		};
		this.reload = frappe.utils.debounce(() => this.refresh({ fresh: false }), 1000);
		frappe.realtime.on("doc_update", (data) => this.updated(data));
	}

	// Listen on each record's realtime room, as a form does on load.
	async hear(opened) {
		this.opened = opened || [];
		for (const one of this.opened) {
			// frappe lets one subscription through a second; wait our turn.
			while (frappe.flags.doc_subscribe) await new Promise((done) => setTimeout(done, 250));
			frappe.realtime.doc_subscribe(one.doctype, one.name);
		}
	}

	// Somebody saved one of these records. Untouched, the page reloads; with
	// changes in it, it says so and keeps them (model.js).
	updated(data) {
		const one = this.opened.find((it) => it.doctype === data.doctype && it.name === data.name);
		if (!one || this.saving || !data.modified || data.modified <= one.modified) return;
		if (this.dirty) this.conflict();
		else if (this.$content && this.$content.is(":visible")) this.reload();
	}

	conflict() {
		if (this.$content.find(".one-shell-conflict").length) return;
		// One title and one action is frappe-ui's row alert: the action on the
		// right, a ghost button in the alert's own colour (Alert.vue).
		const $refresh = $(onedesk.shell.button(__("Refresh"), {}, "ghost")).on("click", () => this.refresh({ fresh: true }));
		$(
			frappe.ui.alert({
				title: __("This form has been modified after you have loaded it"),
				theme: "yellow",
				footer: $refresh,
				css_class: "one-shell-conflict one-shell-alert-row",
			})
		).prependTo(this.$content);
	}

	// Dirty is a difference from what was loaded, so undoing a change makes
	// the page clean again. The warning on leaving is frappe's own, kept out
	// of developer mode as frappe keeps it.
	check() {
		if (!this.values || this.snapshot === undefined) return;
		this.set_dirty(Editor.same(this.values()) !== this.snapshot);
	}

	set_dirty(dirty) {
		this.dirty = dirty;
		if (dirty) this.page.set_indicator(__("Not Saved"), "orange");
		else this.page.clear_indicator();
		removeEventListener("beforeunload", this.leaving, { capture: true });
		if (dirty && !frappe.boot.developer_mode) addEventListener("beforeunload", this.leaving, { capture: true });
	}

	// Every field's value. FieldGroup.get_values leaves an empty field out, so
	// a field somebody cleared would never be sent, and never be cleared.
	static every(group, names) {
		return Object.fromEntries(names.map((name) => [name, group.get_value(name) ?? ""]));
	}

	// Values as compared: empty is empty whatever it is, and order does not count.
	static same(values) {
		return JSON.stringify(
			Object.keys(values || {})
				.sort()
				.map((name) => [name, values[name] === null || values[name] === undefined ? "" : String(values[name])])
				.filter(([, value]) => value !== "")
		);
	}

	// A form made of the record's own fields, saved in one go from the page
	// head, the way a record is. `rows` lays fields out side by side: each row
	// is a list of fieldnames, one per column, or `{ heading, note }` to start
	// a part of its own under a rule, `{ stack }` for fields one under another
	// in one column, `{ row, css }` for a row whose part carries a class, or
	// `{ html }` for something to read.
	form(data, { before = "", after = "", rows = null } = {}) {
		const $card = $(`<div class="one-shell-section">${before}<div class="one-shell-form"></div>${after}</div>`).appendTo(this.$content);
		const own = Object.fromEntries(data.fields.map((one) => [one.fieldname, { ...one, default: data.values[one.fieldname] }]));
		// A heading names the section the rows after it are in: a section with
		// no fields of its own, frappe hides.
		let heading = null;
		const fields = rows
			? rows.flatMap((row, at) => {
					let css = null;
					if (row.row) [css, row] = [row.css, row.row];
					if (row.heading) {
						heading = { fieldtype: "Section Break", fieldname: `shell_part_${at}`, label: row.heading, description: row.note, css_class: "one-shell-part" };
						return [];
					}
					let opening = heading || (at || css ? { fieldtype: "Section Break", fieldname: `shell_row_${at}` } : null);
					if (opening && css) opening = { ...opening, css_class: [opening.css_class, css].filter(Boolean).join(" ") };
					heading = null;
					if (row.html) return [...(opening ? [opening] : []), { fieldtype: "HTML", fieldname: `shell_html_${at}`, options: row.html }];
					if (row.stack) return [...(opening ? [opening] : []), ...row.stack.map((name) => own[name]).filter(Boolean)];
					return [
						...(opening ? [opening] : []),
						...row.flatMap((name, column) => [
							...(column ? [{ fieldtype: "Column Break", fieldname: `shell_col_${at}_${column}` }] : []),
							...(own[name] ? [own[name]] : []),
						]),
					];
			  })
			: Object.values(own);
		this.group = new frappe.ui.FieldGroup({ fields, body: $card.find(".one-shell-form")[0] });
		this.group.make();
		$card.toggleClass("one-shell-columns", !!rows);
		// Frappe marks a section empty while it is drawn, before its values are
		// in and its fields' depends_on can say they show, and a FieldGroup never
		// looks again. So look again once the values are in, and on every change.
		const shown = () => {
			this.group.refresh_dependency();
			this.group.refresh_sections();
		};
		const ready = this.group.set_values(data.values).then(shown);
		for (const field of this.group.fields_list) {
			const own_change = field.df.change;
			field.df.change = (...args) => {
				shown();
				this.check();
				return own_change && own_change(...args);
			};
		}
		this.saves(() => Editor.every(this.group, Object.keys(own)), $card, ready);
		return $card;
	}

	// Save goes in the page head. What the fields hold once they have settled
	// is what "changed" is measured against.
	saves(values, $watch, ready) {
		this.values = values;
		this.snapshot = undefined;
		this.ready = Promise.resolve(ready).then(() => {
			this.snapshot = Editor.same(values());
		});
		this.page.set_primary_action(__("Save"), () => this.save(values()));
		// Ctrl+S on a page calls its save_action; only a form uses its button (desk.js).
		this.page.wrapper[0].save_action = () => this.save(values());
		$watch.on("input change", "input, select, textarea", () => this.check());
	}

	// No save until a form says what it saves.
	unsaved() {
		this.values = null;
		this.set_dirty(false);
		this.page.clear_primary_action();
		this.page.wrapper[0].save_action = null;
		this.page.clear_indicator();
	}

	// Saved against the records as they were loaded, so frappe refuses the
	// save if somebody changed one since (Document.check_if_latest).
	async save(values) {
		this.saving = true;
		const { method, args } = this.saver(values);
		const said = await new Promise((done) =>
			frappe.call({
				method,
				args: { ...args, opened: this.opened },
				freeze: true,
				callback: (r) => done(r.message),
				error: (r) => {
					if (r && r.exc_type === "TimestampMismatchError") this.conflict();
					done(null);
				},
			})
		).finally(() => (this.saving = false));
		if (!said) return;
		this.data = said;
		frappe.show_alert({ message: __("Saved."), indicator: "green" });
		this.set_dirty(false);
		this.$content.empty();
		this.hear(said.opened);
		this.redraw(said);
	}
};
