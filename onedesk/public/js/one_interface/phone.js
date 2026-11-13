// The shell on a phone (onedesk/one_interface/AGENTS.md, On a phone): frappe's tab
// bar and its navigation sheet, with what a phone could not reach. An Apps
// tab opens the sheet from anywhere; the sheet searches every app's rail,
// lays the apps out as a grid, and carries the bars' tools (Check In,
// Timers, OneAI, Documents, open workbooks), moved in while it is open as
// frappe moves the rail. frappe builds the bar from a bundle it loads on a
// phone, so its class is dressed as it is defined.
frappe.provide("onedesk.interface.phone");

$.extend(onedesk.interface.phone, {
	TOOLS: '.one-bar [data-group="day"], .one-bar [data-group="ai"], .one-bar [data-group="waiting"], .one-bar [data-group="tray"], .one-bar [data-group="open"]',

	/** Every row of every app's rail a person can open, in the dock's order,
	 * with the app it is in: what the sheet's search looks through. */
	pages() {
		const sidebar = frappe.app.sidebar;
		const out = [];
		for (const entry of sidebar.collect_dock_entries(sidebar.get_sidebar_app())) {
			const rail = entry.module && frappe.boot.module_sidebars?.[entry.module];
			if (!rail) continue;
			const walk = (items) => {
				for (const item of items || []) {
					if (item.type === "Link" && item.label) {
						const route = frappe.ui.sidebar_item.get_route(item, false, entry.module);
						if (route) out.push({ label: __(item.label), icon: item.icon, app: entry.label, route });
					}
					walk(item.nested_items);
				}
			};
			walk(rail.items);
		}
		return out;
	},

	found(pages, said) {
		const words = said.toLowerCase().split(/\s+/).filter(Boolean);
		const seen = new Set();
		return pages.filter((one) => {
			const hay = `${one.label} ${one.app}`.toLowerCase();
			if (!words.every((word) => hay.includes(word)) || seen.has(one.route)) return false;
			seen.add(one.route);
			return true;
		});
	},

	dress(MobileNav) {
		const proto = MobileNav.prototype;
		if (proto.__one_phone) return;
		proto.__one_phone = true;
		const phone = onedesk.interface.phone;

		const top = proto.make_back_to_top;
		proto.make_back_to_top = function () {
			top.call(this);
			const main = document.querySelector(".main-section");
			if (!main || !this.update_back_to_top) return;
			main.removeEventListener("scroll", this.update_back_to_top);
			let frame = null;
			const update = () => {
				frame = null;
				document.body.classList.toggle("has-back-to-top", main.scrollTop > main.clientHeight / 2);
			};
			this.update_back_to_top = () => (frame ??= requestAnimationFrame(update));
			main.addEventListener("scroll", this.update_back_to_top, { passive: true });
			frappe.router?.on?.("change", this.update_back_to_top);
		};

		const tabs = proto.get_tabs;
		proto.get_tabs = function () {
			const said = tabs.call(this);
			said.splice(1, 0, { name: "apps", label: __("Apps"), icon: "layout-grid", opens: true });
			return said;
		};

		const tab = proto.make_tab;
		proto.make_tab = function (one) {
			if (!one.opens) {
				const made = tab.call(this, one);
				if (one.name === "search") {
					made.el.addEventListener(
						"click",
						(e) => {
							if (e instanceof CustomEvent) return;
							e.preventDefault();
							e.stopPropagation();
							onedesk.interface.phone.find();
						},
						true
					);
				}
				if (one.name === "notifications") {
					const unread = frappe.boot.notification_unread_count || 0;
					$(made.el).append(
						`<span class="notification-count one-phone-badge ${unread ? "" : "hidden"}">${unread > 99 ? "99+" : unread || ""}</span>`
					);
				}
				return made;
			}
			const item = document.createElement("frappe-mobile-nav-item");
			item.setAttribute("label", one.label);
			item.dataset.oneTab = one.name;
			item.innerHTML = `${frappe.utils.icon(one.icon, "md")}<span class="one-phone-dot"></span>`;
			item.addEventListener("click", (e) => {
				if (e instanceof CustomEvent) return;
				this.open_navigation();
			});
			this.nav.appendChild(item);
			return { ...one, el: item };
		};

		const navigate = proto.open_navigation;
		proto.open_navigation = function () {
			this.one_launching = true;
			try {
				navigate.call(this);
			} finally {
				this.one_launching = false;
			}
			this.tabs.find((one) => one.name === "apps")?.el.toggleAttribute("active", !!this.sheet);
		};

		const sheet = proto.open_sheet;
		proto.open_sheet = function (title, render) {
			if (!this.one_launching) return sheet.call(this, title, render);
			const $find = $(`<div class="one-phone-find">
				<input type="search" class="form-control" autocomplete="off" placeholder="${__("Search Apps and Pages")}" aria-label="${__("Search Apps and Pages")}">
			</div>`);
			sheet.call(this, null, () => {
				const said = render();
				return {
					...said,
					height: "full",
					header: $find[0],
					content: () => phone.arrange(this, said.content(), $find, title),
				};
			});
			if (this.sheet) this.sheet.set_title = (label) => this.$one_heading?.text(label);
		};

		proto.browse_dock_entry = function (entry) {
			this.close_sheet();
			frappe.app.sidebar.open_dock_entry(entry);
		};

		const put_back = proto.return_sidebar;
		proto.return_sidebar = function () {
			put_back.call(this);
			phone.return_tools(this);
			this.tabs.find((one) => one.name === "apps")?.el.removeAttribute("active");
		};
	},

	arrange(nav, body, $find, title) {
		const phone = onedesk.interface.phone;
		const $body = $(body).addClass("one-phone-sheet");
		const $tools = $(`<div class="one-phone-tools"></div>`).prependTo($body);
		nav.one_tools = [];
		$(phone.TOOLS).each((_i, group) => {
			for (const tool of [...group.children]) {
				nav.one_tools.push({ tool, group });
				$tools.append(tool);
			}
		});
		const company = document.querySelector(".one-bar .one-bar-company");
		if (company) {
			nav.one_tools.unshift({ tool: company, group: company.parentElement });
			$tools.prepend(company);
		}
		$tools.on("click", "button:not(.one-bar-company):not(.one-tray)", () => setTimeout(() => nav.close_sheet()));
		nav.$one_heading = $(`<div class="one-phone-heading"></div>`).text(title).insertAfter($body.find(".desk-mobile-sheet-dock"));
		const $found = $(`<div class="one-phone-found hide" role="list"></div>`).appendTo($body);
		let pages = null;
		$find.find("input").on("input", function () {
			const said = this.value.trim();
			$body.toggleClass("one-phone-finding", !!said);
			$found.toggleClass("hide", !said).empty();
			if (!said) return;
			pages ??= phone.pages();
			const rows = phone.found(pages, said).slice(0, 40);
			for (const one of rows) {
				$(`<a class="one-phone-page" role="listitem"></a>`)
					.attr("href", one.route)
					.append(frappe.utils.icon(one.icon || "file", "sm"))
					.append($(`<span class="one-phone-page-label"></span>`).text(one.label))
					.append($(`<span class="one-phone-page-app"></span>`).text(one.app))
					.appendTo($found);
			}
			if (!rows.length) $found.append($(`<div class="one-phone-none"></div>`).text(__("No matching pages")));
		});
		return body;
	},

	/** The address bar slides away while the page scrolls down and comes back
	 * as soon as it scrolls up, or once the page is near its top. It stays while
	 * something in it is being typed in. */
	tuck() {
		const phone = window.matchMedia("(max-width: 767.98px)");
		const set = (on) => document.body.classList.toggle("one-head-tucked", on);
		let last = 0;
		document.addEventListener(
			"scroll",
			(e) => {
				const scroller = e.target;
				if (!(scroller instanceof Element) || !scroller.classList.contains("main-section")) return;
				const at = scroller.scrollTop;
				const moved = at - last;
				last = at;
				if (!phone.matches || at < 64 || document.querySelector(".one-interface-address, .page-head :focus-within")) return set(false);
				if (moved > 6) set(true);
				else if (moved < -6) set(false);
			},
			{ capture: true, passive: true }
		);
		frappe.router?.on("change", () => {
			last = 0;
			set(false);
		});
	},

	/** A page's place name, tapped on a phone, opens the address box, as on a
	 * desk: the app's places are under Apps, and everything else is a search
	 * away. frappe's tab bar sets this as it is built, so it is set after. */
	/** The Apps tab's dot, on while any tool on the bars has a count. Watched
	 * on the bars alone, so nothing else on the page restyles for it. */
	waiting(nav, tries = 0) {
		const tab = nav?.tabs?.find((one) => one.name === "apps")?.el;
		const bars = document.querySelectorAll(".one-bar");
		if (!tab) return;
		if (!bars.length) return tries < 5 && setTimeout(() => onedesk.interface.phone.waiting(nav, tries + 1), 2000);
		const mark = () => tab.classList.toggle("one-waiting", !!document.querySelector(".one-bar .one-bar-badge:not(.hide, .hidden)"));
		const watch = new MutationObserver(mark);
		bars.forEach((bar) => watch.observe(bar, { subtree: true, childList: true, attributes: true, attributeFilter: ["class"] }));
		mark();
	},

	titled() {
		const phone = window.matchMedia("(max-width: 767.98px)");
		frappe.ui.Page.title_action = () =>
			phone.matches && document.body.classList.contains("mobile-nav-title") && onedesk.interface.here()
				? () => onedesk.interface.here()?.address()
				: null;
		frappe.container?.page?.page?.render_breadcrumbs?.();
	},

	/** The app's own places, as a drawer from the start edge, opened by the
	 * menu button before the page's name on a phone. The rail is frappe's own:
	 * its rows are moved in while the drawer is open and put back after, as
	 * frappe's navigation sheet does. */
	drawer() {
		const sidebar = frappe.app?.sidebar;
		if (!sidebar?.$items_container || document.querySelector(".one-drawer")) return;
		frappe.ui.mobile_nav?.close_sheet();
		const home = sidebar.$items_container.parent();
		const $scrim = $(`<div class="one-drawer-scrim"></div>`);
		const $drawer = $(`<nav class="one-drawer" role="dialog" aria-modal="true" tabindex="-1"></nav>`).attr("aria-label", frappe.ui.mobile_nav?.module_label(sidebar.current_module) || __("Apps"));
		const $body = $(`<div class="desk-mobile-sheet one-drawer-body"></div>`).appendTo($drawer);
		const $head = $(`<div class="one-drawer-head"></div>`).appendTo($body);
		const $shown = sidebar.wrapper?.find(".sidebar-header").first();
		const logo = $shown?.find(".header-logo").html();
		const name = $shown?.find(".header-title").html();
		if (logo) $(`<span class="one-drawer-logo"></span>`).html(logo).appendTo($head);
		$(`<span class="one-drawer-name"></span>`)[name ? "html" : "text"](name || $drawer.attr("aria-label")).appendTo($head);
		document.body.classList.add("one-drawer-open");
		const $rail = $(`<div class="body-sidebar desk-mobile-sheet-sidebar one-drawer-rail"></div>`).appendTo($body);
		sidebar.$items_container.appendTo($rail);
		const module = onedesk.interface.foot.module();
		if (module) onedesk.interface.foot.drawer($body, module);
		const shut = () => {
			if (!$drawer.parent().length) return;
			sidebar.$items_container.appendTo(home);
			$drawer.remove();
			$scrim.remove();
			document.body.classList.remove("one-drawer-open");
			$(document).off("keydown.one-drawer");
		};
		$scrim.on("click", shut);
		$drawer.on("click", "a[href]", () => setTimeout(shut));
		$drawer.on("click", ".one-drawer-foot button", shut);
		$(document).on("keydown.one-drawer", (e) => e.key === "Escape" && shut());
		frappe.router?.once?.("change", shut);
		$("body").append($scrim, $drawer);
		requestAnimationFrame(() => {
			$scrim.addClass("is-open");
			$drawer.addClass("is-open");
			$drawer.trigger("focus");
		});
	},

	/** The menu button before a list's, a report's or an app home's name on a
	 * phone. A record keeps its back button instead. */
	burger() {
		const put = () => {
			if (!frappe.is_mobile() || (frappe.get_route() || [])[0] === "Form") return;
			const title = frappe.container?.page?.page?.wrapper?.find(".page-head .page-title").first();
			if (!title?.length || title.prev(".one-burger").length) return;
			frappe.ui
				.button({
					icon: "menu",
					variant: "ghost",
					title: __("Menu"),
					css_class: "one-burger",
					onclick: (e) => {
						e.stopPropagation();
						onedesk.interface.phone.drawer();
					},
				})
				.insertBefore(title);
		};
		frappe.router?.on?.("change", () => setTimeout(put, 0));
		$(document).on("page-change", () => setTimeout(put, 0));
		setTimeout(put, 0);
	},

	/** Every sheet closes as a phone's own sheets do: pulled down from
	 * anywhere in it while its content is at the top, not only by the grip,
	 * and let go past a short way or flicked. */
	pull(Sheet) {
		const proto = Sheet.prototype;
		if (proto.__one_pull) return;
		proto.__one_pull = true;
		const SHORT = 96;
		const FLICK = 0.4;
		const bind = proto.bind;
		proto.bind = function (...args) {
			const said = bind.apply(this, args);
			if (this.popover || !this.panel) return said;
			const sheet = this;
			let pull = null;
			const reset = () => {
				sheet.panel?.removeAttribute("data-dragging");
				if (sheet.panel) sheet.panel.style.transform = "";
				if (sheet.scrim) sheet.scrim.style.opacity = "";
			};
			this.onpullstart = (e) => {
				if (sheet.drag || e.touches.length !== 1) return;
				const body = e.target.closest(".es-bottom-sheet__body");
				pull = { y: e.touches[0].clientY, t: e.timeStamp, body, moved: 0, on: false, v: 0 };
			};
			this.onpullmove = (e) => {
				if (!pull || sheet.drag) return;
				const y = e.touches[0].clientY;
				const dy = y - pull.y;
				if (!pull.on) {
					if (dy < 8 || (pull.body && pull.body.scrollTop > 0)) {
						if (dy < -4 || (pull.body && pull.body.scrollTop > 0)) pull = null;
						return;
					}
					pull.on = true;
					pull.y = y;
					pull.from = e.timeStamp;
					sheet.panel.setAttribute("data-dragging", "");
				}
				e.preventDefault();
				const moved = Math.max(0, y - pull.y);
				const dt = e.timeStamp - pull.t;
				if (dt > 0) pull.v = (moved - pull.moved) / dt;
				pull.moved = moved;
				pull.t = e.timeStamp;
				sheet.panel.style.transform = moved ? `translateY(${moved}px)` : "";
				sheet.scrim.style.opacity = String(1 - moved / sheet.panel.offsetHeight);
			};
			this.onpullend = () => {
				const done = pull;
				pull = null;
				if (!done?.on) return;
				const speed = done.moved / Math.max(1, done.t - done.from);
				if ((done.moved > SHORT || Math.max(done.v, speed) > FLICK) && sheet.dismissible) {
					sheet.panel.removeAttribute("data-dragging");
					sheet.close("swipe");
					return;
				}
				reset();
			};
			this.panel.addEventListener("touchstart", this.onpullstart, { passive: true });
			this.panel.addEventListener("touchmove", this.onpullmove, { passive: false });
			this.panel.addEventListener("touchend", this.onpullend);
			this.panel.addEventListener("touchcancel", this.onpullend);
			return said;
		};
		const unbind = proto.unbind;
		proto.unbind = function (...args) {
			this.panel?.removeEventListener("touchstart", this.onpullstart);
			this.panel?.removeEventListener("touchmove", this.onpullmove);
			this.panel?.removeEventListener("touchend", this.onpullend);
			this.panel?.removeEventListener("touchcancel", this.onpullend);
			return unbind.apply(this, args);
		};
	},

	/** Search on a phone: a panel that drops from the top with its box
	 * focused in the same tap, so the keyboard is up at once, and frappe's
	 * search bar answering under it as in a desk's address box (AddressBar),
	 * recent places first. The Search tab, the bar's glass, a place name and
	 * Ctrl+K open it. */
	find() {
		const open = document.querySelector(".one-find input");
		if (open) return open.focus();
		const $find = $(`<div class="one-find" role="dialog" aria-modal="true">
			<div class="one-find-scrim"></div>
			<div class="one-find-panel"><div class="one-find-row"><div class="one-find-box"><input type="search"></div></div></div>
		</div>`)
			.attr("aria-label", __("Search"))
			.appendTo(document.body);
		const $input = $find.find("input").attr({
			placeholder: __("Search"),
			"aria-label": __("Search"),
			enterkeyhint: "search",
			autocomplete: "off",
			spellcheck: "false",
		});
		$input[0].focus();
		const room = () => {
			const tall = window.visualViewport?.height || window.innerHeight;
			$find.find(".one-find-panel").css("max-height", `${tall}px`);
			$find.find("[role=listbox]").css("max-height", `${tall - 64}px`);
		};
		const esc = (e) => {
			if (e.key !== "Escape") return;
			e.stopPropagation();
			close();
		};
		const close = () => {
			if (!$find.parent().length) return;
			window.visualViewport?.removeEventListener("resize", room);
			document.removeEventListener("keydown", esc, true);
			$input.trigger("blur");
			$find.removeClass("one-find-open");
			setTimeout(() => $find.remove(), 200);
		};
		room();
		window.visualViewport?.addEventListener("resize", room);
		document.addEventListener("keydown", esc, true);
		$find.find(".one-find-scrim").on("click", close);
		$find.find(".one-find-row").append(frappe.ui.button({ label: __("Cancel"), variant: "ghost", css_class: "one-find-cancel", onclick: close }));
		new onedesk.interface.AddressBar($find.find(".one-find-box"), $input, close);
		room();
		$input.trigger("focus");
		requestAnimationFrame(() => $find.addClass("one-find-open"));
	},

	/** On a phone the address box is the drop-down search. */
	search(Frame) {
		const proto = Frame?.prototype;
		if (!proto || proto.__one_find) return;
		proto.__one_find = true;
		const address = proto.address;
		proto.address = function (...args) {
			if (window.matchMedia("(max-width: 767.98px)").matches) return onedesk.interface.phone.find();
			return address.apply(this, args);
		};
	},

	return_tools(nav) {
		for (const { tool, group } of nav.one_tools || []) group.appendChild(tool);
		nav.one_tools = [];
		nav.$one_heading = null;
	},
});

