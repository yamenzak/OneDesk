// The window (docs/WINDOW.md): every screen in one frame, built from frappe's
// own parts. Nothing here redraws what frappe draws; it places it, and adds
// Back, Forward, Up, Refresh, a search box, a status row and a details pane.
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
		this.$commands = $(`<div class="one-window-commands"></div>`).insertBefore($content.children(".standard-items-section"));
		this.$switch = $(button("details", "panel-right", __("Details pane"))).addClass("one-window-switch").appendTo($content).hide();
		this.$status = $(
			`<footer class="one-window-status" hidden><span class="one-window-said"></span><span class="one-window-more"></span></footer>`
		).appendTo(this.$wrapper);
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

	// A container in the nav pane, under this view's row, for a tree of its
	// own (`onedesk.window.nav.place`).
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
		const $slot = this.views_slot().empty();
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
	});
	$(document).on("app_ready", () => onedesk.window.nav.setup());
	$(() => setTimeout(() => onedesk.window.nav.setup(), 0));
})();

// The trial: lists and forms on the window for whoever turned it on.
(() => {
	if (!onedesk.window.trial()) return;
	$("body").addClass("one-window-trial");

	const Base = frappe.views && frappe.views.BaseList;
	if (Base && !Object.hasOwn(Base.prototype, "one_window")) {
		Base.prototype.one_window = true;
		const menu = Base.prototype.setup_view_menu;
		Base.prototype.setup_view_menu = function (...args) {
			const said = menu.apply(this, args);
			const win = this.page && this.page.window;
			if (win && this.views_list) win.views_of(this.views_list);
			// Filter and Sort are commands, as Explorer has them: frappe's own
			// buttons, moved before the view toggles. The quick filters stay as
			// the row under the commands.
			const $filters = win && this.$page && this.$page.find(".filter-section").first();
			if (win && $filters && $filters.length) win.views_slot().prepend($filters.addClass("one-window-filters"));
			return said;
		};
	}

	const List = frappe.views && frappe.views.ListView;
	if (List && !Object.hasOwn(List.prototype, "one_window")) {
		List.prototype.one_window = true;
		const setup_page = List.prototype.setup_page;
		List.prototype.setup_page = function (...args) {
			const said = setup_page.apply(this, args);
			const win = this.page && this.page.window;
			if (win) {
				win.$wrapper.attr("data-one-view", "list");
				// A list's primary button is New: it leads the command row, as
				// OneCloud's New does. It is frappe's own node, which frappe
				// still shows, hides and relabels through page.btn_primary.
				if (this.page.btn_primary && this.page.btn_primary.length) win.$commands.prepend(this.page.btn_primary);
				win.handle({
					up: () => frappe.app.sidebar && frappe.app.sidebar.current_module && frappe.app.sidebar.open_module(frappe.app.sidebar.current_module),
				}).can({ up: true });
				const field = this.meta.title_field || "name";
				win.search({
					placeholder: __("Search {0}", [__(this.doctype)]),
					on_input: (text) => {
						const had = this.filter_area.get().find((one) => one[1] === field && one[2] === "like");
						if (had) this.filter_area.remove(field);
						if (text) this.filter_area.add([[this.doctype, field, "like", `%${text}%`]]);
						else if (had) this.refresh();
					},
				});
			}
			return said;
		};
		const paging = List.prototype.setup_paging_area;
		List.prototype.setup_paging_area = function (...args) {
			const said = paging.apply(this, args);
			const win = this.page && this.page.window;
			if (win && this.$paging_area) win.status("", { more: this.$paging_area });
			return said;
		};
		const count = List.prototype.get_count_str;
		List.prototype.get_count_str = function (...args) {
			return count.apply(this, args).then((text) => {
				const win = this.page && this.page.window;
				if (win) win.status(frappe.utils.html2text ? frappe.utils.html2text(String(text)) : $("<div>").html(text).text());
				return text;
			});
		};
	}

	const Form = frappe.ui.form && frappe.ui.form.Form;
	if (Form && !Object.hasOwn(Form.prototype, "one_window")) {
		Form.prototype.one_window = true;
		const setup = Form.prototype.setup;
		Form.prototype.setup = function (...args) {
			const said = setup.apply(this, args);
			const win = this.page && this.page.window;
			if (win) {
				win.$wrapper.attr("data-one-view", "form");
				win.handle({
					refresh: () => !this.is_new() && this.reload_doc(),
					up: () => frappe.set_route("List", this.doctype),
				}).can({ up: true });
			}
			return said;
		};
	}
})();
