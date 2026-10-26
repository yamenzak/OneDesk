// A module's What's New and Help, in frappe's settings dialog as its
// Settings are (one/versions.py). The sidebar is the module's mark, a search
// and a tree: versions under the major and minor they belong to, or pages
// with their sections. One page at a time on the right, at the dialog's
// width and scrolling in place. Both are written in English only, for the
// people using the module.
frappe.provide("onedesk.whats_new");
frappe.provide("onedesk.help");

onedesk.module_docs = {
	// What's New marks each version by its kind (docs/READY.md, Which number
	// moves): a release, something new, or a fix.
	ICONS: { major: "rocket", minor: "sparkles", fix: "wrench" },
	KINDS: () => ({ major: __("Major"), minor: __("Update"), fix: __("Fix") }),
	SEARCH: "__search",

	// The words of a version or a page, laid out for reading: a picture
	// becomes a figure captioned with what it shows, a table scrolls in its
	// own frame.
	page($into, html) {
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
		return $doc;
	},

	// A page's sections: what comes before its first heading, then each
	// heading with what follows it, for the tree and for search.
	sections(id, title, html) {
		const found = [{ page: id, anchor: null, title, text: "" }];
		const $doc = $("<div></div>").html(html);
		$doc.find("td, th, li").append(" · ");
		for (const node of $doc.children().toArray()) {
			if (node.tagName === "H2") found.push({ page: id, anchor: node.id, title: node.textContent.trim(), text: "" });
			else found[found.length - 1].text += ` ${node.textContent}`;
		}
		return found.filter((one, i) => i > 0 || one.text.trim());
	},

	words(text) {
		return (text || "").toLowerCase().split(/\s+/).filter(Boolean);
	},

	matches(section, words) {
		const said = `${section.title} ${section.text}`.toLowerCase();
		return words.every((word) => said.includes(word));
	},

	pattern(words) {
		return new RegExp(`(${words.map((w) => w.replace(/[.*+?^${}()|[\]\\]/g, "\\$&")).join("|")})`, "gi");
	},

	// A line of a section around the first word found, every word marked.
	snippet(text, words) {
		const flat = text.replace(/\s+/g, " ").trim();
		const lower = flat.toLowerCase();
		const at = Math.min(...words.map((w) => lower.indexOf(w)).filter((i) => i >= 0), flat.length);
		const start = Math.max(0, at - 60);
		const piece = (start ? "…" : "") + flat.slice(start, start + 180) + (start + 180 < flat.length ? "…" : "");
		return frappe.utils.escape_html(piece).replace(onedesk.module_docs.pattern(words), "<mark>$1</mark>");
	},
};

