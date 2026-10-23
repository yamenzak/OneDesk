// A tree on the window (docs/WINDOW.md): frappe's TreeView (accounts, cost
// centres, item groups...). Its New and menu lead the command row as a
// list's do, its views are the same toggles, and the address row's search
// is the tree's own search.
onedesk.window.adapt("tree", () => {
	const Tree = frappe.views && frappe.views.TreeView;
	if (!Tree || Object.hasOwn(Tree.prototype, "one_window")) return;
	Tree.prototype.one_window = true;
	const make_page = Tree.prototype.make_page;
	Tree.prototype.make_page = function (...args) {
		const said = make_page.apply(this, args);
		const win = this.page && this.page.window;
		if (!win) return said;
		win.view({
			kind: "tree",
			primary: this.page.btn_primary,
			menu: { $button: this.page.menu_btn_group, dropdown: this.page.menu_dropdown },
			views: this.views_list,
			up: onedesk.window.home,
			search: {
				placeholder: __("Search {0}", [__(this.doctype)]),
				on_input: (text) => (text ? this.apply_search(text) : this.reset_search()),
			},
		});
		return said;
	};
});
