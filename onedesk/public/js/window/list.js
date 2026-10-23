// A list on the window (docs/WINDOW.md): frappe's ListView, its report, board
// and other views, saying what they have through `window.view`. Every node
// handed over is frappe's own, which frappe keeps a reference to, so it still
// shows, hides and relabels them.
onedesk.window.adapt("list", () => {
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
	List.prototype.one_window = true;

	const setup_page = List.prototype.setup_page;
	List.prototype.setup_page = function (...args) {
		const said = setup_page.apply(this, args);
		const win = this.page && this.page.window;
		if (!win) return said;
		const field = this.meta.title_field || "name";
		const sidebar = frappe.app && frappe.app.sidebar;
		win.view({
			kind: "list",
			primary: this.page.btn_primary,
			menu: { $button: this.page.menu_btn_group, dropdown: this.page.menu_dropdown },
			up: () => sidebar && sidebar.current_module && sidebar.open_module(sidebar.current_module),
			search: {
				placeholder: __("Search {0}", [__(this.doctype)]),
				on_input: (text) => {
					const had = this.filter_area.get().find((one) => one[1] === field && one[2] === "like");
					if (had) this.filter_area.remove(field);
					if (text) this.filter_area.add([[this.doctype, field, "like", `%${text}%`]]);
					else if (had) this.refresh();
				},
			},
		});
		return said;
	};

	const paging = List.prototype.setup_paging_area;
	List.prototype.setup_paging_area = function (...args) {
		const said = paging.apply(this, args);
		const win = this.page && this.page.window;
		if (win && this.$paging_area) win.view({ status: "", more: this.$paging_area });
		return said;
	};

	const count = List.prototype.get_count_str;
	List.prototype.get_count_str = function (...args) {
		return count.apply(this, args).then((text) => {
			const win = this.page && this.page.window;
			if (win) win.view({ status: $("<div>").html(String(text)).text() });
			return text;
		});
	};
});
