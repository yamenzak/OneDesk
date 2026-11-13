// The window's tree: rows in the nav pane under a view's rail row, drawn as
// the rail's own rows so a screen's folders read as the rail going on.
// OneCloud's folders, OneMail's mailboxes and a module's lists are this one
// tree; a screen hands it rows and is told what was done to them.
//
//   rows   [{ id, label, note, icon, depth, open, active, count, href, title,
//             strong, warn, actions }] in order, as deep as the screen opened them.
//          `note` is a second, quieter line under the label (a mailbox's
//          address).
//          `open` is true or false on a row that holds others and absent
//          on a leaf; `icon` is a lucide name; with an `href` a row opens in
//          a new tab, and a plain click is still the screen's.
//          `section` makes a row a name over the rows after it, drawn as
//          the rail's own section names (OneCalendar's Mine and Workspace).
//          `check` (true or false) puts a box where the icon goes, inked
//          in `color` (a frappe-ui colour); clicking the row ticks it.
//          Without `check`, `color` inks the icon (a folder's colour).
//   heading  a name over the rows, drawn as the rail's own section names
//          (Centers); with `alone` the tree is its own section of the rail,
//          before the section names, rather than under the view's row.
//   pick   (id, event) a row was chosen.
//   check  (id, on) a row's box was ticked or cleared.
//   twist  (id) a row's twisty was clicked; choosing a row never folds it.
//   over   (id, event) something is dragged over a row; true takes it, and
//          the row is lit until the drag leaves or drops.
//   leave  (id) the drag left a row.
//   drop   (id, event) it was dropped there.
//   menu   (id) a row with `actions` was right-clicked or its … clicked;
//          answers frappe.ui.ContextMenu's items ({ label, icon, theme,
//          onclick }). A row without `actions` has no … and keeps the
//          browser's own right-click.
onedesk.interface.Tree = class Tree {
	constructor($host, spec = {}) {
		this.$host = $host.addClass("one-interface-tree").attr("role", "tree");
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
		const section = (label) =>
			`<div class="sidebar-item-container section-item one-interface-tree-heading"><div class="standard-sidebar-item"><span class="item-anchor section-break"><span class="sidebar-item-label">${esc(
				label
			)}</span></span></div></div>`;
		const html = (this.spec.rows || [])
			.map((row) => {
				if (row.section) return section(row.label);
				const holds = row.open === true || row.open === false;
				const twisty = holds
					? `<span class="one-interface-twisty" data-twist role="button" aria-label="${row.open ? __("Collapse") : __("Expand")}">${icon(
							row.open ? "chevron-down" : "chevron-right",
							"xs"
					  )}</span>`
					: `<span class="one-interface-twisty"></span>`;
				const warn = row.warn ? `<span class="one-interface-warn" title="${esc(row.warn)}">${icon("triangle-alert")}</span>` : "";
				const count = row.count ? `<span class="one-interface-count">${esc(String(row.count))}</span>` : "";
				const more = this.spec.menu && row.actions
					? `<span class="one-interface-more" data-more role="button" aria-label="${__("More")}" title="${__("More")}">${icon("ellipsis")}</span>`
					: "";
				const lit = `${row.active ? " active-sidebar" : ""}${row.strong ? " one-interface-strong" : ""}${row.note ? " one-interface-noted" : ""}`;
				const label = row.note
					? `<span class="one-interface-label"><span class="sidebar-item-label">${esc(row.label)}</span><span class="one-interface-note">${esc(
							row.note
					  )}</span></span>`
					: `<span class="sidebar-item-label">${esc(row.label)}</span>`;
				return `<div class="standard-sidebar-item${lit}" role="treeitem" data-id="${esc(row.id)}"${row.actions ? " data-actions" : ""} style="--depth:${cint(row.depth)}"${
					holds ? ` aria-expanded="${row.open}"` : ""
				}${row.active ? ` aria-current="page"` : ""}><a class="item-anchor" href="${esc(row.href || "#")}" title="${esc(
					row.title || row.label
				)}">${twisty}<span class="sidebar-item-icon"${
					row.color && row.check === undefined ? ` style="color: var(--ink-${esc(row.color)}-7)"` : ""
				}>${
					row.check === undefined
						? icon(row.icon)
						: `<input type="checkbox" class="one-interface-check" data-check aria-label="${esc(row.label)}"${row.check ? " checked" : ""}${
								row.color ? ` style="--one-check: var(--ink-${esc(row.color)}-7)"` : ""
						  }>`
				}</span>${label}${warn}${count}${more}</a></div>`;
			})
			.join("");
		const heading = this.spec.heading ? section(this.spec.heading) : "";
		this.$host.html(heading + html);
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
			.on("click", "[data-check]", (e) => {
				e.stopPropagation();
				if (this.spec.check) this.spec.check(id(e), e.currentTarget.checked);
			})
			.on("click", ".item-anchor", (e) => {
				if ($(e.currentTarget).attr("href") !== "#" && (e.ctrlKey || e.metaKey || e.shiftKey)) return;
				e.preventDefault();
				const $box = $(e.currentTarget).find("[data-check]");
				if ($box.length) {
					$box.prop("checked", !$box.prop("checked"));
					if (this.spec.check) this.spec.check(id(e), $box.prop("checked"));
					return;
				}
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
			on_close: () => this.$host.find(".one-interface-menu").removeClass("one-interface-menu"),
			options: () => (this.menu_id && this.spec.menu(this.menu_id)) || [],
		});
	}

	mark($row) {
		this.menu_id = $row.attr("data-id") || null;
		this.$host.find(".one-interface-menu").removeClass("one-interface-menu");
		$row.addClass("one-interface-menu");
	}

	open_menu($row, x, y) {
		this.mark($row);
		this.menu.open_at(x, y);
	}

	light(row) {
		this.$host.find(".one-interface-drop").not(row).removeClass("one-interface-drop");
		if (row) $(row).addClass("one-interface-drop");
	}
};

