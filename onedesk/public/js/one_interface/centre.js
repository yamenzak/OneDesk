// The centre frame (onedesk/one_interface/AGENTS.md, Centres): every centre
// opens in it, from its declaration. frappe's SettingsDialog is the engine:
// sections on the left, one at a time on the right. The frame draws one
// header atop the sections (the centre's name and whose it is, with Help,
// Enlarge and Close in the corner, dialogs.js), one search across every
// section, the sections as a list or a tree, and a section's body from the
// kind it declares. A centre declares what it holds, never how it opens:
//
//   onedesk.centers.declare("setup", {
//       help: ["One", "setup"],
//       async sections(ctx) { return [{ group, items: [section, …] }]; },
//   });
//
// A section is { id, label, icon | icon_html, title, description, needs,
// count } and one body: `rows` (a list of rows), `fields` and `save` (a
// form with Save), `section` (a CenterSection, loaded and saved through its
// server module), `page` (words to read, with `before` and `after` around
// them), `opens` (another centre, so no body) or `go` (somewhere else in
// this centre). `render` draws a body itself, only where none of these
// fits, with a docstring saying why.
frappe.provide("onedesk.centers");

onedesk.centers.declared = {};
onedesk.centers.parts = {};
onedesk.centers.shown = {};
onedesk.centers.SEARCH = "__search";

/** Declares a centre by its key (its manifest's Centre.key). */
onedesk.centers.declare = (key, declaration) => {
	onedesk.centers.declared[key] = declaration;
};

/** Declares one module's part of a centre, such as a module's own sections
 * of ControlCenter; what it says stands over the centre's. */
onedesk.centers.part = (key, module, declaration = {}) => {
	onedesk.centers.parts[key] = onedesk.centers.parts[key] || {};
	onedesk.centers.parts[key][module] = declaration;
};

/** The centre a key names, from the registry (frappe.boot.one_centres). */
onedesk.centers.of = (key) => (frappe.boot.one_centres || []).find((one) => one.key === key) || { key, id: key, icon: "circle" };
onedesk.centers.name = (key) => onedesk.names.of(onedesk.centers.of(key).id);

/** The centre a module is, where a list of apps holds one (AccountCenter,
 * TrustCenter): drawn as the centre, as One's rail draws it. */
onedesk.centers.as_centre = (app) => (frappe.boot.one_centres || []).find((one) => onedesk.names.of(one.id) === app) || null;

onedesk.centers.app_icon = (app, fallback = "bell") => {
	const centre = onedesk.centers.as_centre(app);
	return frappe.utils.icon(centre ? centre.icon : onedesk.brand.mark_of(app.replace(/^One/, "")) || fallback, "sm");
};

/** The header atop the sections: the centre's name, drawn as One's names
 * are, and under it, small, whose it is: a module, by its mark and name, or
 * one thing, by an icon and a label (the reader, the workspace, a mailbox). */
onedesk.centers.head = ($into, { key, module = null, label = null, icon = null }) => {
	const $head = $(`<div class="one-module-head"></div>`).prependTo($into);
	const name = onedesk.brand.center(onedesk.centers.name(key).replace(/Center$/, ""));
	$(`<div class="one-module-head-name"></div>`).append(name).appendTo($head);
	const $of = $(`<div class="one-module-head-of"></div>`).appendTo($head);
	const rest = module && module.replace(/^One/, "");
	if (module && rest !== module) $of.append(onedesk.brand.named(rest, true));
	else {
		if (icon) $of.append(frappe.utils.icon(icon, "xs"));
		$(`<span></span>`).text(label || module || "").appendTo($of);
	}
	return $head;
};

/** Whether the reader's role allows a section: `needs` is an ability's key,
 * a list of keys any one of which will do, or a function of them all. */
onedesk.centers.allows = (needs, may) => {
	if (!needs) return true;
	if (typeof needs === "function") return !!needs(may);
	return [].concat(needs).some((key) => may[key]);
};

