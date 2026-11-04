frappe.provide("onedesk.crumbs");

onedesk.crumbs.suggest = onedesk.crumbs.suggest || {};

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

const matching = (options, txt) => {
	const word = (txt || "").trim().toLowerCase();
	if (!word) return options;
	const keep = (row) => `${row.label || ""} ${row.description || ""}`.toLowerCase().includes(word);
	return sections(options).map((one) => ({ group: one.group, pinned: one.pinned, options: one.pinned ? one.rows : one.rows.filter(keep) }));
};
onedesk.crumbs.matching = matching;

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

onedesk.crumbs.switch = ($crumb, { options, placeholder = __("Search"), button = false }) => {
	if (!$crumb?.length) return;
	if (!button) $crumb.addClass("one-crumb-switch");
	if (!button) $crumb.find("a").removeAttr("href").attr({ role: "button", tabindex: 0 });
	if (!button && !$crumb.find(".one-crumb-chevron").length) {
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

onedesk.crumbs.places = ($crumb, here) =>
	onedesk.crumbs.switch($crumb, {
		placeholder: __("Go to"),
		options: (txt) => matching(onedesk.panel.options(here), txt),
	});

onedesk.crumbs.records = ($crumb, { doctype, name, list, button = false }) =>
	onedesk.crumbs.switch($crumb, {
		button,
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
			const route = frappe.get_route();
			const form = route[0] === "Form" && route[2] && !String(route[2]).startsWith("new-");
			const doctype = form ? route[1] : this.one_record;
			const name = form ? route[2] : this.one_record && route[1];
			const at = form ? items.length - 1 : items.findIndex((item) => item.one_record);
			this.page_actions?.children(".one-head-record, .one-head-scope").remove();
			const below = (i, kind, wire) => {
				if (at < 0 || i < at || !this.page_actions) return;
				$crumbs.eq(i).addClass(i === at ? "one-crumb-record" : "one-crumb-scope");
				const $button = frappe.ui.button({ label: items[i].label, icon_right: "chevrons-up-down", css_class: kind });
				this.page_actions.prepend($button);
				wire($button);
			};
			const done = new Set();
			const phone_title = frappe.ui.Page.title_action?.();
			items.forEach((item, i) => {
				if (!item.one_menu) return;
				const menu = item.one_menu;
				const options = async (txt) => matching(await menu(), txt);
				if (!(phone_title && i === items.length - 1)) onedesk.crumbs.switch($crumbs.eq(i), { options });
				done.add(i);
				below(i, i === at ? "one-head-record" : "one-head-scope", ($b) => onedesk.crumbs.switch($b, { options, button: true }));
			});
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
			const list = place >= 0 ? items[place].label : null;
			const record = { doctype, name, list };
			if (!window.matchMedia("(max-width: 767.98px)").matches) {
				if (place >= 0 && !done.has(place)) onedesk.crumbs.places($crumbs.eq(place).addClass("one-places"), here);
			} else if (doctype && name && at > 0) {
				const kind = place >= 0 && !done.has(place) ? place : 0;
				onedesk.crumbs.records($crumbs.eq(kind).addClass("one-places"), record);
			}
			if (doctype && name && at >= 0 && !done.has(at)) {
				onedesk.crumbs.records($crumbs.eq(at), record);
				below(at, "one-head-record", ($b) => onedesk.crumbs.records($b, { ...record, button: true }));
			}
		};
	}
}

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
