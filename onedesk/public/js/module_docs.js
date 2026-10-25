// A module's What's New and Help, in frappe's settings dialog as its
// Settings are (one/versions.py): versions or help pages on the left, one
// at a time on the right, at one size and scrolling in place. Both are
// written in English only, for the people using the module.
frappe.provide("onedesk.whats_new");
frappe.provide("onedesk.help");

onedesk.module_docs = {
	ICONS: { major: "sparkles", minor: "plus", fix: "wrench" },
	KINDS: () => ({ major: __("Major"), minor: __("Update"), fix: __("Fix") }),

	// The words of a version or a page, laid out for reading.
	page($into, html) {
		return $(`<div class="one-doc"></div>`).html(html).appendTo($into);
	},

	dialog(title, tabs, opening) {
		const dialog = new frappe.ui.SettingsDialog({ title, default_tab: opening, tabs });
		dialog.$wrapper.addClass("one-docs-dialog");
		dialog.show();
		return dialog;
	},
};

onedesk.whats_new.open = async (module, version = null) => {
	const said = await frappe.xcall("onedesk.one.versions.whats_new", { module });
	const kinds = onedesk.module_docs.KINDS();
	const esc = frappe.utils.escape_html;
	const items = said.versions.map((one) => ({
		id: one.version,
		label: one.version,
		icon_html: one.new
			? `<span class="one-docs-new" aria-label="${esc(__("New"))}"></span>`
			: frappe.utils.icon(onedesk.module_docs.ICONS[one.kind] || "dot", "sm"),
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
					.on("click", () => {
						dialog.hide();
						onedesk.help.open(module, page.id);
					})
					.appendTo($more);
			}
		},
	}));
	const dialog = onedesk.module_docs.dialog(__("What's New in {0}", [module]), [{ group: module, items }], version || items[0]?.id);
	const ours = frappe.boot.one_versions && frappe.boot.one_versions[module];
	if (ours) ours.unseen = 0;
	$(document).trigger("one-version-seen", [module]);
	return dialog;
};

onedesk.help.open = async (module, page = null) => {
	const said = await frappe.xcall("onedesk.one.versions.help_pages", { module });
	const items = said.pages.map((one) => ({
		id: one.id,
		label: one.title,
		icon: one.icon,
		title: one.title,
		actions: [
			{
				label: __("What's New"),
				icon: "sparkles",
				click: () => {
					dialog.hide();
					onedesk.whats_new.open(module);
				},
			},
		],
		render(panel) {
			onedesk.module_docs.page(panel.body.empty(), one.html);
		},
	}));
	const dialog = onedesk.module_docs.dialog(__("{0} Help", [module]), [{ group: module, items }], page || items[0]?.id);
	return dialog;
};