/** While one of a module's setup steps waits for the reader
 * (one/setup_steps.py), its centre starts with Getting Started, which opens
 * SetupCenter on the module. */
onedesk.centers.starting = (module) => {
	const steps = (frappe.boot.one_setup || {})[module] || [];
	if (!steps.some((step) => !step.done)) return [];
	const item = { id: "getting_started", label: __("Getting Started"), icon: "list-checks", opens: () => onedesk.centers.open("setup", { at: module }) };
	return [{ group: __("Start Here"), items: [item] }];
};

/** What a module's ControlCenter ends with, found rather than declared
 * (docs/READY.md, mechanism 18): Roles and Access for a module that
 * declares abilities, Notifications for one that sends any, OneAI for one
 * OneAI works in, Keyboard Shortcuts for one with keys, and Your Data for
 * every module, each opening its centre on the module. */
onedesk.centers.found = (module) => {
	const has = frappe.boot.one_centers || {};
	const opens = (key) => () => onedesk.centers.open(key, { module });
	const items = [];
	if ((has.access || []).includes(module)) items.push({ id: "access_center", label: __("Roles and Access"), icon: "key-round", opens: opens("access") });
	if ((has.notifications || []).includes(module)) items.push({ id: "notification_center", label: __("Notifications"), icon: "bell", opens: opens("notifications") });
	if ((has.ai || []).includes(module)) items.push({ id: "ai_center", label: onedesk.names.of("one_ai"), icon: "oneai", opens: opens("ai") });
	if (((frappe.boot.one_shortcuts || {}).shortcuts || []).some((one) => one.module === module)) {
		items.push({ id: "shortcut_center", label: __("Keyboard Shortcuts"), icon: "keyboard", opens: opens("shortcuts") });
	}
	items.push({ id: "trust_center", label: __("Your Data"), icon: "shield-check", opens: opens("trust") });
	return [{ group: null, items }];
};

/** The files a module's part needs before it is declared, where they are
 * not loaded with the desk. */
onedesk.centers.FILES = () => ({
	[onedesk.names.of("one_mail")]: ["/assets/onedesk/js/one_mail/onemail_settings.js", "/assets/onedesk/css/one_mail/onemail_settings.css"],
});

