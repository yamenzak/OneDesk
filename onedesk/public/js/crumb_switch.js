// A crumb is where the reader goes next (docs/STANDARD.md, The breadcrumb).
// Every crumb with somewhere else to go is a switcher: a search box over the
// choices, as frappe-ui's Combobox draws one with trigger="button", in an
// espresso popover with the menu's rows.
// - The place's crumb ("Projects", "Purchase Orders") lists the app's
//   places, the panel's own rows under its section names (panel_menu.js).
// - A record's crumb lists the records of its kind and searches them as a
//   link field does (frappe.desk.search.search_link), with the kind's own
//   suggestions before anything is typed (`onedesk.crumbs.suggest`), and
//   the whole list last.
// - A crumb a page gives choices of its own (shell.trail's `menu` and
//   `after`) lists those, filtered by what is typed.
frappe.provide("onedesk.crumbs");

// Per doctype, what its record's crumb offers before anything is typed:
// `(current) => options`, frappe.ui.Dropdown's options or a Promise of them.
onedesk.crumbs.suggest = onedesk.crumbs.suggest || {};

// The choices as rows and sections, `{ label, description, icon, selected,
// onclick }` and `{ group, options }`, whatever shape they came in.
const sections = (options) => {
	const out = [];
	for (const one of (options || []).filter(Boolean)) {
		if (one.group !== undefined) {
			const rows = (one.options || []).filter(Boolean);
			if (rows.length) out.push({ group: one.group, rows, pinned: !!one.pinned });
		} else if (out.length && out[out.length - 1].group === null) out[out.length - 1].rows.push(one);
		else out.push({ group: null, rows: [one] });
	}
	return out;
};

// What a typed word keeps of fixed choices.
const matching = (options, txt) => {
	const word = (txt || "").trim().toLowerCase();
	if (!word) return options;
	const keep = (row) => `${row.label || ""} ${row.description || ""}`.toLowerCase().includes(word);
	return sections(options).map((one) => ({ group: one.group, pinned: one.pinned, options: one.pinned ? one.rows : one.rows.filter(keep) }));
};
onedesk.crumbs.matching = matching;

// The panel: the search row, then the rows, then the pinned ones (the whole
// list) under them, as frappe-ui's Combobox has its footer; the highlight
// moved by the arrow keys and the pointer alike, as frappe's menu moves its
// data-highlighted.
const panel = ({ options, placeholder, picked }) => {
	const $panel = $(`<div class="one-crumb-switch-panel">
		<label class="one-crumb-switch-search">
			${frappe.utils.icon("search", "sm")}
			<input type="text" autocomplete="off" spellcheck="false" role="combobox" aria-expanded="true" aria-autocomplete="list">
		</label>
		<div class="one-crumb-switch-rows" role="listbox"></div>
		<div class="one-crumb-switch-foot"></div>
	</div>`);
	const $input = $panel.find("input").attr({ placeholder, "aria-label": placeholder });
	const $rows = $panel.find(".one-crumb-switch-rows");
	const $foot = $panel.find(".one-crumb-switch-foot");
	let rows = [];
	let asked = 0;

	const highlight = (at) => {
		rows.forEach((row, i) => (i === at ? row.el.setAttribute("data-highlighted", "") : row.el.removeAttribute("data-highlighted")));
		if (rows[at]) rows[at].el.scrollIntoView({ block: "nearest" });
	};
	const lit = () => rows.findIndex((row) => row.el.hasAttribute("data-highlighted"));
	const choose = (row) => {
		if (!row) return;
		picked();
		row.item.onclick?.();
	};

	const draw = (options) => {
		$rows.empty();
		$foot.empty();
		rows = [];
		const found = sections(options);
		if (!found.some((one) => !one.pinned)) $rows.append($('<div class="es-menu__empty"></div>').text(__("No matches")));
		for (const one of found) {
			const $group = $('<div class="es-menu__group" role="group"></div>').appendTo(one.pinned ? $foot : $rows);
			if (one.group) $('<div class="es-menu__group-label"></div>').text(one.group).appendTo($group);
			const spaced = one.rows.some((row) => row.icon);
			for (const item of one.rows) {
				const el = document.createElement("button");
				el.type = "button";
				el.className = "es-menu__item";
				el.setAttribute("role", "option");
				el.setAttribute("tabindex", "-1");
				if (item.selected) {
					el.setAttribute("data-state", "checked");
					el.setAttribute("aria-selected", "true");
				}
				if (item.icon) el.insertAdjacentHTML("beforeend", frappe.utils.icon(item.icon, "sm", "", "", "", true));
				else if (spaced) el.insertAdjacentHTML("beforeend", '<span class="es-menu__icon-space" aria-hidden="true"></span>');
				const label = $('<span class="es-menu__label"></span>').text(item.label || "");
				if (item.description) label.append($('<span class="es-menu__description"></span>').text(item.description));
				el.appendChild(label[0]);
				const row = { el, item };
				el.addEventListener("pointermove", () => highlight(rows.indexOf(row)));
				el.addEventListener("click", () => choose(row));
				rows.push(row);
				$group.append(el);
			}
		}
		highlight(Math.max(0, rows.findIndex((row) => row.item.selected && $input.val() === "")));
	};

	const load = async () => {
		const mine = ++asked;
		const got = await options($input.val().trim());
		if (mine === asked) draw(got);
	};
	const typed = frappe.utils.debounce(load, 200);
	$input.on("input", typed);
	$input.on("keydown", (e) => {
		const at = lit();
		if (e.key === "ArrowDown" || e.key === "ArrowUp") {
			e.preventDefault();
			if (!rows.length) return;
			const step = e.key === "ArrowDown" ? 1 : -1;
			highlight((at + step + rows.length) % rows.length);
		} else if (e.key === "Enter") {
			e.preventDefault();
			choose(rows[at] || rows[0]);
		}
	});
	$rows.append(`<div class="es-menu__loading"><span class="es-spinner" aria-hidden="true"></span><span>${__("Loading...")}</span></div>`);
	load();
	return { el: $panel[0], focus: () => $input.trigger("focus") };
};