// The settings dialog with its sidebar drawn as the module's own: its mark,
// a search, and a tree whose leaves open the dialog's tabs.
onedesk.module_docs.Dialog = class ModuleDocsDialog extends frappe.ui.SettingsDialog {
	make() {
		super.make();
		this.$wrapper.addClass("one-docs-dialog");
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
		this._items[onedesk.module_docs.SEARCH] = this.search_item();

		const $head = onedesk.module_head(
			this.$sidebar,
			this.module ? { center: this.center, module: this.module } : { center: this.center, label: __("Your Workspace"), icon: "building" },
		);
		if (this.expand) {
			onedesk.module_head_expand($head, () => {
				this.hide();
				this.expand();
			});
		}

		const $search = $(`<label class="one-docs-search" data-tour="docs-search"></label>`).appendTo(this.$sidebar);
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

		this.$tree = $(`<nav class="one-docs-tree" data-tour="docs-tree"></nav>`).appendTo(this.$sidebar);
		for (const node of this.tree) this.$tree.append(this.make_node(node, 0));
	}

	make_node(node, depth) {
		const children = node.children || [];
		const $node = $(`<div class="one-docs-node"></div>`).attr("data-node", node.id).toggleClass("open", !!node.open);
		const $row = $(`<button type="button" class="settings-dialog-tab-item one-docs-row"></button>`)
			.css("--depth", depth)
			.appendTo($node);
		if (node.tab !== false) $row.attr("data-tab-id", node.id);
		const $content = $(`<span class="settings-dialog-tab-item-content"></span>`).appendTo($row);
		const $toggle = $(`<span class="one-docs-toggle"></span>`).appendTo($content);
		if (children.length) {
			$toggle.addClass("has-children").html(frappe.utils.icon("chevron-right", "xs"));
			$toggle.on("click", (event) => {
				event.stopPropagation();
				$node.toggleClass("open");
			});
		}
		const icon = node.icon_html || (node.icon ? frappe.utils.icon(node.icon, "sm") : "");
		if (icon) $(`<span class="settings-dialog-tab-icon"></span>`).html(icon).appendTo($content);
		const $label = $(`<span class="settings-dialog-tab-label"></span>`).text(node.label).appendTo($content);
		if (node.hint) $row.attr("title", node.hint);
		if (node.unseen) $(`<span class="one-docs-new"></span>`).attr("aria-label", __("New")).appendTo($content);
		$(`<span class="one-docs-count"></span>`).appendTo($content);
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
		super.activate(id);
		if (id === onedesk.module_docs.SEARCH) return;
		this.here = id;
		this.node(id).parents(".one-docs-node").addClass("open");
		this.on_page && this.on_page(id);
	}

	// Open a tab and bring a section to the top, its words marked when they
	// came from a search.
	async go(id, anchor = null, words = null) {
		if (!this._items[id]) return;
		this.activate(id);
		const $body = this.get_panel(id).body;
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
		const pattern = onedesk.module_docs.pattern(words);
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

	search_item() {
		return {
			id: onedesk.module_docs.SEARCH,
			render: (panel) => {
				const words = this.query || [];
				const found = (this.index || []).filter((one) => onedesk.module_docs.matches(one, words));
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
					$(`<div class="one-docs-result-text"></div>`).html(onedesk.module_docs.snippet(one.text, words)).appendTo($hit);
					$hit.on("click", () => this.go(one.page, one.anchor, words));
				}
			},
		};
	}

	search(text) {
		const words = onedesk.module_docs.words(text);
		this.$sidebar.toggleClass("searching", !!words.length);
		this.$tree.find(".one-docs-node").removeClass("hit");
		this.$tree.find(".one-docs-count").text("");
		this.query = words.length ? words : null;
		if (!this.query) {
			this.activate(this.here);
			return;
		}
		const counts = {};
		for (const one of this.index || []) {
			if (!onedesk.module_docs.matches(one, words)) continue;
			counts[one.page] = (counts[one.page] || 0) + 1;
			this.node(one.page).parents(".one-docs-node").addBack().addClass("hit open");
			if (one.anchor) this.node(`${one.page}#${one.anchor}`).addClass("hit");
		}
		for (const [page, count] of Object.entries(counts)) this.node(page).children(".one-docs-row").find(".one-docs-count").text(count);
		const panel = this.get_panel(onedesk.module_docs.SEARCH);
		if (panel) panel.refresh();
		super.activate(onedesk.module_docs.SEARCH);
	}
};

// What's New and Help open on a module, or on all of One (`module` null):
// every module that has versions, each a branch of the tree. A page's id is
// the module's own then, `OneMail/overview`, `OneMail@1.6.1`.
onedesk.module_docs.modules = (module) => (module ? [module] : Object.keys(frappe.boot.one_versions || {}));