// This view's tree, in the nav pane under its row.
onedesk.interface.Frame.prototype.tree = function (spec) {
	if (spec.alone !== undefined) this.tree_alone = !!spec.alone;
	if (!this._tree) this._tree = new onedesk.interface.Tree(this.nav_slot(), spec);
	else this._tree.set(spec);
	return this._tree;
};

// How full something is, at the foot of the nav pane while this view is on
// screen (OneCloud's storage and database): [{ label, used, limit, said,
// near, over }], frappe's own progress bar each. With no limit the size is
// said with no bar.
onedesk.interface.Frame.prototype.meters = function (rows) {
	if (!this.$meters) this.$meters = $(`<div class="one-interface-meters"></div>`);
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
	onedesk.interface.nav.place();
	return this;
};

// A button at the end of the rail's head while this view is on screen, for
// what adds to the rail itself (OneMail's Connect Mailbox): { icon, title,
// click }.
onedesk.interface.Frame.prototype.head_action = function ({ icon, title, click }) {
	if (!this.$head_action) {
		this.$head_action = $(
			frappe.ui.button.html({ variant: "ghost", icon, title, attrs: { "aria-label": title } })
		)
			.addClass("one-interface-head-action")
			.on("click", (e) => {
				e.preventDefault();
				e.stopPropagation();
				click();
			});
	}
	onedesk.interface.nav.place();
	return this;
};

// A module's foot, drawn here for every module's rail and nowhere else
// (docs/READY.md, mechanism 5): Help, the tour of the screen it is on and the
// version, which has a dot until its reader has seen it and opens What's New
// (UpdateCenter). A module's settings are in the top bar's tray
// (onedesk.centers.tray). On a phone the same parts end the rail's drawer.
onedesk.interface.foot = {
	/** The module whose rail is on screen, by its name (the registry's app
	 * whose `sidebar` it is), or null. */
	module() {
		const sidebar = frappe.app && frappe.app.sidebar && frappe.app.sidebar.current_module;
		const found = sidebar && Object.values(frappe.boot.one_names || {}).find((one) => one.sidebar === sidebar);
		return found ? found.name : null;
	},

	/** What the foot holds for a module: Help, the tour and its version. */
	parts(module) {
		const said = (frappe.boot.one_versions || {})[module];
		return {
			help: { icon: "circle-question-mark", name: __("Help"), aria: __("{0} Help", [module]), click: () => onedesk.centers.open("help", { module }) },
			tour: { icon: "circle-play", name: __("Take the Tour"), aria: __("Take the Tour of This Screen"), click: () => onedesk.tour.run(module) },
			version: said ? { text: said.version, aria: __("What's New in {0}", [module]), unseen: () => !!said.unseen, click: () => onedesk.centers.open("updates", { module }) } : null,
		};
	},

	/** The foot at the bottom of a window's rail, as the rail's own rows are. */
	draw(win, module) {
		const { help, tour, version } = this.parts(module);
		win.$foot_action = $(
			`<div class="one-interface-foot-action one-interface-foot-action--icons" data-tour="interface-foot"><div class="standard-sidebar-item"><a class="item-anchor" href="#" role="button"><span class="sidebar-item-icon">${frappe.utils.icon(
				help.icon,
				"sm"
			)}</span><span class="sidebar-item-label"></span></a></div></div>`
		);
		win.$foot_action.find(".sidebar-item-label").text(help.name);
		win.$foot_action
			.find(".item-anchor")
			.attr({ title: help.name, "aria-label": help.aria })
			.on("click", (e) => {
				e.preventDefault();
				help.click();
			});
		const $row = win.$foot_action.find(".standard-sidebar-item");
		$(`<button type="button" class="one-interface-foot-help" data-tour="interface-tour"></button>`)
			.attr({ title: tour.name, "aria-label": tour.aria })
			.html(frappe.utils.icon(tour.icon, "sm"))
			.on("click", tour.click)
			.appendTo($row);
		if (!version) return;
		const $chip = $(`<button type="button" class="one-interface-foot-version"></button>`)
			.attr({ title: __("What's New"), "aria-label": version.aria })
			.text(version.text)
			.on("click", version.click)
			.appendTo($row);
		const dot = () => $chip.toggleClass("one-interface-foot-version--unseen", version.unseen());
		dot();
		$(document).on("one-version-seen", (_e, seen) => seen === module && dot());
	},

	/** The same parts at the end of the rail's drawer on a phone. */
	drawer($into, module) {
		const { help, tour, version } = this.parts(module);
		const $foot = $(`<div class="one-drawer-foot"></div>`).appendTo($into);
		frappe.ui.button({ icon: help.icon, label: help.name, variant: "ghost", onclick: help.click }).attr("aria-label", help.aria).appendTo($foot);
		frappe.ui.button({ icon: tour.icon, variant: "ghost", title: tour.name, onclick: tour.click }).appendTo($foot);
		if (!version) return;
		frappe.ui
			.button({ label: version.text, variant: "ghost", title: version.aria, css_class: `one-drawer-version${version.unseen() ? " one-drawer-unseen" : ""}`, onclick: version.click })
			.appendTo($foot);
	},
};

$(document).on("page-change", () =>
	setTimeout(() => {
		const win = onedesk.interface.current();
		const module = onedesk.interface.foot.module();
		if (!win || win.$foot_action || !module) return;
		onedesk.interface.foot.draw(win, module);
		onedesk.interface.nav.place();
	}, 0)
);
