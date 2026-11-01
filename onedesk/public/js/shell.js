
frappe.provide("onedesk.shell");

$.extend(onedesk.shell, {
	page(wrapper, title, { hide_sidebar = false, mark = null, window: in_window = false, fit = false } = {}) {
		const page = frappe.ui.make_app_page({
			parent: wrapper,
			title,
			single_column: true,
			hide_sidebar,
			one_interface: in_window,
			one_interface_fit: fit,
		});
		if (mark) page.$title_area.prepend(`<span class="one-shell-mark">${frappe.utils.icon(mark, "md")}</span>`);
		page.$shell = $(`<section class="one-shell"></section>`).appendTo(page.main);
		return page;
	},

	body($shell, { wide = false } = {}) {
		$shell.html(`<div class="one-shell-body">${onedesk.shell.quiet(__("Loading…"))}</div>`);
		return $shell.find(".one-shell-body").toggleClass("one-shell-wide", !!wide);
	},

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

	pane_head($pane, html) {
		return $(`<div class="one-shell-pane-head">${html || ""}</div>`).prependTo($pane);
	},

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

	name(label, { route = null, page = frappe.get_current_page() } = {}) {
		page && page.set_breadcrumbs([{ label, ...(route ? { href: route } : {}) }]);
		frappe.utils.set_title(label);
		if (onedesk.oneai && onedesk.oneai.panel) onedesk.oneai.panel.moved(onedesk.oneai.where());
	},

	trail(parent, route, label, between = [], menu = null, page = frappe.get_current_page(), after = []) {
		if (page) {
			page.set_breadcrumbs([
				{ label: parent, href: route },
				...between.map((one) => ({ label: one.label, href: one.route })),
				{ label, one_record: true, ...(menu ? { one_menu: menu } : {}) },
				...after.map((one) => ({ label: one.label, one_menu: one.menu })),
			]);
		}
		frappe.utils.set_title(label);
		if (onedesk.oneai && onedesk.oneai.panel) onedesk.oneai.panel.moved(onedesk.oneai.where());
	},

	record($into, { page, parent, route, title, status = null, side = "", actions = [] }) {
		if (parent) onedesk.shell.trail(parent, route, title, [], null, page);
		if (status) page.set_indicator(status.label, status.colour);
		const $view = $(`<div class="one-record-view"><div class="one-record-main"></div><div class="one-record-side form-sidebar">${side}</div></div>`);
		$into.closest(".one-shell-body").addBack(".one-shell-body").addClass("one-shell-record");
		$into.empty().append($view);
		for (const one of actions) page.add_inner_button(one.label, one.action, one.group);
		return $view.find(".one-record-main");
	},

	async table($into, { title = "", note = "", rows = [], columns, open = null, empty = "", none = "", icon = "list", page_size = 20, actions = "", mark = null, choose = null } = {}) {
		await frappe.require("embedded_list.bundle.js");
		const esc = frappe.utils.escape_html;
		const list = new frappe.ui.EmbeddedList({
			wrapper: $into,
			title: title ? `${mark ? `<span class="one-shell-part-mark">${frappe.utils.icon(mark, "md")}</span>` : ""}${esc(title)}` : "",
			description: note ? esc(note) : "",
			show_search: rows.length > 5,
			page_size,
			empty_icon: icon,
			empty_message: empty || __("Nothing to show"),
			no_match_message: none || __("No matches"),
			get_data: () => Promise.resolve(rows),
			on_row_click: open,
			columns,
		});
		if (actions) list.$header.show().find(".embedded-list-header-actions").append(actions);
		if (choose) {
			const values = [...new Set(rows.map((row) => row[choose.key]).filter(Boolean))].sort();
			const $at = $('<div class="one-shell-choose"></div>').prependTo(list.$header.show().find(".embedded-list-header-actions"));
			const select = frappe.ui.form.make_control({
				df: { fieldtype: "Select", fieldname: choose.key, options: [choose.all, ...values].join("\n") },
				parent: $at,
				render_input: true,
				only_input: true,
			});
			select.$input.addClass("form-control-sm");
			list.chosen = values.includes(choose.value) ? choose.value : choose.all;
			select.set_value(list.chosen);
			list.get_data = () =>
				Promise.resolve(list.chosen && list.chosen !== choose.all ? rows.filter((row) => row[choose.key] === list.chosen) : rows);
			select.$input.on("change", () => {
				list.chosen = select.get_value();
				list.refresh();
			});
		}
		list.refresh();
		return list;
	},

	side({ image = null, initials = "", mark = null, title = "", sub = "", groups = [], meta = [] } = {}) {
		const esc = frappe.utils.escape_html;
		const picture = image
			? `<img class="sidebar-image" src="${esc(image)}">`
			: mark
			? `<div class="sidebar-standard-image one-record-mark">${frappe.utils.icon(mark, "xl")}</div>`
			: `<div class="sidebar-standard-image"><div class="standard-image">${esc(initials)}</div></div>`;
		return `<div class="sidebar-section sidebar-image-section"><div class="sidebar-image-wrapper">${picture}</div></div>
			<div class="sidebar-section sidebar-meta-details border-bottom">
				<div class="form-title-text"><span class="bold">${esc(title)}</span></div>
				${sub ? `<div class="text-muted one-record-sub">${sub}</div>` : ""}
			</div>
			${groups
				.filter((group) => group.html)
				.map((group) => `<div class="sidebar-section border-bottom">${group.label ? `<div class="form-sidebar-label">${esc(group.label)}</div>` : ""}${group.html}</div>`)
				.join("")}
			${meta.length ? `<div class="sidebar-section one-record-meta">${meta.map((line) => `<div>${esc(line)}</div>`).join("")}</div>` : ""}`;
	},

	button(label, attrs = {}, variant = "subtle", icon = null, theme = null) {
		return frappe.ui.button.html({ label, attrs, variant, icon, theme: theme || undefined });
	},

	section(title, body, note, aside = "") {
		const esc = frappe.utils.escape_html;
		return `<div class="one-shell-section">${title ? `<div class="one-shell-section-title"><span>${esc(title)}</span>${aside}</div>` : ""}${
			note ? `<div class="one-shell-quiet one-shell-note">${esc(note)}</div>` : ""
		}${body}</div>`;
	},

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

	app(label, mark) {
		const esc = frappe.utils.escape_html;
		return `<span class="one-shell-app">${mark ? `<span class="one-shell-app-mark">${frappe.utils.icon(mark, "sm")}</span>` : ""}${esc(label)}</span>`;
	},

	list(rows) {
		return `<div class="one-shell-list">${rows}</div>`;
	},

	actions(html) {
		return `<div class="one-shell-actions">${html}</div>`;
	},

	empty(title, description, { icon = null } = {}) {
		return frappe.ui.empty_state.html({ title, description, icon: icon || undefined, css_class: "one-shell-empty" });
	},

	search($parent, { placeholder = "", title = "" } = {}) {
		const $box = $(`<div class="one-shell-search">${frappe.utils.icon("search", "sm")}</div>`).appendTo($parent);
		const control = frappe.ui.form.make_control({
			df: { fieldtype: "Data", fieldname: "search", placeholder },
			parent: $box,
			render_input: true,
			only_input: true,
		});
		control.$input.attr({ type: "search", spellcheck: "false", autocomplete: "off", title: title || null });
		return control.$input;
	},

	quiet(text) {
		return `<div class="one-shell-quiet">${frappe.utils.escape_html(text)}</div>`;
	},

	// Each app's mark before its field's label, on a form of app levels.
	marks($wrapper, apps) {
		for (const app of apps) {
			$wrapper.find(`.frappe-control[data-fieldname="app_${app.icon}"] .control-label`).first().prepend(`<span class="one-shell-app-mark">${frappe.utils.icon(app.icon, "sm")}</span>`);
		}
	},

	pairs(names) {
		const rows = [];
		for (let at = 0; at < names.length; at += 2) rows.push([names[at], names[at + 1] || ""]);
		return rows;
	},

	two_columns(list, field) {
		const half = Math.ceil(list.length / 2);
		return list.flatMap((one, at) => [...(at === half ? [{ fieldtype: "Column Break" }] : []), field(one, at)]);
	},
});

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

	async hear(opened) {
		this.opened = opened || [];
		for (const one of this.opened) {
			while (frappe.flags.doc_subscribe) await new Promise((done) => setTimeout(done, 250));
			frappe.realtime.doc_subscribe(one.doctype, one.name);
		}
	}

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

	check() {
		if (!this.values || this.snapshot === undefined) return;
		this.set_dirty(Editor.same(this.values()) !== this.snapshot);
	}

	set_dirty(dirty) {
		this.dirty = dirty;
		if (dirty) this.page.set_indicator(__("Not Saved"), "orange");
		else {
			this.page.clear_indicator();
			this.show_status && this.show_status();
		}
		removeEventListener("beforeunload", this.leaving, { capture: true });
		if (dirty && !frappe.boot.developer_mode) addEventListener("beforeunload", this.leaving, { capture: true });
	}

	static every(group, names) {
		return Object.fromEntries(names.map((name) => [name, group.get_value(name) ?? ""]));
	}

	static same(values) {
		const text = (value) => {
			if (value === null || value === undefined) return "";
			if (typeof value !== "object") return String(value);
			return JSON.stringify(value, (key, one) => (key === "name" || key === "idx" || key === "doctype" || key.startsWith("__") ? undefined : one));
		};
		return JSON.stringify(
			Object.keys(values || {})
				.sort()
				.map((name) => [name, text(values[name])])
				.filter(([, value]) => value !== "" && value !== "[]")
		);
	}

	form(data, { before = "", after = "", rows = null } = {}) {
		const $card = $(`<div class="one-shell-section">${before}<div class="one-shell-form"></div>${after}</div>`).appendTo(this.$content);
		const own = Object.fromEntries(data.fields.map((one) => [one.fieldname, { ...one, default: data.values[one.fieldname] }]));
		let heading = null;
		const marks = {};
		const fields = rows
			? rows.flatMap((row, at) => {
					let css = null;
					if (row.row) [css, row] = [row.css, row.row];
					if (row.heading) {
						heading = { fieldtype: "Section Break", fieldname: `shell_part_${at}`, label: row.heading, description: row.note, css_class: "one-shell-part" };
						if (row.mark) marks[`shell_part_${at}`] = row.mark;
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
		for (const [fieldname, mark] of Object.entries(marks)) {
			const part = this.group.fields_dict[fieldname];
			if (part) part.wrapper.find(".section-head").first().prepend(`<span class="one-shell-part-mark">${frappe.utils.icon(mark, "md")}</span>`);
		}
		$card.toggleClass("one-shell-columns", !!rows);
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

	saves(values, $watch, ready) {
		this.values = values;
		this.snapshot = undefined;
		this.ready = Promise.resolve(ready).then(() => {
			this.snapshot = Editor.same(values());
		});
		this.page.set_primary_action(__("Save"), () => this.save(values()));
		this.page.wrapper[0].save_action = () => this.save(values());
		$watch.on("input change", "input, select, textarea", () => this.check());
		$watch.on("click mouseup", ".frappe-control[data-fieldtype='Table']", frappe.utils.debounce(() => this.check(), 150));
	}

	unsaved() {
		this.values = null;
		this.status = null;
		this.trailed = false;
		this.set_dirty(false);
		this.page.clear_primary_action();
		this.page.clear_inner_toolbar();
		this.page.wrapper[0].save_action = null;
		this.page.clear_indicator();
	}

	as_record(record) {
		this.trailed = true;
		this.status = record.status || null;
		this.$content = onedesk.shell.record(this.$content, { ...record, page: this.page });
		return this.$content;
	}

	show_status() {
		if (this.status) this.page.set_indicator(this.status.label, this.status.colour);
	}

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
		frappe.show_alert({ message: __("Saved"), indicator: "green" });
		this.set_dirty(false);
		this.$content.empty();
		this.hear(said.opened);
		this.redraw(said);
	}
};

{
	const named = (doctype) => ((frappe.boot.one_titles || {}).Crumb || {})[doctype];
	const homes = (doctype) => (frappe.boot.one_homes || {})[doctype];
	const home_crumbs = (home) => home.map((one) => ({ label: __(one.label), href: encodeURI(one.route) }));
	// A doctype's list, in whichever rail it is open and in any of its views
	// (/desk/onehr/department, /desk/department/view/List).
	const is_list = (href, doctype) => {
		const path = (href || "").split("?")[0].replace(/\/view\/[^/]+(\/.*)?$/, "");
		const slug = frappe.router.slug(doctype);
		return path === `/desk/${slug}` || new RegExp(`^/desk/[^/]+/${slug}$`).test(path);
	};

	const List = frappe.views.BaseList;
	if (List && !List.prototype.__one_crumbs) {
		List.prototype.__one_crumbs = true;
		const listed = List.prototype.get_breadcrumbs;
		List.prototype.get_breadcrumbs = function () {
			const items = listed.call(this);
			const home = homes(this.doctype);
			if (!home) return items;
			// A home's crumb for this very list names the list itself.
			const crumbs = home_crumbs(home);
			const at = crumbs.findIndex((one) => is_list(one.href, this.doctype));
			if (at >= 0 && items.length) items[items.length - 1] = { ...items[items.length - 1], label: crumbs.splice(at, 1)[0].label };
			return [...crumbs, ...items];
		};
	}

	const formed = frappe.ui.form.get_breadcrumbs;
	if (formed && !formed.__one) {
		frappe.ui.form.get_breadcrumbs = function (frm) {
			const items = formed(frm);
			const at = items.findIndex((one) => is_list(one.href, frm.doctype));
			const home = homes(frm.doctype);
			if (at >= 0 && home) items.splice(at, 1, ...home_crumbs(home));
			else if (at >= 0 && named(frm.doctype)) items[at] = { ...items[at], label: __(named(frm.doctype)) };
			return items;
		};
		frappe.ui.form.get_breadcrumbs.__one = true;
	}

	const Sidebar = frappe.ui.Sidebar;
	if (Sidebar && !Sidebar.prototype.__one_homes) {
		Sidebar.prototype.__one_homes = true;
		const found = Sidebar.prototype.find_active_item;
		const list = (path) => onedesk.panel.path(path);
		const light = (sidebar, $row) => {
			if (sidebar.active_item) sidebar.active_item.removeClass("active-sidebar");
			sidebar.active_item = null;
			if (!$row || !$row.length) return false;
			sidebar.active_item = $row;
			return true;
		};
		Sidebar.prototype.find_active_item = function () {
			// A kind whose home is a row of this rail lights that row, before
			// frappe's own match, which would light the rail's Home for any
			// list under it (/desk/onehr/department).
			const asked = frappe.get_route() || [];
			const kept = ["Form", "List"].includes(asked[0]) && homes(asked[1]);
			// A rail's own rows carry its name (/desk/onehr/one?center=…).
			const tail = kept && kept[0].route.replace(/^\/desk/, "");
			const exact = kept && $(".item-anchor[href]").filter((_i, a) => a.getAttribute("href").endsWith(tail));
			if (exact && light(this, exact.first().parent())) return true;
			// A kind with a home that is no row of this rail (One's Lists, in
			// the nav pane's own tree) lights nothing rather than Home.
			// frappe decodes the address, and cannot decode a name with a
			// bare % in it.
			let matched = false;
			try {
				matched = !kept && found.call(this);
			} catch {
				matched = false;
			}
			if (matched) return true;
			const narrows = (a) => new URLSearchParams(a.getAttribute("href").split("?")[1] || "").size;
			const row = (path) =>
				$(".item-anchor[href]")
					.not(".one-interface-nav-slot *")
					.toArray()
					.filter((a) => list(a.getAttribute("href")) === list(path))
					.sort((a, b) => narrows(a) - narrows(b))[0];
			const route = frappe.get_route() || [];
			const home = ["Form", "List"].includes(route[0]) && homes(route[1]);
			const path = home ? home[0].route : route[0] === "Form" ? `/desk/${frappe.router.slug(route[1])}` : window.location.pathname;
			// A home in a centre (/desk/one?center=…) was a row only if it matched
			// exactly above; by its path alone it is the rail's Home.
			if (home && path.includes("?")) return light(this, null);
			const found_row = row(path) || (route[0] === "Form" ? null : row(window.location.pathname));
			return light(this, found_row && $(found_row).parent());
		};

		// The row a page was reached from stays lit where the page is no row
		// of its own. A rail row whose page moves its address (Mark
		// Attendance) lit Home, whose address every page of the rail begins
		// with, and so did a list opened from Home's Setup; now the row clicked
		// stays lit, and a page opened from another keeps that page's row.
		const own = Sidebar.prototype.find_active_item;
		const href = ($row) => $row && $row.find(".item-anchor[href]").first().attr("href");
		const here = () => window.location.pathname + window.location.search;
		let at = null;
		let held = null;
		$(document).on("click", ".body-sidebar .sidebar-items .item-anchor[href]", (e) => {
			onedesk.shell.clicked = e.currentTarget.getAttribute("href");
		});
		Sidebar.prototype.find_active_item = function () {
			const was = href(this.active_item);
			const found = own.call(this);
			const now = here();
			if (now !== at) {
				const clicked = onedesk.shell.clicked;
				onedesk.shell.clicked = null;
				const lit = href(this.active_item);
				const own_row = lit && list(lit) === list(window.location.pathname);
				const home = $(".body-sidebar .sidebar-items .item-anchor[href]").first().attr("href");
				const weak = !lit || lit === home;
				held = own_row ? null : clicked || (weak && was && was !== lit ? was : null);
				at = now;
			}
			if (!held) return found;
			const $held = $(".body-sidebar .sidebar-items .item-anchor[href]")
				.filter((_i, a) => a.getAttribute("href") === held)
				.first();
			return $held.length ? light(this, $held.parent()) : found;
		};
	}

	// A rail's row into a centre (Lists, /desk/one?center=settings&module=…)
	// opens it over the page the reader is on, rather than taking them to
	// One's Home to open it there; a Lists row for a reader with no lists of
	// that app is not drawn.
	const centre = (a) => {
		const url = new URL(a.getAttribute("href"), window.location.origin);
		const asked = Object.fromEntries(url.searchParams);
		return url.pathname === "/desk/one" && asked.center ? asked : null;
	};
	document.addEventListener(
		"click",
		(e) => {
			const a = e.target.closest && e.target.closest(".body-sidebar .sidebar-items .item-anchor[href]");
			const asked = a && !e.metaKey && !e.ctrlKey && centre(a);
			if (!asked) return;
			e.preventDefault();
			e.stopImmediatePropagation();
			onedesk.centers.open(asked.center, asked);
		},
		true
	);
	if (Sidebar && !Sidebar.prototype.__one_centre_rows) {
		Sidebar.prototype.__one_centre_rows = true;
		const made = Sidebar.prototype.make_sidebar;
		Sidebar.prototype.make_sidebar = function (...args) {
			const said = made.apply(this, args);
			this.wrapper.find(".item-anchor[href*='at=lists']").each((_i, a) => {
				const asked = centre(a);
				const none = asked && asked.module && !((frappe.boot.one_lists || {})[asked.module] || []).length;
				$(a).closest(".sidebar-item-container").toggle(!none);
			});
			return said;
		};
	}

	// A page that changes its own address in place (Home's tabs) asks the
	// rail to light the row for it.
	for (const method of ["pushState", "replaceState"]) {
		const said = history[method];
		if (said.one_rail) continue;
		history[method] = function (...args) {
			const out = said.apply(this, args);
			setTimeout(() => frappe.get_route() && frappe.app && frappe.app.sidebar && frappe.app.sidebar.highlight_active_item && frappe.app.sidebar.highlight_active_item(), 0);
			return out;
		};
		history[method].one_rail = true;
	}

	// The sidebar's header names the space and opens nothing: frappe's menu on
	// it switched to other apps and frappe's own desk, which One does not show.
	const Header = frappe.ui.SidebarHeader;
	if (Header && !Header.prototype.__one_still) {
		Header.prototype.__one_still = true;
		Header.prototype.setup_menu = function () {};
	}

	// A key or secret field is never a sign-in: told so, the browser stops
	// filling the saved email into the field before it.
	const Password = frappe.ui.form.ControlPassword;
	if (Password && !Password.prototype.__one_not_a_login) {
		Password.prototype.__one_not_a_login = true;
		const make_input = Password.prototype.make_input;
		Password.prototype.make_input = function (...args) {
			const out = make_input.apply(this, args);
			this.$input?.attr("autocomplete", "new-password");
			return out;
		};
	}

	// A page named like a doctype (presentation, workbook) is the editor for
	// it: the router takes the doctype first, which shows anyone who can read
	// it (a System Manager) the record's form instead.
	const pages_first = () => {
		for (const slug of Object.keys(frappe.router.routes || {})) {
			if (frappe.boot?.page_info?.[slug]) delete frappe.router.routes[slug];
		}
	};
	if (frappe.router && !frappe.router.__one_pages_first) {
		frappe.router.__one_pages_first = true;
		const setup = frappe.router.setup;
		frappe.router.setup = function (...args) {
			const out = setup.apply(this, args);
			pages_first();
			return out;
		};
		pages_first();
	}

	// The rail's mark opens One as One's own rail button does. Followed as a
	// link, the router keeps the app on screen and lands on /desk/<app>/one.
	const Dock = frappe.ui.Dock;
	if (Dock && !Dock.prototype.__one_home) {
		Dock.prototype.__one_home = true;
		const made = Dock.prototype.make;
		Dock.prototype.make = function (...args) {
			made.apply(this, args);
			if (!this.$header) return;
			this.$header.attr("href", "/desk/one").on("click", (e) => {
				if (e.ctrlKey || e.metaKey || e.shiftKey) return;
				e.preventDefault();
				e.stopPropagation();
				this.sidebar.open_module("One");
			});
		};
	}
}

{
	const RTL = "\u0590-\u08FF\uFB1D-\uFDFF\uFE70-\uFEFF";
	const symbol = new RegExp(`([${RTL}][^\\s\\d\u200e]*)(\\s+)(?=[-+(]?\\d)`, "g");
	onedesk.shell.ltr = (text) => (typeof text === "string" ? text.replace(symbol, "$1\u200e$2") : text);
	const theirs = window.format_currency;
	if (theirs && !theirs.__one_ltr) {
		window.format_currency = function (...args) {
			return onedesk.shell.ltr(theirs.apply(this, args));
		};
		window.format_currency.__one_ltr = true;
	}
}
