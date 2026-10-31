// The library (one/news/library.json): feeds gathered by others, added with
// one click. Whoever publishes a feed owns it; the dialog says so.
frappe.listview_settings["News Source"] = {
	onload(listview) {
		if (!frappe.model.can_create("News Source")) return;
		listview.page.add_inner_button(__("From Library"), () => onedesk.news.library(listview));
	},
};

frappe.provide("onedesk.news");

onedesk.news.library = (listview) => {
	let asked = 0;
	const dialog = new frappe.ui.Dialog({
		title: __("From Library"),
		size: "large",
		fields: [
			{
				fieldtype: "HTML",
				fieldname: "owned",
				options: `<p class="text-muted small">${__(
					"These feeds belong to their publishers. You need each publisher's permission to show their content."
				)}</p>`,
			},
			{ fieldtype: "Section Break" },
			{ fieldtype: "Data", fieldname: "query", label: __("Search"), placeholder: __("Name or address") },
			{ fieldtype: "Column Break" },
			{ fieldtype: "Select", fieldname: "category", label: __("Category") },
			{ fieldtype: "Column Break" },
			{ fieldtype: "Select", fieldname: "country", label: __("Country") },
			{ fieldtype: "Section Break" },
			{ fieldtype: "HTML", fieldname: "found" },
		],
	});
	const $found = dialog.get_field("found").$wrapper;
	const draw = async () => {
		const mine = ++asked;
		const said = await frappe.xcall("onedesk.one.news.library.search", {
			query: dialog.get_value("query") || "",
			category: dialog.get_value("category") || "",
			country: dialog.get_value("country") || "",
		});
		if (mine !== asked) return;
		if (!dialog._filled) {
			dialog._filled = true;
			dialog.set_df_property("category", "options", ["", ...said.categories].map((one) => ({ value: one, label: one ? __(one) : "" })));
			dialog.set_df_property("country", "options", ["", ...said.countries]);
		}
		$found.empty();
		if (!said.feeds.length) return $found.html(`<p class="text-muted">${__("No feeds found.")}</p>`);
		const esc = frappe.utils.escape_html;
		for (const one of said.feeds) {
			const host = (one.url.match(/^https?:\/\/([^/]+)/) || [])[1] || "";
			const $row = $(`<div class="flex justify-between align-center" style="gap: var(--padding-md); padding: var(--padding-sm) 0; border-bottom: 1px solid var(--outline-gray-1)">
				<div style="min-width: 0"><div class="bold ellipsis">${esc(one.name)}</div>
				<div class="text-muted small ellipsis">${esc([__(one.category), one.country, host].filter(Boolean).join(" · "))}</div></div>
			</div>`).appendTo($found);
			const added = () => frappe.ui.button({ label: __("Added"), variant: "ghost", disabled: true });
			const add = one.added
				? added()
				: frappe.ui.button({
						label: __("Add"),
						variant: "outline",
						onclick: async () => {
							await frappe.xcall("onedesk.one.news.library.add", { url: one.url });
							add.replaceWith(added());
							listview.refresh();
						},
				  });
			$row.append(add);
		}
		if (said.more) $found.append(`<p class="text-muted small">${__("{0} more feeds match. Refine your search to see them.", [said.more])}</p>`);
	};
	const again = frappe.utils.debounce(draw, 300);
	dialog.fields_dict.query.$input.on("input", again);
	dialog.fields_dict.category.$input.on("change", again);
	dialog.fields_dict.country.$input.on("change", again);
	dialog.show();
	draw();
};
