// A list on the window (onedesk/one_interface/AGENTS.md): frappe's ListView and every view
// made from it (Report, Kanban, Calendar, Gantt, Image, Map, Dashboard,
// Inbox, File), saying what they have through `window.view`. Every node
// handed over is frappe's own, which frappe keeps a reference to, so it still
// shows, hides and relabels them.
onedesk.interface.adapt("list", () => {
	// Views drawn as frappe's list rows, which the stylesheet sets as rows.
	const ROWS = ["List", "File", "Inbox"];
	// Views that show a page of records, so a count and paging mean something;
	// a board, a calendar and a dashboard show all of theirs.
	const COUNTED = ["List", "Report", "Image", "Gantt", "Map", "Inbox", "File"];
	const kind = (view) => (ROWS.includes(view.view_name) ? "list" : String(view.view_name || "list").toLowerCase());
	const counted = (view) => COUNTED.includes(view.view_name);

	const Base = frappe.views && frappe.views.BaseList;
	if (Base && !Object.hasOwn(Base.prototype, "one_interface")) {
		Base.prototype.one_interface = true;
		const menu = Base.prototype.setup_view_menu;
		Base.prototype.setup_view_menu = function (...args) {
			const said = menu.apply(this, args);
			const win = this.page && this.page.interface;
			if (win) {
				win.view({
					views: this.views_list,
					controls: this.$page && this.$page.find(".filter-section").first(),
				});
			}
			return said;
		};
	}

	const List = frappe.views && frappe.views.ListView;
	if (!List || Object.hasOwn(List.prototype, "one_interface")) return;


	// A module's tree, the window's (`win.tree`), under the list's row in the
	// nav pane, for the lists it says are its (`onedesk.interface.trees`,
	// { covers(doctype), draw(win, doctype) }): a module's lists (lists.js). Drawn again
	// each time the list is shown, since what it counts changes elsewhere.
	const tree = (view) => {
		const win = view.page && view.page.interface;
		const own = win && onedesk.interface.trees.find((one) => one.covers(view.doctype));
		if (own) own.draw(win, view.doctype);
	};
	$(document).on("page-change", () => {
		const view = window.cur_list;
		if (view && view.page && frappe.container.page && frappe.container.page.page === view.page) tree(view);
	});
	List.prototype.one_interface = true;

	const setup_page = List.prototype.setup_page;
	List.prototype.setup_page = function (...args) {
		const said = setup_page.apply(this, args);
		const win = this.page && this.page.interface;
		if (!win) return said;
		if (kind(this) === "list" && !frappe.is_mobile()) {
			win.fit = true;
			win.$wrapper.addClass("one-interface-fit");
			if (frappe.container.page?.page === this.page) $("body").addClass("full-height-page");
		}
		const field = this.meta.title_field || "name";
		win.view({
			kind: kind(this),
			primary: this.page.btn_primary,
			menu: { $button: this.page.menu_btn_group, dropdown: this.page.menu_dropdown },
			up: onedesk.interface.home,
			search:
				this.view_name === "Dashboard"
					? null
					: {
							placeholder: __("Search {0}", [__(this.doctype)]),
							on_input: (text) => {
								const had = this.filter_area.get().find((one) => one[1] === field && one[2] === "like");
								if (had) this.filter_area.remove(field);
								if (text) this.filter_area.add([[this.doctype, field, "like", `%${text}%`]]);
								else if (had) this.refresh();
							},
					  },
		});
		tree(this);
		return said;
	};

	const paging = List.prototype.setup_paging_area;
	List.prototype.setup_paging_area = function (...args) {
		const said = paging.apply(this, args);
		const win = this.page && this.page.interface;
		if (win && this.$paging_area && counted(this)) win.view({ status: "", more: this.$paging_area });
		return said;
	};

	const count = List.prototype.get_count_str;
	List.prototype.get_count_str = function (...args) {
		return count.apply(this, args).then((text) => {
			const win = this.page && this.page.interface;
			if (win && counted(this)) win.view({ status: $("<div>").html(String(text)).text() });
			return text;
		});
	};
});