onedesk.centers.kit = (() => {
	const esc = frappe.utils.escape_html;
	const saved = () => frappe.show_alert({ message: __("Saved"), indicator: "green" });

	const heading = (title, description) =>
		`<div class="settings-dialog-section-heading"><div class="settings-dialog-section-title">${esc(title)}</div>${
			description ? `<div class="settings-dialog-section-description">${esc(description)}</div>` : ""
		}</div>`;

	const heading_with = (title, description) => {
		const $row = $(`<div class="one-set-heading">${heading(title, description)}<span class="one-set-heading-end"></span></div>`);
		return { $row, $end: $row.find(".one-set-heading-end") };
	};

	const row = ({ lead, title, sub = "", end = "", open = null }) => {
		const $row = $(`<div class="one-set-row${open ? " one-set-row-open" : ""}">
			<span class="one-set-lead">${lead}</span>
			<span class="one-set-text"><span class="one-set-title">${esc(title)}</span>${sub ? `<span class="one-set-sub">${sub}</span>` : ""}</span>
			<span class="one-set-end">${end}</span>
		</div>`);
		if (open) {
			$row.attr({ role: "button", tabindex: 0 }).on("click keydown", (e) => {
				if (e.type === "keydown" && e.key !== "Enter") return;
				if ($(e.target).closest(".one-set-end button, .one-set-end input, .one-set-end label").length) return;
				open();
			});
		}
		return $row;
	};
	const glyph = (name) => `<span class="one-set-glyph">${frappe.utils.icon(name, "sm")}</span>`;
	const chevron = () => `<span class="one-set-chevron">${frappe.utils.icon("chevron-right", "sm")}</span>`;
	const empty = (words) => `<div class="one-set-empty">${esc(words)}</div>`;
	const fields = ($into, list) => {
		const group = new frappe.ui.FieldGroup({ fields: list, body: $into.get(0) });
		group.make();
		return group;
	};
	const button = (opts) => $(frappe.ui.button.html(opts));
	const buttons = ($into) => $(`<div class="one-set-buttons"></div>`).appendTo($into);
	const remove = (click) =>
		button({ variant: "ghost", icon: "x", title: __("Remove"), attrs: { "aria-label": __("Remove") } }).on("click", click);

	const view = (panel, opts) => {
		panel.shown = (panel.shown || 0) + 1;
		panel.set_view(opts);
		return panel.one_back(() => panel.refresh());
	};

	const track = (panel) => {
		const $save = panel.$header.find(".one-set-save").addClass("hide");
		const now = () => JSON.stringify(panel.fieldgroup ? panel.fieldgroup.get_values(true) : {});
		let was = null;
		setTimeout(() => (was = now()), 600);
		const check = () => was !== null && $save.toggleClass("hide", now() === was);
		(panel.fieldgroup?.fields_list || []).forEach((field) => {
			const before = field.df.change;
			field.df.change = function () {
				if (before) before.apply(this, arguments);
				check();
			};
		});
		panel.body.on("input", check);
		panel.clean = () => {
			was = now();
			$save.addClass("hide");
		};
	};

	const switch_at = ($parent, value) => {
		const control = frappe.ui.form.make_control({ df: { fieldtype: "Switch", fieldname: "on", label: "" }, parent: $parent, render_input: true });
		control.set_value(value ? 1 : 0);
		return control;
	};

	const header_switch = (panel, value, change) => {
		const control = switch_at($(`<span class="one-set-switch one-set-head-switch"></span>`).appendTo(panel.$header.find(".settings-dialog-panel-title")), value);
		control.$input.attr("aria-label", panel.item.title);
		const shown = (on) => panel.body.toggleClass("hide", !on);
		control.$input.on("change", async () => {
			const on = control.get_value() ? 1 : 0;
			shown(on);
			await change(on);
			saved();
		});
		shown(value);
		return control;
	};

	const switched = ($body, title, description, value, change) => {
		const top = heading_with(title, description);
		top.$row.appendTo($body);
		const control = switch_at($(`<span class="one-set-switch"></span>`).appendTo(top.$end), value);
		control.$input.on("change", async () => {
			await change(control.get_value() ? 1 : 0);
			saved();
		});
		return control;
	};

	return { esc, saved, heading, heading_with, row, glyph, chevron, empty, fields, button, buttons, remove, view, track, header_switch, switched };
})();

/** Words to read (a Help page, a version, an agreement), laid out for
 * reading: a picture becomes a figure captioned with what it shows, a table
 * scrolls in its own frame. */
onedesk.centers.page = ($into, html) => {
	const $doc = $(`<div class="one-doc"></div>`).html(html).appendTo($into);
	$doc.find("img").each((_i, img) => {
		const $figure = $(`<figure class="one-doc-figure"></figure>`);
		const $p = $(img).parent("p");
		$(img).replaceWith($figure);
		$figure.append(img);
		if (img.alt) $(`<figcaption></figcaption>`).text(img.alt).appendTo($figure);
		if ($p.length && $p.children().length === 1 && !$p.text().trim()) $p.replaceWith($figure);
	});
	$doc.find("table").removeClass("table table-bordered").wrap(`<div class="one-doc-table"></div>`);
	$doc.find("img[data-here]").each((_i, img) => {
		img.addEventListener("error", () => img.dataset.here && img.src !== img.dataset.here && (img.src = img.dataset.here), { once: true });
		if (img.complete && !img.naturalWidth) img.src = img.dataset.here;
	});
	return $doc;
};

