// The window (onedesk/one_interface/AGENTS.md): every screen in one frame, built from frappe's
// own parts. Nothing here redraws what frappe draws; it places it, and adds
// Back, Forward, Up, Refresh, a search box, a status row and a details pane.
//
// This file is the frame and the one place that decides where anything goes.
// A view says what it has through `window.view({...})`; the files beside this
// one (list.js, form.js) are adapters that say it for frappe's own views.
frappe.provide("onedesk.interface");

$.extend(onedesk.interface, {
	// What the window remembers for each person (the trial, the nav pane's
	// width, each details pane), in frappe's user settings under one name,
	// read from the boot so nothing jumps when a page opens.
	SETTINGS: "One Interface",
	NAV: { min: 180, max: 440, rail: 48, key: "nav", state: "nav_state" },

	settings() {
		if (!onedesk.interface.held) {
			onedesk.interface.held = $.extend(true, {}, frappe.boot.one_interface_held || {});
			frappe.model.user_settings[onedesk.interface.SETTINGS] =
				frappe.model.user_settings[onedesk.interface.SETTINGS] || $.extend(true, {}, onedesk.interface.held);
		}
		return onedesk.interface.held;
	},

	kept(key, fallback) {
		const said = onedesk.interface.settings()[key];
		return said === undefined || said === null ? fallback : said;
	},

	keep(key, value) {
		onedesk.interface.settings()[key] = value;
		return frappe.model.user_settings.save(onedesk.interface.SETTINGS, key, value);
	},

	// The trees modules hang under a list's row in the nav pane (list.js).
	trees: [],

	// The kinds of view on the window, for everybody: each was walked before
	// it joined (onedesk/one_interface/AGENTS.md).
	ON: ["page", "list", "board", "report", "tree", "form", "print", "workspace"],

	covers(kind) {
		return onedesk.interface.ON.includes(kind);
	},

	// An adapter puts one kind of frappe's views on the window. It installs
	// only where the kind is covered, so nothing changes for anybody else.
	adapt(kind, install) {
		if (onedesk.interface.covers(kind)) install();
	},

	// frappe defines some views only when their bundle loads (Kanban v2):
	// `then` is given the class as soon as frappe assigns it. Everybody who
	// waits on one class waits here, so no one's hook takes another's place.
	when(owner, name, then) {
		if (owner[name]) return then(owner[name]);
		const waiting = (onedesk.interface.waiting ||= new WeakMap());
		const names = waiting.get(owner) || {};
		waiting.set(owner, names);
		if (names[name]) return names[name].push(then);
		names[name] = [then];
		Object.defineProperty(owner, name, {
			configurable: true,
			enumerable: true,
			get: () => undefined,
			set: (value) => {
				Object.defineProperty(owner, name, { value, writable: true, configurable: true, enumerable: true });
				const all = names[name];
				delete names[name];
				all.forEach((one) => one(value));
			},
		});
	},

	// The window on screen shows its status (what is here, its paging) in the
	// frame's bottom bar, as a taskbar does; any other window keeps its own,
	// out of sight. Without the bars (a phone) it stays the window's row.
	place_status() {
		const $slot = $(".one-bar-status");
		const current = onedesk.interface.current();
		$slot.children(".one-interface-status").each((_, el) => {
			const win = $(el).data("one-interface");
			if (win && win !== current) win.$status.appendTo(win.$wrapper);
		});
		if (current && $slot.length) current.$status.appendTo($slot);
	},

	// Up from a list, a report or a tree: the home of the app it is in.
	home() {
		const sidebar = frappe.app && frappe.app.sidebar;
		return sidebar && sidebar.current_module && sidebar.open_module(sidebar.current_module);
	},

	of(page, options = {}) {
		if (!page) return null;
		return page.interface || new onedesk.interface.Frame(page, options);
	},

	// A drag along an edge, as a width: `edge` is the handle, `from` reads the
	// width when the drag starts, `to` is told each new one. The pointer's
	// own direction is reversed in a right-to-left page and for a pane whose
	// handle is on its leading side.
	drag(edge, { from, to, done, leading = false, axis = "x" }) {
		$(edge).on("mousedown", (e) => e.preventDefault());
		$(edge).on("pointerdown", (e) => {
			if (e.button !== 0) return;
			const read = (p) => (axis === "y" ? p.clientY : p.clientX);
			const start = read(e);
			const way = (axis === "x" && document.dir === "rtl" ? -1 : 1) * (leading ? -1 : 1);
			let width = 0;
			let px = 0;
			let moved = false;
			let frame = null;
			let last = 0;
			let at = e.timeStamp;
			let speed = 0;
			const paint = () => {
				frame = null;
				to(px);
			};
			const move = (m) => {
				const dx = (read(m) - start) * way;
				if (!moved && Math.abs(dx) < 4) return;
				if (!moved) {
					moved = true;
					width = from();
					edge.setPointerCapture?.(e.pointerId);
					document.body.classList.add("one-interface-dragging");
					document.body.dataset.oneDrag = axis;
				}
				const gone = m.timeStamp - at;
				if (gone > 0) speed = 0.7 * ((dx - last) / gone) + 0.3 * speed;
				last = dx;
				at = m.timeStamp;
				px = width + dx;
				if (frame === null) frame = requestAnimationFrame(paint);
			};
			const up = (u) => {
				document.removeEventListener("pointermove", move);
				document.removeEventListener("pointerup", up);
				document.removeEventListener("pointercancel", up);
				if (!moved) return;
				if (frame !== null) cancelAnimationFrame(frame);
				to(px);
				document.body.classList.remove("one-interface-dragging");
				delete document.body.dataset.oneDrag;
				done && done(px, u.timeStamp - at > 80 ? 0 : speed);
				const swallow = (c) => {
					c.stopImmediatePropagation();
					c.preventDefault();
				};
				document.addEventListener("click", swallow, { capture: true, once: true });
				setTimeout(() => document.removeEventListener("click", swallow, { capture: true }), 0);
			};
			document.addEventListener("pointermove", move);
			document.addEventListener("pointerup", up);
			document.addEventListener("pointercancel", up);
		});
	},

	// Where a released pane is heading: a flick carries on past the pointer.
	aim: (px, speed) => px + speed * 160,
});

