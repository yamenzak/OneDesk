// A desk page on the window (onedesk/one_interface/AGENTS.md): any page frappe loads by name
// (a dashboard, print, a query report, a page of ours). What every page has
// is frappe's primary button and its menu, said once here when the page has
// loaded; a view that knows more says it in its own adapter.
onedesk.interface.adapt("page", () => {
	const Page = frappe.views && frappe.views.Page;
	if (!Page || Object.hasOwn(Page.prototype, "one_interface")) return;
	Page.prototype.one_interface = true;
	const trigger = Page.prototype.trigger_page_event;
	Page.prototype.trigger_page_event = function (event, ...args) {
		const said = trigger.call(this, event, ...args);
		const page = event === "on_page_load" && this.wrapper && this.wrapper.page;
		if (page && page.interface) {
			page.interface.view({
				primary: page.btn_primary,
				menu: { $button: page.menu_btn_group, dropdown: page.menu_dropdown },
			});
		}
		return said;
	};
});

onedesk.interface.skeleton = {
	NAME: "One Skeletons",
	WAIT: 150,
	QUIET: 140,
	LIMIT: 6000,
	MOST: 40,
	BOXES: 200,
	TEXT: 0,
	CONTROL: 1,
	MEDIA: 2,
	CARD: 3,
	shapes: {},

	key() {
		const route = frappe.get_route() || [];
		const head = route[0];
		const name = head === "List" ? route.slice(0, 3) : route.slice(0, 2);
		return `${frappe.is_mobile() ? "phone/" : ""}${name.join("/") || "home"}`;
	},

	phone(key) {
		const { TEXT, CONTROL, CARD } = this;
		const out = [];
		const add = (kind, x, y, w, h, r = 6) => out.push([kind, x, y, w, h, r]);
		add(TEXT, 40, 24, 420, 18);
		add(CONTROL, 780, 16, 180, 32);
		if (key.includes("Form/")) {
			add(TEXT, 40, 72, 620, 22);
			add(CARD, 40, 112, 920, 76, 12);
			add(TEXT, 80, 132, 300, 11);
			add(TEXT, 80, 154, 420, 16);
			add(CARD, 40, 204, 920, 480, 14);
			for (let row = 0; row < 6; row++) {
				add(TEXT, 80, 228 + row * 74, 320, 11);
				add(CONTROL, 80, 248 + row * 74, 840, 32);
			}
			return out;
		}
		for (let i = 0; i < 3; i++) add(CONTROL, 40 + i * 240, 68, 220, 28);
		add(CARD, 40, 112, 920, 620, 14);
		for (let row = 0; row < 9; row++) {
			add(TEXT, 80, 134 + row * 66, 520, 13);
			add(TEXT, 80, 158 + row * 66, 320, 10);
			add(CONTROL, 760, 138 + row * 66, 160, 22);
		}
		return out;
	},

	generic(key) {
		if (key.startsWith("phone/")) return this.phone(key);
		const { TEXT, CONTROL, CARD } = this;
		const out = [];
		const add = (kind, x, y, w, h, r = 6) => out.push([kind, x, y, w, h, r]);
		add(CARD, 10, 10, 980, 42, 12);
		add(TEXT, 40, 25, 220, 12);
		add(CONTROL, 880, 18, 90, 26);
		if (key.startsWith("Form/")) {
			add(TEXT, 10, 84, 300, 22);
			add(TEXT, 10, 120, 170, 11);
			add(CARD, 10, 150, 240, 74, 12);
			add(TEXT, 28, 170, 110, 11);
			add(TEXT, 28, 194, 150, 16);
			for (let i = 0; i < 4; i++) add(CONTROL, 10 + i * 90, 250, 78, 24);
			add(CARD, 10, 292, 730, 380, 16);
			for (let row = 0; row < 4; row++) {
				for (const x of [40, 390]) {
					add(TEXT, x, 322 + row * 84, 110, 11);
					add(CONTROL, x, 342 + row * 84, 310, 32);
				}
			}
			add(CARD, 760, 292, 230, 380, 16);
			for (let row = 0; row < 5; row++) add(TEXT, 780, 322 + row * 40, 150, 11);
			return out;
		}
		add(TEXT, 10, 84, 240, 22);
		add(CONTROL, 240, 80, 70, 30);
		if (key.startsWith("List/") || key.startsWith("query-report/")) {
			for (let i = 0; i < 5; i++) add(CONTROL, 10 + i * 80, 126, 68, 24);
			add(CARD, 10, 166, 980, 620, 14);
			for (let row = 0; row < 12; row++) {
				add(TEXT, 32, 190 + row * 50, 180, 12);
				add(TEXT, 270, 190 + row * 50, 90, 12);
				add(TEXT, 430, 190 + row * 50, 150, 12);
				add(TEXT, 660, 190 + row * 50, 100, 12);
				add(TEXT, 850, 190 + row * 50, 110, 12);
			}
			return out;
		}
		for (let i = 0; i < 3; i++) {
			add(CARD, 10 + i * 330, 130, 320, 120, 14);
			add(TEXT, 34 + i * 330, 156, 130, 11);
			add(TEXT, 34 + i * 330, 186, 190, 20);
		}
		add(CARD, 10, 266, 980, 460, 14);
		for (let row = 0; row < 8; row++) {
			add(TEXT, 34, 296 + row * 52, 420, 12);
			add(TEXT, 760, 296 + row * 52, 160, 12);
		}
		return out;
	},

	box([kind, x, y, w, h, r], mirror) {
		const left = mirror ? 1000 - x - w : x;
		const radius = r >= 999 ? "50%" : `${r}px`;
		const css = kind === this.CARD ? "one-skeleton-card" : "es-skeleton";
		return `<div class="${css}" style="left:${left / 10}%;top:${y}px;width:${w / 10}%;height:${h}px;border-radius:${radius}"></div>`;
	},

	show() {
		const main = document.querySelector(".main-section");
		if (!main) return;
		const area = main.getBoundingClientRect();
		const held = this.shapes[this.current];
		const boxes = held ? held.b : this.generic(this.current);
		const mirror = !held && document.dir === "rtl";
		const cards = boxes.filter((b) => b[0] === this.CARD).map((b) => this.box(b, mirror));
		const bars = boxes.filter((b) => b[0] !== this.CARD).map((b) => this.box(b, mirror));
		const el = document.createElement("div");
		el.className = "one-page-skeleton";
		el.setAttribute("aria-hidden", "true");
		const top = Math.max(0, area.top);
		const bottom = Math.min(window.innerHeight, area.bottom);
		el.style.cssText = `left:${area.left}px;top:${top}px;width:${area.width}px;height:${bottom - top}px;border-radius:${getComputedStyle(main).borderRadius}`;
		el.innerHTML = `${cards.join("")}<div class="one-skeleton-bars">${bars.join("")}</div>`;
		document.body.appendChild(el);
		el.offsetWidth;
		el.dataset.on = "1";
		main.setAttribute("aria-busy", "true");
		this.el = el;
	},

	hide() {
		const el = this.el;
		this.el = null;
		document.querySelector(".main-section")?.removeAttribute("aria-busy");
		if (!el) return;
		delete el.dataset.on;
		setTimeout(() => el.remove(), 220);
	},

	stop() {
		clearTimeout(this.waiting);
		clearTimeout(this.calm);
		clearTimeout(this.giving_up);
		this.watching?.disconnect();
		this.watching = null;
	},

	begin() {
		const route = frappe.get_route_str();
		if (route === this.route) return;
		this.stop();
		this.hide();
		this.route = route;
		this.current = this.key();
		this.arrived = false;
		this.waiting = setTimeout(() => this.show(), this.WAIT);
		this.giving_up = setTimeout(() => this.finish(), this.LIMIT);
		const main = document.querySelector(".main-section");
		if (main) {
			this.watching = new MutationObserver(() => this.wait());
			this.watching.observe(main, { childList: true, subtree: true, characterData: true });
		}
		this.wait();
	},

	wait() {
		clearTimeout(this.calm);
		this.calm = setTimeout(() => (this.ready() ? this.finish() : this.wait()), this.QUIET);
	},

	ready() {
		const root = this.arrived && frappe.container && frappe.container.page;
		if (!root || !root.offsetParent) return false;
		const visible = (el) => el.getClientRects().length > 0;
		if ([...root.querySelectorAll(".list-skeleton, .es-skeleton, .freeze-row, .animate-spin")].some(visible)) return false;
		if (frappe.request.ajax_count > 0) return false;
		if (!this.island_ready(root, visible)) return false;
		return root.textContent.trim().length > 8;
	},

	island_ready(root, visible) {
		if (!root.querySelector(".one-island")) return true;
		const host = root.querySelector(".one-island .frappe-island");
		const inside = host && (host.shadowRoot || host);
		if (!inside || [...inside.querySelectorAll(".animate-spin")].some(visible)) return false;
		return [...inside.children].some((child) => child.tagName !== "STYLE" && child.childElementCount > 0);
	},

	finish() {
		this.stop();
		const shown = !!this.el;
		this.hide();
		if (!this.ready()) return;
		frappe.container.page.one_seen = true;
		const key = this.current;
		const measure = () => key === this.current && this.remember(key, this.capture());
		if (window.requestIdleCallback) requestIdleCallback(measure, { timeout: 1200 });
		else setTimeout(measure, shown ? 300 : 100);
	},

	painted(colour) {
		return !!colour && colour !== "transparent" && !/^rgba\(0, 0, 0, 0\)$|\/ 0\)$/.test(colour);
	},

	capture() {
		const main = document.querySelector(".main-section");
		const root = frappe.container && frappe.container.page;
		if (!main || !root) return [];
		const area = main.getBoundingClientRect();
		const width = main.clientWidth;
		const top = area.top - main.scrollTop;
		const limit = Math.min(area.bottom, window.innerHeight);
		const boxes = [];
		const skip = ".one-page-skeleton, .dropdown-menu, .modal, .es-tooltip, .one-interface-details-edge, [hidden]";
		const whole = "button, .btn, .es-button, input, select, textarea, .form-control, .es-badge, .indicator-pill, .avatar";
		const pictures = "svg, img, canvas, video";
		const radius = (style) => {
			const said = style.borderTopLeftRadius;
			if (said.endsWith("%")) return 999;
			return Math.min(Math.round(parseFloat(said) || 0), 24);
		};
		const push = (kind, r, round) => {
			if (r.width < 4 || r.height < 3 || r.bottom < area.top || r.top > limit) return;
			boxes.push([kind, Math.round(((r.left - area.left) / width) * 1000), Math.round(r.top - top), Math.round((r.width / width) * 1000), Math.round(r.height), round]);
		};
		const lines = (node) => {
			const range = document.createRange();
			range.selectNodeContents(node);
			for (const r of range.getClientRects()) {
				const h = Math.min(r.height * 0.62, 14);
				push(this.TEXT, { left: r.left, right: r.right, width: r.width, height: h, top: r.top + (r.height - h) / 2, bottom: r.bottom }, 4);
			}
		};
		const walk = (el, under) => {
			if (boxes.length >= this.BOXES || el.matches(skip)) return;
			const rect = el.getBoundingClientRect();
			if (!rect.width || !rect.height || rect.bottom < area.top || rect.top > limit) return;
			const style = getComputedStyle(el);
			if (style.visibility === "hidden" || style.opacity === "0") return;
			if (el.matches(whole)) return push(this.CONTROL, rect, radius(style));
			if (el.matches(pictures)) return push(this.MEDIA, rect, radius(style));
			const fill = style.backgroundColor;
			const filled = this.painted(fill) && fill !== under;
			const edged = parseFloat(style.borderTopWidth) > 0 && parseFloat(style.borderBottomWidth) > 0 && parseFloat(style.borderLeftWidth) > 0;
			if ((filled || edged) && rect.height >= 36 && rect.width >= 64 && rect.width < width * 0.995) push(this.CARD, rect, radius(style));
			const beneath = this.painted(fill) ? fill : under;
			for (const child of (el.shadowRoot || el).childNodes) {
				if (child.nodeType === Node.TEXT_NODE && child.nodeValue.trim()) lines(child);
				else if (child.nodeType === Node.ELEMENT_NODE) walk(child, beneath);
			}
		};
		walk(root, getComputedStyle(main).backgroundColor);
		return boxes;
	},

	remember(key, boxes) {
		if (boxes.length < 4) return;
		const held = this.shapes[key];
		if (held && Math.abs(held.b.length - boxes.length) <= Math.max(6, boxes.length * 0.2)) return;
		const names = Object.keys(this.shapes);
		if (!held && names.length >= this.MOST) {
			delete this.shapes[names.reduce((old, one) => (this.shapes[one].at < this.shapes[old].at ? one : old))];
		}
		this.shapes[key] = { at: Math.floor(Date.now() / 86400000), b: boxes };
		frappe.model.user_settings.update(this.NAME, this.shapes);
	},

	setup() {
		const render = frappe.router.render;
		const skeleton = this;
		frappe.router.render = function (...args) {
			skeleton.begin();
			return render.apply(this, args);
		};
		$(document).on("page-change", () => {
			this.arrived = true;
			if (frappe.container.page?.one_seen) this.finish();
		});
		$(document).on("app_ready", () => {
			frappe.model.user_settings.get(this.NAME).then((said) => {
				this.shapes = said || {};
			});
		});
	},
};

onedesk.interface.skeleton.setup();
