// A desk page whose body is a frappe-ui island (docs/ISLANDS.md). Desk keeps
// the page: its head, breadcrumb, buttons and menu, set from what the island
// reports, the way frappe sets the head of its own Frappe UI pages
// (frappe/ui/island/decisions/0010).
//
// The island gets the route below the page and the query, as frappe's page
// islands do, and reports:
// - `onTitle(title)`: the page's name, after `parent` in the breadcrumb, or
//   `{ title, between }` with `{ label, route }`s between the two;
// - `onStatus({ label, color })`: the indicator beside it, or null;
// - `onActions(actions)`: frappe's `{ label, icon?, onClick | href }`, with
//   `primary` for the page's main button and `button` for one beside it; the
//   rest go in the ··· menu, as frappe puts them.
frappe.provide("onedesk");

onedesk.island_page = (wrapper, { island, title, parent = null, requires = [] }) => {
	const page = frappe.ui.make_app_page({ parent: wrapper, title, single_column: true });
	const $body = $('<div class="one-island"></div>').appendTo(page.main);
	const chrome = { title: null, between: [], status: null, actions: [] };
	let handle = null;

	const draw_chrome = () => {
		const name = chrome.title || title;
		if (parent) onedesk.shell.trail(parent.label, parent.route, name, chrome.between);
		else onedesk.shell.name(name);
		if (chrome.status) page.set_indicator(chrome.status.label, chrome.status.color);
		else page.clear_indicator();
		page.clear_primary_action();
		page.clear_inner_toolbar();
		page.clear_menu();
		for (const action of chrome.actions) {
			const run = action.href ? () => window.open(action.href, "_blank") : action.onClick;
			if (action.primary) page.set_primary_action(action.label, run);
			else if (action.button) page.add_inner_button(action.label, run);
			else page.add_menu_item(action.label, run);
		}
	};
	const where = () => ({
		route: frappe.get_route().slice(1),
		query: Object.fromEntries(new URLSearchParams(window.location.search)),
	});
	const loaded = frappe.require(requires);

	const show = () =>
		loaded.then(() => {
			if (handle) handle.update(where());
			else {
				handle = frappe.ui.mount_island(island, $body[0], {
					...where(),
					onTitle: (said) => {
						chrome.title = typeof said === "string" ? said : said?.title;
						chrome.between = (typeof said === "object" && said?.between) || [];
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
