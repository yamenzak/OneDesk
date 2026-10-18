
frappe.provide("onedesk.outside");

onedesk.outside.skipping = (page, labels, build) => {
	const add = page.add_menu_item;
	page.add_menu_item = function (label, ...rest) {
		return labels.includes(label) ? $() : add.call(this, label, ...rest);
	};
	try {
		return build();
	} finally {
		page.add_menu_item = add;
	}
};

onedesk.outside.without = (groups, names) =>
	(groups || []).map((group) => ({
		...group,
		options: Array.isArray(group.options)
			? group.options.filter((one) => !names.includes(one.name))
			: group.options,
	}));

(() => {
	const Toolbar = frappe.ui.form && frappe.ui.form.Toolbar;
	if (!Toolbar || Toolbar.prototype.one_outside) return;
	Toolbar.prototype.one_outside = true;
	const audit = Toolbar.prototype.add_audit_trail;
	Toolbar.prototype.add_audit_trail = function () {
		if (frappe.model.can_read("Audit Trail")) audit.call(this);
	};
})();

(() => {
	const Report = frappe.views && frappe.views.ReportView;
	if (!Report || Report.prototype.one_outside) return;
	Report.prototype.one_outside = true;
	const items = Report.prototype.report_menu_items;
	Report.prototype.report_menu_items = function () {
		const menu = items.call(this);
		return frappe.model.can_read("Auto Email Report")
			? menu
			: menu.filter((one) => one.label !== __("Setup Auto Email"));
	};
})();

(() => {
	const form = frappe.ui.form;
	if (!form || Object.getOwnPropertyDescriptor(form, "PrintView")?.set) return;
	let View = form.PrintView;
	Object.defineProperty(form, "PrintView", {
		configurable: true,
		get: () => View,
		set(value) {
			View = class OnePrintView extends value {
				setup_menu() {
					if (!frappe.boot.one_elsewhere) return super.setup_menu();
					return onedesk.outside.skipping(this.page, [__("Print Settings")], () => super.setup_menu());
				}
			};
		},
	});
})();

if (frappe.boot.one_elsewhere && frappe.ui.SidebarHeader && frappe.ui.Sidebar) {
	frappe.ui.SidebarHeader = class OneSidebarHeader extends frappe.ui.SidebarHeader {
		menu_items() {
			return onedesk.outside.without(super.menu_items(), ["edit-sidebar", "all-apps"]);
		}

		get_custom_help_links() {
			return [
				{
					name: "ask-oneai",
					label: __("Ask OneAI"),
					icon: "sparkles",
					onclick: () => onedesk.oneai.open({ ask: __("How does this page work?") }),
				},
			];
		}
	};
	frappe.ui.Sidebar = class OneUserMenuSidebar extends frappe.ui.Sidebar {
		create_user_menu(args) {
			const Dropdown = frappe.ui.Dropdown;
			frappe.ui.Dropdown = class extends Dropdown {
				constructor(opts) {
					const options = onedesk.outside.without(opts.options, ["workspace-selector"]);
					const group = options.find((one) => Array.isArray(one.options) && one.options.some((o) => o.name === "reload"));
					group?.options.splice(group.options.findIndex((o) => o.name === "reload"), 0, {
						name: "theme",
						label: __("Theme"),
						icon: "sun-moon",
						onclick: () => new frappe.ui.ThemeSwitcher().show(),
					});
					super({ ...opts, options });
				}
			};
			try {
				return super.create_user_menu(args);
			} finally {
				frappe.ui.Dropdown = Dropdown;
			}
		}
	};
}

onedesk.outside.instead = (sub_path) => {
	const [doctype, name] = (sub_path || "").split("/");
	const me = frappe.session.user;
	switch (doctype) {
		case "notification-settings":
			return ["settings", { section: "notifications" }];
		case "user":
			if (name && decodeURIComponent(name) === me) return ["settings", { section: "profile" }];
			return name && name !== "new" && !name.startsWith("new-")
				? ["workspace-settings", { section: "people", person: decodeURIComponent(name) }]
				: ["workspace-settings", { section: "people" }];
		case "file":
			return name ? null : ["onecloud"];
		case "todo":
			return name ? null : ["my-tasks"];
		case "print-settings":
			return ["workspace-settings", { section: "printing" }];
		case "print-format":
		case "letter-head":
			return name ? null : ["workspace-settings", { section: "printing" }];
		case "communication":
			return !name || name === "view" ? ["onemail"] : null;
	}
	return null;
};

if (frappe.boot.one_elsewhere) {
	const own = frappe.router.re_route;
	frappe.router.re_route = function (sub_path) {
		const instead = onedesk.outside.instead(sub_path);
		if (!instead) return own.call(this, sub_path);
		frappe.route_flags.replace_route = true;
		frappe.set_route(...instead);
		return true;
	};
}

onedesk.outside.ours = (kind) => {
	const named = new Set();
	for (const sidebar of Object.values(frappe.boot.module_sidebars || {})) {
		for (const item of sidebar.items || []) if (item.link_type === kind && item.link_to) named.add(item.link_to);
	}
	return named;
};