onedesk.whats_new.open = async (module = null, version = null) => {
	const modules = onedesk.module_docs.modules(module);
	const all = await Promise.all(modules.map((one) => frappe.xcall("onedesk.one.versions.whats_new", { module: one })));
	const kinds = onedesk.module_docs.KINDS();
	const id = (of, one) => (module ? one.version : `${of}@${one.version}`);
	// Every version wears its kind's icon; one the reader hasn't seen has a
	// dot after its number.
	const icon = (one) => frappe.utils.icon(onedesk.module_docs.ICONS[one.kind] || "dot", "sm");
	const items = [];
	const branches = [];
	all.forEach((said, at) => {
		const of = modules[at];
		for (const one of said.versions) {
			items.push({
				id: id(of, one),
				label: one.version,
				icon_html: icon(one),
				title: module ? one.title : `${of} ${one.version} · ${one.title}`,
				description: [kinds[one.kind] || one.kind, frappe.datetime.str_to_user(one.date)].join(" · "),
				render(panel) {
					if (one.new) panel.$header.find(".settings-dialog-panel-title").append(" ", frappe.ui.badge.html({ label: __("New"), theme: "blue" }));
					onedesk.module_docs.page(panel.body.empty(), one.html);
					if (!one.docs.length) return;
					const $more = $(`<div class="one-docs-more"></div>`).appendTo(panel.body);
					$(`<div class="one-docs-more-title"></div>`).text(__("Read More")).appendTo($more);
					for (const page of one.docs) {
						$(frappe.ui.button.html({ label: page.title, variant: "outline", icon: "book-open" }))
							.on("click", () => {
								dialog.hide();
								onedesk.help.open(of, page.id);
							})
							.appendTo($more);
					}
				},
			});
		}
		// A fix sits under the minor it fixes and a minor under its major, each
		// newest first, so the left reads as the module's story.
		const nodes = {};
		for (const one of said.versions) {
			nodes[one.version] = { id: id(of, one), label: one.version, hint: one.title, unseen: !!one.new, icon_html: icon(one), open: true, children: [] };
		}
		const roots = [];
		for (const one of said.versions) {
			const [major, minor] = one.version.split(".");
			const parent = { fix: nodes[`${major}.${minor}.0`] || nodes[`${major}.0.0`], minor: nodes[`${major}.0.0`] }[one.kind];
			(parent && parent !== nodes[one.version] ? parent.children : roots).push(nodes[one.version]);
		}
		branches.push(
			module ? roots : [{ id: `module:${of}`, label: of, icon_html: frappe.utils.icon(of.toLowerCase(), "sm"), tab: false, open: true, children: roots }],
		);
	});

	const dialog = new onedesk.module_docs.Dialog({
		title: module ? __("What's New in {0}", [module]) : __("What's New"),
		module,
		center: "updates",
		tabs: [{ items }],
		tree: branches.flat(),
		default_tab: (module && version) || items[0]?.id,
		expand: module ? () => onedesk.whats_new.open() : null,
	});
	dialog.index = [];
	all.forEach((said, at) =>
		said.versions.forEach((one) => dialog.index.push(...onedesk.module_docs.sections(id(modules[at], one), `${one.version} ${one.title}`, one.html))),
	);
	dialog.show();
	for (const of of modules) {
		const ours = frappe.boot.one_versions && frappe.boot.one_versions[of];
		if (ours) ours.unseen = 0;
		$(document).trigger("one-version-seen", [of]);
	}
	return dialog;
};

