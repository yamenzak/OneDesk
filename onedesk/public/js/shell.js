// The shell every page of ours is built in (docs/SHELL.md). A page composes
// these parts rather than drawing its own, so every page of One looks like one
// product and like the desk it sits in:
//
// - the head is frappe's page head: the title, the breadcrumb, the indicator,
//   Save as the primary action with Ctrl+S, the buttons and the menu;
// - the body is a column (the desk form's width), wide (a table's width), or
//   panes side by side, fitted to the window, for a list beside what it opens;
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
	// `hide_sidebar` is for a page whose panes are its own sidebar: OneMail's
	// mailboxes, OneCloud's tree.
	page(wrapper, title, { hide_sidebar = false } = {}) {
		const page = frappe.ui.make_app_page({ parent: wrapper, title, single_column: true, hide_sidebar });
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

	// Panes side by side, fitted to the window once for every page that has
	// them: a list beside what it opens, or a column of choices beside what they
	// choose. Each is `{ key, width }`, a width in pixels or none for the rest;
	// a rule divides them, and nothing boxes them. A pane may be hidden (its
	// `data-pane`) and the others close up. `fit: false` is for panes inside
	// something that sizes itself: OneCloud's window, or a record's tab.
	// Returns each pane by key.
	panes($into, panes, { fit = true } = {}) {
		const $panes = $(`<div class="one-shell-panes${fit ? "" : " one-shell-panes-inset"}"></div>`);
		const found = {};
		for (const one of panes) {
			found[one.key] = $(`<div class="one-shell-pane" data-pane="${one.key}"></div>`)
				.css("flex", one.width ? `0 0 ${one.width}px` : "1 1 0")
				.appendTo($panes);
		}
		$into.empty().append($panes);
		if (fit) onedesk.shell.fit($panes);
		return found;
	},

	// A pane's own head: what switches or narrows what the pane shows, above
	// it, on a rule.
	pane_head($pane, html) {
		return $(`<div class="one-shell-pane-head">${html || ""}</div>`).prependTo($pane);
	},

	// As tall as the window leaves it, from where it starts down to the bottom,
	// and again when the window changes. The one place a page is sized to the
	// window.
	fit($el) {
		const size = () => {
			if (!$el.is(":visible") || window.innerWidth < 768) return $el.css("height", "");
			const top = $el[0].getBoundingClientRect().top + window.scrollY;
			$el.css("height", `${Math.max(window.innerHeight - top, 420)}px`);
		};
		requestAnimationFrame(size);
		$(window).on("resize", frappe.utils.debounce(size, 100));
		$(document).on("page-change", () => setTimeout(size, 50));
	},

	// The page head is a breadcrumb in v17, so a page's name goes there, and
	// to the browser tab. `route` is where the name leads, when that is not
	// this page: a record's calendar leads back to the record.
	name(label, { route = null } = {}) {
		frappe.breadcrumbs.add({ type: "Custom", label: frappe.utils.escape_html(label), route: route || frappe.get_route_str() });
		frappe.utils.set_title(label);
		// OneAI's panel names where the reader is by the page's title, which the
		// router's change came before; tell it again now that it is right.
		if (onedesk.oneai && onedesk.oneai.panel) onedesk.oneai.panel.moved(onedesk.oneai.where());
	},

	button(label, attrs = {}, variant = "subtle", icon = null, theme = null) {
		return frappe.ui.button.html({ label, attrs, variant, icon, theme: theme || undefined });
	},

	// One part of a page: a heading and what it holds, divided from the next
	// by a rule, the way a record's sections are. `aside` goes beside the
	// heading: a count, a badge.
	section(title, body, note, aside = "") {
		const esc = frappe.utils.escape_html;
		return `<div class="one-shell-section">${title ? `<div class="one-shell-section-title">${esc(title)}${aside}</div>` : ""}${
			note ? `<div class="one-shell-quiet one-shell-note">${esc(note)}</div>` : ""
		}${body}</div>`;
	},

	// A row of a list, as frappe-ui's ListRow is: what it is (`title`, which may
	// carry badges), a line under it (`sub`), a quieter one (`quiet`), and on
	// the right what it says in passing (`meta`: a date, a count) and its
	// actions. `lead` goes before it all: a tick, an avatar. `link` makes the
	// whole row the target, with the list-row hover, and `attrs` names a row
	// that is not one; `href` makes it a link to another page. `active` is the
	// row open beside the list, `unread` one not yet opened, as in a mailbox,
	// and `picked` one ticked for what is done to several at once.
	row({
		title = "",
		sub = "",
		quiet = "",
		meta = "",
		actions = "",
		lead = "",
		link = null,
		href = null,
		attrs = {},
		css = "",
		active = false,
		unread = false,
		picked = false,
	} = {}) {
		const esc = frappe.utils.escape_html;
		const named = (pairs) => Object.entries(pairs || {}).map(([key, value]) => ` ${key}="${esc(value)}"`).join("");
		attrs = named(attrs) + (link ? named(link) + ' tabindex="0"' : "") + (href ? ` href="${esc(href)}"` : "");
		const states = [link || href ? "one-shell-row-link" : "", active ? "is-active" : "", unread ? "is-unread" : "", picked ? "is-picked" : "", css].filter(Boolean);
		const chevron = link && !active && !unread && !meta ? `<span class="one-shell-chevron">${frappe.utils.icon("chevron-right", "sm")}</span>` : "";
		const tag = href ? "a" : "div";
		return `<${tag} class="one-shell-row${states.length ? ` ${states.join(" ")}` : ""}"${attrs}>
			${lead ? `<div class="one-shell-row-lead">${lead}</div>` : ""}
			<div class="one-shell-row-main">${title ? `<div class="one-shell-row-title">${title}</div>` : ""}${
				sub ? `<div class="one-shell-row-sub">${sub}</div>` : ""
			}${quiet ? `<div class="one-shell-quiet one-shell-row-quiet">${quiet}</div>` : ""}</div>
			${meta ? `<div class="one-shell-row-meta">${meta}</div>` : ""}
			${actions || chevron ? `<div class="one-shell-row-actions">${actions}${chevron}</div>` : ""}
		</${tag}>`;
	},

	// Rows, as one list.
	list(rows) {
		return `<div class="one-shell-list">${rows}</div>`;
	},

	actions(html) {
		return `<div class="one-shell-actions">${html}</div>`;
	},

	// Nothing to show: frappe's own empty state, sized for a section rather
	// than a whole page.
	empty(title, description, { icon = null } = {}) {
		return frappe.ui.empty_state.html({ title, description, icon: icon || undefined, css_class: "one-shell-empty" });
	},

	quiet(text) {
		return `<div class="one-shell-quiet">${frappe.utils.escape_html(text)}</div>`;
	},

	// Somebody else saved what is open here. One title and one action is
	// frappe-ui's row alert: Refresh on the right, a ghost button in the
	// alert's own colour (Alert.vue). A page, a record and a record it links
	// to all say it this way.
	changed(title, refresh, css_class = "") {
		const $refresh = $(onedesk.shell.button(__("Refresh"), {}, "ghost")).on("click", refresh);
		return $(
			frappe.ui.alert({
				title,
				theme: "yellow",
				footer: $refresh,
				css_class: `one-shell-alert-row ${css_class}`.trim(),
			})
		);
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
		onedesk.shell
			.changed(__("This form has been modified after you have loaded it"), () => this.refresh({ fresh: true }), "one-shell-conflict")
			.prependTo(this.$content);
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