onedesk.interface.folds = {
	PARTS: {
		top: { axis: "y", key: "fold:top", full: "--one-bar-height", floor: 0, now: "--one-bar-top" },
		bottom: { axis: "y", leading: true, key: "fold:bottom", full: "--one-bar-height", floor: 0, now: "--one-bar-bottom" },
		dock: { axis: "x", key: "fold:dock", full: "--dock-width", floor: 6, now: "--one-dock-now" },
	},
	HEIGHTS: ".main-section, .dock, .body-sidebar, .sidebar-panel",
	bars: { top: null, bottom: null },

	full(part) {
		return parseFloat(getComputedStyle(document.documentElement).getPropertyValue(part.full)) || 0;
	},

	part(name) {
		return name === "dock" ? $(".dock") : $(`.one-bar[data-at="${name}"]`);
	},

	edge(name) {
		return $(`.one-fold-edge[data-one-fold="${name}"]`);
	},

	paint(name, px) {
		const part = this.PARTS[name];
		const value = Math.max(part.floor, Math.min(this.full(part), px));
		const held = (el) => el.style.setProperty(part.now, `${value}px`);
		this.part(name).each((_, el) => held(el));
		this.edge(name).each((_, el) => held(el));
		if (name !== "dock") this.frame(name, value);
		return value;
	},

	frame(name, px) {
		this.bars[name] = px;
		const body = document.body;
		const gutter = body.classList.contains("dock-pinned") ? parseFloat(getComputedStyle(body).getPropertyValue("--one-frame-gutter")) || 0 : 0;
		body.style.setProperty(`padding-${name}`, `${px + gutter}px`, "important");
		const full = this.full(this.PARTS.top);
		const top = this.bars.top ?? full;
		const bottom = this.bars.bottom ?? full;
		const height = `calc(100dvh - ${top + bottom + 2 * gutter}px)`;
		$(this.HEIGHTS).each((_, el) => {
			el.style.height = height;
		});
		this.edge("dock").each((_, el) => {
			el.style.top = `${top + gutter}px`;
			el.style.bottom = `${bottom + gutter}px`;
		});
	},

	commit() {
		const body = document.body;
		body.classList.remove("one-folds-moving");
		const full = this.full(this.PARTS.top);
		["top", "bottom"].forEach((name) => {
			body.style.setProperty(this.PARTS[name].now, `${this.bars[name] ?? full}px`);
			body.style.removeProperty(`padding-${name}`);
		});
		$(this.HEIGHTS).each((_, el) => {
			el.style.height = "";
		});
		this.edge("dock").each((_, el) => {
			el.style.top = "";
			el.style.bottom = "";
		});
		window.dispatchEvent(new Event("resize"));
	},

	set(name, open) {
		const part = this.PARTS[name];
		this.paint(name, open ? this.full(part) : part.floor);
		this.part(name).prop("inert", !open);
	},

	settle(name, open) {
		if (name !== "dock") $("body").addClass("one-folds-moving");
		this.set(name, open);
		onedesk.interface.keep(this.PARTS[name].key, !open);
		clearTimeout(this.committing);
		this.committing = setTimeout(() => this.commit(), 320);
	},

	setup() {
		if (this.ready || !$(".one-bar").length || !$(".dock").length || frappe.is_mobile()) return;
		this.ready = true;
		Object.entries(this.PARTS).forEach(([name, part]) => {
			const $edge = $(`<div class="one-fold-edge" data-one-fold="${name}" aria-hidden="true"></div>`).appendTo("body");
			const held = onedesk.interface.kept(part.key, false);
			this.set(name, !held);
			let open = !held;
			onedesk.interface.drag($edge[0], {
				axis: part.axis,
				leading: part.leading,
				from: () => {
					this.part(name).prop("inert", false);
					return open ? this.full(part) : part.floor;
				},
				to: (px) => this.paint(name, px),
				done: (px, speed) => {
					open = onedesk.interface.aim(px, speed) > (part.floor + this.full(part)) / 2;
					this.settle(name, open);
				},
			});
			$edge.on("click", () => {
				open = !open;
				this.settle(name, open);
			});
		});
		this.commit();
	},
};