// A crumb made a switcher. `options(txt)` gives the rows for what is typed.
onedesk.crumbs.switch = ($crumb, { options, placeholder = __("Search") }) => {
	if (!$crumb?.length) return;
	$crumb.addClass("one-crumb-switch");
	// The crumb opens its switcher; where it led is the first of its rows.
	$crumb.find("a").removeAttr("href").attr({ role: "button", tabindex: 0 });
	if (!$crumb.find(".one-crumb-chevron").length) {
		$crumb.children().first().append($(frappe.utils.icon("chevrons-up-down", "xs")).addClass("one-crumb-chevron"));
	}
	let drawn = null;
	const popover = new frappe.ui.Popover({
		trigger: $crumb,
		css_class: "one-crumb-switch-popover",
		content: () => (drawn = panel({ options, placeholder, picked: () => popover.close("owner") })).el,
		on_open: () => drawn?.focus(),
	});
};

// The place's switcher: the panel's rows, `here` ticked, the typed word
// matched against a row's name and its section's.
onedesk.crumbs.places = ($crumb, here) =>
	onedesk.crumbs.switch($crumb, {
		placeholder: __("Go to"),
		options: (txt) => matching(onedesk.panel.options(here), txt),
	});

// A record's switcher: the records of its kind, as a link field finds them.
onedesk.crumbs.records = ($crumb, { doctype, name, list }) =>
	onedesk.crumbs.switch($crumb, {
		placeholder: __("Search {0}", [list || __(doctype)]),
		options: async (txt) => {
			const all = { label: __("All {0}", [list || __(doctype)]), icon: "list", onclick: () => frappe.set_route("List", doctype) };
			const open = (one) => () => frappe.set_route("Form", doctype, one);
			let found;
			if (!txt && onedesk.crumbs.suggest[doctype]) found = await onedesk.crumbs.suggest[doctype](name);
			else {
				const said = await frappe.xcall("frappe.desk.search.search_link", { doctype, txt, page_length: 12 });
				found = (said || []).map((one) => ({
					label: one.label || one.value,
					description: [one.label && one.label !== one.value ? one.value : "", one.description || ""].filter(Boolean).join(" · "),
					selected: one.value === name,
					onclick: open(one.value),
				}));
			}
			return [...(found || []), { group: "", pinned: true, options: [all] }];
		},
	});

// Each drawing of a page's trail makes its crumbs switchers: the crumbs a
// page gave choices to, the record's own, and the one that names the place.
{
	const Page = frappe.ui.Page;
	if (Page && !Page.prototype.__one_crumb_switch) {
		Page.prototype.__one_crumb_switch = true;
		const drawn = Page.prototype.render_breadcrumbs;
		Page.prototype.render_breadcrumbs = function () {
			drawn.call(this);
			const $crumbs = this.$breadcrumbs && this.$breadcrumbs.children("li");
			if (!$crumbs || !$crumbs.length) return;
			const items = this.get_breadcrumbs();
			const done = new Set();
			items.forEach((item, i) => {
				if (!item.one_menu) return;
				const menu = item.one_menu;
				onedesk.crumbs.switch($crumbs.eq(i), { options: async (txt) => matching(await menu(), txt) });
				done.add(i);
			});
			// The record: a form's, or a record page's (onedesk.island_page `record`).
			const route = frappe.get_route();
			const form = route[0] === "Form" && route[2] && !String(route[2]).startsWith("new-");
			const doctype = form ? route[1] : this.one_record;
			const name = form ? route[2] : this.one_record && route[1];
			const at = form ? items.length - 1 : items.findIndex((item) => item.one_record);
			// The place: the crumb that leads back to it, or the place's own page.
			let place = -1;
			let here = null;
			items.forEach((item, i) => {
				if (place >= 0 || done.has(i) || i === at || !item.href) return;
				const row = onedesk.panel.row(item.href);
				if (row) [place, here] = [i, row];
			});
			if (place < 0 && at < 0) {
				here = onedesk.panel.row(window.location.pathname);
				if (here) place = items.length - 1;
			}
			if (place >= 0 && !done.has(place)) onedesk.crumbs.places($crumbs.eq(place).addClass("one-places"), here);
			if (doctype && name && at >= 0 && !done.has(at)) {
				const list = place >= 0 ? items[place].label : null;
				onedesk.crumbs.records($crumbs.eq(at), { doctype, name: decodeURIComponent(name), list });
			}
		};
	}
}

// The panel is drawn after the page on a cold load: the trail is drawn again
// once it is there, so the place's crumb finds its rows.
{
	const Sidebar = frappe.ui.Sidebar;
	if (Sidebar && !Sidebar.prototype.__one_crumb_panel) {
		Sidebar.prototype.__one_crumb_panel = true;
		const made = Sidebar.prototype.make_sidebar;
		Sidebar.prototype.make_sidebar = function (...args) {
			const result = made.apply(this, args);
			frappe.get_current_page?.()?.render_breadcrumbs();
			return result;
		};
	}
}
