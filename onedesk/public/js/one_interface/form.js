// A form on the window (onedesk/one_interface/AGENTS.md): frappe's Form, saying what it has
// through `window.view`. Its one main action leads the command row as New
// does on a list (frappe's Save, Submit or Update; when frappe has none, the
// record's own solid button, such as Record Payment), its other buttons
// follow, then frappe's menu. Cancel stays at the row's far end. The ‹ › to
// the record before and after end the address row, the tabs are the row under the
// commands, and who edited it last is the status. Its sidebar is the window's
// details pane, and holds the record panel.
onedesk.interface.adapt("form", () => {
	const Form = frappe.ui.form && frappe.ui.form.Form;
	if (!Form || Object.hasOwn(Form.prototype, "one_interface")) return;
	Form.prototype.one_interface = true;
	const setup = Form.prototype.setup;
	Form.prototype.setup = function (...args) {
		const said = setup.apply(this, args);
		const win = this.page && this.page.interface;
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
			if (onedesk.interface.panelled(this) && $side.length) win.details({ key: "form", width: 400, pane: $side });
		}
		return said;
	};

	// frappe's Create group, what a record leads on to, marked so the command
	// row can lead with it where nothing is solid (window/views.css).
	const Page = frappe.ui.Page;
	const grouped = Page && Page.prototype.get_or_add_inner_group_button;
	if (grouped && !grouped.one_interface) {
		Page.prototype.get_or_add_inner_group_button = function (label, ...rest) {
			const $group = grouped.call(this, label, ...rest);
			if (label === "Create" || label === __("Create")) $group.addClass("one-onward");
			return $group;
		};
		Page.prototype.get_or_add_inner_group_button.one_interface = true;
	}

	// A form's Check fields are frappe's own Switch, which is Check with a
	// switch's markup: the same 0/1, the same df, so every script that reads a
	// checkbox still reads it. Only a form's own fields; a table's rows and a
	// dialog keep their boxes. On a form frappe also draws its read-only tick
	// (a disabled checkbox) inside the switch's label, before the real one, so
	// a click on the label went to it and did nothing. The track says the
	// value instead, read-only too, where frappe builds no checkbox to read.
	const make = frappe.ui.form.make_control;
	const Switch =
		frappe.ui.form.ControlSwitch &&
		class extends frappe.ui.form.ControlSwitch {
			set_disp_area(value) {
				if (this.disp_area) this.disp_area.innerHTML = "";
				this.$wrapper.find(".switch-control").toggleClass("one-on", !!cint(value));
			}
		};
	if (make && Switch && !make.one_interface) {
		frappe.ui.form.make_control = function (opts) {
			const frm = opts && opts.frm;
			if (opts && opts.df && opts.df.fieldtype === "Check" && frm && opts.layout && opts.layout === frm.layout && ((frm.page && frm.page.interface) || frm.one_create)) {
				return new Switch(opts);
			}
			return make.call(this, opts);
		};
		frappe.ui.form.make_control.one_interface = true;
	}

	// Making a record on the window (onedesk/one_interface/AGENTS.md): one dialog for every
	// create, in place of frappe's quick entry and its full-page new form alike.
	// It is frappe's own form, mounted in frappe's SettingsDialog as frappe's
	// Data Import dialog mounts one, so the doctype's scripts, its depends_on and
	// its validation all run as on the page; the form's tabs are the dialog's
	// rail. Saved, it does what quick entry does: fills the link it was asked for
	// from, or hands the record to whoever asked, or opens it.
	const quick = frappe.ui.form.make_quick_entry;
	if (quick && !quick.one_interface) {
		frappe.ui.form.make_quick_entry = function (doctype, after_insert, init_callback, doc, force, skip_insert) {
			const args = arguments;
			// The doctype is loaded first: from a link field it often is not yet.
			return new Promise((resolve) =>
				frappe.model.with_doctype(doctype, () => {
					const meta = frappe.get_meta(doctype);
					if (skip_insert || !meta || meta.istable || meta.issingle || !frappe.ui.SettingsDialog) return resolve(quick.apply(this, args));
					// A doctype whose making is a few questions, not its form, has a dialog of its own.
					const own = onedesk.interface.creators[doctype];
					if (own) return resolve(own({ after_insert, init_callback, doc }));
					resolve(onedesk.interface.create(doctype, { after_insert, init_callback, doc }));
				})
			);
		};
		frappe.ui.form.make_quick_entry.one_interface = true;
	}

	const Layout = frappe.ui.form.Layout;
	if (Layout && !Object.hasOwn(Layout.prototype, "one_interface")) {
		Layout.prototype.one_interface = true;
		const tabbed = Layout.prototype.setup_tabbed_layout;
		Layout.prototype.setup_tabbed_layout = function (...args) {
			const said = tabbed.apply(this, args);
			const win = this.frm && this.frm.page && this.frm.page.interface;
			const $list = this.page.children(".form-tabs-list");
			if (win && $list.length) {
				win.view({ row: $list });
				onedesk.interface.tabs($list);
			}
			return said;
		};
	}

	const Sidebar = frappe.ui.form.Sidebar;
	if (Sidebar && !Object.hasOwn(Sidebar.prototype, "one_interface")) {
		Sidebar.prototype.one_interface = true;
		const refresh = Sidebar.prototype.refresh;
		Sidebar.prototype.refresh = function (...args) {
			const said = refresh.apply(this, args);
			const win = this.frm.page && this.frm.page.interface;
			if (win) {
				win.view({ status: onedesk.interface.edited(this.frm.doc) });
				onedesk.interface.viewers(this.frm, this.sidebar);
				onedesk.interface.cloud(this.frm, this.sidebar);
				win.details_edge();
				onedesk.interface.panel(this.frm, this.sidebar);
				onedesk.interface.panel_refresh(this.frm);
			}
			return said;
		};
	}

	// Frappe draws a record's connections after its sidebar.
	$(document).on("form-refresh", (_, frm) => frm && frm.one_panel && onedesk.interface.panel_refresh(frm));
});

