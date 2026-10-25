// A module's What's New and Help, in frappe's settings dialog as its
// Settings are (one/versions.py). The sidebar is the module's mark, a search
// and a tree: versions under the major and minor they belong to, or pages
// with their sections. One page at a time on the right, at the dialog's
// width and scrolling in place. Both are written in English only, for the
// people using the module.
frappe.provide("onedesk.whats_new");
frappe.provide("onedesk.help");

onedesk.module_docs = {
	ICONS: { major: "sparkles", minor: "plus", fix: "wrench" },
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

		const $head = $(`<div class="one-docs-head"></div>`).appendTo(this.$sidebar);
		const rest = this.module.replace(/^One/, "");
		$(`<div class="one-docs-name"></div>`)
			.append(rest !== this.module ? onedesk.brand.named(rest, true) : document.createTextNode(this.module))
			.appendTo($head);
		$(`<div class="one-docs-kind"></div>`).text(this.kind).appendTo($head);

		const $search = $(`<label class="one-docs-search"></label>`).appendTo(this.$sidebar);
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

		this.$tree = $(`<nav class="one-docs-tree"></nav>`).appendTo(this.$sidebar);
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
		if (node.note) $(`<span class="one-docs-note"></span>`).text(node.note).appendTo($label);
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

onedesk.whats_new.open = async (module, version = null) => {
	const said = await frappe.xcall("onedesk.one.versions.whats_new", { module });
	const kinds = onedesk.module_docs.KINDS();
	const esc = frappe.utils.escape_html;
	const icon = (one) =>
		one.new
			? `<span class="one-docs-new" aria-label="${esc(__("New"))}"></span>`
			: frappe.utils.icon(onedesk.module_docs.ICONS[one.kind] || "dot", "sm");
	const items = said.versions.map((one) => ({
		id: one.version,
		label: one.version,
		icon_html: icon(one),
		title: one.title,
		description: [kinds[one.kind] || one.kind, frappe.datetime.str_to_user(one.date)].join(" · "),
		render(panel) {
			if (one.new) panel.$header.find(".settings-dialog-panel-title").append(" ", frappe.ui.badge.html({ label: __("New"), theme: "blue" }));
			onedesk.module_docs.page(panel.body.empty(), one.html);
			if (!one.docs.length) return;
			const $more = $(`<div class="one-docs-more"></div>`).appendTo(panel.body);
			$(`<div class="one-docs-more-title"></div>`).text(__("Read More")).appendTo($more);
			for (const page of one.docs) {
				$(frappe.ui.button.html({ label: page.title, variant: "outline", icon: "book-open" }))
					.on("click", () => dialog.follow(page.id))
					.appendTo($more);
			}
		},
	}));

	// A fix sits under the minor it fixes and a minor under its major, each
	// newest first, so the left reads as the module's story.
	const nodes = {};
	for (const one of said.versions) {
		nodes[one.version] = { id: one.version, label: one.version, note: one.title, icon_html: icon(one), open: true, children: [] };
	}
	const roots = [];
	for (const one of said.versions) {
		const [major, minor] = one.version.split(".");
		const parent = { fix: nodes[`${major}.${minor}.0`] || nodes[`${major}.0.0`], minor: nodes[`${major}.0.0`] }[one.kind];
		(parent && parent !== nodes[one.version] ? parent.children : roots).push(nodes[one.version]);
	}

	const dialog = new onedesk.module_docs.Dialog({
		title: __("What's New in {0}", [module]),
		module,
		kind: __("What's New"),
		tabs: [{ items }],
		tree: roots,
		default_tab: version || items[0]?.id,
	});
	dialog.index = said.versions.flatMap((one) => onedesk.module_docs.sections(one.version, `${one.version} ${one.title}`, one.html));
	dialog.follow = (page, anchor = null) => {
		dialog.hide();
		onedesk.help.open(module, page, anchor);
	};
	dialog.show();
	const ours = frappe.boot.one_versions && frappe.boot.one_versions[module];
	if (ours) ours.unseen = 0;
	$(document).trigger("one-version-seen", [module]);
	return dialog;
};

onedesk.help.open = async (module, page = null, anchor = null) => {
	const said = await frappe.xcall("onedesk.one.versions.help_pages", { module });
	const items = said.pages.map((one) => ({
		id: one.id,
		label: one.title,
		icon: one.icon,
		title: one.title,
		render(panel) {
			onedesk.module_docs.page(panel.body.empty(), one.html);
			panel.body.off("scroll.one-docs").on(
				"scroll.one-docs",
				frappe.utils.throttle(() => dialog.spy(one.id), 80),
			);
		},
	}));
	const sections = said.pages.map((one) => onedesk.module_docs.sections(one.id, one.title, one.html));
	const tree = said.pages.map((one, i) => ({
		id: one.id,
		label: one.title,
		icon: one.icon,
		children: sections[i]
			.filter((section) => section.anchor)
			.map((section) => ({
				id: `${one.id}#${section.anchor}`,
				label: section.title,
				tab: false,
				click: () => dialog.go(one.id, section.anchor),
			})),
	}));
	const dialog = new onedesk.module_docs.Dialog({
		title: __("{0} Help", [module]),
		module,
		kind: __("Help"),
		tabs: [{ items }],
		tree,
		default_tab: page || items[0]?.id,
	});
	dialog.index = sections.flat();

	// The section at the top of the page, marked in the tree.
	dialog.spy = (id) => {
		const panel = dialog.get_panel(id);
		if (!panel || dialog.query) return;
		let here = null;
		panel.body.find(".one-doc > h2").each((_i, h2) => {
			if ($(h2).position().top <= 32) here = h2.id;
		});
		dialog.$tree.find(".one-docs-row.here").removeClass("here");
		if (here) dialog.node(`${id}#${here}`).children(".one-docs-row").addClass("here");
	};
	// Only the open page shows its sections, unless a search shows more.
	dialog.on_page = (id) => {
		if (!dialog.query) dialog.$tree.children(".one-docs-node").each((_i, el) => $(el).toggleClass("open", el.dataset.node === id));
		dialog.spy(id);
	};
	dialog.on_page(dialog.active_tab);
	dialog.show();
	if (anchor) setTimeout(() => dialog.go(page, anchor), 300);
	return dialog;
};