/** A page's sections, for the tree and for search: what comes before its
 * first heading, then each heading with what follows it. */
onedesk.centers.sections = (id, title, html) => {
	const found = [{ page: id, anchor: null, title, text: "" }];
	const $doc = $("<div></div>").html(html);
	$doc.find("td, th, li").append(" · ");
	for (const node of $doc.children().toArray()) {
		if (node.tagName === "H2") found.push({ page: id, anchor: node.id, title: node.textContent.trim(), text: "" });
		else found[found.length - 1].text += ` ${node.textContent}`;
	}
	return found.filter((one, i) => i > 0 || one.text.trim());
};

onedesk.centers.search_words = (text) => (text || "").toLowerCase().split(/\s+/).filter(Boolean);
onedesk.centers.matches = (section, words) => {
	const said = `${section.title} ${section.text}`.toLowerCase();
	return words.every((word) => said.includes(word));
};
onedesk.centers.pattern = (words) => new RegExp(`(${words.map((w) => w.replace(/[.*+?^${}()|[\]\\]/g, "\\$&")).join("|")})`, "gi");

/** A line of a section around the first word found, every word marked. */
onedesk.centers.snippet = (text, words) => {
	const flat = text.replace(/\s+/g, " ").trim();
	const lower = flat.toLowerCase();
	const at = Math.min(...words.map((w) => lower.indexOf(w)).filter((i) => i >= 0), flat.length);
	const start = Math.max(0, at - 60);
	const piece = (start ? "…" : "") + flat.slice(start, start + 180) + (start + 180 < flat.length ? "…" : "");
	return frappe.utils.escape_html(piece).replace(onedesk.centers.pattern(words), "<mark>$1</mark>");
};

/** A section's body from the kind it declares, as frappe's settings
 * dialog draws a tab: its `render`. */
onedesk.centers.body = (declared) => {
	const kit = onedesk.centers.kit;
	const item = { title: declared.label, ...declared };
	if (item.section) {
		return {
			...item,
			render(panel) {
				panel.section = panel.section || new item.section(panel, item.id);
				panel.section.open(item.id, { record: item.record || null });
			},
		};
	}
	if (item.rows) {
		return {
			...item,
			async render(panel) {
				const $list = $(`<div class="one-set-list"></div>`).appendTo(panel.body.empty());
				const rows = await item.rows(panel);
				if (!rows.length && item.empty) $list.append(kit.empty(item.empty));
				for (const one of rows) kit.row(one).appendTo($list);
			},
		};
	}
	if (item.fields) {
		return {
			...item,
			actions: [
				{
					label: __("Save"),
					variant: "solid",
					class: "one-set-save",
					click: async (panel) => {
						const values = panel.get_values();
						if (!values) return;
						await item.save(values, panel);
						kit.saved();
						panel.clean && panel.clean();
					},
				},
			],
			async render(panel) {
				panel.body.empty();
				const fields = await item.fields(panel);
				panel.add_fields(fields);
				if (fields.some((one) => !one.read_only)) kit.track(panel);
				else panel.$header.find(".one-set-save").addClass("hide");
			},
		};
	}
	if (item.page !== undefined) {
		return {
			...item,
			render(panel) {
				panel.body.empty();
				if (item.before) item.before(panel);
				const html = typeof item.page === "function" ? item.page(panel) : item.page;
				if (html) onedesk.centers.page(panel.body, html);
				if (item.after) item.after(panel);
				panel.body.off("scroll.one-docs").on("scroll.one-docs", frappe.utils.throttle(() => panel.dialog.spy(item.id), 80));
			},
		};
	}
	return item;
};

