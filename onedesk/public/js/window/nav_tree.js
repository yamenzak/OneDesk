// The window's tree: rows in the nav pane under a view's rail row, drawn as
// the rail's own rows so a screen's folders read as the rail going on.
// OneCloud's folders, OneMail's mailboxes and Masters' kinds are this one
// tree; a screen hands it rows and is told what was done to them.
//
//   rows   [{ id, label, note, icon, depth, open, active, count, href, title,
//             strong, warn, actions }] in order, as deep as the screen opened them.
//          `note` is a second, quieter line under the label (a mailbox's
//          address).
//          `open` is true or false on a row that holds others and absent
//          on a leaf; `icon` is a lucide name; with an `href` a row opens in
//          a new tab, and a plain click is still the screen's.
//   pick   (id, event) a row was chosen.
//   twist  (id) a row's twisty was clicked; choosing a row never folds it.
//   over   (id, event) something is dragged over a row; true takes it, and
//          the row is lit until the drag leaves or drops.
//   leave  (id) the drag left a row.
//   drop   (id, event) it was dropped there.
//   menu   (id) a row with `actions` was right-clicked or its … clicked;
//          answers frappe.ui.ContextMenu's items ({ label, icon, theme,
//          onclick }). A row without `actions` has no … and keeps the
//          browser's own right-click.
onedesk.window.Tree = class Tree {
	constructor($host, spec = {}) {
		this.$host = $host.addClass("one-window-tree").attr("role", "tree");
		this.spec = {};
		this.bind();
		this.set(spec);
	}

	set(spec) {
		Object.assign(this.spec, spec);
		if (this.spec.menu && !this.menu) this.make_menu();
		if (spec.label !== undefined) this.$host.attr("aria-label", spec.label);
		this.draw();
		return this;
	}

	draw() {
		const esc = frappe.utils.escape_html;
		const icon = (name, size = "sm") => (name ? frappe.utils.icon(name, size) : "");
		const html = (this.spec.rows || [])
			.map((row) => {
				const holds = row.open === true || row.open === false;
				const twisty = holds
					? `<span class="one-window-twisty" data-twist role="button" aria-label="${row.open ? __("Collapse") : __("Expand")}">${icon(
							row.open ? "chevron-down" : "chevron-right",
							"xs"
					  )}</span>`
					: `<span class="one-window-twisty"></span>`;
				const warn = row.warn ? `<span class="one-window-warn" title="${esc(row.warn)}">${icon("triangle-alert")}</span>` : "";
				const count = row.count ? `<span class="one-window-count">${esc(String(row.count))}</span>` : "";
				const more = this.spec.menu && row.actions
					? `<span class="one-window-more" data-more role="button" aria-label="${__("More")}" title="${__("More")}">${icon("ellipsis")}</span>`
					: "";
				const lit = `${row.active ? " active-sidebar" : ""}${row.strong ? " one-window-strong" : ""}${row.note ? " one-window-noted" : ""}`;
				const label = row.note
					? `<span class="one-window-label"><span class="sidebar-item-label">${esc(row.label)}</span><span class="one-window-note">${esc(
							row.note
					  )}</span></span>`
					: `<span class="sidebar-item-label">${esc(row.label)}</span>`;
				return `<div class="standard-sidebar-item${lit}" role="treeitem" data-id="${esc(row.id)}"${row.actions ? " data-actions" : ""} style="--depth:${cint(row.depth)}"${
					holds ? ` aria-expanded="${row.open}"` : ""
				}${row.active ? ` aria-current="page"` : ""}><a class="item-anchor" href="${esc(row.href || "#")}" title="${esc(
					row.title || row.label
				)}">${twisty}<span class="sidebar-item-icon">${icon(row.icon)}</span>${label}${warn}${count}${more}</a></div>`;
			})
			.join("");
		this.$host.html(html);
	}

	bind() {
		const id = (e) => $(e.currentTarget).closest("[data-id]").attr("data-id");
		this.$host
			.on("contextmenu", "[data-id]:not([data-actions])", (e) => e.stopImmediatePropagation())
			.on("click", "[data-twist]", (e) => {
				e.preventDefault();
				e.stopPropagation();
				if (this.spec.twist) this.spec.twist(id(e));
			})
			.on("click", "[data-more]", (e) => {
				e.preventDefault();
				e.stopPropagation();
				const box = e.currentTarget.getBoundingClientRect();
				this.open_menu($(e.currentTarget).closest("[data-id]"), box.left, box.bottom + 4);
			})
			.on("click", ".item-anchor", (e) => {
				if ($(e.currentTarget).attr("href") !== "#" && (e.ctrlKey || e.metaKey || e.shiftKey)) return;
				e.preventDefault();
				if (this.spec.pick) this.spec.pick(id(e), e);
			})
			.on("dragover", "[data-id]", (e) => {
				if (!this.spec.over || !this.spec.over(id(e), e.originalEvent)) return this.light(null);
				e.preventDefault();
				this.light(e.currentTarget);
			})
			.on("dragleave", "[data-id]", (e) => {
				if (e.currentTarget.contains(e.originalEvent.relatedTarget)) return;
				this.light(null);
				if (this.spec.leave) this.spec.leave(id(e));
			})
			.on("drop", "[data-id]", (e) => {
				this.light(null);
				if (!this.spec.drop) return;
				e.preventDefault();
				this.spec.drop(id(e), e.originalEvent);
			});
	}

	// frappe's own right-click menu, for the row under the pointer, which is
	// lit while it is open. A row's … opens the same menu under it.
	make_menu() {
		this.menu = new frappe.ui.ContextMenu({
			target: this.$host,
			on_open: (e) => this.mark($(e.target).closest("[data-id]")),
			on_close: () => this.$host.find(".one-window-menu").removeClass("one-window-menu"),
			options: () => (this.menu_id && this.spec.menu(this.menu_id)) || [],
		});
	}

	mark($row) {
		this.menu_id = $row.attr("data-id") || null;
		this.$host.find(".one-window-menu").removeClass("one-window-menu");
		$row.addClass("one-window-menu");
	}

	open_menu($row, x, y) {
		this.mark($row);
		this.menu.open_at(x, y);
	}

	light(row) {
		this.$host.find(".one-window-drop").not(row).removeClass("one-window-drop");
		if (row) $(row).addClass("one-window-drop");
	}
};

