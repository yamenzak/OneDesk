// A form on the window (docs/WINDOW.md): frappe's Form, saying what it has
// through `window.view`. Its one main action leads the command row as New
// does on a list (frappe's Save, Submit or Update; when frappe has none, the
// record's own solid button, such as Record Payment), its other buttons
// follow, then frappe's menu. Cancel stays at the row's far end. The ‹ › to
// the record before and after go beside Up, the tabs are the row under the
// commands, and who edited it last is the status. Its sidebar is the window's
// details pane, and holds the record panel.
onedesk.window.adapt("form", () => {
	const Form = frappe.ui.form && frappe.ui.form.Form;
	if (!Form || Object.hasOwn(Form.prototype, "one_window")) return;
	Form.prototype.one_window = true;
	const setup = Form.prototype.setup;
	Form.prototype.setup = function (...args) {
		const said = setup.apply(this, args);
		const win = this.page && this.page.window;
		if (win) {
			win.view({
				kind: "form",
				primary: this.page.btn_primary,
				commands: this.page.custom_actions,
				menu: { $button: this.page.menu_btn_group, dropdown: this.page.menu_dropdown },
				steps: this.page.icon_group,
				refresh: () => !this.is_new() && this.reload_doc(),
				up: () => frappe.set_route("List", this.doctype),
			});
			const $side = this.page.wrapper.find(".layout-main > .layout-side-section").first();
			if (onedesk.window.panelled(this) && $side.length) win.details({ key: "form", width: 400, pane: $side });
		}
		return said;
	};

	const Layout = frappe.ui.form.Layout;
	if (Layout && !Object.hasOwn(Layout.prototype, "one_window")) {
		Layout.prototype.one_window = true;
		const tabbed = Layout.prototype.setup_tabbed_layout;
		Layout.prototype.setup_tabbed_layout = function (...args) {
			const said = tabbed.apply(this, args);
			const win = this.frm && this.frm.page && this.frm.page.window;
			const $list = this.page.children(".form-tabs-list");
			if (win && $list.length) {
				win.view({ row: $list });
				onedesk.window.tabs($list);
			}
			return said;
		};
	}

	const Sidebar = frappe.ui.form.Sidebar;
	if (Sidebar && !Object.hasOwn(Sidebar.prototype, "one_window")) {
		Sidebar.prototype.one_window = true;
		const refresh = Sidebar.prototype.refresh;
		Sidebar.prototype.refresh = function (...args) {
			const said = refresh.apply(this, args);
			const win = this.frm.page && this.frm.page.window;
			if (win) {
				win.view({ status: onedesk.window.edited(this.frm.doc) });
				onedesk.window.viewers(this.frm, this.sidebar);
				onedesk.window.cloud(this.frm, this.sidebar);
				win.details_edge();
				onedesk.window.panel(this.frm, this.sidebar);
				onedesk.window.panel_refresh(this.frm);
			}
			return said;
		};
	}

	// Frappe draws a record's connections after its sidebar.
	$(document).on("form-refresh", (_, frm) => frm && frm.one_panel && onedesk.window.panel_refresh(frm));
});

// The record panel: a form's sidebar, as the window's details pane, holds the
// record's Overview (its head: cards, charts, the track, and frappe's own
// stats, heatmap and graph), its Activity (frappe's comments and timeline),
// its Mail and its Connections (frappe's links to the records made from it),
// as tabs under Assign, Tags and Share. Only where the window covers forms and the screen is wide
// enough for frappe to show its sidebar; elsewhere each stays where it was.
onedesk.window.panelled = (frm) =>
	!!(frm && frm.page && frm.page.window && onedesk.window.covers("form") && window.innerWidth >= 992);

onedesk.window.PANEL = ["overview", "activity", "mail", "connections"];

onedesk.window.panel = (frm, $sidebar) => {
	if (frm.one_panel || !onedesk.window.panelled(frm)) return frm.one_panel || null;
	const names = onedesk.window.PANEL;
	const labels = { overview: __("Overview"), activity: __("Activity"), mail: __("Mail"), connections: __("Connections") };
	// frappe's own icons for these, where it has one (Tab's ICON_MAP).
	const icons = { overview: "layout-dashboard", activity: "rotate-ccw-clock", mail: "mail", connections: "waypoints" };
	const panes = Object.fromEntries(names.map((name) => [name, $(`<div class="one-panel-pane" data-pane="${name}"></div>`)]));
	const tabs = new frappe.ui.Tabs({
		css_class: "one-panel-tabs",
		tabs: names.map((name) => ({ label: "", icon: icons[name], content: panes[name][0] })),
		on_change: (i) => {
			if (!frm.one_panel.picking) onedesk.window.keep(`panel:${frm.doctype}`, names[i]);
			onedesk.window.panel_show(frm, names[i]);
		},
	});
	// The bar shows icons; the name is the tab's tooltip and what a screen
	// reader says.
	tabs.tabs.forEach(({ button }, i) => {
		button.title = labels[names[i]];
		button.setAttribute("aria-label", labels[names[i]]);
	});
	// Overview holds our head and, under it, frappe's dashboard sections.
	const head = $(`<div class="one-panel-head"></div>`).appendTo(panes.overview);
	const sections = $(`<div class="one-panel-sections"></div>`).appendTo(panes.overview);
	panes.connections[0].style.setProperty("--one-open", JSON.stringify(__("open")));
	const $panel = $(`<div class="sidebar-section one-panel"></div>`).append(tabs.$el);
	const $after = $sidebar.find(".form-shared").first();
	$after.length ? $panel.insertAfter($after) : $panel.appendTo($sidebar);
	// frappe's stats arrive from a doctype's refresh, after the panel has drawn.
	const watch = new MutationObserver(() => {
		onedesk.window.indicators(sections, head);
		const i = names.indexOf("overview");
		tabs.tabs[i].button.hidden = !(head.children().length || sections.children(":not(.hide-control)").length);
		tabs.position_indicator();
	});
	frm.one_panel = { tabs, panes, head, sections, $panel, watch };
	return frm.one_panel;
};

