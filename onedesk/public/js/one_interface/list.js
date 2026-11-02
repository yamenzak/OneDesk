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

// A map view opens blank in frappe: ListView's constructor sets
// `this.load_lib` to a promise, which hides MapView's own load_lib method,
// so its setup_view throws "this.load_lib is not a function" before Leaflet
// loads. The map's setup calls its class's method by name instead.
{
	const MapView = frappe.views && frappe.views.MapView;
	if (MapView && !Object.hasOwn(MapView.prototype, "one_loads")) {
		MapView.prototype.one_loads = true;
		const load = MapView.prototype.load_lib;
		MapView.prototype.setup_view = function () {
			return load.call(this).then(() => this.setup_map());
		};
	}
}