onedesk.help.open = async (module = null, page = null, anchor = null) => {
	const modules = onedesk.module_docs.modules(module);
	const all = await Promise.all(modules.map((one) => frappe.xcall("onedesk.one.versions.help_pages", { module: one })));
	const id = (of, one) => (module ? one : `${of}/${one}`);
	const items = [];
	const tree = [];
	const index = [];
	all.forEach((said, at) => {
		const of = modules[at];
		const nodes = [];
		for (const one of said.pages) {
			const here = id(of, one.id);
			items.push({
				id: here,
				label: one.title,
				icon: one.icon,
				title: one.title,
				render(panel) {
					onedesk.module_docs.page(panel.body.empty(), one.html);
					panel.body.off("scroll.one-docs").on(
						"scroll.one-docs",
						frappe.utils.throttle(() => dialog.spy(here), 80),
					);
				},
			});
			const sections = onedesk.module_docs.sections(here, one.title, one.html);
			index.push(...sections);
			nodes.push({
				id: here,
				label: one.title,
				icon: one.icon,
				children: sections
					.filter((section) => section.anchor)
					.map((section) => ({
						id: `${here}#${section.anchor}`,
						label: section.title,
						tab: false,
						click: () => dialog.go(here, section.anchor),
					})),
			});
		}
		tree.push(...(module ? nodes : [{ id: `module:${of}`, label: of, icon_html: frappe.utils.icon(of.toLowerCase(), "sm"), tab: false, open: true, children: nodes }]));
	});
	const dialog = new onedesk.module_docs.Dialog({
		title: module ? __("{0} Help", [module]) : __("Help"),
		module,
		center: "help",
		tabs: [{ items }],
		tree,
		default_tab: (module && page) || items[0]?.id,
		expand: module ? () => onedesk.help.open() : null,
	});
	dialog.index = index;
	// A link in a page is to another page of the same module.
	if (!module) dialog.follow = (to, at = null) => dialog.go(`${dialog.here.split("/")[0]}/${to}`, at);

	// The section at the top of the page, marked in the tree.
	dialog.spy = (here) => {
		const panel = dialog.get_panel(here);
		if (!panel || dialog.query) return;
		let at = null;
		panel.body.find(".one-doc > h2").each((_i, h2) => {
			if ($(h2).position().top <= 32) at = h2.id;
		});
		dialog.$tree.find(".one-docs-row.here").removeClass("here");
		if (at) dialog.node(`${here}#${at}`).children(".one-docs-row").addClass("here");
	};
	// Only the open page shows its sections, unless a search shows more.
	dialog.on_page = (here) => {
		if (!dialog.query) {
			dialog.$tree.find(".one-docs-node").each((_i, el) => {
				if (el.dataset.node.startsWith("module:")) return;
				if (!el.querySelector(":scope > .one-docs-children .one-docs-row:not([data-tab-id])")) return;
				$(el).toggleClass("open", el.dataset.node === here);
			});
		}
		dialog.spy(here);
	};
	dialog.on_page(dialog.active_tab);
	dialog.show();
	if (anchor) setTimeout(() => dialog.go(id(module, page), anchor), 300);
	return dialog;
};

// A module's tours (one/tours.py), one for each area of its screen, each
// step at a `data-tour` mark, on frappe's driver. The area on screen is the
// first whose `at` mark is shown; its tour starts on its own the first time,
// and again from the tour button in the module's foot.
frappe.provide("onedesk.tour");

onedesk.tour.shown = (target) => {
	const el = onedesk.tour.find(target);
	return el && el.getClientRects().length ? el : null;
};

onedesk.tour.here = async (module) => {
	onedesk.tour._of = onedesk.tour._of || {};
	if (!onedesk.tour._of[module]) onedesk.tour._of[module] = frappe.xcall("onedesk.one.tours.tour", { module });
	const tours = await onedesk.tour._of[module];
	return tours.find((one) => onedesk.tour.shown(one.at));
};

