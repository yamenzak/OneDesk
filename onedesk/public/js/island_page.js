frappe.provide("onedesk");

onedesk.island_page = (wrapper, { island, title, parent = null, requires = [], hide_sidebar = false, menu = null, record = null, files = null, mark = null, views = null, bare = null, fit = false }) => {
	const page = frappe.ui.make_app_page({ parent: wrapper, title, single_column: !record, sidebar_position: "Right", hide_sidebar, one_window_fit: fit });
	if (bare) $(wrapper).addClass(bare);
	page.one_record = record;
	// A record page on the window is laid out as a form is (docs/ONEINTERFACE.md,
	// A record page): its sidebar is the details pane with its switch, its
	// own buttons are the command row's, and the island is told it may put
	// its tabs in the view row and its activity in the record panel.
	const win = page.window;
	if (win && record) {
		$(wrapper).addClass("one-record-page");
		win.record_panel = onedesk.window.panelled({ page });
		win.view({ commands: page.custom_actions });
		const $side = page.wrapper.find(".layout-main > .layout-side-section").first();
		if (win.record_panel && $side.length) win.details({ key: "form", width: 400, pane: $side });
	}
	if (mark) page.$title_area.prepend(`<span class="one-shell-mark">${frappe.utils.icon(mark, "md")}</span>`);
	let framed = null;
	let unframe = () => {};
	const frame = () => {
		const name = frappe.get_route()[1];
		if (!record || !name || name === framed) return;
		unframe();
		framed = name;
		unframe = onedesk.record.sidebar(page, record, name, { files: files ? () => view(files) : null });
	};
	const $body = $('<div class="one-island"></div>').appendTo(page.main);
	const chrome = { title: null, between: [], after: [], status: null, actions: [] };
	let handle = null;

	const draw_chrome = () => {
		const name = chrome.title || title;
		if (parent) onedesk.shell.trail(parent.label, parent.route, name, chrome.between, menu, page, chrome.after);
		else onedesk.shell.name(name, { page });
		if (chrome.status) page.set_indicator(chrome.status.label, chrome.status.color);
		else page.clear_indicator();
		page.clear_primary_action();
		page.clear_inner_toolbar();
		page.clear_menu();
		for (const action of chrome.actions) {
			const run = action.href ? () => window.open(action.href, "_blank") : action.onClick;
			if (action.primary) page.set_primary_action(action.label, run);
			else if (action.button) page.add_inner_button(action.label, run);
			else page.add_menu_item(action.label, run, !!action.standard);
		}
		if (views) onedesk.page_views.switcher(page, views);
	};
	const view = (key) => {
		const url = new URL(window.location.href);
		url.searchParams.set("view", key);
		window.history.replaceState(window.history.state, "", url);
		if (handle) handle.update(where());
		page.main[0].scrollIntoView({ block: "start", behavior: "smooth" });
	};
	const where = () => ({
		route: frappe.get_route().slice(1),
		query: Object.fromEntries(new URLSearchParams(window.location.search)),
	});
	const loaded = frappe.require(requires);

	const show = () =>
		loaded.then(() => {
			frame();
			if (handle) handle.update(where());
			else {
				handle = frappe.ui.mount_island(island, $body[0], {
					...where(),
					win: page.window || null,
					onTitle: (said) => {
						chrome.title = typeof said === "string" ? said : said?.title;
						chrome.between = (typeof said === "object" && said?.between) || [];
						chrome.after = (typeof said === "object" && said?.after) || [];
						draw_chrome();
					},
					onStatus: (said) => ((chrome.status = said), draw_chrome()),
					onActions: (said) => ((chrome.actions = said || []), draw_chrome()),
				});
				handle.ready.catch((error) => {
					console.error(`could not mount the "${island}" island`, error);
					$body.html(onedesk.shell.empty(__("This page has not been built"), frappe.boot.developer_mode ? error.message : ""));
				});
			}
			draw_chrome();
		});
	$(wrapper).on("show", show);
	return page;
};