{
	const company = (view) => {
		const said = frappe.boot.one_companies;
		if (said && (said.doctypes || []).includes(view.doctype) && !(view.filters || []).some((one) => one[1] === "company"))
			view.filters = [...(view.filters || []), [view.doctype, "company", "=", said.current]];
	};
	const boards = () => {
		const Board = frappe.views.KanbanView;
		if (!Board || Object.hasOwn(Board.prototype, "one_company")) return;
		Board.prototype.one_company = true;
		const boarded = Board.prototype.get_board;
		Board.prototype.get_board = function (...args) {
			return boarded.apply(this, args).then((said) => {
				company(this);
				return said;
			});
		};
	};
	const pipeline = (Board) => {
		if (!Board || Object.hasOwn(Board.prototype, "one_company")) return;
		Board.prototype.one_company = true;
		const laid = Board.prototype.setup_quick_filters;
		Board.prototype.setup_quick_filters = function (...args) {
			company(this);
			return laid.apply(this, args);
		};
	};
	onedesk.interface.when(frappe.views, "KanbanV2Page", pipeline);
	frappe.provide("frappe.kanban_v2");
	onedesk.interface.when(frappe.kanban_v2, "FrappeDataProvider", (Provider) => {
		const loaded = Provider.prototype.loadBoard;
		Provider.prototype.loadBoard = async function (...args) {
			const said = await loaded.apply(this, args);
			(said?.columns || []).forEach((column) => (column.title = __(column.id)));
			return said;
		};
	});
	const settle = frappe.views.ListView.prototype.setup_defaults;
	frappe.views.ListView.prototype.setup_defaults = function (...args) {
		boards();
		const done = settle.apply(this, args);
		company(this);
		return done;
	};
}

