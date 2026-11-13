// The launcher (one/rail.py): every app on the person's rail, those opened
// lately first, then the rest in their order with their folders, and typing
// finds apps and the pages inside them. The Apps button on the rail opens it;
// on a phone it is the Apps sheet (phone.js).
frappe.provide("onedesk.rail");

/** Draws the launcher into `$into`; `$find` is the box typed in, `opened`
 * opens an app and `left` follows a page. */
onedesk.rail.draw = ($into, { $find, opened, left }) => {
	const rail = onedesk.rail;
	const entries = rail.entries();
	const $body = $(`<div class="one-launcher"></div>`).appendTo($into);
	const tile = (entry) => {
		const $tile = $(`<button type="button" class="one-launcher-app">${frappe.utils.icon(entry.icon || "app-window", "lg")}<span class="one-launcher-name"></span></button>`);
		$tile.find(".one-launcher-name").text(entry.label);
		return $tile.on("click", () => opened(entry));
	};
	const group = (title, list) => {
		if (!list.length) return;
		const $group = $(`<section class="one-launcher-group"><h4 class="one-launcher-head"></h4><div class="one-launcher-grid"></div></section>`).appendTo($body);
		$group.find(".one-launcher-head").text(title);
		for (const entry of list) tile(entry).appendTo($group.find(".one-launcher-grid"));
	};
	const all = () => {
		$body.empty();
		const laid = rail.laid(entries);
		group(__("Recent"), rail.recent(entries).slice(0, 4));
		group(__("All Apps"), laid.filter((one) => one.entry).map((one) => one.entry));
		for (const one of laid) if (one.folder) group(one.folder.name, one.entries);
	};
	let pages = null;
	const found = (said) => {
		$body.empty();
		const words = said.toLowerCase().split(/\s+/).filter(Boolean);
		const apps = entries.filter((one) => words.every((word) => one.label.toLowerCase().includes(word)));
		group(__("Apps"), apps);
		pages ??= onedesk.interface.phone.pages();
		const rows = onedesk.interface.phone.found(pages, said).slice(0, 40);
		if (rows.length) {
			const $pages = $(`<section class="one-launcher-group"><h4 class="one-launcher-head"></h4><div class="one-launcher-pages" role="list"></div></section>`).appendTo($body);
			$pages.find(".one-launcher-head").text(__("Pages"));
			for (const one of rows) {
				$(`<a class="one-launcher-page" role="listitem"></a>`)
					.attr("href", one.route)
					.append(frappe.utils.icon(one.icon || "file", "sm"))
					.append($(`<span class="one-launcher-page-name"></span>`).text(one.label))
					.append($(`<span class="one-launcher-page-app"></span>`).text(one.app))
					.on("click", () => left && setTimeout(left))
					.appendTo($pages.find(".one-launcher-pages"));
			}
		}
		if (!apps.length && !rows.length) $body.append(frappe.ui.empty_state.html({ title: __("No apps or pages found"), css_class: "one-launcher-none" }));
		return apps[0];
	};
	let first = null;
	$find.on("input", () => {
		const said = ($find.val() || "").trim();
		first = said ? found(said) : (all(), null);
	});
	$find.on("keydown", (e) => e.key === "Enter" && first && opened(first));
	all();
	return $body;
};

onedesk.rail.launcher = () => {
	const dialog = new frappe.ui.Dialog({ title: __("Apps"), size: "large", fields: [{ fieldtype: "HTML", fieldname: "apps" }] });
	const $wrap = dialog.fields_dict.apps.$wrapper;
	const $find = $(`<input type="search" class="form-control one-launcher-find" autocomplete="off">`)
		.attr({ placeholder: __("Search Apps and Pages"), "aria-label": __("Search Apps and Pages") })
		.appendTo($wrap);
	onedesk.rail.draw($wrap, {
		$find,
		opened: (entry) => {
			dialog.hide();
			onedesk.rail.open(entry);
		},
		left: () => dialog.hide(),
	});
	const $foot = $(`<div class="one-launcher-foot"></div>`).appendTo($wrap);
	$(frappe.ui.button.html({ label: __("Arrange Apps"), icon: "arrow-up-down", variant: "ghost" }))
		.on("click", () => {
			dialog.hide();
			onedesk.rail.arrange();
		})
		.appendTo($foot);
	if (frappe.boot.one_administers) {
		$(frappe.ui.button.html({ label: onedesk.names.of("one_marketplace"), icon: "store", variant: "ghost" }))
			.on("click", () => {
				dialog.hide();
				frappe.set_route("marketplace");
			})
			.appendTo($foot);
	}
	dialog.show();
	setTimeout(() => $find.trigger("focus"), 150);
};
