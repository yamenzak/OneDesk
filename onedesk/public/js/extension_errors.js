onedesk.record_tabs.register("errors", {
	async refresh(frm, field) {
		if (!field || frm.is_new()) return;
		const rows = await frappe.xcall("onedesk.one_studio.mend.listed", { extension: frm.doc.name });
		onedesk.record_tabs.count(frm, "errors", rows.length);
		const esc = frappe.utils.escape_html;
		field.$wrapper.empty();
		onedesk.shell.table(field.$wrapper, {
			note: __("Last 14 days"),
			rows,
			icon: "circle-check",
			empty: __("No errors"),
			columns: [
				{ label: __("When"), render: (one) => esc(frappe.datetime.str_to_user(one.on)) },
				{
					label: __("Record"),
					render: (one) =>
						one.record_name
							? `<a href="/desk/${frappe.router.slug(one.record_doctype)}/${encodeURIComponent(one.record_name)}">${esc(__(one.record_doctype))} ${esc(one.record_name)}</a>`
							: esc(__(one.record_doctype || "")),
				},
				{ label: __("Error"), render: (one) => esc(one.what || "") },
			],
		});
	},
});