onedesk.interface.phone.tuck();
onedesk.interface.phone.burger();
onedesk.interface.phone.search(onedesk.interface.Frame);

if (frappe.ui.mobile_nav) {
	onedesk.interface.phone.titled();
	onedesk.interface.phone.waiting(frappe.ui.mobile_nav);
}
else {
	let made;
	Object.defineProperty(frappe.ui, "mobile_nav", {
		configurable: true,
		enumerable: true,
		get: () => made,
		set: (nav) => {
			made = nav;
			onedesk.interface.phone.titled();
			onedesk.interface.phone.waiting(nav);
		},
	});
}

if (frappe.ui.BottomSheet) onedesk.interface.phone.pull(frappe.ui.BottomSheet);
else {
	let sheet;
	Object.defineProperty(frappe.ui, "BottomSheet", {
		configurable: true,
		enumerable: true,
		get: () => sheet,
		set: (made) => {
			sheet = made;
			onedesk.interface.phone.pull(made);
		},
	});
}

if (frappe.ui.MobileNav) onedesk.interface.phone.dress(frappe.ui.MobileNav);
else {
	let held;
	Object.defineProperty(frappe.ui, "MobileNav", {
		configurable: true,
		enumerable: true,
		get: () => held,
		set: (made) => {
			held = made;
			onedesk.interface.phone.dress(made);
		},
	});
}

$(document).on("click", ".frappe-control .control-label", (event) => {
	if (!frappe.is_mobile()) return;
	const trigger = event.currentTarget.querySelector(".info-trigger, .one-help");
	if (!trigger || event.target.closest(".info-trigger, .info-card, .one-help")) return;
	trigger.dispatchEvent(new MouseEvent("click", { bubbles: true }));
});