onedesk.tour.run = async (module, tour = null) => {
	tour = tour || (await onedesk.tour.here(module));
	const shown = ((tour && tour.steps) || []).map((step) => ({ step, el: onedesk.tour.shown(step.target) })).filter(({ el }) => el);
	if (!shown.length) {
		frappe.show_alert({ message: __("There is no tour of this screen yet."), indicator: "blue" });
		return;
	}
	// A tour of a dialog keeps the dialog above driver's overlay, and each
	// step is outlined in it rather than lifted out of it.
	const in_dialog = shown.some(({ el }) => el.closest(".modal"));
	document.body.classList.toggle("one-tour-in-dialog", in_dialog);
	const done = () => {
		document.body.classList.remove("one-tour-in-dialog");
		const unseen = frappe.boot.one_tours_unseen || [];
		const at = unseen.indexOf(`${module}:${tour.key}`);
		if (at >= 0) unseen.splice(at, 1);
		onedesk.tour._running = false;
		frappe.xcall("onedesk.one.tours.seen", { module, key: tour.key });
	};
	onedesk.tour._running = true;
	const driver = new frappe.Driver({
		className: "frappe-driver one-tour",
		allowClose: true,
		padding: 6,
		opacity: 0.25,
		nextBtnText: __("Next"),
		prevBtnText: __("Previous"),
		doneBtnText: __("Done"),
		closeBtnText: __("Close"),
		onReset: done,
	});
	driver.defineSteps(
		shown.map(({ step, el }) => ({
			element: el,
			popover: { title: step.title, description: step.text, position: step.side },
			onHighlighted: () => {
				onedesk.tour.lift(el);
				if (in_dialog) $(el).parents(".driver-fix-stacking").removeClass("driver-fix-stacking");
			},
		}))
	);
	driver.start();
};

// An island's parts sit in shadow roots of their own, so a mark is looked
// for in every one, and driver's highlight rules are lent to the root it is in.
onedesk.tour.find = (target, root = document) => {
	// A dialog closed earlier can still hold the same mark, so a shown one wins.
	const all = [...root.querySelectorAll(`[data-tour="${CSS.escape(target)}"]`)];
	const el = all.find((one) => one.getClientRects().length) || all[0];
	if (el) return onedesk.tour.lend(el);
	for (const host of root.querySelectorAll("*")) {
		const found = host.shadowRoot && onedesk.tour.find(target, host.shadowRoot);
		if (found) return found;
	}
};

onedesk.tour.lend = (el) => {
	const root = el.getRootNode();
	if (!(root instanceof ShadowRoot)) return el;
	if (!onedesk.tour._sheet) {
		onedesk.tour._sheet = new CSSStyleSheet();
		const rules = [...document.styleSheets].flatMap((sheet) => {
			try {
				return [...sheet.cssRules].map((rule) => rule.cssText).filter((text) => text.includes(".driver-"));
			} catch (e) {
				return [];
			}
		});
		onedesk.tour._sheet.replaceSync(rules.join("\n"));
	}
	if (!root.adoptedStyleSheets.includes(onedesk.tour._sheet))
		root.adoptedStyleSheets = [...root.adoptedStyleSheets, onedesk.tour._sheet];
	return el;
};

// Driver lifts a mark out of the layers above it, but stops at a shadow
// root; the layers outside it (the sticky command row) are lifted here.
onedesk.tour.lift = (el) => {
	for (let at = el.getRootNode().host; at && at !== document.body; at = at.parentElement || at.getRootNode().host) {
		const style = getComputedStyle(at);
		if (/[0-9]/.test(style.zIndex) || +style.opacity < 1 || style.transform !== "none" || style.filter !== "none")
			at.classList.add("driver-fix-stacking");
	}
};

// The first time somebody opens an area of a module, once it has drawn:
// asked when the module draws its foot and whenever the route changes.
onedesk.tour.first = (module) => {
	onedesk.tour._module = module;
	const unseen = (frappe.boot.one_tours_unseen || []).filter((one) => one.startsWith(`${module}:`));
	if (!unseen.length) return;
	// An island draws after its foot, so the area is looked for a few times.
	clearTimeout(onedesk.tour._wait);
	const look = async (left) => {
		if (onedesk.tour._running || onedesk.tour._module !== module || $(".modal.show").length) return;
		const tour = await onedesk.tour.here(module);
		if (tour && unseen.includes(`${module}:${tour.key}`)) onedesk.tour.run(module, tour);
		else if (!tour && left) onedesk.tour._wait = setTimeout(() => look(left - 1), 500);
	};
	onedesk.tour._wait = setTimeout(() => look(10), 1500);
};

frappe.router.on("change", () => onedesk.tour._module && onedesk.tour.first(onedesk.tour._module));
