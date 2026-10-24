// A list on the window (docs/WINDOW.md): frappe's ListView and every view
// made from it (Report, Kanban, Calendar, Gantt, Image, Map, Dashboard,
// Inbox, File), saying what they have through `window.view`. Every node
// handed over is frappe's own, which frappe keeps a reference to, so it still
// shows, hides and relabels them.
onedesk.window.adapt("list", () => {
	// Views drawn as frappe's list rows, which the stylesheet sets as rows.
	const ROWS = ["List", "File", "Inbox"];
	// Views that show a page of records, so a count and paging mean something;
	// a board, a calendar and a dashboard show all of theirs.
	const COUNTED = ["List", "Report", "Image", "Gantt", "Map", "Inbox", "File"];
	const kind = (view) => (ROWS.includes(view.view_name) ? "list" : String(view.view_name || "list").toLowerCase());
	const counted = (view) => COUNTED.includes(view.view_name);

	const Base = frappe.views && frappe.views.BaseList;
	if (Base && !Object.hasOwn(Base.prototype, "one_window")) {
		Base.prototype.one_window = true;
		const menu = Base.prototype.setup_view_menu;
		Base.prototype.setup_view_menu = function (...args) {
			const said = menu.apply(this, args);
			const win = this.page && this.page.window;
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
	if (!List || Object.hasOwn(List.prototype, "one_window")) return;

	// A module's tree, the window's (`win.tree`), under the list's row in the
	// nav pane, for the lists it says are its (`onedesk.window.trees`,
	// { covers(doctype), draw(win, doctype) }): Masters' kinds. Drawn again
	// each time the list is shown, since what it counts changes elsewhere.
	const tree = (view) => {
		const win = view.page && view.page.window;
		const own = win && onedesk.window.trees.find((one) => one.covers(view.doctype));
		if (own) own.draw(win, view.doctype);
	};
	$(document).on("page-change", () => {
		const view = window.cur_list;
		if (view && view.page && frappe.container.page && frappe.container.page.page === view.page) tree(view);
	});
	List.prototype.one_window = true;

	const setup_page = List.prototype.setup_page;
	List.prototype.setup_page = function (...args) {
		const said = setup_page.apply(this, args);
		const win = this.page && this.page.window;
		if (!win) return said;
		const field = this.meta.title_field || "name";
		win.view({
			kind: kind(this),
			primary: this.page.btn_primary,
			menu: { $button: this.page.menu_btn_group, dropdown: this.page.menu_dropdown },
			up: onedesk.window.home,
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
		const win = this.page && this.page.window;
		if (win && this.$paging_area && counted(this)) win.view({ status: "", more: this.$paging_area });
		return said;
	};

	const count = List.prototype.get_count_str;
	List.prototype.get_count_str = function (...args) {
		return count.apply(this, args).then((text) => {
			const win = this.page && this.page.window;
			if (win && counted(this)) win.view({ status: $("<div>").html(String(text)).text() });
			return text;
		});
	};
});
