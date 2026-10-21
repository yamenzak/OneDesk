/** Workbooks left for another screen, on the bar: leaving one puts it
 * there, going back to it takes it off, and × drops it. One goes straight
 * back; several open a list. Kept in the person's Workbook user settings,
 * and only the ones they may still open are shown (one_sheet/api.py, titles). */
frappe.provide("onedesk.workbooks");

onedesk.workbooks.KEY = "left";
onedesk.workbooks.MOST = 5;
onedesk.workbooks.at = null;
onedesk.workbooks.ready = Promise.resolve();

onedesk.workbooks.held = () => frappe.model.user_settings.Workbook?.[onedesk.workbooks.KEY] || [];

onedesk.workbooks.keep = (list) => {
	if (JSON.stringify(list) === JSON.stringify(onedesk.workbooks.held())) return onedesk.workbooks.draw();
	frappe.model.user_settings.Workbook = { ...(frappe.model.user_settings.Workbook || {}), [onedesk.workbooks.KEY]: list };
	onedesk.workbooks.draw();
	return frappe.model.user_settings.update("Workbook", frappe.model.user_settings.Workbook);
};

/** On every route: the workbook just left goes on the bar, the one opened
 * comes off it. */
onedesk.workbooks.moved = () => {
	const route = frappe.get_route();
	const now = route[0] === "workbook" && route[1] ? route[1] : null;
	const was = onedesk.workbooks.at;
	onedesk.workbooks.at = now;
	onedesk.workbooks.ready.then(() => {
		let list = onedesk.workbooks.held().filter((one) => one.id !== now);
		if (was && was !== now) {
			const kept = list.find((one) => one.id === was);
			list = [kept || { id: was, title: "" }, ...list.filter((one) => one.id !== was)].slice(0, onedesk.workbooks.MOST);
		}
		onedesk.workbooks.keep(list);
		if (list.some((one) => !one.title)) onedesk.workbooks.titled(list);
	});
};

onedesk.workbooks.titled = (list) =>
	frappe.xcall("onedesk.one_sheet.api.titles", { names: list.map((one) => one.id) }).then((titles) => {
		onedesk.workbooks.keep(
			onedesk.workbooks.held()
				.filter((one) => titles[one.id] !== undefined)
				.map((one) => ({ ...one, title: titles[one.id] || __("Untitled Workbook") }))
		);
	});

onedesk.workbooks.drop = (id) => onedesk.workbooks.keep(onedesk.workbooks.held().filter((one) => one.id !== id));

onedesk.workbooks.go = (id) => {
	onedesk.workbooks.close();
	frappe.set_route("workbook", id);
};

onedesk.workbooks.close = () => $(".one-workbooks-list").removeClass("show");

onedesk.workbooks.draw = () => {
	const esc = frappe.utils.escape_html;
	const list = onedesk.workbooks.held().filter((one) => one.title);
	const $tile = $(".one-workbooks");
	const $x = $(".one-workbooks-x");
	const $menu = $(".one-workbooks-list");
	if (!$tile.length) return;
	$tile.toggleClass("hide", !list.length);
	$x.toggleClass("hide", list.length !== 1);
	if (!list.length) return onedesk.workbooks.close();
	const label = list.length === 1 ? __("Back to {0}", [list[0].title]) : __("{0} workbooks open", [list.length]);
	$tile.find(".one-workbooks-text").text(list.length === 1 ? list[0].title : __("{0} workbooks", [list.length]));
	onedesk.dock.name($tile, label);
	if (list.length === 1) onedesk.dock.name($x, __("Close {0}", [list[0].title]));
	$menu.html(
		list
			.map(
				(one) =>
					`<div class="one-workbooks-item"><button class="dropdown-item" data-open="${esc(one.id)}">${esc(one.title)}</button><button class="one-workbooks-drop" data-drop="${esc(
						one.id
					)}" aria-label="${esc(__("Close {0}", [one.title]))}">${frappe.utils.icon("x", "xs")}</button></div>`
			)
			.join("")
	);
	if (list.length < 2) onedesk.workbooks.close();
};

/** The tiles on the bar, drawn once it is there (desk.js, onedesk.dock.bar). */
onedesk.workbooks.place = (add) => {
	const $group = $('.one-bar [data-group="open"]');
	add({
		label: __("Workbooks"),
		icon: "onesheet",
		css: "one-workbooks hide",
		text: `<span class="one-workbooks-text"></span>`,
		group: "open",
		click: (event) => {
			const list = onedesk.workbooks.held().filter((one) => one.title);
			if (list.length === 1) return onedesk.workbooks.go(list[0].id);
			event.stopPropagation();
			$group.find(".one-workbooks-list").toggleClass("show");
		},
	});
	add({
		label: __("Close"),
		icon: "x",
		css: "one-workbooks-x hide",
		group: "open",
		click: () => onedesk.workbooks.drop(onedesk.workbooks.held().find((one) => one.title)?.id),
	});
	$(`<div class="dropdown-menu one-workbooks-list"></div>`)
		.appendTo($group)
		.on("click", "[data-open]", (event) => onedesk.workbooks.go($(event.currentTarget).attr("data-open")))
		.on("click", "[data-drop]", (event) => {
			event.stopPropagation();
			onedesk.workbooks.drop($(event.currentTarget).attr("data-drop"));
		});
	$(document).on("click", (event) => {
		if (!$(event.target).closest(".one-workbooks-list").length) onedesk.workbooks.close();
	});
	onedesk.workbooks.at = frappe.get_route()[0] === "workbook" ? frappe.get_route()[1] || null : null;
	onedesk.workbooks.ready = frappe.model.user_settings.get("Workbook").then((said) => {
		frappe.model.user_settings.Workbook = said;
		const list = onedesk.workbooks.held();
		onedesk.workbooks.draw();
		if (list.length) onedesk.workbooks.titled(list);
	});
	frappe.router.on("change", onedesk.workbooks.moved);
};