onedesk.interface.layouts = {
	pending: null,

	key: (doctype) => `layouts:${doctype}`,

	said(doctype) {
		return onedesk.interface.kept(this.key(doctype), {});
	},

	note(doctype, name, change) {
		const all = { ...this.said(doctype) };
		if (change.default) Object.keys(all).forEach((one) => (all[one] = { ...all[one], default: 0 }));
		all[name] = { ...all[name], ...change };
		onedesk.interface.keep(this.key(doctype), all);
		this.sidebar();
	},

	forget(doctype, name) {
		const all = { ...this.said(doctype) };
		delete all[name];
		onedesk.interface.keep(this.key(doctype), all);
		this.sidebar();
	},

	default_of(doctype) {
		return Object.entries(this.said(doctype)).find(([, one]) => one.default)?.[0] || null;
	},

	emoji: (icon) => !!icon && !/^[a-z0-9-]+$/.test(icon),

	columns(view) {
		const widths = view.one_widths || {};
		return view.list_filter
			.get_current_columns_state()
			.map((one) => ({ fieldname: one.fieldname, label: one.label, width: widths[one.fieldname] || null }));
	},

	state(view) {
		return {
			filters: (view.filter_area?.get() || []).map((one) => one.slice(0, 4)),
			columns: this.columns(view),
			sort_field: view.sort_by,
			sort_order: view.sort_order,
		};
	},

	plain(said) {
		return JSON.stringify({
			filters: [...said.filters].map(String).sort(),
			columns: said.columns.map((one) => [one.fieldname, cint(one.width)]),
			sort: [said.sort_field, String(said.sort_order || "").toLowerCase()],
		});
	},

	changed(view, layout) {
		const filter = view.list_filter;
		return (
			this.plain(this.state(view)) !==
			this.plain({
				filters: filter.parse_layout_filters(layout).map((one) => one.slice(0, 4)),
				columns: filter.get_layout_columns(layout),
				sort_field: layout.sort_field,
				sort_order: layout.sort_order,
			})
		);
	},

	personal(view) {
		const filter = view.list_filter;
		if (filter && filter.active_layout_name !== "default_layout") return;
		onedesk.interface.keep(`columns:${view.doctype}`, this.columns(view));
	},

	apply(view, columns) {
		view.last_args = null;
		return view.setup_columns(columns).then(() => {
			this.personal(view);
			return view.refresh(true);
		});
	},

	saved(view, filter, state) {
		return { ...state, route_signature: filter.get_route_signature_from_filters(state.filters) };
	},

	update(view) {
		const filter = view.list_filter;
		const layout = filter.get_active_layout();
		const state = this.saved(view, filter, this.state(view));
		return filter
			.update_layout_from_dialog(layout, { filter_name: layout.filter_name, ...state })
			.then(() => filter.get_list_filters())
			.then(() => frappe.show_alert({ message: __("Layout updated."), indicator: "green" }));
	},

	dialog(view, layout = null, from = null) {
		const filter = view.list_filter;
		const held = (layout && this.said(view.doctype)[layout.name]) || {};
		const editable = !layout || filter.can_edit_layout(layout);
		const dialog = new frappe.ui.Dialog({
			title: layout ? __("Edit Layout") : __("Save Layout"),
			fields: [
				{ fieldtype: "Data", fieldname: "filter_name", label: __("Layout Name"), reqd: 1, read_only: !editable, default: layout?.filter_name || (from ? __("{0} Copy", [from.filter_name]) : "") },
				{ fieldtype: "Icon", fieldname: "icon", label: __("Icon"), options: "Emojis", default: held.icon || "" },
				{ fieldtype: "Check", fieldname: "default", label: __("Set as Default"), default: held.default ? 1 : 0 },
				{ fieldtype: "Check", fieldname: "sidebar", label: __("Add to Sidebar"), default: held.sidebar ? 1 : 0 },
			],
			primary_action_label: __("Save"),
			primary_action: (values) => {
				const meta = { icon: values.icon || "", default: values.default, sidebar: values.sidebar, label: values.filter_name };
				const done = (name) => {
					this.note(view.doctype, name, meta);
					view.views_list?.refresh_trigger?.();
					dialog.hide();
					return filter.setup_layout_menu({ refetch: true }).then(() => filter.select_layout(name, values.filter_name));
				};
				if (layout) {
					if (!editable) return done(layout.name);
					const state = {
						filters: filter.parse_layout_filters(layout),
						columns: filter.get_layout_columns(layout),
						sort_field: layout.sort_field,
						sort_order: layout.sort_order,
					};
					return filter.update_layout_from_dialog(layout, { filter_name: values.filter_name, ...this.saved(view, filter, state) }).then(() => done(layout.name));
				}
				const state = from
					? { filters: filter.parse_layout_filters(from), columns: filter.get_layout_columns(from), sort_field: from.sort_field, sort_order: from.sort_order }
					: this.state(view);
				return filter.create_layout_from_dialog({ filter_name: values.filter_name, ...this.saved(view, filter, state) }).then((doc) => done(doc.name));
			},
		});
		dialog.show();
	},

	dress(filter) {
		const view = filter.list_view;
		const held = this.said(view.doctype);
		const row = (one) => {
			const layout = (filter.filters || []).find((each) => filter.get_layout_label(each) === one.label);
			const icon = layout && held[layout.name]?.icon;
			if (!icon) return one;
			return this.emoji(icon) ? { ...one, label: `${icon} ${one.label}` } : { ...one, icon };
		};
		return (items) =>
			items.map((one) => {
				if (one.group === undefined) return row(one);
				if (one.hide_label) return one;
				return { ...one, options: one.options.map(row) };
			});
	},

	menu(filter, items) {
		const view = filter.list_view;
		const shown = this.dress(filter)(items);
		const actions = [{ label: __("Create Layout"), icon: "plus", onclick: () => this.dialog(view) }];
		const active = filter.get_active_layout();
		if (active && filter.can_edit_layout(active) && this.changed(view, active)) {
			actions.push({ label: __("Update Layout"), icon: "save", onclick: () => this.update(view) });
		}
		actions.push({ label: __("Manage Layouts"), icon: "settings", onclick: () => filter.open_manage_layouts_dialog() });
		shown[shown.length - 1] = { ...shown[shown.length - 1], options: actions };
		return shown;
	},

	patch(Filter) {
		const P = Filter.prototype;
		if (Object.hasOwn(P, "one_layouts")) return;
		P.one_layouts = true;
		const layouts = onedesk.interface.layouts;
		const menu = P.get_layout_menu_items;
		P.get_layout_menu_items = function () {
			return layouts.menu(this, menu.call(this));
		};
		P.open_layout_dialog = function (layout = null, { duplicate_from = null } = {}) {
			layouts.dialog(this.list_view, layout, duplicate_from);
		};
		const saved = P.get_saved_active_layout_name;
		P.get_saved_active_layout_name = function () {
			const doctype = this.list_view.doctype;
			if (layouts.pending?.doctype === doctype) return layouts.pending.name;
			return layouts.default_of(doctype) || saved.call(this);
		};
		const restore = P.restore_layout_from_route_signature;
		P.restore_layout_from_route_signature = function (opts = {}) {
			const doctype = this.list_view.doctype;
			const name = layouts.pending?.doctype === doctype ? layouts.pending.name : layouts.default_of(doctype);
			const layout = name && this.find_layout_by_name(name);
			if (!layout || this._user_selected_layout || opts.has_route_filters === undefined || !layouts.opened_plainly(this, opts)) return restore.call(this, opts);
			const finish = () => {
				this._initial_layout_restored = true;
				this.list_view.views_list?.refresh_trigger?.();
			};
			this.set_active_layout(layout);
			if (layout.name === opts.shown_name) return finish(), Promise.resolve();
			return this.apply_saved_layout(layout, { refresh: opts.refresh }).then(finish, finish);
		};
		const deleted = P.delete_layout;
		P.delete_layout = function (layout) {
			return deleted.call(this, layout).then((said) => {
				layouts.forget(this.list_view.doctype, layout.name);
				return said;
			});
		};
	},

	opened_plainly(filter, opts) {
		if (!opts.has_route_filters) return true;
		const bare = (text) => text.split("&").filter((one) => one && !one.startsWith("company=")).join("&");
		const slug = `/${frappe.router.slug(filter.list_view.doctype)}`;
		const link = [...document.querySelectorAll(".body-sidebar a.item-anchor[href]:not([data-one-layout])")].find((a) => a.pathname.replace(/\/view\/list$/, "").endsWith(slug));
		const said = link ? filter._signature_from_search_params(new URLSearchParams(link.search)) : "";
		return bare(filter.get_route_signature()) === bare(said);
	},

	open(doctype, name, label) {
		const view = window.cur_list;
		if (view?.doctype === doctype && view.view_name === "List" && frappe.container.page?.page === view.page) {
			return view.list_filter?.select_layout(name, label);
		}
		this.pending = { doctype, name, label };
		frappe.set_route(frappe.router.slug(doctype), "view", "list");
	},

	arrived() {
		const pending = this.pending;
		const view = window.cur_list;
		if (!pending || view?.doctype !== pending.doctype || frappe.container.page?.page !== view.page) return;
		this.pending = null;
		Promise.resolve(view.list_filter?.setup_promise).then(() => view.list_filter?.select_layout(pending.name, pending.label));
	},

	face(icon) {
		if (this.emoji(icon)) return `<span class="sidebar-item-icon one-layout-emoji">${frappe.utils.escape_html(icon)}</span>`;
		return `<span class="sidebar-item-icon">${frappe.utils.icon(icon || "list", "sm", "", "", "current-color", true)}</span>`;
	},

	sidebar() {
		const all = onedesk.interface.settings();
		Object.keys(all)
			.filter((key) => key.startsWith("layouts:") && all[key])
			.forEach((key) => {
				const doctype = key.slice("layouts:".length);
				const rows = Object.entries(all[key]).filter(([, one]) => one.sidebar);
				const slug = `/${frappe.router.slug(doctype)}`;
				const $link = $(".body-sidebar a.item-anchor[href]:not([data-one-layout])")
					.filter((_, a) => a.pathname.replace(/\/view\/list$/, "").endsWith(slug))
					.first();
				if (!$link.length) return;
				const $row = $link.closest(".sidebar-item-container");
				const $nested = $row.children(".nested-container");
				const signature = JSON.stringify(rows);
				if ($nested.attr("data-one-layouts") === signature) return;
				$nested.attr("data-one-layouts", signature);
				$link.find(".one-layout-twisty").remove();
				$link.closest(".standard-sidebar-item").toggleClass("indent", !!rows.length);
				if (!rows.length) return void $nested.empty().removeClass("one-layout-rows");
				const open = onedesk.interface.kept(`layouts_open:${doctype}`, true);
				const $twisty = $(`<button type="button" class="btn-reset drop-icon one-layout-twisty" aria-label="${__("Views")}">${frappe.utils.icon("chevron-right", "xs")}</button>`).toggleClass("one-layout-open", !!open);
				$link.find(".sidebar-item-control").append($twisty);
				$nested.addClass("one-layout-rows").toggleClass("hidden", !open).attr("data-one-doctype", doctype);
				$nested.html(
					rows
						.map(
							([name, one]) => `<div class="sidebar-item-container"><div class="standard-sidebar-item"><a class="item-anchor" data-one-layout="${frappe.utils.escape_html(name)}">${this.face(one.icon)}<span class="sidebar-item-label">${frappe.utils.escape_html(one.label || name)}</span></a></div></div>`
						)
						.join("")
				);
				$twisty.on("click", (e) => {
					e.preventDefault();
					e.stopPropagation();
					const now = $nested.hasClass("hidden");
					$nested.toggleClass("hidden", !now);
					$twisty.toggleClass("one-layout-open", now);
					onedesk.interface.keep(`layouts_open:${doctype}`, now);
				});
				$nested.find("[data-one-layout]").on("click", (e) => {
					e.preventDefault();
					e.stopPropagation();
					const name = e.currentTarget.dataset.oneLayout;
					this.open(doctype, name, all[key][name].label || name);
				});
			});
		this.mark();
	},

	mark() {
		const view = window.cur_list;
		const shown = view?.view_name === "List" && frappe.container.page?.page === view.page;
		$(".one-layout-rows").each((_, rows) => {
			const here = shown && view.doctype === rows.dataset.oneDoctype;
			const active = here ? view.list_filter?.active_layout_name : null;
			let chosen = false;
			$(rows)
				.find("[data-one-layout]")
				.each((_i, row) => {
					const on = row.dataset.oneLayout === active;
					chosen = chosen || on;
					$(row).closest(".standard-sidebar-item").toggleClass("active-sidebar", on);
				});
			$(rows).parent().children(".standard-sidebar-item").toggleClass("active-sidebar", here && !chosen);
		});
	},

	picker(view, $at) {
		const held = new Map(this.columns(view).map((one) => [one.fieldname, one]));
		const subject = view.meta.title_field || "name";
		const fields = frappe.meta
			.get_docfields(view.doctype)
			.filter((df) => frappe.model.is_value_type(df) && !df.hidden && df.fieldname !== subject)
			.map((df) => ({ fieldname: df.fieldname, label: __(df.label, null, df.parent) }));
		if (frappe.has_indicator?.(view.doctype)) fields.unshift({ fieldname: "status_field", label: __("Status") });
		let changed = false;
		const $panel = $(`<div class="one-crumb-switch-panel"><label class="one-crumb-switch-search">${frappe.utils.icon("search", "sm")}<input placeholder="${__("Search")}"></label><div class="one-crumb-switch-rows one-column-rows"></div></div>`);
		const $rows = $panel.find(".one-column-rows");
		const draw = (text = "") => {
			const needle = text.trim().toLowerCase();
			$rows.html(
				fields
					.filter((one) => !needle || one.label.toLowerCase().includes(needle))
					.map((one) => `<label class="one-column-row"><input type="checkbox" data-field="${one.fieldname}" ${held.has(one.fieldname) ? "checked" : ""}><span>${frappe.utils.escape_html(one.label)}</span></label>`)
					.join("")
			);
		};
		draw();
		$panel.find(".one-crumb-switch-search input").on("input", (e) => draw(e.target.value));
		$rows.on("change", "input", (e) => {
			const field = e.target.dataset.field;
			changed = true;
			if (e.target.checked) held.set(field, { fieldname: field, label: fields.find((one) => one.fieldname === field).label, width: null });
			else held.delete(field);
		});
		new frappe.ui.Popover({
			trigger: $at,
			align: "end",
			css_class: "one-crumb-switch-popover",
			content: () => $panel[0],
			on_close: () => {
				if (!changed) return;
				changed = false;
				this.apply(view, [...held.values()]);
			},
		});
	},

	head(view) {
		const $head = view.$result?.find(".list-row-head").first();
		if (!$head?.length || view.view_name !== "List") return;
		$head.find(".list-row-col[data-fieldname]").not(".tag-col").each((_, col) => {
			const field = col.dataset.fieldname;
			if (field && field !== "undefined" && !col.querySelector(".list-col-resize-handle")) col.insertAdjacentHTML("beforeend", '<div class="list-col-resize-handle"></div>');
		});
		const box = $head.closest(".result-container")[0];
		const clip = () => $head[0].style.setProperty("--one-list-x", `${Math.abs(box.scrollLeft)}px`);
		clip();
		$(box).off("scroll.one-layouts").on("scroll.one-layouts", clip);
		const $left = $head.find(".level-left").first();
		view.one_sortable?.destroy();
		view.one_sortable = new Sortable($left[0], {
			draggable: ".list-row-col:not(.list-subject, .tag-col)",
			filter: ".list-col-resize-handle",
			preventOnFilter: false,
			animation: 180,
			onEnd: (e) => {
				if (e.oldIndex === e.newIndex) return;
				const order = [...$left.children(".list-row-col[data-fieldname]")].map((col) => col.dataset.fieldname);
				const columns = this.columns(view).sort((a, b) => order.indexOf(a.fieldname) - order.indexOf(b.fieldname));
				this.apply(view, columns);
			},
		});
		const $right = $head.find(".level-right").first();
		if (!view.list_filter || $right.find(".one-column-picker").length) return;
		const $button = frappe.ui.button({ icon: "columns-3", variant: "ghost", css_class: "one-column-picker", attrs: { "aria-label": __("Columns"), title: __("Columns") } });
		$right.prepend($button);
		this.picker(view, $button);
	},

	setup() {
		const layouts = this;
		onedesk.interface.when(frappe.views, "ListFilter", (Filter) => layouts.patch(Filter));
		onedesk.interface.when(frappe.views, "ListViewSelect", (Select) => {
			if (Object.hasOwn(Select.prototype, "one_layouts")) return;
			Select.prototype.one_layouts = true;
			const label = Select.prototype.get_trigger_label;
			Select.prototype.get_trigger_label = function () {
				const said = label.call(this);
				return said === this.label_map[this.current_view] ? __(this.current_view) : said;
			};
			const content = Select.prototype.set_trigger_content;
			Select.prototype.set_trigger_content = function (text) {
				content.call(this, text);
				layouts.mark();
				const filter = this.current_view === "List" ? this.list_view?.list_filter : null;
				const icon = filter && filter.active_layout_name !== "default_layout" && layouts.said(this.doctype)[filter.active_layout_name]?.icon;
				if (!icon) return;
				const $first = this.$trigger.children("svg").first();
				if (layouts.emoji(icon)) $first.replaceWith(`<span class="one-crumb-emoji">${frappe.utils.escape_html(icon)}</span>`);
				else $first.replaceWith(frappe.utils.icon(icon, "sm"));
			};
		});
		const List = frappe.views.ListView;
		const columns = List.prototype.setup_columns;
		List.prototype.setup_columns = function (override = null) {
			if (this.view_name !== "List") return columns.call(this, override);
			const plain = !this.list_filter || this.list_filter.active_layout_name === "default_layout";
			const mine = override || (plain ? onedesk.interface.kept(`columns:${this.doctype}`, null) : null) || (!plain && this.list_filter.get_layout_columns(this.list_filter.get_active_layout())) || null;
			this.one_widths = {};
			(mine || []).forEach((one) => {
				if (!one.width) return;
				this.one_widths[one.fieldname] = cint(one.width);
				this.column_max_widths[one.fieldname] = cint(one.width);
			});
			return columns.call(this, mine && mine.length ? mine : null);
		};
		const resize = List.prototype.setup_column_resize;
		List.prototype.setup_column_resize = function (...args) {
			if (this.view_name === "List" && !frappe.is_mobile()) layouts.head(this);
			return resize.apply(this, args);
		};
		List.prototype.save_column_width = function (fieldname, width) {
			this.one_widths = { ...this.one_widths, [fieldname]: cint(width) };
			layouts.personal(this);
		};
		List.prototype.load_more_on_scroll = function () {
			if (this.loading_more || this.data.length < this.page_length) return;
			this.loading_more = true;
			this.start = this.data.length;
			this.page_length = this.selected_page_count;
			this.refresh_now().finally(() => {
				this.loading_more = false;
				this.observe_list_end();
			});
		};
		const observe = List.prototype.observe_list_end;
		List.prototype.observe_list_end = function () {
			if (frappe.is_mobile()) return observe.call(this);
			this.scroll_observer?.disconnect();
			this.scroll_observer = new IntersectionObserver(
				(entries) => {
					if (entries.some((entry) => entry.isIntersecting)) this.load_more_on_scroll();
				},
				{ root: this.$result.closest(".result-container")[0], rootMargin: "0px 0px 600px 0px" }
			);
			this.scroll_observer.observe(this.$list_end[0]);
		};
		const toggled = List.prototype.toggle_result_area;
		List.prototype.toggle_result_area = function (...args) {
			const said = toggled.apply(this, args);
			if (this.load_on_scroll) this.$paging_area.hide();
			return said;
		};
		$(document).on("page-change", () => layouts.arrived());
	},
};

onedesk.interface.layouts.setup();
