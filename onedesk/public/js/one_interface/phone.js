// The shell on a phone (onedesk/one_interface/AGENTS.md, On a phone): frappe's tab
// bar and its navigation sheet, with what a phone could not reach. An Apps
// tab opens the sheet from anywhere; the sheet searches every app's rail,
// lays the apps out as a grid, and carries the bars' tools (Check In,
// Timers, OneAI, Documents, open workbooks), moved in while it is open as
// frappe moves the rail. frappe builds the bar from a bundle it loads on a
// phone, so its class is dressed as it is defined.
frappe.provide("onedesk.interface.phone");

$.extend(onedesk.interface.phone, {
	TOOLS: '.one-bar [data-group="day"], .one-bar [data-group="ai"], .one-bar [data-group="waiting"], .one-bar [data-group="open"]',

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
		$tools.on("click", "button", () => setTimeout(() => nav.close_sheet()));
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

	return_tools(nav) {
		for (const { tool, group } of nav.one_tools || []) group.appendChild(tool);
		nav.one_tools = [];
		nav.$one_heading = null;
	},
});

onedesk.interface.phone.tuck();

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