// The record panel: a form's sidebar, as the window's details pane, holds the
// record's Overview (its head: cards, charts, the track, and frappe's own
// stats, heatmap and graph), its Activity (frappe's comments and timeline),
// its Mail and its Connections (frappe's links to the records made from it),
// as tabs under Assign, Tags and Share. Only where the window covers forms and the screen is wide
// enough for frappe to show its sidebar; elsewhere each stays where it was.
onedesk.interface.panelled = (frm) =>
	!!(frm && frm.page && frm.page.interface && onedesk.interface.covers("form") && window.innerWidth >= 992);

onedesk.interface.PANEL = ["overview", "activity", "mail", "connections"];

onedesk.interface.panel = (frm, $sidebar) => {
	if (frm.one_panel || !onedesk.interface.panelled(frm)) return frm.one_panel || null;
	const names = onedesk.interface.PANEL;
	const labels = { overview: __("Overview"), activity: __("Activity"), mail: __("Mail"), connections: __("Connections") };
	// frappe's own icons for these, where it has one (Tab's ICON_MAP).
	const icons = { overview: "layout-dashboard", activity: "rotate-ccw-clock", mail: "mail", connections: "waypoints" };
	const panes = Object.fromEntries(names.map((name) => [name, $(`<div class="one-panel-pane" data-pane="${name}"></div>`)]));
	const tabs = new frappe.ui.Tabs({
		css_class: "one-panel-tabs",
		tabs: names.map((name) => ({ label: "", icon: icons[name], content: panes[name][0] })),
		on_change: (i) => {
			if (!frm.one_panel.picking) onedesk.interface.keep(`panel:${frm.doctype}`, names[i]);
			onedesk.interface.panel_show(frm, names[i]);
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
		onedesk.interface.indicators(sections, head);
		const i = names.indexOf("overview");
		tabs.tabs[i].button.hidden = !(head.children().length || sections.children(":not(.hide-control)").length);
		tabs.position_indicator();
	});
	frm.one_panel = { tabs, panes, head, sections, $panel, watch };
	// And the blocks a doctype adds to frappe's dashboard after a call of its
	// own (hrms's Allocated Leaves, a batch's stock levels): they come into
	// the panel as they land, not only the ones there when it drew.
	const dashboard = frm.dashboard && frm.dashboard.parent && frm.dashboard.parent[0];
	if (dashboard) {
		let due = false;
		new MutationObserver(() => {
			if (due || !dashboard.querySelector(":scope > .form-dashboard-section")) return;
			due = true;
			requestAnimationFrame(() => {
				due = false;
				onedesk.interface.panel_refresh(frm);
			});
		}).observe(dashboard, { childList: true });
	}
	frm.page.interface.panel_frm = frm;
	onedesk.interface.panel_own(frm);
	return frm.one_panel;
};

// What the panel has for this record: its head where it has one, its activity
// where frappe keeps a timeline, its mail where the Mail tab is declared.
onedesk.interface.panel_refresh = (frm) => {
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
	onedesk.interface.indicators(panel.sections, panel.head);
	panel.watch.observe(panel.sections[0], { childList: true, subtree: true });
	onedesk.interface.panel_own(frm);
	const own = (name) => panel.panes[name].children(".one-panel-own").length > 0;
	const has = {
		overview: panel.head.children().length > 0 || panel.sections.children(":not(.hide-control)").filter((_, el) => getComputedStyle(el).display !== "none").length > 0,
		activity: !!(footer && footer.length) || own("activity"),
		mail: onedesk.record_tabs.applies(frm, "mail"),
		connections: !!(links && links.length && !links.hasClass("hide-control")),
	};
	// New Email is the Mail tab's, which has its own; the timeline's goes
	// where the Mail tab is there to write from instead.
	panel.panes.activity
		.find(".timeline-actions .action-btn")
		.filter((_, button) => $(button).text().trim() === __("New Email"))
		.toggle(!has.mail);
	const names = onedesk.interface.PANEL;
	names.forEach((name, i) => (panel.tabs.tabs[i].button.hidden = !has[name]));
	panel.tabs.position_indicator();
	const shown = names.filter((name) => has[name]);
	panel.$panel.toggle(shown.length > 0);
	if (!shown.length) return;
	// The tab somebody last chose for this kind of record, where it has
	// something; else the first that does. Choosing for them is not kept.
	const now = panel.tabs.active === null || panel.tabs.active === undefined ? null : names[panel.tabs.active];
	const kept = onedesk.interface.kept(`panel:${frm.doctype}`, null);
	const want = has[kept] ? kept : shown[0];
	if (want === now) return onedesk.interface.panel_show(frm, want);
	panel.picking = true;
	panel.tabs.set_active(names.indexOf(want));
	panel.picking = false;
};

// What a view on the window drew for the panel itself (frame.js
// `panel_slot`), moved into its tab; a record page made again for another
// record takes the same parts into its new panel.
onedesk.interface.panel_own = (frm) => {
	const panel = frm.one_panel;
	const parts = (frm.page && frm.page.interface && frm.page.interface.panel_parts) || {};
	if (!panel) return;
	for (const [name, $part] of Object.entries(parts)) {
		if (panel.panes[name] && !$.contains(panel.panes[name][0], $part[0])) panel.panes[name].append($part);
	}
};

onedesk.interface.panel_show = (frm, name) => {
	const panel = frm.one_panel;
	if (!panel) return;
	if (name === "mail") onedesk.record_mail.open(frm, panel.panes.mail);
	if (name === "overview") requestAnimationFrame(() => window.dispatchEvent(new Event("resize")));
};

// frappe's stats say "Annual Billing: 92,400.00" in one span; in the
// panel they are figures, the name on the left and the value on the right.
// Where our head shows a figure by the same name, frappe's is the one kept
// and ours steps aside.
onedesk.interface.indicators = ($in, $head) => {
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
onedesk.interface.cloud = (frm, $sidebar) => {
	const $likes = $sidebar.find(".form-stats-likes").first();
	$likes.find(".one-cloud-open").remove();
	if (!onedesk.interface.panelled(frm) || frm.is_new() || !onedesk.record_tabs.applies(frm, "files")) return;
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
	onedesk.interface.cloud_count(frm, ((frm.get_docinfo() || {}).attachments || []).length);
};

onedesk.interface.cloud_count = (frm, count) => {
	const $count = frm.sidebar && frm.sidebar.sidebar && frm.sidebar.sidebar.find(".one-cloud-open .one-files-count");
	if ($count && $count.length) $count.text(count ? cint(count) : "");
};

// A count beside a panel tab's name, as a record tab carries one.
onedesk.interface.panel_count = (frm, name, count) => {
	if (name === "files") onedesk.interface.cloud_count(frm, count);
	const panel = frm.one_panel;
	const i = onedesk.interface.PANEL.indexOf(name);
	if (!panel || i < 0) return;
	const button = panel.tabs.tabs[i].button;
	$(button).find(".one-files-count").remove();
	if (count) $(button).append(`<span class="one-files-count">${cint(count)}</span>`);
};

// Who made a record and who changed it last, for the status row.
onedesk.interface.edited = (doc) => {
	if (!doc || doc.__islocal) return "";
	const by = (user) => frappe.user.full_name(user) || user;
	const created = __("Created {0} by {1}", [frappe.datetime.prettyDate(doc.creation), by(doc.owner)]);
	if (!doc.modified || doc.modified === doc.creation) return created;
	return [__("Edited {0} by {1}", [frappe.datetime.prettyDate(doc.modified), by(doc.modified_by)]), created].join(" · ");
};

// Who else has the record open: frappe's own avatars (frm.viewers, kept live
// over realtime), moved out of the command row into a sidebar row above
// Assign, shown only while somebody is there.
onedesk.interface.viewers = (frm, $sidebar) => {
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
onedesk.interface.tabs = ($list) => {
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

// Dialogs that make a record of one doctype in place of the form
// (one/news's Add News Source): each takes { after_insert } and resolves
// with the record made, or null.
onedesk.interface.creators = onedesk.interface.creators || {};

// At most this many fields to fill, and the create dialog is a small one.
const SMALL = 6;

onedesk.interface.create = (doctype, { after_insert = null, init_callback = null, doc = null } = {}) =>
	new Promise((resolve) =>
		frappe.model.with_doctype(doctype, () => {
			const dialog = new frappe.ui.SettingsDialog({ title: __("New {0}", [__(doctype)]), tabs: [] });
			dialog.$wrapper.addClass("one-create");
			// Each dialog's own listeners: one made over another must not take
			// the other's away when it closes.
			const ns = `.one-create-${frappe.utils.get_random(6)}`;
			const $host = $(`<div class="one-create-form"></div>`).appendTo(dialog.$panels);
			// Save stays at the foot of the dialog whatever tab is open, and says
			// what is still missing while it cannot save.
			const $missing = $(`<div class="one-create-missing"></div>`);
			const $save = frappe.ui.button({ label: __("Save"), variant: "solid", onclick: () => save() });
			const $foot = $(`<div class="one-create-foot"></div>`).append($missing, $save);
			dialog.show();

			const before = window.cur_frm;
			const frm = new frappe.ui.form.Form(doctype, $host[0], false);
			frm.in_dialog = true;
			frm.one_create = dialog;
			const name = doc ? doc.name : frappe.model.make_new_doc_and_get_name(doctype, true);
			if (init_callback) init_callback(frappe.get_doc(doctype, name));
			frm.refresh(name);

			let saved = false;
			// Not returned: frm.save's promise never settles when validation
			// refuses, and frappe's button would stay busy waiting for it.
			const save = () => {
				frm.save("Save", () => {
					if (frm.is_new()) return;
					saved = true;
					dialog.hide();
					// Asked for from a field of a record still being made in a
					// dialog of its own, the field is filled where it is: frappe's
					// way back routes to the calling record, which has no page.
					const from = frappe._from_link;
					if (from && from.field_obj && from.field_obj.frm && from.field_obj.frm.one_create) {
						delete frappe._from_link;
						if (after_insert) after_insert(frm.doc);
						else from.field_obj.set_value(frm.doc.name);
					} else if (from) frappe.ui.form.update_calling_link(frm.doc);
					else if (after_insert) after_insert(frm.doc);
					else frappe.set_route("Form", frm.doctype, frm.doc.name);
				});
			};

			// The rail is the form's tabs that show; a form without tabs is one.
			const tab = (one) => ({
				id: one ? one.df.fieldname : "__details",
				label: one ? __(one.label, null, doctype) : __("Details"),
				// A form with one tab or none has no rail, and its heading says what is made.
				title: one && tabs().length > 1 ? __(one.label, null, doctype) : __("New {0}", [__(doctype)]),
				actions: [{ icon: "x", variant: "ghost", click: () => dialog.hide() }],
				// Beside the panel's body, not in it: the SettingsDialog styles a
				// body's fields as settings rows (a line between switches, a line
				// over each headed section), and this is a form, drawn as on the page.
				on_activate: (panel) => {
					$host.appendTo(panel.$el);
					// A tab's panel is made when first opened, after the foot.
					if ($foot.parent().length) $foot.appendTo(dialog.$panels);
					if (one) one.set_active();
				},
			});
			const tabs = () => (frm.layout.tabs || []).filter((one) => !one.hidden);
			const rail = () => [{ group: __("New {0}", [__(doctype)]), items: (tabs().length ? tabs() : [null]).map(tab) }];
			const drawn = () => tabs().map((one) => one.df.fieldname).join();
			let shown = drawn();
			// reset() empties the panels, the form and the foot among them: they
			// are taken out first, the form put back by the tab that opens.
			const reset = (at = null) => {
				$host.detach();
				$foot.detach();
				dialog.$wrapper.toggleClass("one-create-single", tabs().length < 2);
				// A form of a few fields is a small dialog as tall as they are.
				const asked = frm.fields.filter((one) => one.df && !frappe.model.layout_fields.includes(one.df.fieldtype) && one.df.fieldtype !== "HTML" && one.disp_status === "Write");
				dialog.$wrapper.toggleClass("one-create-small", tabs().length < 2 && asked.length <= SMALL);
				dialog.reset(rail(), at);
				$foot.appendTo(dialog.$panels);
			};
			reset();
			// A tab can come or go as the record is filled in (depends_on).
			const redraw = () => {
				if (drawn() === shown) return;
				shown = drawn();
				const at = dialog.active_tab;
				reset(tabs().some((one) => one.df.fieldname === at) ? at : null);
			};
			// Values change by typing and by scripts (a fetch, a default), which
			// fire nothing on the page: what is missing is read again as the
			// person works and twice a second while the dialog is open.
			const check = () => {
				const missing = onedesk.interface.missing(frm);
				$save.prop("disabled", missing.length > 0);
				$missing.text(missing.length ? __("Still needed: {0}", [missing.join(", ")]) : "");
			};
			const watch = setInterval(check, 500);
			check();
			$(document).on(`form-refresh${ns}`, (_, refreshed) => refreshed === frm && (redraw(), check()));
			frm.$wrapper.on(`change${ns} input${ns}`, () => requestAnimationFrame(() => (redraw(), check())));

			dialog.$wrapper.on(`keydown${ns}`, (e) => {
				if ((e.ctrlKey || e.metaKey) && e.key.toLowerCase() === "s" && !$save.prop("disabled")) {
					e.preventDefault();
					save();
				}
			});
			dialog.$wrapper.on("hide.bs.modal", () => {
				clearInterval(watch);
				$(document).off(ns);
				removeEventListener("beforeunload", frm.beforeUnloadListener, { capture: true });
				if (window.cur_frm === frm) window.cur_frm = before || null;
				if (!saved && frm.doc && frm.doc.__islocal) frappe.model.clear_doc(doctype, frm.doc.name);
				resolve(saved ? frm.doc : null);
			});
		})
	);

// What a record being made still lacks before frappe will save it, read as
// frappe's check_mandatory reads it (every row of it, reqd or
// mandatory_depends_on, frappe's has_value, a name to type where the doctype
// asks for one), only without its scrolling, unfolding and message: a label
// for each, a table's as "Items: Item Code".
onedesk.interface.missing = (frm) => {
	if (!frm || !frm.doc) return [];
	const out = [];
	const mandatory = (doc, df) => {
		const rule = df.mandatory_depends_on;
		if (!rule) return !!df.reqd;
		if (typeof rule === "boolean") return rule;
		if (typeof rule === "function") return !!rule(doc);
		if (rule.startsWith("eval:")) {
			try {
				return !!frappe.utils.eval(rule.slice(5), { doc, parent: frm.doc });
			} catch (e) {
				return false;
			}
		}
		const value = doc[rule];
		return Array.isArray(value) ? !!value.length : !!value;
	};
	if (frm.is_new() && frm.meta.autoname === "Prompt" && !frm.doc.__newname) out.push(__("Name"));
	for (const doc of frappe.model.get_all_docs(frm.doc)) {
		const fields = frappe.meta.get_docfield_copy(doc.doctype, doc.name) || {};
		for (const listed of frappe.meta.docfield_list[doc.doctype] || []) {
			const df = listed.fieldname && fields[listed.fieldname];
			if (!df || df.fieldtype === "Fold" || (!df.reqd && !df.mandatory_depends_on)) continue;
			if (!mandatory(doc, df) || frappe.model.has_value(doc.doctype, doc.name, df.fieldname)) continue;
			const label = __(df.label, null, df.parent);
			const table = doc.parentfield && frappe.meta.get_docfield(frm.doctype, doc.parentfield);
			const said = table ? `${__(table.label, null, frm.doctype)}: ${label}` : label;
			if (!out.includes(said)) out.push(said);
		}
	}
	return out;
};


// A record's shortcuts, as its module declares them in the registry (ready.MODULES "links", frappe.boot.one_interface):
// a new record filled from this one, or the list of those belonging to it. They go through frappe's own sidebar
// user actions, so a shortcut a script adds (a dialog) sits beside them and looks the same.
onedesk.interface.holds = (doc, when) =>
	(when || []).every(([field, op, value]) =>
		op === "=" ? doc[field] == value : op === "!=" ? doc[field] != value : op === "in" ? value.includes(doc[field]) : false
	);

onedesk.interface.links = (frm) => {
	const said = frappe.boot.one_interface?.[frm.doctype]?.links;
	if (!said?.length || frm.is_new() || !frm.sidebar) return;
	frm.sidebar.clear_user_actions();
	for (const link of said) {
		if (!onedesk.interface.holds(frm.doc, link.when)) continue;
		if (link.new ? !frappe.model.can_create(link.new) : !frappe.model.can_read(link.list)) continue;
		const values = Object.fromEntries(Object.entries(link.with).map(([theirs, ours]) => [theirs, frm.doc[ours]]));
		frm.sidebar
			.add_user_action(`${frappe.utils.icon(link.icon, "sm")}<span>${__(link.label)}</span>`, () =>
				link.new ? frappe.new_doc(link.new, values) : frappe.set_route("List", link.list, values)
			)
			.attr("data-kind", link.new ? "new" : "list");
	}
};

Object.keys(frappe.boot.one_interface || {}).forEach((doctype) =>
	frappe.ui.form.on(doctype, { refresh: (frm) => onedesk.interface.links(frm) })
);