onedesk.Centre = class Centre extends frappe.ui.SettingsDialog {
	make() {
		super.make();
		this.$wrapper.addClass("one-set one-centre");
		this.$panels.on("click", ".one-doc a[href]", (event) => {
			const href = $(event.currentTarget).attr("href") || "";
			if (href.includes("://") || href.startsWith("mailto:")) return;
			event.preventDefault();
			const [page, anchor] = href.split("#");
			this.follow ? this.follow(page, anchor) : this.go(page, anchor);
		});
	}

	render_sidebar() {
		this.$sidebar.empty().addClass("one-docs-sidebar");
		this._items = {};
		for (const group of this.tabs) for (const item of group.items || []) this._items[item.id] = item;
		this._items[onedesk.centers.SEARCH] = this.search_item();
		onedesk.centers.head(this.$sidebar, this.whose || this.first_whose);
		if (this.help) {
			this.one_help(() => {
				const [module, page] = typeof this.help === "function" ? this.help(this.active_tab || "") : this.help;
				onedesk.centers.open("help", { module, at: page });
			});
		}

		const $search = $(`<label class="one-docs-search" data-tour="centre-search"></label>`).appendTo(this.$sidebar);
		$search.append(frappe.utils.icon("search", "sm"));
		this.$search = $(`<input type="search" class="one-docs-search-input">`)
			.attr({ placeholder: __("Search"), "aria-label": __("Search") })
			.appendTo($search)
			.on("input", frappe.utils.debounce(() => this.search(this.$search.val()), 120))
			.on("keydown", (event) => {
				if (event.key !== "Escape" || !this.$search.val()) return;
				event.stopPropagation();
				this.$search.val("");
				this.search("");
			});

		this.$tree = $(`<nav class="one-docs-tree" data-tour="centre-tree"></nav>`).appendTo(this.$sidebar);
		const tree = this.tree || this.tabs.flatMap((group) => [...(group.group ? [{ heading: group.group }] : []), ...group.items]);
		this.nested = tree.some((node) => (node.children || []).length);
		for (const node of tree) {
			if (node.heading) $(`<div class="settings-dialog-group-header"><span></span></div>`).find("span").text(node.heading).end().appendTo(this.$tree);
			else this.$tree.append(this.make_node(node, 0));
		}
	}

	make_node(node, depth) {
		const children = node.children || [];
		const $node = $(`<div class="one-docs-node"></div>`).attr("data-node", node.id).toggleClass("open", !!node.open);
		const $row = $(`<button type="button" class="settings-dialog-tab-item one-docs-row"></button>`).css("--depth", depth).appendTo($node);
		if (node.tab !== false) $row.attr("data-tab-id", node.id);
		const $content = $(`<span class="settings-dialog-tab-item-content"></span>`).appendTo($row);
		if (this.nested) {
			const $toggle = $(`<span class="one-docs-toggle"></span>`).appendTo($content);
			if (children.length) {
				$toggle.addClass("has-children").html(frappe.utils.icon("chevron-right", "xs"));
				$toggle.on("click", (event) => {
					event.stopPropagation();
					$node.toggleClass("open");
				});
			}
		}
		const icon = node.icon_html || (node.icon ? frappe.utils.icon(node.icon, "sm") : "");
		if (icon) $(`<span class="settings-dialog-tab-icon"></span>`).html(icon).appendTo($content);
		$(`<span class="settings-dialog-tab-label"></span>`).text(node.label).appendTo($content);
		if (node.hint) $row.attr("title", node.hint);
		if (node.unseen) $(`<span class="one-docs-new"></span>`).attr("aria-label", __("New")).appendTo($content);
		if (node.count) $(frappe.ui.badge.html({ label: String(node.count), theme: "amber" })).addClass("one-docs-waiting").appendTo($content);
		$(`<span class="one-docs-count"></span>`).appendTo($content);
		if (node.opens) $row.addClass("one-set-opens").find(".settings-dialog-tab-item-content").append(frappe.utils.icon("arrow-up-right", "xs"));
		$row.on("click", () => (node.click ? node.click() : this.activate(node.id)));
		if (children.length) {
			const $children = $(`<div class="one-docs-children"></div>`).appendTo($node);
			for (const child of children) $children.append(this.make_node(child, depth + 1));
		}
		return $node;
	}

	node(id) {
		return this.$tree.find(`.one-docs-node[data-node="${CSS.escape(id)}"]`);
	}

	activate(id) {
		const item = this._items[id];
		if (item && item.opens) {
			this.hide();
			item.opens();
			return;
		}
		if (item && item.go) return item.go(this);
		if (item && id !== onedesk.centers.SEARCH) {
			const page = this.key !== "settings" ? this.key : (this.module || "One").toLowerCase();
			onedesk.centers.here = { page, section: id, record: "", label: item.label || "" };
			if (!this.forgets) {
				this.forgets = true;
				this.$wrapper.on("hidden.bs.modal", () => (onedesk.centers.here = null));
			}
		}
		super.activate(id);
		if (!item || id === onedesk.centers.SEARCH) return;
		this.here = id;
		this.node(id).parents(".one-docs-node").addClass("open");
		this.on_page(id);
	}

	/** Only the open page shows its sections in the tree, unless a search
	 * shows more; a branch of pages stays as it is. */
	on_page(id) {
		if (!this.query) {
			this.$tree.find(".one-docs-node").each((_i, el) => {
				if (el.dataset.node.startsWith("module:")) return;
				if (el.querySelector(":scope > .one-docs-children .one-docs-row[data-tab-id]")) return;
				if (!el.querySelector(":scope > .one-docs-children .one-docs-row:not([data-tab-id])")) return;
				$(el).toggleClass("open", el.dataset.node === id);
			});
		}
		this.spy(id);
	}

	/** The section at the top of a page, marked in the tree. */
	spy(id) {
		const panel = this.get_panel(id);
		if (!panel || this.query) return;
		let at = null;
		panel.body.find(".one-doc > h2").each((_i, h2) => {
			if ($(h2).position().top <= 32) at = h2.id;
		});
		this.$tree.find(".one-docs-row.here").removeClass("here");
		if (at) this.node(`${id}#${at}`).children(".one-docs-row").addClass("here");
	}

	/** Opens a section and brings a part of it to the top, its words marked
	 * when they came from a search. */
	async go(id, anchor = null, words = null) {
		if (!this._items[id]) return;
		this.activate(id);
		const panel = this.get_panel(id);
		if (!panel) return;
		const $body = panel.body;
		await Promise.all($body.find("img").toArray().map((img) => img.decode().catch(() => null)));
		$body.find("mark.one-docs-found").contents().unwrap();
		const $at = anchor ? $body.find(`[id="${CSS.escape(anchor)}"]`) : $();
		$body.scrollTop($at.length ? $at.position().top + $body.scrollTop() : 0);
		if (!words || !words.length) return;
		const $doc = $body.find(".one-doc");
		const $section = $at.length ? $at.nextUntil("h2").addBack() : $doc.children().first().nextUntil("h2").addBack();
		$section.each((_i, el) => this.highlight(el, words));
		const $first = $body.find("mark.one-docs-found").first();
		if ($first.length) $body.scrollTop(Math.max(0, $first.position().top + $body.scrollTop() - 96));
	}

	highlight(root, words) {
		const pattern = onedesk.centers.pattern(words);
		const walker = document.createTreeWalker(root, NodeFilter.SHOW_TEXT);
		const nodes = [];
		while (walker.nextNode()) nodes.push(walker.currentNode);
		for (const node of nodes) {
			pattern.lastIndex = 0;
			if (!pattern.test(node.nodeValue)) continue;
			const span = document.createElement("span");
			span.innerHTML = frappe.utils.escape_html(node.nodeValue).replace(pattern, `<mark class="one-docs-found">$1</mark>`);
			node.replaceWith(...span.childNodes);
		}
	}

	/** What search looks through: a page's sections where the centre gave
	 * them, else each section's name and what it is for. */
	searched() {
		const own = (this.index || []).filter((one) => this._items[one.page]);
		const paged = new Set(own.map((one) => one.page));
		const rest = Object.values(this._items)
			.filter((item) => item.id !== onedesk.centers.SEARCH && !paged.has(item.id))
			.map((item) => ({ page: item.id, anchor: null, title: item.label || "", text: [item.title, item.description].filter(Boolean).join(" ") }));
		return [...own, ...rest];
	}

	search_item() {
		return {
			id: onedesk.centers.SEARCH,
			render: (panel) => {
				const words = this.query || [];
				const found = this.searched().filter((one) => onedesk.centers.matches(one, words));
				panel.set_header({
					title: __("Results for “{0}”", [words.join(" ")]),
					description: found.length === 1 ? __("1 matching section") : __("{0} matching sections", [found.length]),
				});
				if (!found.length) {
					$(`<div class="one-docs-none"></div>`).text(__("Nothing matches. Try fewer words.")).appendTo(panel.body);
					return;
				}
				const $list = $(`<div class="one-docs-results"></div>`).appendTo(panel.body);
				for (const one of found) {
					const item = this._items[one.page];
					const $hit = $(`<button type="button" class="one-docs-result"></button>`).appendTo($list);
					const $where = $(`<div class="one-docs-result-where"></div>`).appendTo($hit);
					$where.append(item.icon_html || frappe.utils.icon(item.icon || "file", "sm"), $(`<span></span>`).text(item.label));
					if (one.anchor) $where.append(frappe.utils.icon("chevron-right", "xs"), $(`<span></span>`).text(one.title));
					if (one.text.trim()) $(`<div class="one-docs-result-text"></div>`).html(onedesk.centers.snippet(one.text, words)).appendTo($hit);
					$hit.on("click", () => this.go(one.page, one.anchor, words));
				}
			},
		};
	}

	search(text) {
		const words = onedesk.centers.search_words(text);
		this.$sidebar.toggleClass("searching", !!words.length);
		this.$tree.find(".one-docs-node").removeClass("hit");
		this.$tree.find(".one-docs-count").text("");
		this.query = words.length ? words : null;
		if (!this.query) {
			if (this.here) this.activate(this.here);
			return;
		}
		const counts = {};
		for (const one of this.searched()) {
			if (!onedesk.centers.matches(one, words)) continue;
			counts[one.page] = (counts[one.page] || 0) + 1;
			this.node(one.page).parents(".one-docs-node").addBack().addClass("hit open");
			if (one.anchor) this.node(`${one.page}#${one.anchor}`).addClass("hit");
		}
		for (const [page, count] of Object.entries(counts)) this.node(page).children(".one-docs-row").find(".one-docs-count").text(count);
		const panel = this.get_panel(onedesk.centers.SEARCH);
		if (panel) panel.refresh();
		super.activate(onedesk.centers.SEARCH);
	}
};