if (frappe.boot.one_elsewhere && frappe.search?.utils) {
	const utils = frappe.search.utils;
	const app_of = (module) => (frappe.boot.module_app || {})[frappe.scrub(module || "")];
	const keep = (kind, info, found) => {
		const named = onedesk.outside.ours(kind);
		return found.filter((one) => {
			const name = (one.route || []).at(-1);
			return named.has(name) || app_of(info[name]?.module) === "onedesk";
		});
	};
	const pages = utils.get_pages;
	utils.get_pages = function (keywords) {
		const found = pages.call(this, keywords).filter((one) => one.type !== "Calendar");
		return keep("Page", frappe.boot.page_info || {}, found);
	};
	const reports = utils.get_reports;
	utils.get_reports = function (keywords) {
		return keep("Report", frappe.boot.allowed_reports || {}, reports.call(this, keywords));
	};
}

let drawn = 0;
onedesk.outside.lost = ({ code = "", core = "one" }) => {
	const id = `one-lost-${++drawn}`;
	const digit = (d) => (code ? `<span class="one-lost__digit">${d}</span>` : "");
	const mark = {
		empty: "",
		check: `<path d="M74 97l15 15 30-32" stroke-width="12"/>`,
	}[core] ?? `<path d="M86 78l10-8v52M84 122h24" stroke-width="12"/>`;
	return `<div class="one-lost__art" aria-hidden="true">${digit(code[0])}<span class="one-lost__ring">
		<span class="one-lost__orbit"><i></i><i></i><i></i><i></i></span>
		<svg viewBox="19 19 154 154" fill="none"><defs>
			<linearGradient id="${id}-band" x1="28" y1="28" x2="164" y2="164" gradientUnits="userSpaceOnUse">
				<stop offset="0" style="stop-color: var(--one-suite-1)"/><stop offset=".35" style="stop-color: var(--one-suite-2)"/>
				<stop offset=".68" style="stop-color: var(--one-suite-3)"/><stop offset="1" style="stop-color: var(--one-suite-4)"/></linearGradient>
			<radialGradient id="${id}-core" cx="96" cy="96" r="54" gradientUnits="userSpaceOnUse">
				<stop offset="0" style="stop-color: var(--one-suite-core-glow)"/><stop offset="1" style="stop-color: var(--one-suite-core)"/></radialGradient></defs>
			<circle class="one-lost__band" cx="96" cy="96" r="68" stroke="url(#${id}-band)" stroke-width="18"/>
			<circle cx="96" cy="96" r="52" fill="url(#${id}-core)"/>
			<circle cx="96" cy="96" r="52" style="stroke: var(--one-suite-glint)" stroke-opacity=".12" stroke-width="1.5"/>
			<g class="one-lost__core one-lost__core--${core}" style="stroke: var(--one-suite-glint)" stroke-linecap="round" stroke-linejoin="round">${mark}</g>
		</svg></span>${digit(code[2])}</div>`;
};

if (frappe.boot.one_elsewhere) {
	const draw = (page_name, { title, line, ...art }) => {
		page_name = page_name || frappe.get_route_str();
		const wrapper = frappe.pages[page_name] || frappe.container.add_page(page_name);
		if (!wrapper.page) frappe.ui.make_app_page({ parent: wrapper, single_column: true });
		const $scene = $(`<div class="one-lost one-lost--desk">
			${onedesk.outside.lost(art)}
			<h1>${frappe.utils.escape_html(title)}</h1>
			<p class="one-lost__line">${frappe.utils.escape_html(line)}</p>
			<div class="one-lost__actions">
				${frappe.ui.button.html({ label: __("Go Back"), size: "md", attrs: { "data-go": "back" } })}
				${frappe.ui.button.html({ label: __("Go Home"), size: "md", variant: "solid", attrs: { "data-go": "home" } })}
			</div>
		</div>`);
		$scene.find("[data-go=back]").on("click", () => window.history.back());
		$scene.find("[data-go=home]").on("click", () => frappe.set_route("one"));
		$(wrapper.page.main).empty().append($scene);
		frappe.container.change_to(page_name);
	};
	frappe.show_not_found = (page_name) =>
		draw(page_name, {
			code: "404",
			core: "empty",
			title: __("Page not found"),
			line: __("The link may be broken, or the page has moved."),
		});
	frappe.show_not_permitted = (page_name) =>
		draw(page_name, {
			code: "403",
			core: "empty",
			title: __("No access"),
			line: __("Ask an administrator for access."),
		});

	const show = frappe.views.pageview.show;
	frappe.views.pageview.show = function (name) {
		const known =
			!name ||
			frappe.standard_pages[name] ||
			frappe.boot.page_info?.[name] ||
			frappe.pages[name] ||
			locals.Page?.[name];
		if (known) return show.call(this, name);
		frappe
			.xcall("onedesk.one.outside.kind_of", { name })
			.then((kind) => (kind ? frappe.show_not_permitted(name) : frappe.show_not_found(name)))
			.catch(() => frappe.show_not_found(name));
	};
}