// The nav pane is frappe's sidebar. Its edge folds it when clicked, as
// frappe made it; dragged, it sets frappe's own --sidebar-width.
onedesk.interface.nav = {
	width(px) {
		const { min, max } = onedesk.interface.NAV;
		const value = Math.round(Math.min(max, Math.max(min, px)));
		document.documentElement.style.setProperty("--sidebar-width", `${value}px`);
		return value;
	},

	state: "open",
	fold: "hidden",

	sidebar() {
		return frappe.app && frappe.app.sidebar;
	},

	hold(sidebar) {
		const nav = this;
		const { hides_when_collapsed, open, close } = sidebar;
		sidebar.hides_when_collapsed = function () {
			if (frappe.is_mobile() || nav.state === "open") return hides_when_collapsed.call(this);
			return nav.state === "hidden";
		};
		sidebar.open = function () {
			if (!frappe.is_mobile()) nav.remember("open");
			open.call(this);
		};
		sidebar.close = function () {
			if (!frappe.is_mobile()) nav.remember(nav.fold);
			close.call(this);
		};
	},

	remember(state) {
		this.state = state;
		if (state !== "open") this.fold = state;
		onedesk.interface.keep(onedesk.interface.NAV.state, { state, fold: this.fold });
	},

	show(state) {
		const sidebar = this.sidebar();
		if (!sidebar || this.shown === state) return;
		this.shown = state;
		this.state = state;
		sidebar.sidebar_expanded = state === "open";
		sidebar.apply_expanded_state();
		if (state === "open") sidebar.highlight_active_item();
	},

	live($container, px) {
		const { min, max, rail } = onedesk.interface.NAV;
		const value = Math.max(0, Math.min(max, px));
		const el = $container[0];
		el.style.setProperty("--one-nav-live", `${value}px`);
		el.style.setProperty("--one-nav-ink", Math.max(0, Math.min(1, (value - (rail + min) / 2) / ((min - rail) / 2))));
		this.show(value >= (rail + min) / 2 ? "open" : "rail");
		return value;
	},

	settle($container, px, speed) {
		const { min, max, rail, key } = onedesk.interface.NAV;
		const aim = onedesk.interface.aim(px, speed);
		const state = aim < rail / 2 ? "hidden" : aim < (rail + min) / 2 ? "rail" : "open";
		$container.removeClass("no-transition one-nav-live");
		if (state === "open") onedesk.interface.keep(key, this.width(Math.min(max, Math.max(min, px))));
		this.show(state);
		const sidebar = this.sidebar();
		if (sidebar && !frappe.is_mobile()) sidebar.save_collapsed_state(state !== "open");
		this.remember(state);
		window.setTimeout(() => window.dispatchEvent(new Event("resize")), 320);
	},

	restore(sidebar, $container) {
		const held = onedesk.interface.kept(onedesk.interface.NAV.state, null);
		if (held) {
			this.state = held.state;
			this.fold = held.fold || "hidden";
			if (!sidebar.wrapper) return;
			$container.addClass("no-transition");
			this.shown = null;
			this.show(held.state);
			sidebar.save_collapsed_state(held.state !== "open");
			$container[0].offsetWidth;
			$container.removeClass("no-transition");
			return;
		}
		this.state = sidebar.sidebar_expanded ? "open" : sidebar.hides_when_collapsed() ? "hidden" : "rail";
		this.shown = this.state;
	},

	setup() {
		const kept = onedesk.interface.kept(onedesk.interface.NAV.key, null);
		if (kept) onedesk.interface.nav.width(kept);
		const $container = $(".body-sidebar-container");
		$container.find(".body-sidebar").first().attr("data-tour", "interface-nav");
		onedesk.interface.folds.setup();
		const edge = $container.find(".sidebar-edge")[0];
		if (!edge || edge.one_interface) return;
		edge.one_interface = true;
		const sidebar = this.sidebar();
		if (sidebar && !frappe.is_mobile()) {
			this.hold(sidebar);
			this.restore(sidebar, $container);
		}
		onedesk.interface.drag(edge, {
			from: () => {
				const width = $container.find(".body-sidebar")[0].getBoundingClientRect().width;
				$container[0].style.setProperty("--one-nav-live", `${width}px`);
				$container.addClass("no-transition one-nav-live");
				this.shown = this.state;
				return width;
			},
			to: (px) => this.live($container, px),
			done: (px, speed) => this.settle($container, px, speed),
		});
		$(edge).attr("title", __("Drag to resize, click to fold"));
	},

	// A view's own tree goes under its row in the pane, and only while that
	// view is on screen.
	place() {
		const current = frappe.container && frappe.container.page && frappe.container.page.page;
		const win = current && current.interface;
		$(".one-interface-nav-slot").each((_, el) => {
			if (!win || el !== (win.$slot && win.$slot[0])) $(el).detach();
		});
		$(".one-interface-meters").each((_, el) => {
			if (!win || el !== (win.$meters && win.$meters[0])) $(el).detach();
		});
		const $bottom = win && win.$meters && frappe.app && frappe.app.sidebar && frappe.app.sidebar.wrapper.find(".body-sidebar-bottom");
		if ($bottom && $bottom.length && !$.contains($bottom[0], win.$meters[0])) win.$meters.prependTo($bottom);
		$(".one-interface-foot-action").each((_, el) => {
			if (!win || el !== (win.$foot_action && win.$foot_action[0])) $(el).detach();
		});
		const $foot = win && win.$foot_action && frappe.app && frappe.app.sidebar && frappe.app.sidebar.wrapper.find(".body-sidebar-bottom");
		if ($foot && $foot.length && !$.contains($foot[0], win.$foot_action[0])) win.$foot_action.appendTo($foot);
		$(".one-interface-head-action").each((_, el) => {
			if (!win || el !== (win.$head_action && win.$head_action[0])) $(el).detach();
		});
		const $head = win && win.$head_action && frappe.app && frappe.app.sidebar && frappe.app.sidebar.wrapper.find(".sidebar-header").first();
		if ($head && $head.length && !$.contains($head[0], win.$head_action[0])) {
			const $menu = $head.children(".drop-icon");
			if ($menu.length) win.$head_action.insertBefore($menu);
			else win.$head_action.appendTo($head);
		}
		if (!win || !win.$slot) return;
		const $items = frappe.app && frappe.app.sidebar && frappe.app.sidebar.$sidebar;
		if (!$items || !$items.length) return;
		// A tree of its own (a module's lists) is a section of the rail, before
		// the first section name, not a part of whichever row is lit.
		if (win.tree_alone) {
			const $sections = $items.find(".sidebar-items > .sidebar-item-container").filter((_, el) => $(el).find("> .standard-sidebar-item > .section-break").length);
			// With no section names (OneCalendar's rail) it follows the rows.
			const $rows = $items.find(".sidebar-items").first();
			if ($sections.length) {
				if ($sections.first().prev()[0] !== win.$slot[0]) win.$slot.insertBefore($sections.first());
			} else if (!$.contains(($rows[0] || $items[0]), win.$slot[0])) win.$slot.appendTo($rows.length ? $rows : $items);
			win.$slot.removeClass("one-interface-nav-whole");
			return;
		}
		const said = frappe.app.sidebar.sidebar_items || [];
		const one = said.length === 1 && !(said[0].nested_items || []).length;
		let $at = $items.find(".standard-sidebar-item.active-sidebar").not(".one-interface-nav-slot *").first().closest(".sidebar-item-container");
		// A rail whose one row is this screen (OneCloud's Files, OneMail's
		// Mail) keeps the row, which is what claims the page for the rail, and
		// draws only the tree under it; frappe stops lighting the row once the
		// address carries a query, so it is found by being the only one.
		if (!$at.length && one) $at = $items.find(".sidebar-items > .sidebar-item-container").first();
		if ($at.length) {
			if ($at.next()[0] !== win.$slot[0]) win.$slot.insertAfter($at);
		} else if (!$.contains($items[0], win.$slot[0])) {
			win.$slot.appendTo($items);
		}
		const alone = $at.length && one;
		$items.find(".one-interface-nav-alone").not($at).removeClass("one-interface-nav-alone");
		$at.toggleClass("one-interface-nav-alone", !!alone);
		win.$slot.toggleClass("one-interface-nav-whole", !!alone);
	},
};

