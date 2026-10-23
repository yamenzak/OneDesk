// The window (docs/WINDOW.md): every screen in one frame, built from frappe's
// own parts. Nothing here redraws what frappe draws; it places it, and adds
// Back, Forward, Up, Refresh, a search box, a status row and a details pane.
//
// This file is the frame and the one place that decides where anything goes.
// A view says what it has through `window.view({...})`; the files beside this
// one (list.js, form.js) are adapters that say it for frappe's own views.
frappe.provide("onedesk.window");

$.extend(onedesk.window, {
	// What the window remembers for each person (the trial, the nav pane's
	// width, each details pane), in frappe's user settings under one name,
	// read from the boot so nothing jumps when a page opens.
	SETTINGS: "One Window",
	NAV: { min: 180, max: 440, key: "nav" },

	settings() {
		if (!onedesk.window.held) {
			onedesk.window.held = $.extend(true, {}, frappe.boot.one_window || {});
			frappe.model.user_settings[onedesk.window.SETTINGS] =
				frappe.model.user_settings[onedesk.window.SETTINGS] || $.extend(true, {}, onedesk.window.held);
		}
		return onedesk.window.held;
	},

	kept(key, fallback) {
		const said = onedesk.window.settings()[key];
		return said === undefined || said === null ? fallback : said;
	},

	keep(key, value) {
		onedesk.window.settings()[key] = value;
		return frappe.model.user_settings.save(onedesk.window.SETTINGS, key, value);
	},

	trial() {
		return !!onedesk.window.kept("trial", false);
	},

	set_trial(on) {
		onedesk.window.keep("trial", !!on).then(() => window.location.reload());
	},

	// Which kinds of view are on the window: a page that asks for it always,
	// the rest while the trial is on. A kind leaves the trial by moving from
	// TRIAL to ON, and that is the whole of it.
	ON: ["page"],
	TRIAL: ["list", "board", "report", "tree", "form", "print", "workspace"],

	covers(kind) {
		return onedesk.window.ON.includes(kind) || (onedesk.window.trial() && onedesk.window.TRIAL.includes(kind));
	},

	// An adapter puts one kind of frappe's views on the window. It installs
	// only where the kind is covered, so nothing changes for anybody else.
	adapt(kind, install) {
		if (onedesk.window.covers(kind)) install();
	},

	// frappe defines some views only when their bundle loads (Kanban v2):
	// `then` is given the class as soon as frappe assigns it.
	when(owner, name, then) {
		if (owner[name]) return then(owner[name]);
		Object.defineProperty(owner, name, {
			configurable: true,
			enumerable: true,
			get: () => undefined,
			set: (value) => {
				Object.defineProperty(owner, name, { value, writable: true, configurable: true, enumerable: true });
				then(value);
			},
		});
	},

	// The window on screen shows its status (what is here, its paging) in the
	// frame's bottom bar, as a taskbar does; any other window keeps its own,
	// out of sight. Without the bars (a phone) it stays the window's row.
	place_status() {
		const $slot = $(".one-bar-status");
		const current = onedesk.window.current();
		$slot.children(".one-window-status").each((_, el) => {
			const win = $(el).data("one-window");
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
		return page.window || new onedesk.window.Window(page, options);
	},

	// A drag along an edge, as a width: `edge` is the handle, `from` reads the
	// width when the drag starts, `to` is told each new one. The pointer's
	// own direction is reversed in a right-to-left page and for a pane whose
	// handle is on its leading side.
	drag(edge, { from, to, done, leading = false }) {
		$(edge).on("pointerdown", (e) => {
			if (e.button !== 0) return;
			const start = e.clientX;
			const width = from();
			const way = (document.dir === "rtl" ? -1 : 1) * (leading ? -1 : 1);
			let moved = false;
			const move = (m) => {
				const dx = (m.clientX - start) * way;
				if (!moved && Math.abs(dx) < 4) return;
				moved = true;
				document.body.classList.add("one-window-dragging");
				to(width + dx);
			};
			const up = () => {
				document.removeEventListener("pointermove", move);
				document.removeEventListener("pointerup", up);
				document.body.classList.remove("one-window-dragging");
				if (!moved) return;
				done && done();
				const swallow = (c) => {
					c.stopImmediatePropagation();
					c.preventDefault();
				};
				document.addEventListener("click", swallow, { capture: true, once: true });
				setTimeout(() => document.removeEventListener("click", swallow, { capture: true }), 0);
			};
			document.addEventListener("pointermove", move);
			document.addEventListener("pointerup", up);
		});
	},
});

// The nav pane is frappe's sidebar. Its edge folds it when clicked, as
// frappe made it; dragged, it sets frappe's own --sidebar-width.
onedesk.window.nav = {
	width(px) {
		const { min, max } = onedesk.window.NAV;
		const value = Math.round(Math.min(max, Math.max(min, px)));
		document.documentElement.style.setProperty("--sidebar-width", `${value}px`);
		return value;
	},

	setup() {
		const kept = onedesk.window.kept(onedesk.window.NAV.key, null);
		if (kept) onedesk.window.nav.width(kept);
		const $container = $(".body-sidebar-container");
		const edge = $container.find(".sidebar-edge")[0];
		if (!edge || edge.one_window) return;
		edge.one_window = true;
		let now = null;
		onedesk.window.drag(edge, {
			from: () => {
				$container.addClass("no-transition");
				return $container.find(".body-sidebar")[0].getBoundingClientRect().width;
			},
			to: (px) => {
				if (!$container.hasClass("expanded")) return;
				now = onedesk.window.nav.width(px);
			},
			done: () => {
				$container.removeClass("no-transition");
				if (now) onedesk.window.keep(onedesk.window.NAV.key, now);
			},
		});
		$(edge).attr("title", __("Drag to resize, click to fold"));
	},

	// A view's own tree goes under its row in the pane, and only while that
	// view is on screen.
	place() {
		const current = frappe.container && frappe.container.page && frappe.container.page.page;
		const win = current && current.window;
		$(".one-window-nav-slot").each((_, el) => {
			if (!win || el !== (win.$slot && win.$slot[0])) $(el).detach();
		});
		if (!win || !win.$slot) return;
		const $items = frappe.app && frappe.app.sidebar && frappe.app.sidebar.$sidebar;
		if (!$items || !$items.length) return;
		const $at = $items.find(".standard-sidebar-item.active-sidebar").first().closest(".sidebar-item-container");
		if ($at.length) {
			if ($at.next()[0] !== win.$slot[0]) win.$slot.insertAfter($at);
		} else if (!$.contains($items[0], win.$slot[0])) {
			win.$slot.appendTo($items);
		}
	},
};

onedesk.window.Window = class Window {
	constructor(page, { fit = false } = {}) {
		this.page = page;
		this.fit = !!fit;
		page.window = this;
		this.handlers = {};
		this.$wrapper = page.wrapper.addClass("one-window").toggleClass("one-window-fit", !!fit);
		const $content = this.$wrapper.find(".page-head-content").first();
		const button = (act, icon, label) =>
			frappe.ui.button.html({ variant: "ghost", icon, title: label, attrs: { "data-window": act, "aria-label": label } });
		this.$nav = $(
			`<div class="one-window-nav">${button("back", "arrow-left", __("Back"))}${button("forward", "arrow-right", __("Forward"))}${button(
				"up",
				"arrow-up",
				__("Up")
			)}</div>`
		).prependTo($content);
		this.$tools = $(`<div class="one-window-tools">${button("refresh", "refresh-cw", __("Refresh"))}<div class="one-window-search"></div></div>`).insertAfter(
			$content.children(".page-title")
		);
		$(`<div class="one-window-break"></div>`).insertAfter(this.$tools);
		this.$commands = $(
			`<div class="one-window-commands"><span class="one-window-group" data-group="primary"></span><span class="one-window-group" data-group="own"></span><span class="one-window-group" data-group="menu"></span></div>`
		).insertBefore($content.children(".standard-items-section"));
		this.$switch = $(button("details", "panel-right", __("Details pane"))).addClass("one-window-switch").appendTo($content).hide();
		this.$status = $(
			`<div class="one-window-status" hidden><span class="one-window-said"></span><span class="one-window-more"></span></div>`
		)
			.data("one-window", this)
			.appendTo(this.$wrapper);
		this.$tools.find("[data-window=refresh]").hide();
		$content.on("click", "[data-window]", (e) => {
			e.preventDefault();
			this.act(e.currentTarget.dataset.window);
		});
		page.$title_area.on("click", (e) => {
			if (!$(e.target).closest("a, button, input, .one-crumb-switch, .one-window-address").length) this.address();
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
	//   status    what is here, in the status row; `more` beside it (paging)
	//   back, forward, up, refresh, path: what it does for those itself
	//
	// Between groups of commands the window draws a line, as OneCloud does.
	view(parts = {}) {
		const { kind, primary, commands, menu, controls, views, search, status, more, ...handlers } = parts;
		if (kind) this.$wrapper.attr("data-one-view", kind);
		if (primary) this.group("primary").append(primary);
		if (commands) this.group("own").empty().append(commands);
		if (menu && menu.$button && menu.$button.length) {
			this.group("menu").append(menu.$button);
			if (menu.dropdown) menu.dropdown.align = "start";
		}
		if (views) {
			if (typeof views.get_views === "function") this.views_of(views);
			else this.views_slot().append(views);
		}
		if (controls && controls.length) this.views_slot().prepend(controls.addClass("one-window-filters"));
		if (search) this.search(search);
		if (status !== undefined || more) this.status(status, { more });
		if (Object.keys(handlers).length) {
			this.handle(handlers);
			if ("up" in handlers) this.can({ up: !!handlers.up });
		}
		return this;
	}

	group(name) {
		return this.$commands.children(`[data-group=${name}]`);
	}

	// The address box: frappe's breadcrumbs while at rest; clicked, or Ctrl+K,
	// a box to type a place, a record or a command in, answered by frappe's
	// own search bar (`AddressBar`). A view that has paths of its own
	// (OneCloud's folders) is asked first when what is typed has a "/" in it.
	address() {
		if (this.$address) return this.$address.find("input").trigger("focus");
		const $area = this.page.$title_area.addClass("one-window-typing");
		this.$address = $(`<div class="one-window-address"><input type="text" spellcheck="false" autocomplete="off"></div>`).appendTo($area);
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
		new onedesk.window.AddressBar(this.$address, $input, () => this.close_address());
		$input.trigger("focus");
	}

	close_address() {
		if (!this.$address) return;
		this.$address.remove();
		this.$address = null;
		this.page.$title_area.removeClass("one-window-typing");
	}

	// What the view does for Back, Forward, Up and Refresh; anything it does
	// not say is the browser's (Back, Forward) or the breadcrumb's (Up).
	handle(handlers) {
		Object.assign(this.handlers, handlers);
		this.$tools.find("[data-window=refresh]").toggle(!!this.handlers.refresh && !this.$reload);
		return this;
	}

	// frappe's own reload button, which a list, a report, a board and a tree
	// add with page.add_action_icon("refresh-cw"), goes where the window keeps
	// Refresh, and the window's own Refresh steps aside. The button is
	// frappe's, with its click and its tooltip.
	adopt_reload($button) {
		this.$reload = $button;
		this.$tools.find("[data-window=refresh]").hide().after($button);
		$button.addClass("one-window-reload");
		if (!this.page.icon_group.children().length) this.page.icon_group.addClass("hide");
	}

	// What can be pressed. Back and Forward are the browser's history unless
	// the view keeps its own, so the browser is asked (the Navigation API
	// where it has one); Up is the breadcrumb's unless the view says.
	can({ back, forward, up } = {}) {
		if (up !== undefined) this.up_said = up;
		const history = window.navigation && "canGoBack" in window.navigation ? window.navigation : null;
		const $find = (act) => this.$nav.find(`[data-window=${act}]`);
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
	}

	search({ placeholder = "", on_input, on_key } = {}) {
		if (!this.$search) {
			this.$search = onedesk.shell.search(this.$tools.find(".one-window-search"), { placeholder });
			if (on_input) this.$search.on("input", frappe.utils.debounce(() => on_input(this.$search.val().trim()), 300));
			if (on_key) this.$search.on("keydown", on_key);
		}
		this.$search.attr("placeholder", placeholder);
		return this.$search;
	}

	status(text, { more = null } = {}) {
		this.$status.prop("hidden", false).find(".one-window-said").text(text || "");
		if (more) this.$status.find(".one-window-more").empty().append(more);
		return this.$status;
	}

	// The pane right of the view, its width and whether it is open kept per
	// kind of view.
	details({ key, width = 280 } = {}) {
		if (this.$details) return this.$details;
		this.details_key = `details:${key || "page"}`;
		const kept = onedesk.window.kept(this.details_key, { open: true, width });
		const $main = this.$wrapper.find(".layout-main").first();
		const $pane = $(`<aside class="one-window-details" role="complementary"><div class="one-window-details-edge"></div><div class="one-window-details-body"></div></aside>`).appendTo(
			$main
		);
		this.$details_pane = $pane;
		this.$details = $pane.find(".one-window-details-body");
		const size = (px) => Math.round(Math.min(560, Math.max(200, px)));
		$pane.css("--one-details-width", `${size(kept.width || width)}px`);
		onedesk.window.drag($pane.find(".one-window-details-edge")[0], {
			leading: true,
			from: () => $pane[0].getBoundingClientRect().width,
			to: (px) => $pane.css("--one-details-width", `${size(px)}px`),
			done: () => this.remember_details({ width: $pane[0].getBoundingClientRect().width }),
		});
		this.$switch.show();
		this.show_details(kept.open !== false);
		return this.$details;
	}

	remember_details(change) {
		const kept = onedesk.window.kept(this.details_key, {});
		onedesk.window.keep(this.details_key, { ...kept, ...change });
	}

	show_details(open) {
		this.details_open = !!open;
		this.$details_pane.prop("hidden", !open);
		this.$switch.attr("data-state", open ? "on" : null).attr("aria-pressed", open ? "true" : "false");
		this.$wrapper.trigger("one-window-details", [open]);
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
		if (!this.$views) this.$views = $(`<div class="one-window-views"></div>`).insertBefore(this.$switch);
		return this.$views;
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
		const $slot = this.views_slot();
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
		select.$wrapper.addClass("one-window-variants").appendTo($slot);
		select.$trigger.attr({ title: __("More views"), "aria-label": __("More views"), "data-variant": "ghost" });
	}

	// A container in the nav pane, under this view's row, for a tree of its
	// own (`onedesk.window.nav.place`).
	nav_slot() {
		if (!this.$slot) this.$slot = $(`<div class="one-window-nav-slot" role="tree"></div>`);
		onedesk.window.nav.place();
		return this.$slot;
	}
};

// frappe's search bar, answering in the address box rather than its modal:
// the same options, the same `awesomebar_search` hooks, the same filters of
// what One shows. Only where it draws differs.
onedesk.window.AddressBar = class AddressBar extends frappe.search.AwesomeBar {
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
onedesk.window.current = () => {
	const page = frappe.container && frappe.container.page && frappe.container.page.page;
	return page && page.window && window.innerWidth >= 768 ? page.window : null;
};

(() => {
	if (frappe.search.open_awesomebar_from_global_search_shortcut && !frappe.search.one_window) {
		frappe.search.one_window = true;
		const theirs = frappe.search.open_awesomebar_from_global_search_shortcut;
		frappe.search.open_awesomebar_from_global_search_shortcut = function (e) {
			const win = onedesk.window.current();
			if (!win) return theirs.call(this, e);
			win.address();
			return false;
		};
		document.addEventListener(
			"click",
			(e) => {
				const win = e.target.closest && e.target.closest(".navbar-modal-search-mobile") && onedesk.window.current();
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
	if (!Page || Object.hasOwn(Page.prototype, "one_window")) return;
	Page.prototype.one_window = true;
	const icon = Page.prototype.add_action_icon;
	Page.prototype.add_action_icon = function (name, ...rest) {
		const $button = icon.call(this, name, ...rest);
		if (this.window && name === "refresh-cw") this.window.adopt_reload($button);
		return $button;
	};
})();

(() => {
	if (frappe.ui.make_app_page.one_window) return;
	const make = frappe.ui.make_app_page;
	frappe.ui.make_app_page = function (opts) {
		const page = make.call(this, opts);
		if (page && (opts.one_window || onedesk.window.trial())) onedesk.window.of(page, { fit: !!opts.one_window_fit });
		return page;
	};
	frappe.ui.make_app_page.one_window = true;

	const Sidebar = frappe.ui.Sidebar;
	if (Sidebar && !Object.hasOwn(Sidebar.prototype, "one_window")) {
		Sidebar.prototype.one_window = true;
		const highlight = Sidebar.prototype.highlight_active_item;
		Sidebar.prototype.highlight_active_item = function (...args) {
			const said = highlight.apply(this, args);
			onedesk.window.nav.place();
			return said;
		};
	}
	$(document).on("page-change", () => {
		const current = frappe.container && frappe.container.page && frappe.container.page.page;
		$("body").toggleClass("full-height-page", !!(current && current.window && current.window.fit));
		if (current && current.window) setTimeout(() => current.window.can(), 0);
		onedesk.window.nav.place();
		onedesk.window.place_status();
	});
	$(document).on("app_ready", () => onedesk.window.nav.setup());
	$(() => setTimeout(() => onedesk.window.nav.setup(), 0));
})();

if (onedesk.window.trial()) $("body").addClass("one-window-trial");