/** Opens a centre: the one way in, from a rail row, a link, an address
 * (`?center=`), a module's foot or another centre. `at` is a section, and
 * `record` one record in it; `module` opens a module's part. */
onedesk.centers.open = async (key, { at = null, record = null, module = null, ...rest } = {}) => {
	if (!onedesk.centers.declared[key]) key = "account";
	const ctx = { key, at, record, module, ...rest };
	await frappe.require((module && onedesk.centers.FILES()[module]) || []);
	const declared = onedesk.centers.declared[key];
	const part = declared.part ? declared.part(ctx) : ((onedesk.centers.parts[key] || {})[module] || null);
	module = ctx.module;
	const d = { ...declared, ...(part || {}) };
	const instead = d.instead && d.instead(ctx);
	if (instead) return instead();
	if (d.files) await frappe.require(d.files);
	const said = d.sections ? await d.sections(ctx) : [];
	const { groups, tree = null, index = null } = Array.isArray(said) ? { groups: said } : said;
	const found = d.found ? d.found(ctx) : null;
	const steps = d.steps ? d.steps(ctx) : found;
	const may = d.may ? d.may(ctx) : {};
	const all = [
		...(steps ? onedesk.centers.starting(steps) : []),
		...groups,
		...(found ? [...onedesk.lists.tab(found), ...onedesk.centers.found(found)] : []),
	];
	const shown = all
		.map((group) => ({ ...group, items: (group.items || []).filter((item) => item && onedesk.centers.allows(item.needs, may)).map(onedesk.centers.body) }))
		.filter((group) => group.items.length);
	const items = shown.flatMap((group) => group.items);
	const ids = items.map((item) => item.id);
	const opening = d.at ? d.at(ctx, ids) : ctx.at;
	const own = items.filter((item) => !item.opens);
	if (!own.length && !ids.includes(opening)) return items.length ? items[0].opens() : null;

	const whose = d.whose ? d.whose(ctx) : module ? { key, module } : { key, label: __("Your Workspace"), icon: "building" };
	const kept = `${key}:${module || ""}`;
	if (onedesk.centers.shown[kept]) onedesk.centers.shown[kept].$wrapper.remove();
	const centre = new onedesk.Centre({
		title: onedesk.centers.name(key),
		key,
		module,
		first_whose: { key, ...whose },
		tabs: shown,
		tree,
		index,
		follow: d.follow ? (page, anchor) => d.follow(centre, page, anchor) : null,
		default_tab: ids.includes(opening) ? opening : own[0].id,
		help: typeof d.help === "function" ? (tab) => d.help(tab, ctx) : d.help || null,
	});
	ctx.centre = centre;
	centre.ctx = ctx;
	centre.home = shown;
	if (d.css) centre.$wrapper.addClass(d.css);
	onedesk.centers.shown[kept] = centre;
	centre.show();
	if (d.opened) d.opened(centre, ctx);
	if (d.tour && (frappe.boot.one_tours_unseen || []).includes(`${d.tour[0]}:${d.tour[1]}`)) {
		setTimeout(async () => {
			const tour = await onedesk.tour.here(d.tour[0]);
			if (tour && centre.display) onedesk.tour.run(d.tour[0], tour);
		}, 600);
	}
	return centre;
};