onedesk.interface.Frame = class Frame {
	constructor(page, { fit = false } = {}) {
		this.page = page;
		this.fit = !!fit;
		page.interface = this;
		this.handlers = {};
		this.$wrapper = page.wrapper.addClass("one-interface").toggleClass("one-interface-fit", !!fit);
		const $content = (this.$content = this.$wrapper.find(".page-head-content").first());
		const button = (act, icon, label) =>
			frappe.ui.button.html({ variant: "ghost", icon, title: label, attrs: { "data-interface": act, "aria-label": label } });
		this.$nav = $(
			`<div class="one-interface-nav">${button("back", "arrow-left", __("Back"))}${button("forward", "arrow-right", __("Forward"))}${button(
				"up",
				"arrow-up",
				__("Up")
			)}</div>`
		).prependTo($content);
		this.$tools = $(`<div class="one-interface-tools">${button("refresh", "refresh-cw", __("Refresh"))}${button("address", "search", __("Search"))}<div class="one-interface-search" data-tour="interface-search"></div></div>`).insertAfter(
			$content.children(".page-title")
		);
		$(`<div class="one-interface-break"></div>`).insertAfter(this.$tools);
		this.$commands = $(
			`<div class="one-interface-commands"><span class="one-interface-group" data-group="primary"></span><span class="one-interface-group" data-group="own"></span><span class="one-interface-group" data-group="menu"></span></div>`
		).insertBefore($content.children(".standard-items-section"));
		this.groups = {};
		this.$commands.children("[data-group]").each((_, el) => (this.groups[el.dataset.group] = $(el)));
		this.$switch = $(button("details", "panel-right", __("Details pane"))).addClass("one-interface-switch").appendTo($content).hide();
		this.$status = $(
			`<div class="one-interface-status" hidden><span class="one-interface-said"></span><span class="one-interface-more"></span></div>`
		)
			.data("one-interface", this)
			.appendTo(this.$wrapper);
		this.$tools.find("[data-interface=refresh]").hide();
		$content.on("click", "[data-interface]", (e) => {
			e.preventDefault();
			this.act(e.currentTarget.dataset.interface);
		});
		page.$title_area.on("click", (e) => {
			if (!$(e.target).closest("a, button, input, .one-crumb-switch, .one-interface-address").length) this.address();
		});
		this.can({});
	}

	// What a view tells the window, and the only way it tells it. Every part
	// is optional and may be said again (a list knows its count only after it
	// loads); where each part goes is decided here, so every view on the
	// window is laid out alike and changes in one place.
	//
	//   kind      what the view is, for the stylesheet (data-one-view)
	//   primary   its one main command (a list's New): leads the command row
	//   commands  its own commands, after the primary
	//   menu      frappe's … menu ({ $button, dropdown }): last, opening rightwards
	//   controls  what narrows the view (a list's Filter and Sort): before its views
	//   views     its ways of looking (frappe's view switcher, or toggles of its own)
	//   search    { placeholder, on_input, on_key } for the address row's box
	//   steps     its own ‹ › to the one before and after (a form's records): at
	//             the address row's end, away from Back, Forward and Up
	//   row       what it shows across the window under the commands (a form's tabs)
	//   status    what is here, in the status row; `more` beside it (paging)
	//   back, forward, up, refresh, path: what it does for those itself
	//
	// Between groups of commands the window draws a line, as OneCloud does.
	view(parts = {}) {
		const { kind, primary, commands, menu, controls, views, search, steps, row, status, more, ...handlers } = parts;
		if (kind) this.$wrapper.attr("data-one-view", kind);
		if (primary) this.group("primary").append(primary);
		if (commands) this.group("own").empty().append(commands);
		if (menu && menu.$button && menu.$button.length) {
			this.group("menu").append(menu.$button);
			if (menu.dropdown) menu.dropdown.align = "start";
		}
		if (views) {
			if (typeof views.get_views === "function") this.views_of(views);
			else this.ways_slot().append(views);
		}
		if (controls && controls.length) this.views_slot().prepend(controls.addClass("one-interface-filters"));
		if (search) this.search(search);
		if (steps && steps.length) this.$tools.append(steps.addClass("one-interface-steps"));
		if (row && row.length) this.row().empty().append(row);
		if (status !== undefined || more) this.status(status, { more });
		if (Object.keys(handlers).length) {
			this.handle(handlers);
			if ("up" in handlers) this.can({ up: !!handlers.up });
		}
		return this;
	}

	// Held by reference, so a look may place a group elsewhere (Canvas puts
	// a list's New beside its heading and the menu in the address row).
	group(name) {
		return this.groups[name];
	}

	// A row across the window under the commands, for what a view shows over
	// all of itself (a form's tabs), held with the head as the page scrolls.
	row() {
		if (!this.$row) this.$row = $(`<div class="one-interface-row"></div>`).appendTo(this.$content);
		return this.$row;
	}

	// A part of the record panel a view draws itself (an island's own
	// activity), kept here until the panel is made and moved into its tab
	// then (form.js `panel`), so the view may mount before the record loads.
	panel_slot(name) {
		this.panel_parts ||= {};
		if (!this.panel_parts[name]) {
			this.panel_parts[name] = $(`<div class="one-panel-own" data-own="${name}"></div>`);
			if (this.panel_frm) requestAnimationFrame(() => onedesk.interface.panel_refresh(this.panel_frm));
		}
		return this.panel_parts[name];
	}

	// The address box: frappe's breadcrumbs while at rest; clicked, or Ctrl+K,
	// a box to type a place, a record or a command in, answered by frappe's
	// own search bar (`AddressBar`). A view that has paths of its own
	// (OneCloud's folders) is asked first when what is typed has a "/" in it.
	address() {
		if (this.$address) return this.$address.find("input").trigger("focus");
		const $area = this.page.$title_area.addClass("one-interface-typing");
		this.$address = $(`<div class="one-interface-address"><input type="text" spellcheck="false" autocomplete="off"></div>`).appendTo($area);
		const $input = this.$address
			.find("input")
			.attr({ "aria-label": __("Address"), placeholder: __("Go to a place, a record or a command") });
		$input.on("keydown", (e) => {
			const typed = $input.val().trim();
			if (e.key !== "Enter" || !this.handlers.path || !typed.includes("/")) return;
			e.preventDefault();
			e.stopImmediatePropagation();
			Promise.resolve(this.handlers.path(typed)).then((went) => went && this.close_address());
		});
		let leaving = null;
		$input.on("blur", () => (leaving = setTimeout(() => this.close_address(), 200)));
		$input.on("focus", () => clearTimeout(leaving));
		new onedesk.interface.AddressBar(this.$address, $input, () => this.close_address());
		$input.trigger("focus");
	}

	close_address() {
		if (!this.$address) return;
		this.$address.remove();
		this.$address = null;
		this.page.$title_area.removeClass("one-interface-typing");
	}

	// What the view does for Back, Forward, Up and Refresh; anything it does
	// not say is the browser's (Back, Forward) or the breadcrumb's (Up).
	handle(handlers) {
		Object.assign(this.handlers, handlers);
		this.$tools.find("[data-interface=refresh]").toggle(!!this.handlers.refresh && !this.$reload);
		return this;
	}

	// frappe's own reload button, which a list, a report, a board and a tree
	// add with page.add_action_icon("refresh-cw"), goes where the window keeps
	// Refresh, and the window's own Refresh steps aside. The button is
	// frappe's, with its click and its tooltip.
	adopt_reload($button) {
		this.$reload = $button;
		this.$tools.find("[data-interface=refresh]").hide().after($button);
		$button.addClass("one-interface-reload");
		if (!this.page.icon_group.children().length) this.page.icon_group.addClass("hide");
	}

	// frappe's Print on a report (page.add_action_icon("printer")) sits
	// beside the reload in the address row, as a record's print does.
	adopt_print($button) {
		const $reload = this.$tools.find(".one-interface-reload");
		if ($reload.length) $button.insertBefore($reload);
		else this.$tools.find("[data-interface=refresh]").before($button);
		$button.addClass("one-interface-print");
		if (!this.page.icon_group.children().length) this.page.icon_group.addClass("hide");
	}

	// What can be pressed. Back and Forward are the browser's history unless
	// the view keeps its own, so the browser is asked (the Navigation API
	// where it has one); Up is the breadcrumb's unless the view says.
	can({ back, forward, up } = {}) {
		if (up !== undefined) this.up_said = up;
		const history = window.navigation && "canGoBack" in window.navigation ? window.navigation : null;
		const $find = (act) => this.$nav.find(`[data-interface=${act}]`);
		$find("back").prop("disabled", !(back !== undefined ? back : history ? history.canGoBack : true));
		$find("forward").prop("disabled", !(forward !== undefined ? forward : history ? history.canGoForward : true));
		$find("up").prop("disabled", this.up_said === undefined || this.up_said === null ? !this.up_route() : !this.up_said);
		return this;
	}

	up_route() {
		const links = this.page.$title_area ? this.page.$title_area.find(".es-breadcrumbs a[href]").toArray() : [];
		const last = links[links.length - 1];
		return last ? last.getAttribute("href") : null;
	}

	act(name) {
		if (this.handlers[name]) return this.handlers[name]();
		if (name === "back") return window.history.back();
		if (name === "forward") return window.history.forward();
		if (name === "up") {
			const route = this.up_route();
			return route && frappe.set_route(route);
		}
		if (name === "details") return this.toggle_details();
		if (name === "address") return this.address();
	}

	search({ placeholder = "", on_input, on_key } = {}) {
		if (!this.$search) {
			this.$search = onedesk.shell.search(this.$tools.find(".one-interface-search"), { placeholder });
			if (on_input) this.$search.on("input", frappe.utils.debounce(() => on_input(this.$search.val().trim()), 300));
			if (on_key) this.$search.on("keydown", (event) => void on_key(event));
		}
		this.$search.attr("placeholder", placeholder);
		return this.$search;
	}

	status(text, { more = null } = {}) {
		this.$status.prop("hidden", false).find(".one-interface-said").text(text || "");
		if (more) this.$status.find(".one-interface-more").empty().append(more);
		// A view made after the page changed (a form) says its status late.
		if (!$.contains($(".one-bar-status")[0] || document.body, this.$status[0]) && onedesk.interface.current() === this) onedesk.interface.place_status();
		return this.$status;
	}

	// The pane right of the view, its width and whether it is open kept per
	// kind of view. A view that already has a pane of its own there (a form's
	// sidebar) hands it over as `pane`, and it becomes this one: the switch in
	// the command row folds it, its edge drags it as wide as most of the window.
	details({ key, width = 280, pane = null } = {}) {
		if (this.$details) return this.$details;
		this.details_key = `details:${key || "page"}`;
		const kept = onedesk.interface.kept(this.details_key, { open: true, width });
		const $main = this.$wrapper.find(".layout-main").first();
		const $pane = pane
			? pane.addClass("one-interface-details one-interface-details-own")
			: $(`<aside class="one-interface-details" role="complementary"><div class="one-interface-details-body"></div></aside>`).appendTo($main);
		this.$details_pane = $pane;
		this.$details = pane ? $pane : $pane.find(".one-interface-details-body");
		this.details_size = (px) => Math.round(Math.min(Math.max(320, this.$wrapper.width() * 0.6), Math.max(200, px)));
		$pane.css("--one-details-width", `${this.details_size(kept.width || width)}px`);
		this.details_edge();
		this.$switch.show();
		this.show_details(kept.open !== false);
		requestAnimationFrame(() => $pane.addClass("one-interface-details-ready"));
		return this.$details;
	}

	// The pane's edge, dragged to size it. A pane the view rebuilds (frappe
	// empties a form's sidebar when it makes it) is given it back.
	details_edge() {
		const $pane = this.$details_pane;
		if (!$pane || $pane.children(".one-interface-details-edge").length) return;
		const $edge = $(`<div class="one-interface-details-edge"></div>`).prependTo($pane);
		const set = (px) => $pane[0].style.setProperty("--one-details-width", `${px}px`);
		onedesk.interface.drag($edge[0], {
			leading: true,
			from: () => {
				const width = $pane[0].getBoundingClientRect().width;
				$pane.addClass("one-interface-details-live");
				set(width);
				$pane.removeClass("one-interface-details-shut");
				return width;
			},
			to: (px) => set(px < 200 ? Math.max(8, px) : this.details_size(px)),
			done: (px, speed) => {
				const open = onedesk.interface.aim(px, speed) >= 120;
				$pane.removeClass("one-interface-details-live");
				if (open) {
					const width = this.details_size(Math.max(200, px));
					set(width);
					this.remember_details({ width, open: true });
				} else {
					this.remember_details({ open: false });
				}
				this.show_details(open);
				window.setTimeout(() => window.dispatchEvent(new Event("resize")), 320);
			},
		});
	}

	remember_details(change) {
		const kept = onedesk.interface.kept(this.details_key, {});
		onedesk.interface.keep(this.details_key, { ...kept, ...change });
	}

	show_details(open) {
		this.details_open = !!open;
		this.$details_pane.toggleClass("one-interface-details-shut", !open);
		this.$switch.attr("data-state", open ? "on" : null).attr("aria-pressed", open ? "true" : "false");
		this.$wrapper.trigger("one-interface-details", [open]);
	}

	toggle_details() {
		if (!this.$details_pane) return;
		this.show_details(!this.details_open);
		this.remember_details({ open: this.details_open });
	}

	// The view's ways of looking at what is here (OneCloud's Details and
	// Tiles, a list's List, Report, Kanban...), at the command row's far end
	// beside the details switch, where Explorer keeps them.
	views_slot() {
		if (!this.$views) this.$views = $(`<div class="one-interface-views"></div>`).insertBefore(this.$switch);
		return this.$views;
	}

	// The ways of looking themselves, apart from what narrows the view, so a
	// look may put them by the heading (Canvas) and leave Filter where it is.
	ways_slot() {
		if (!this.$ways) this.$ways = $(`<span class="one-interface-ways"></span>`).appendTo(this.views_slot());
		return this.$ways;
	}

	// frappe's view switcher drawn as the window draws views: one toggle per
	// view it offers, from its own list, icons and actions. Its own menu stays,
	// as a chevron after them, for what a view has inside it (saved layouts,
	// kanban boards, saved reports, calendars).
	views_of(select) {
		const views = select.get_views();
		const options = frappe.views.view_modes
			.filter((view) => views[view] && views[view].condition)
			.map((view) => {
				const label = select.label_map[view] || __(view);
				return { value: view, icon: select.icon_map[view] || "list", label, title: label };
			});
		const $slot = this.ways_slot();
		// Said again, the toggles are drawn again; frappe's menu is its own
		// node and is only moved, never removed, so its handlers stay.
		$slot.children(".es-tab-buttons").remove();
		if (options.length > 1) {
			frappe.ui
				.tab_buttons({
					type: "ghost",
					label: __("View"),
					value: select.current_view,
					options,
					on_change: (view) => views[view].action(),
				})
				.appendTo($slot);
		}
		select.$wrapper.addClass("one-interface-variants").appendTo($slot);
		select.$trigger.attr({ title: __("More views"), "aria-label": __("More views"), "data-variant": "ghost" });
	}

	// A container in the nav pane, under this view's row, for a tree of its
	// own (`onedesk.interface.nav.place`).
	nav_slot() {
		if (!this.$slot) this.$slot = $(`<div class="one-interface-nav-slot" role="tree" data-tour="interface-nav"></div>`);
		onedesk.interface.nav.place();
		return this.$slot;
	}
};