// This view's tree, in the nav pane under its row.
onedesk.window.Window.prototype.tree = function (spec) {
	if (!this._tree) this._tree = new onedesk.window.Tree(this.nav_slot(), spec);
	else this._tree.set(spec);
	return this._tree;
};

// How full something is, at the foot of the nav pane while this view is on
// screen (OneCloud's storage and database): [{ label, used, limit, said,
// near, over }], frappe's own progress bar each. With no limit the size is
// said with no bar.
onedesk.window.Window.prototype.meters = function (rows) {
	if (!this.$meters) this.$meters = $(`<div class="one-window-meters"></div>`);
	const html = (rows || []).map((row) =>
		frappe.ui.progress.html({
			label: row.label,
			value: row.limit ? Math.min(100, Math.round((100 * row.used) / row.limit)) : 0,
			hint: () => row.said,
			size: "md",
			css_class: [row.over ? "one-meter-over" : row.near ? "one-meter-near" : "", row.limit ? "" : "one-meter-free"].filter(Boolean).join(" "),
		})
	);
	this.$meters.html(html.join(""));
	onedesk.window.nav.place();
	return this;
};

// A button at the end of the rail's head while this view is on screen, for
// what adds to the rail itself (OneMail's Connect Mailbox): { icon, title,
// click }.
onedesk.window.Window.prototype.head_action = function ({ icon, title, click }) {
	if (!this.$head_action) {
		this.$head_action = $(
			frappe.ui.button.html({ variant: "ghost", icon, title, attrs: { "aria-label": title } })
		)
			.addClass("one-window-head-action")
			.on("click", (e) => {
				e.preventDefault();
				e.stopPropagation();
				click();
			});
	}
	onedesk.window.nav.place();
	return this;
};

// A row at the foot of the rail while this view is on screen, drawn as the
// rail's own rows are, for where the view is set up (OneMail's Settings):
// { icon, label, click }.
// `version` puts the module's version at the row's end, with a dot until its
// reader has seen it, opening What's New (public/js/whats_new.js).
onedesk.window.Window.prototype.foot_action = function ({ icon, label, click, version = null }) {
	if (!this.$foot_action) {
		const esc = frappe.utils.escape_html;
		this.$foot_action = $(
			`<div class="one-window-foot-action"><div class="standard-sidebar-item"><a class="item-anchor" href="#" role="button"><span class="sidebar-item-icon">${frappe.utils.icon(
				icon,
				"sm"
			)}</span><span class="sidebar-item-label">${esc(label)}</span></a></div></div>`
		).on("click", ".item-anchor", (e) => {
			e.preventDefault();
			click();
		});
		if (version) this.foot_version(version);
	}
	onedesk.window.nav.place();
	return this;
};

onedesk.window.Window.prototype.foot_version = function ({ module }) {
	const said = (frappe.boot.one_versions || {})[module];
	if (!said) return;
	const $chip = $(`<button type="button" class="one-window-foot-version"></button>`)
		.attr({ title: __("What's New"), "aria-label": __("What's New in {0}", [module]) })
		.text(said.version)
		.on("click", () => onedesk.whats_new.open(module))
		.appendTo(this.$foot_action.find(".standard-sidebar-item"));
	const dot = () => $chip.toggleClass("one-window-foot-version--unseen", !!said.unseen);
	dot();
	$(document).on("one-version-seen", (_e, seen) => seen === module && dot());
};