// Every centre on One's rail is found by Ctrl+K too, opened as its row opens it.
if (frappe.search?.utils && !frappe.search.utils.one_centres) {
	const utils = frappe.search.utils;
	utils.one_centres = true;
	const pages = utils.get_pages;
	utils.get_pages = function (keywords) {
		const rail = frappe.boot.module_sidebars?.[onedesk.names.sidebar("one")]?.items || [];
		const centres = rail
			.filter((one) => one.label && (one.url || "").includes("?center="))
			.flatMap((one) => {
				const found = this.fuzzy_search(keywords, one.label, true);
				if (!found.score) return [];
				const asked = Object.fromEntries(new URLSearchParams(one.url.split("?")[1]));
				return [
					{
						type: "Page",
						label: __("Open {0}", [found.marked_string || one.label]),
						value: __("Open {0}", [one.label]),
						match: one.label,
						index: found.score,
						onclick: () => onedesk.centers.open(asked.center, asked),
					},
				];
			});
		return pages.call(this, keywords).concat(centres);
	};
}

// A centre opened by its address, from a link in a mail or a notification:
// /desk/one?center=account&at=plan opens AccountCenter on Plan and Credits
// over Home, and the address loses the question so that going back does not
// open it again.
$(document).on("page-change", () => {
	onedesk.centers.here = null;
	const asked = frappe.utils.get_query_params();
	if (!asked.center) return;
	window.history.replaceState(null, "", window.location.pathname);
	frappe.route_options = null;
	onedesk.centers.open(asked.center, asked);
});