// frappe's search bar, answering in the address box rather than its modal:
// the same options, the same `awesomebar_search` hooks, the same filters of
// what One shows. Only where it draws differs.
onedesk.interface.AddressBar = class AddressBar extends frappe.search.AwesomeBar {
	constructor($host, $input, done) {
		super();
		this.options = [];
		this.global_results = [];
		const find = $host.find.bind($host);
		$host.find = (selector) => (selector === "#navbar-search" ? $input : find(selector));
		$host.modal = () => done();
		this.search_modal = $host;
		this.setup_event_listeners($host);
	}
};

// The current page's window, if it has one and the screen is wide enough
// for its address row.
onedesk.interface.current = () => {
	const win = onedesk.interface.here();
	return win && window.innerWidth >= 768 ? win : null;
};

// The current page's window on any screen: a phone's address bar is typed
// into as a desk's is.
onedesk.interface.here = () => {
	const page = frappe.container && frappe.container.page && frappe.container.page.page;
	return (page && page.interface) || null;
};

(() => {
	if (frappe.search.open_awesomebar_from_global_search_shortcut && !frappe.search.one_interface) {
		frappe.search.one_interface = true;
		const theirs = frappe.search.open_awesomebar_from_global_search_shortcut;
		frappe.search.open_awesomebar_from_global_search_shortcut = function (e) {
			const win = onedesk.interface.here();
			if (!win) return theirs.call(this, e);
			win.address();
			return false;
		};
		document.addEventListener(
			"click",
			(e) => {
				const win = e.target.closest && e.target.closest(".navbar-modal-search-mobile") && onedesk.interface.here();
				if (!win) return;
				e.stopPropagation();
				e.preventDefault();
				win.address();
			},
			{ capture: true }
		);
	}
})();