// What the panel has for this record: its head where it has one, its activity
// where frappe keeps a timeline, its mail where the Mail tab is declared.
onedesk.window.panel_refresh = (frm) => {
	const panel = frm.one_panel;
	if (!panel) return;
	panel.$panel.prop("hidden", frm.is_new());
	if (frm.is_new()) return;
	const footer = frm.footer && frm.footer.wrapper;
	if (footer && footer.length && !$.contains(panel.panes.activity[0], footer[0])) panel.panes.activity.append(footer);
	// Frappe's dashboard leaves its tab for the panel: its connections to
	// Connections, every other section (stats, heatmap, graph, progress, and
	// any a doctype adds) to Overview under the head. The tab, with nothing
	// left in it, hides itself.
	const dashboard = frm.dashboard;
	const links = dashboard && dashboard.links_area && dashboard.links_area.wrapper;
	if (links && links.length && !$.contains(panel.panes.connections[0], links[0])) panel.panes.connections.append(links);
	if (dashboard && dashboard.parent) panel.sections.append(dashboard.parent.children(".form-dashboard-section"));
	onedesk.window.indicators(panel.sections, panel.head);
	panel.watch.observe(panel.sections[0], { childList: true, subtree: true });
	const has = {
		overview: panel.head.children().length > 0 || panel.sections.children(":not(.hide-control)").length > 0,
		activity: !!(footer && footer.length),
		mail: onedesk.record_tabs.applies(frm, "mail"),
		connections: !!(links && links.length && !links.hasClass("hide-control")),
	};
	// New Email is the Mail tab's, which has its own; the timeline's goes
	// where the Mail tab is there to write from instead.
	panel.panes.activity
		.find(".timeline-actions .action-btn")
		.filter((_, button) => $(button).text().trim() === __("New Email"))
		.toggle(!has.mail);
	const names = onedesk.window.PANEL;
	names.forEach((name, i) => (panel.tabs.tabs[i].button.hidden = !has[name]));
	panel.tabs.position_indicator();
	const shown = names.filter((name) => has[name]);
	panel.$panel.toggle(shown.length > 0);
	if (!shown.length) return;
	// The tab somebody last chose for this kind of record, where it has
	// something; else the first that does. Choosing for them is not kept.
	const now = panel.tabs.active === null || panel.tabs.active === undefined ? null : names[panel.tabs.active];
	const kept = onedesk.window.kept(`panel:${frm.doctype}`, null);
	const want = has[kept] ? kept : shown[0];
	if (want === now) return onedesk.window.panel_show(frm, want);
	panel.picking = true;
	panel.tabs.set_active(names.indexOf(want));
	panel.picking = false;
};

onedesk.window.panel_show = (frm, name) => {
	const panel = frm.one_panel;
	if (!panel) return;
	if (name === "mail") onedesk.record_mail.open(frm, panel.panes.mail);
	if (name === "overview") requestAnimationFrame(() => window.dispatchEvent(new Event("resize")));
};

// frappe's stats say "Annual Billing: 92,400.00" in one span; in the
// panel they are figures, the name on the left and the value on the right.
// Where our head shows a figure by the same name, frappe's is the one kept
// and ours steps aside.
onedesk.window.indicators = ($in, $head) => {
	$in.find(".indicator-column > .indicator:not([data-one-split])").each((_, el) => {
		el.dataset.oneSplit = "1";
		if (el.children.length) return;
		const text = el.textContent;
		const at = text.indexOf(": ");
		if (at < 0) return;
		$(el).empty().append($(`<span class="one-indicator-label">`).text(text.slice(0, at)), $(`<span class="one-indicator-value">`).text(text.slice(at + 2)));
	});
	const said = new Set(
		$in
			.find(".form-stats:not(.hide-control) .one-indicator-label")
			.map((_, el) => el.textContent.trim().toLowerCase())
			.get()
	);
	$head.find(".one-stats > *").each((_, el) => {
		const label = $(el).find(".es-stat-card__label").first().text().trim().toLowerCase();
		$(el).toggleClass("one-said", !!label && said.has(label));
	});
};

