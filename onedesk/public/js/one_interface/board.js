// A Kanban board on the window (onedesk/one_interface/AGENTS.md): frappe's Kanban v2, whose
// code frappe loads only when a board opens, so the adapter waits for the
// class. Its Add and menu lead the command row. Its Filter, Group and
// Settings stay in its own filter row: the board places its quick filters
// beside them, so moving them would take the quick filters too. The older
// board is a list view and list.js has it.
onedesk.interface.adapt("board", () => {
	onedesk.interface.when(frappe.views, "KanbanV2Page", (Board) => {
		if (Object.hasOwn(Board.prototype, "one_interface")) return;
		Board.prototype.one_interface = true;
		const toolbar = Board.prototype.setup_toolbar;
		Board.prototype.setup_toolbar = function (...args) {
			const said = toolbar.apply(this, args);
			const win = this.page && this.page.interface;
			if (win) {
				win.view({
					kind: "board",
					primary: this.page.btn_primary,
					menu: { $button: this.page.menu_btn_group, dropdown: this.page.menu_dropdown },
					up: onedesk.interface.home,
				});
			}
			return said;
		};
	});
});
