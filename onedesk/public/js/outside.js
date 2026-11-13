
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

// frappe's, erpnext's and hrms's record types and reports link to their own
// documentation, from an empty list, a list's and a form's menu, a report's
// and a field's help. One's help is OneAI, so the links go before anything
// that draws them reads them.
onedesk.outside.undocumented = (docs) => {
	for (const doc of docs || []) {
		if (!doc) continue;
		if (doc.doctype === "DocType") {
			delete doc.documentation;
			for (const field of doc.fields || []) delete field.documentation_url;
		} else if (doc.doctype === "Report") {
			delete doc.documentation_url;
		}
	}
};

(() => {
	if (frappe.model.sync.one_outside) return;
	const sync = frappe.model.sync;
	frappe.model.sync = function (r) {
		const docs = r && (r.docs || (r.docinfo ? null : r));
		onedesk.outside.undocumented(Array.isArray(docs) ? docs : [docs]);
		return sync.call(this, r);
	};
	frappe.model.sync.one_outside = true;
})();

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

if (frappe.boot.one_elsewhere && frappe.ui.Sidebar) {
	frappe.ui.Sidebar = class OneUserMenuSidebar extends frappe.ui.Sidebar {
		create_user_menu(args) {
			const Dropdown = frappe.ui.Dropdown;
			frappe.ui.Dropdown = class extends Dropdown {
				constructor(opts) {
					const options = opts.options;
					// frappe's Settings is AccountCenter here (desk.js, show_user_settings),
					// and its Manage Dock is Arrange Apps (arrange.js), which saves
					// through frappe's own save_user_dock.
					for (const one of options.flatMap((it) => it.options || [])) {
						if (one.name === "settings") Object.assign(one, { label: onedesk.names.of("account_center"), icon: "user" });
						if (one.name === "workspace-selector") Object.assign(one, { label: __("Arrange Apps"), icon: "arrow-up-down", onclick: () => onedesk.rail.arrange() });
					}
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
			// The bell's gear opens NotificationCenter where the reader is.
			onedesk.centers.open("notifications");
			return frappe.get_route();
		case "profile":
			return ["one", { center: "account", at: "profile" }];
		case "user":
			// A person is AccountCenter's: your own profile, or People.
			if (name && decodeURIComponent(name) === me) return ["one", { center: "account", at: "profile" }];
			return name && name !== "new" && !name.startsWith("new-")
				? ["one", { center: "account", at: "people", record: decodeURIComponent(name) }]
				: ["one", { center: "account", at: "people" }];
		case "file":
			return name ? null : ["onecloud"];
		case "todo":
		case "my-tasks":
			return name && doctype === "todo" ? null : ["List", "Task", "Kanban", "My Tasks"];
		case "print-settings":
			return ["one", { center: "settings", module: onedesk.names.of("one_studio"), at: "printing" }];
		case "print-format":
		case "letter-head":
			return name ? null : ["one", { center: "settings", module: onedesk.names.of("one_studio"), at: "printing" }];
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

// What One offers on its own (boot `one_shown`, one/outside.py `shown`): a
// search result that opens anything else is not offered.
onedesk.outside.shown = (kind, name) => {
	const said = frappe.boot.one_shown;
	if (!said || !name || !said[kind]) return true;
	onedesk.outside.held ||= Object.fromEntries(Object.entries(said).map(([one, names]) => [one, new Set(names)]));
	return onedesk.outside.held[kind].has(name);
};

onedesk.outside.ROUTED = { List: "DocType", Form: "DocType", Tree: "DocType", "query-report": "Report", "dashboard-view": "Dashboard" };

onedesk.outside.offered = (one) => {
	if (!one) return false;
	if (one.type === "New") return onedesk.outside.shown("DocType", one.match);
	const route = typeof one.route === "string" ? one.route.split("/") : one.route;
	if (!Array.isArray(route) || !route.length) return true;
	const [first, second] = route.map((part) => (typeof part === "string" ? decodeURIComponent(part) : part));
	if (onedesk.outside.ROUTED[first]) return onedesk.outside.shown(onedesk.outside.ROUTED[first], second);
	if (first === "Workspaces") return onedesk.outside.shown("Workspace", route.at(-1));
	if (frappe.boot.page_info?.[first]) return onedesk.outside.shown("Page", first);
	return true;
};

// Every source frappe's search bar draws from, each filtered; what is left
// out of it is `onedesk.outside.UNFILTERED`, and test_outside.py holds the two
// lists against frappe's own.
onedesk.outside.SOURCES = [
	"get_recent_pages",
	"get_frequent_links",
	"get_search_in_list",
	"get_creatables",
	"get_doctypes",
	"get_doctype_layouts",
	"get_reports",
	"get_pages",
	"get_workspaces",
	"get_dashboards",
];
onedesk.outside.UNFILTERED = { get_global_results: "frappe.utils.global_search.search, filtered on the server", get_executables: "functions, which open nothing" };

if (frappe.boot.one_shown && frappe.search?.utils && !frappe.search.utils.one_outside) {
	const utils = frappe.search.utils;
	utils.one_outside = true;
	for (const name of onedesk.outside.SOURCES) {
		const theirs = utils[name];
		if (typeof theirs !== "function") continue;
		utils[name] = function (...args) {
			const found = theirs.apply(this, args);
			return Array.isArray(found) ? found.filter(onedesk.outside.offered) : found;
		};
	}
	const pages = utils.get_pages;
	utils.get_pages = function (keywords) {
		return pages.call(this, keywords).filter((one) => !["Calendar", "Hub", "Inbox"].includes(one.type));
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