// The record's files are OneCloud's, not a tab in the row: beside frappe's
// print and like, OneCloud's mark (in its colours, as One names a product),
// with how many files it holds, opens the record's folder in a dialog over
// the record, which closing leaves as it was.
onedesk.window.cloud = (frm, $sidebar) => {
	const $likes = $sidebar.find(".form-stats-likes").first();
	$likes.find(".one-cloud-open").remove();
	if (!onedesk.window.panelled(frm) || frm.is_new() || !onedesk.record_tabs.applies(frm, "files")) return;
	const button = frappe.ui.button({
		icon: "onestorage",
		variant: "ghost",
		size: "sm",
		title: __("Open in OneCloud"),
		css_class: "one-cloud-open",
		onclick: () => onedesk.record_files.dialog(frm),
	}).append(`<span class="one-files-count"></span>`);
	const $print = $likes.children(".form-print");
	$print.length ? button.insertBefore($print) : button.prependTo($likes);
	onedesk.window.cloud_count(frm, ((frm.get_docinfo() || {}).attachments || []).length);
};

onedesk.window.cloud_count = (frm, count) => {
	const $count = frm.sidebar && frm.sidebar.sidebar && frm.sidebar.sidebar.find(".one-cloud-open .one-files-count");
	if ($count && $count.length) $count.text(count ? cint(count) : "");
};

// A count beside a panel tab's name, as a record tab carries one.
onedesk.window.panel_count = (frm, name, count) => {
	if (name === "files") onedesk.window.cloud_count(frm, count);
	const panel = frm.one_panel;
	const i = onedesk.window.PANEL.indexOf(name);
	if (!panel || i < 0) return;
	const button = panel.tabs.tabs[i].button;
	$(button).find(".one-files-count").remove();
	if (count) $(button).append(`<span class="one-files-count">${cint(count)}</span>`);
};

// Who made a record and who changed it last, for the status row.
onedesk.window.edited = (doc) => {
	if (!doc || doc.__islocal) return "";
	const by = (user) => frappe.user.full_name(user) || user;
	const created = __("Created {0} by {1}", [frappe.datetime.prettyDate(doc.creation), by(doc.owner)]);
	if (!doc.modified || doc.modified === doc.creation) return created;
	return [__("Edited {0} by {1}", [frappe.datetime.prettyDate(doc.modified), by(doc.modified_by)]), created].join(" · ");
};

// Who else has the record open: frappe's own avatars (frm.viewers, kept live
// over realtime), moved out of the command row into a sidebar row above
// Assign, shown only while somebody is there.
onedesk.window.viewers = (frm, $sidebar) => {
	const $viewers = frm.viewers && frm.viewers.parent;
	if (!$viewers || !$viewers.length || $viewers.closest(".one-viewers").length) return;
	const $row = $(
		`<div class="sidebar-section one-viewers"><div><span class="form-sidebar-items"><span class="form-sidebar-label">${frappe.utils.icon("eye")}<span class="ellipsis">${__("Viewing now")}</span></span></span></div></div>`
	);
	$row.find(".form-sidebar-items").append($viewers);
	$row.insertBefore($sidebar.find(".form-assignments").first());
};

// A form's tabs on one row: those that do not fit fold into More at its end,
// and the tab you are on is always shown.
onedesk.window.tabs = ($list) => {
	const $ul = $list.children(".form-tabs");
	const $more = $(
		`<li class="nav-item dropdown one-tabs-more"><button class="one-tabs-more-button" type="button" data-toggle="dropdown" aria-haspopup="true" aria-expanded="false">${__("More")} ${frappe.utils.icon("chevron-down", "xs")}</button><div class="dropdown-menu dropdown-menu-right"></div></li>`
	);
	const fold = () => {
		$more.appendTo($ul).hide();
		const $tabs = $ul.children(".nav-item").not($more).removeClass("one-folded");
		const room = $ul[0].clientWidth;
		if (!room || $ul[0].scrollWidth <= room) return;
		$more.show();
		const shown = $tabs.toArray().filter((li) => $(li).css("display") !== "none");
		const active = shown.find((li) => $(li).find(".nav-link.active").length);
		let used = $more.outerWidth(true) + (active ? $(active).outerWidth(true) : 0);
		const folded = [];
		for (const li of shown) {
			if (li === active) continue;
			const width = $(li).outerWidth(true);
			if (!folded.length && used + width <= room) used += width;
			else folded.push(li);
		}
		$(folded).addClass("one-folded");
		$more.find(".dropdown-menu").empty().append(
			folded.map((li) =>
				$(`<a class="dropdown-item" href="#"></a>`)
					.text($(li).find(".nav-link").text().trim())
					.on("click", (e) => {
						e.preventDefault();
						$(li).find(".nav-link").trigger("click");
					})
			)
		);
	};
	const later = () => requestAnimationFrame(fold);
	new ResizeObserver(later).observe($list[0]);
	// A tab made active (from More, or by frappe) is shown: watched on the
	// links, which folding never touches.
	new MutationObserver((changes) => changes.some((one) => one.target.classList.contains("nav-link")) && later()).observe($ul[0], {
		subtree: true,
		attributes: true,
		attributeFilter: ["class"],
	});
	$(document).on("form-refresh", later);
};
