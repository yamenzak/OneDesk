/** Workbooks and documents left for another screen, on the bar: leaving one
 * puts it there, going back to it takes it off, and × drops it. One goes
 * straight back; several open a list. Kept in the person's Workbook user
 * settings, and only the ones they may still open are shown (titles in
 * one_sheet/api.py and one_doc/api.py). */
frappe.provide("onedesk.workbooks");

onedesk.workbooks.KEY = "left";
onedesk.workbooks.MOST = 5;
onedesk.workbooks.at = null;
onedesk.workbooks.ready = Promise.resolve();

/** What each kind of page is, by its route: where its titles come from,
 * its mark on the bar, and what an untitled one is called. */
onedesk.workbooks.KINDS = {
	workbook: { titles: "onedesk.one_sheet.api.titles", icon: "onesheet", untitled: () => __("Untitled Workbook") },
	document: { titles: "onedesk.one_doc.api.titles", icon: "onedoc", untitled: () => __("Untitled Document") },
};

onedesk.workbooks.held = () =>
	(frappe.model.user_settings.Workbook?.[onedesk.workbooks.KEY] || []).map((one) => ({ kind: "workbook", ...one }));

onedesk.workbooks.keep = (list) => {
	if (JSON.stringify(list) === JSON.stringify(onedesk.workbooks.held())) return onedesk.workbooks.draw();
	frappe.model.user_settings.Workbook = { ...(frappe.model.user_settings.Workbook || {}), [onedesk.workbooks.KEY]: list };
	onedesk.workbooks.draw();
	return frappe.model.user_settings.update("Workbook", frappe.model.user_settings.Workbook);
};

/** On every route: the workbook just left goes on the bar, the one opened
 * comes off it. */
onedesk.workbooks.here = () => {
	const route = frappe.get_route();
	return onedesk.workbooks.KINDS[route[0]] && route[1] ? { kind: route[0], id: route[1] } : null;
};

onedesk.workbooks.moved = () => {
	const now = onedesk.workbooks.here();
	const was = onedesk.workbooks.at;
	onedesk.workbooks.at = now;
	onedesk.workbooks.ready.then(() => {
		let list = onedesk.workbooks.held().filter((one) => one.id !== now?.id);
		if (was && was.id !== now?.id) {
			const kept = list.find((one) => one.id === was.id);
			list = [kept || { ...was, title: "" }, ...list.filter((one) => one.id !== was.id)].slice(0, onedesk.workbooks.MOST);
		}
		onedesk.workbooks.keep(list);
		if (list.some((one) => !one.title)) onedesk.workbooks.titled(list);
	});
};

onedesk.workbooks.titled = (list) =>
	Promise.all(
		Object.entries(onedesk.workbooks.KINDS).map(([kind, about]) => {
			const names = list.filter((one) => one.kind === kind).map((one) => one.id);
			return names.length ? frappe.xcall(about.titles, { names }) : {};
		})
	).then((found) => {
		const titles = Object.assign({}, ...found);
		onedesk.workbooks.keep(
			onedesk.workbooks.held()
				.filter((one) => titles[one.id] !== undefined)
				.map((one) => ({ ...one, title: titles[one.id] || onedesk.workbooks.KINDS[one.kind].untitled() }))
		);
	});

onedesk.workbooks.drop = (id) => onedesk.workbooks.keep(onedesk.workbooks.held().filter((one) => one.id !== id));

onedesk.workbooks.go = (id) => {
	onedesk.workbooks.close();
	const one = onedesk.workbooks.held().find((held) => held.id === id);
	frappe.set_route(one?.kind || "workbook", id);
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
	const label = list.length === 1 ? __("Back to {0}", [list[0].title]) : __("{0} files open", [list.length]);
	$tile.find(".one-workbooks-text").text(list.length === 1 ? list[0].title : __("{0} files", [list.length]));
	$tile.find(".one-bar-icon").html(frappe.utils.icon(onedesk.workbooks.KINDS[list[0].kind].icon, "sm"));
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

/** The tiles on the bottom bar, drawn once it is there (window/chrome.js). */
onedesk.workbooks.place = (add) => {
	const $group = $('.one-bar [data-group="open"]');
	add({
		label: __("Open Files"),
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
	onedesk.workbooks.at = onedesk.workbooks.here();
	onedesk.workbooks.ready = frappe.model.user_settings.get("Workbook").then((said) => {
		frappe.model.user_settings.Workbook = said;
		const list = onedesk.workbooks.held();
		onedesk.workbooks.draw();
		if (list.length) onedesk.workbooks.titled(list);
	});
	frappe.router.on("change", onedesk.workbooks.moved);
};