(() => {
	const Page = frappe.ui.Page;
	if (!Page || Object.hasOwn(Page.prototype, "one_interface")) return;
	Page.prototype.one_interface = true;
	const icon = Page.prototype.add_action_icon;
	Page.prototype.add_action_icon = function (name, ...rest) {
		const $button = icon.call(this, name, ...rest);
		if (this.interface && name === "refresh-cw") this.interface.adopt_reload($button);
		if (this.interface && name === "printer") this.interface.adopt_print($button);
		return $button;
	};
})();

(() => {
	if (frappe.ui.make_app_page.one_interface) return;
	const make = frappe.ui.make_app_page;
	frappe.ui.make_app_page = function (opts) {
		const page = make.call(this, opts);
		// A page in a dialog (a record being made) is the dialog's, not a window.
		const in_dialog = opts && opts.parent && $(opts.parent).closest(".modal").length > 0;
		if (page && !in_dialog) onedesk.interface.of(page, { fit: !!opts.one_interface_fit });
		return page;
	};
	frappe.ui.make_app_page.one_interface = true;

	const Sidebar = frappe.ui.Sidebar;
	if (Sidebar && !Object.hasOwn(Sidebar.prototype, "one_interface")) {
		Sidebar.prototype.one_interface = true;
		const highlight = Sidebar.prototype.highlight_active_item;
		Sidebar.prototype.highlight_active_item = function (...args) {
			const said = highlight.apply(this, args);
			onedesk.interface.nav.place();
			return said;
		};
	}
	$(document).on("page-change", () => {
		const current = frappe.container && frappe.container.page && frappe.container.page.page;
		$("body").toggleClass("full-height-page", !!(current && current.interface && current.interface.fit));
		if (current && current.interface) setTimeout(() => current.interface.can(), 0);
		onedesk.interface.nav.place();
		onedesk.interface.place_status();
	});
	$(document).on("app_ready", () => onedesk.interface.nav.setup());
	$(() => setTimeout(() => onedesk.interface.nav.setup(), 0));
})();

